from __future__ import annotations

import json
from pathlib import Path

import pytest
from wsection import WSection

from MRFHelper import Frame, from_json


def build_one_story_frame(*, finish: bool = True) -> Frame:
    """Build a small model through the unchanged four-step public API."""
    frame = Frame("OneStory", notes="regression model")
    geometry = frame.building_geometry
    geometry.story_height = [3000]
    geometry.bay_length = [6000]
    frame.finish_building_geometry()

    frame.structural_components.set_beams(2, ["W21x73"])
    frame.structural_components.set_columns(1, ["W24x103", "W24x103"])
    frame.finish_structural_components()

    loads = frame.load_and_material
    loads.set_masses([[9000 / 9800, 9000 / 9800]], [2.5])
    loads.set_loads([[45000, 45000]], [108000])
    loads.set_material(206000, 300, 400)
    frame.finish_load_and_material()

    frame.connection_and_boundary.set_base_support("Fixed")
    frame.connection_and_boundary.set_beam_column_connection("Full")
    frame.connection_and_boundary.set_panel_zone_deformation(True)
    frame.finish_connection_and_boundary()
    if finish:
        frame.finalize()
    return frame


def test_direct_nodal_inputs_are_preserved() -> None:
    frame = build_one_story_frame()
    loads = frame.load_and_material

    assert loads.moment_frame_node_vertical_load[2] == pytest.approx([45000.0, 45000.0])
    assert loads.moment_frame_node_mass[2] == pytest.approx([9000 / 9800, 9000 / 9800])
    assert loads.leaning_column_node_vertical_load[2] == pytest.approx(108000.0)
    assert loads.leaning_column_node_mass[2] == pytest.approx(2.5)


@pytest.mark.parametrize(
    ("method", "args", "message"),
    [
        ("set_masses", ([], []), "should be 1"),
        ("set_masses", ([[1]], [0]), "should be 2"),
        ("set_loads", ([[1, -1]], [0]), "non-negative"),
        ("set_loads", ([[1, float("inf")]], [0]), "finite"),
    ],
)
def test_direct_nodal_input_validation(method: str, args: tuple, message: str) -> None:
    frame = Frame("InputValidation")
    geometry = frame.building_geometry
    geometry.story_height = [3000]
    geometry.bay_length = [6000]
    frame.finish_building_geometry()
    frame.structural_components.set_beams(2, ["W21x73"])
    frame.structural_components.set_columns(1, ["W24x103", "W24x103"])
    frame.finish_structural_components()

    with pytest.raises(ValueError, match=message):
        getattr(frame.load_and_material, method)(*args)


def test_old_distributed_load_api_is_removed() -> None:
    loads = build_one_story_frame().load_and_material
    for name in (
        "set_dead_load",
        "set_live_load",
        "set_cladding_load",
        "set_weight_combination_coefficients",
        "set_mass_combination_coefficients",
        "set_nodal_masses",
        "set_nodal_vertical_loads",
    ):
        assert not hasattr(loads, name)


def test_columns_use_column_yield_strength() -> None:
    frame = build_one_story_frame()
    expected = WSection("W24x103", 400).My
    beam_strength_value = WSection("W24x103", 300).My

    actual = frame.structural_components.column_properties[1][0][7]
    assert actual == pytest.approx(expected)
    assert actual != pytest.approx(beam_strength_value)


def test_public_api_uses_current_names_only() -> None:
    frame = build_one_story_frame()
    assert not hasattr(frame, "BuildingGeometry")
    assert not hasattr(frame, "StructuralComponents")
    assert not hasattr(frame, "LoadAndMaterial")
    assert not hasattr(frame, "ConnectionAndBoundary")
    assert not hasattr(frame, "UserComment")
    for redundant_name in (
        "plane_dimensions",
        "mf_number",
        "exterior_column_tributary_area",
        "interior_column_tributary_area",
    ):
        assert not hasattr(frame.building_geometry, redundant_name)
    frame.structural_components.set_rbs_length(125)
    assert frame.structural_components.rbs_length_all == 125


def test_missing_column_story_is_reported() -> None:
    frame = Frame("MissingColumn")
    frame.building_geometry.story_height = [3000, 3000]
    frame.building_geometry.bay_length = [6000]
    frame.finish_building_geometry()
    frame.structural_components.set_beams(2, ["W21x73"])
    frame.structural_components.set_beams(3, ["W21x73"])
    frame.structural_components.set_columns(1, ["W24x103", "W24x103"])

    with pytest.raises(ValueError, match="Columns on stories"):
        frame.finish_structural_components()


def test_json_loader_uses_current_keys(tmp_path: Path) -> None:
    frame = build_one_story_frame()
    data = frame.dict_info
    data["connection_and_boundary"]["soil_constraint"] = [1]
    data["connection_and_boundary"]["rigid_diaphragm"] = False
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(data), encoding="utf-8")

    loaded = from_json(model_file)

    assert loaded.notes == "regression model"
    assert (
        loaded.load_and_material.moment_frame_node_mass
        == frame.load_and_material.moment_frame_node_mass
    )
    assert (
        loaded.load_and_material.leaning_column_node_vertical_load
        == frame.load_and_material.leaning_column_node_vertical_load
    )
    assert loaded.load_and_material.axial_load_ratio_amplification_factor == pytest.approx(1.25)
    assert loaded.connection_and_boundary.soil_constraint == [1]
    assert loaded.connection_and_boundary.rigid_diaphragm is False


def test_generation_is_headless_and_returns_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = build_one_story_frame()

    def fake_savefig(_figure, path, **_kwargs):
        Path(path).write_bytes(b"test image")

    monkeypatch.setattr("matplotlib.figure.Figure.savefig", fake_savefig)
    paths = frame.generate_scripts(tmp_path)

    assert set(paths) == {"tcl", "python", "json", "image", "html", "information"}
    assert all(path.exists() for path in paths.values())
    python_source = paths["python"].read_text(encoding="utf-8")
    tcl_source = paths["tcl"].read_text(encoding="utf-8")
    compile(python_source, str(paths["python"]), "exec")
    assert "mass_Ids = [11020104, 11020204, 10020300]" in python_source
    assert "from subroutines.BeamHinge import BeamHinge" in python_source
    assert "source BeamHinge.tcl" in tcl_source
    assert 'ops.constraints("Transformation")' in python_source
    assert "constraints Transformation;" in tcl_source
    assert "constraints Plain" not in tcl_source
    assert "set gravityStatus [analyze 10];" in tcl_source
    assert "if {$gravityStatus != 0}" in tcl_source
    assert "gravity_status = ops.analyze(10)" in python_source
    assert "if gravity_status != 0:" in python_source
    assert " 1.25 1;" in tcl_source
    html_source = paths["html"].read_text(encoding="utf-8")
    assert "W21x73" in html_source
    assert "屈服弯矩 My" in html_source
    assert "翼缘宽度 bf" in html_source
    assert "连接与边界输入" in html_source
    assert "节点质量" in html_source
    assert "节点竖向荷载" in html_source
    assert "柱轴压比放大系数" in html_source
    assert "<pre>" not in html_source
    assert "<svg" in html_source
    json_source = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert set(json_source["building_geometry"]) == {"//", "story_height", "bay_length"}
    load_data = json_source["load_and_material"]
    assert set(load_data) == {
        "//",
        "nodal_mass",
        "nodal_vertical_load",
        "axial_load_ratio_amplification_factor",
        "material",
    }
    assert load_data["nodal_mass"]["moment_frame"][0] == pytest.approx([9000 / 9800, 9000 / 9800])
    assert load_data["nodal_vertical_load"]["leaning_column"][0] == 108000
    assert json_source["load_and_material"]["axial_load_ratio_amplification_factor"] == 1.25

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        frame.generate_scripts(tmp_path, overwrite=False)


def test_package_module_filenames_are_snake_case() -> None:
    project_root = Path(__file__).parents[1]
    source_files = [
        path for path in (project_root / "MRFHelper").iterdir() if path.suffix in {".py", ".tcl"}
    ]

    assert all(path.stem == path.stem.lower() for path in source_files)


def test_current_keyword_arguments() -> None:
    from MRFHelper.validation import check_string

    frame = build_one_story_frame()

    frame.load_and_material.set_material(elastic_modulus=200_000, fy_beam=300, fy_column=400)
    assert frame.load_and_material.elastic_modulus == 200_000
    frame.load_and_material.set_axial_load_ratio_amplification_factor(1.5)
    frame.load_and_material._calculate_ppy(frame)
    assert frame.load_and_material.axial_load_ratio_amplification_factor == 1.5
    frame.structural_components.set_rbs_length(rbs_length=126)
    assert frame.structural_components.rbs_length_all == 126
    check_string(None, is_none=True)

    commands = frame.user_comment
    commands.add_material(mat_type="Elastic", material_id=1)
    commands.add_node(node_id=1, x=0, y=0)
    commands.add_element(element_type="elasticBeamColumn", element_id=1, i_node=1, j_node=2)

    assert commands.additional_commands_py[-3:] == [
        {"mat": 'ops.uniaxialMaterial("Elastic", 1)'},
        {"node": "ops.node(1, 0, 0)"},
        {"ele": 'ops.element("elasticBeamColumn", 1, 1, 2)'},
    ]


def test_tcl_structural_subroutines_use_explicit_float_division() -> None:
    project_root = Path(__file__).parents[1]
    rc_hinge = (project_root / "subroutines" / "RCHinge.tcl").read_text(encoding="utf-8")
    old_rc_hinge = (project_root / "subroutines" / "ModSpring_IMK_RC.tcl").read_text(
        encoding="utf-8"
    )
    column_hinge = (project_root / "subroutines" / "ColumnHinge.tcl").read_text(encoding="utf-8")
    panel_zone = (project_root / "subroutines" / "PanelZone.tcl").read_text(encoding="utf-8")

    assert "double($Es)/$Ec" in rc_hinge
    assert "double($fy)/$Es" in rc_hinge
    assert "double($Es)/$Ec" in old_rc_hinge
    assert "double($fy)/$Es" in old_rc_hinge
    assert "9.0/8.0" in column_hinge
    assert "double($E) / (2.0" in panel_zone
