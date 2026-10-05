from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from MRFHelper import Frame, RCFrame


@pytest.mark.parametrize("frame_type", [Frame, RCFrame], ids=["steel", "rc"])
@pytest.mark.parametrize("stories", [1, 2, 3])
@pytest.mark.parametrize("bays", [1, 2])
def test_leaning_column_uses_grid_nodes_and_end_releases(
    tmp_path: Path, frame_type: type[Frame], stories: int, bays: int
) -> None:
    """Both writers must emit the same P-delta topology in Tcl and Python."""
    frame = frame_type("LeaningColumn")
    frame.building_geometry.story_height = [3600] * stories
    frame.building_geometry.bay_length = [6000] * bays
    frame.finish_building_geometry()
    components = frame.structural_components
    if frame_type is RCFrame:
        components.load_sections_csv(
            Path(__file__).parents[1] / "examples" / "RCMRF_2s_sections.csv"
        )
        beam, column = "S250x500", "S300x300"
    else:
        beam, column = "W21x73", "W24x103"
    for story in range(1, stories + 1):
        components.set_beams(story + 1, [beam] * bays)
        components.set_columns(story, [column] * (bays + 1))
    frame.finish_structural_components()
    frame.load_and_material.set_masses(
        [[7.5] * (bays + 1) for _ in range(stories)], [2.0] * stories
    )
    frame.load_and_material.set_loads(
        [[75000] * (bays + 1) for _ in range(stories)], [20000] * stories
    )
    if frame_type is RCFrame:
        frame.load_and_material.set_material(40, 30000, 460)
    else:
        frame.load_and_material.set_material(206000, 300, 400)
    frame.finish_load_and_material()
    frame.connection_and_boundary.set_base_support("Fixed")
    frame.finish_connection_and_boundary()
    frame.finalize()

    paths = frame.generate_scripts(tmp_path)
    tcl = paths["tcl"].read_text(encoding="utf-8")
    python_source = paths["python"].read_text(encoding="utf-8")
    compile(python_source, str(paths["python"]), "exec")
    calls = [node for node in ast.walk(ast.parse(python_source)) if isinstance(node, ast.Call)]

    axis = bays + 2
    grid_nodes = [int(f"10{floor:02d}{axis:02d}00") for floor in range(1, stories + 2)]

    def on_leaning_axis(tag: int) -> bool:
        return tag // 1_000_000 == 10 and tag // 100 % 100 == axis

    tcl_nodes = [int(tag) for tag in re.findall(r"(?:^|;)\s*node (\d+) ", tcl, re.MULTILINE)]
    python_nodes = [
        call.args[0].value
        for call in calls
        if isinstance(call.func, ast.Attribute) and call.func.attr == "node"
    ]
    # The removed coincident end nodes must not reappear on the leaning axis.
    assert [tag for tag in tcl_nodes if on_leaning_axis(tag)] == grid_nodes
    assert sorted(tag for tag in python_nodes if on_leaning_axis(tag)) == grid_nodes
    assert "geomTransf PDelta 2;" in tcl
    assert 'ops.geomTransf("PDelta", 2)' in python_source
    assert f"fix {grid_nodes[0]} 1 1 0;" in tcl
    assert f"ops.fix({grid_nodes[0]}, 1, 1, 0)" in python_source

    expected_tcl = []
    expected_python = []
    for story, (inode, jnode) in enumerate(zip(grid_nodes, grid_nodes[1:]), start=1):
        tag = int(f"10{story:02d}{axis:02d}01")
        release_tcl = " -release 2" if story < stories else ""
        expected_tcl.append(
            f"element elasticBeamColumn {tag} {inode} {jnode} $A_Stiff $E $I_Stiff 2{release_tcl}"
        )
        expected_python.append(
            ["elasticBeamColumn", tag, inode, jnode, "A_Stiff", "E", "I_Stiff", 2]
            + (["-release", 2] if story < stories else [])
        )
    tcl_elements = re.findall(r"\belement elasticBeamColumn (\d+) ([^;]+);", tcl)
    assert [
        f"element elasticBeamColumn {tag} {arguments}"
        for tag, arguments in tcl_elements
        if on_leaning_axis(int(tag))
    ] == expected_tcl
    assert [
        [arg.id if isinstance(arg, ast.Name) else ast.literal_eval(arg) for arg in call.args]
        for call in calls
        if isinstance(call.func, ast.Attribute)
        and call.func.attr == "element"
        and isinstance(call.args[1], ast.Constant)
        and on_leaning_axis(call.args[1].value)
        and call.args[0].value == "elasticBeamColumn"
    ] == expected_python

    # Mass and gravity loads stay on the grid nodes, without leaning-column springs.
    for command, expected in (("mass", [2.0, 1.0e-9, 1.0e-9]), ("load", [0.0, -20000.0, 0.0])):
        tcl_values = {
            int(tag): [float(value) for value in arguments.split()]
            for tag, arguments in re.findall(
                rf"(?:^|;)\s*{command} (\d+) ([^;]+);", tcl, re.MULTILINE
            )
            if on_leaning_axis(int(tag))
        }
        python_values = {
            call.args[0].value: [ast.literal_eval(arg) for arg in call.args[1:]]
            for call in calls
            if isinstance(call.func, ast.Attribute)
            and call.func.attr == command
            and isinstance(call.args[0], ast.Constant)
            and on_leaning_axis(call.args[0].value)
        }
        assert set(tcl_values) == set(python_values) == set(grid_nodes[1:])
        for node in grid_nodes[1:]:
            assert tcl_values[node] == pytest.approx(expected)
            assert python_values[node] == pytest.approx(expected)
    for floor in range(2, stories + 2):
        for position in (7, 8):
            spring_tag = int(f"10{floor:02d}{axis:02d}{position:02d}")
            assert re.search(rf"Spring_(?:Rigid|Zero) {spring_tag}\b", tcl) is None
            assert not any(
                isinstance(call.func, ast.Name)
                and call.func.id in {"Spring_Rigid", "Spring_Zero"}
                and call.args[0].value == spring_tag
                for call in calls
            )
