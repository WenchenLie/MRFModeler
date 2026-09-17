from __future__ import annotations

import ast
import importlib
import inspect
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from matplotlib import pyplot as plt

from MRFHelper import Frame, MCFTJointPanel, RCFrame, RigidJointPanel, __version__, from_json
from MRFHelper._script_builder import ScriptBuilder
from MRFHelper.rc_hinge import _aci_beta_1, calculate_rc_hinge
from MRFHelper.rc_joint import JointMaterialSpec
from MRFHelper.rc_mcft import _mcft_backbone
from MRFHelper.rc_sections import BarGroup, RCSection, load_rc_sections_csv

PROJECT_ROOT = Path(__file__).parents[1]
EXAMPLE_CSV = PROJECT_ROOT / "examples" / "RCMRF_2s_sections.csv"


def build_rc_frame(
    joint_panel_model: str = "Elastic",
    *,
    axial_load_ratio_amplification_factor: float = 1.25,
) -> RCFrame:
    frame = RCFrame("RC_Test", notes="RC regression model")
    geometry = frame.building_geometry
    geometry.story_height = [3600]
    geometry.bay_length = [6000]
    geometry.plane_dimensions = (12000, 6000)
    geometry.mf_number = 2
    geometry.exterior_column_tributary_area = (3000, 3000)
    geometry.interior_column_tributary_area = (6000, 3000)
    frame.finish_building_geometry()

    components = frame.structural_components
    components.load_sections_csv(EXAMPLE_CSV)
    components.set_beams(2, ["S250x500"])
    components.set_columns(1, ["S300x300", "S300x300"])
    frame.finish_structural_components()

    loads = frame.load_and_material
    loads.set_masses([[7.5, 7.5]], [2.0])
    loads.set_loads([[75000, 75000]], [20000])
    loads.set_axial_load_ratio_amplification_factor(axial_load_ratio_amplification_factor)
    loads.set_material(40, 30000, 460)
    frame.finish_load_and_material()

    frame.connection_and_boundary.set_base_support("Fixed")
    frame.connection_and_boundary.set_joint_panel_model(joint_panel_model)
    frame.finish_connection_and_boundary()
    frame.finalize()
    return frame


def test_version_is_fixed_at_2_6() -> None:
    assert __version__ == "2.6"
    assert Frame.version == "2.6"
    assert RCFrame.version == "2.6"


def test_bar_groups_and_section_geometry() -> None:
    group = BarGroup.parse("2D25+1D22", field="bars")
    assert group.count == 3
    assert group.area == pytest.approx(math.pi / 4 * (2 * 25**2 + 22**2))

    section = load_rc_sections_csv(EXAMPLE_CSV)["S250x500"]
    assert section.area == 250 * 500
    assert section.gross_inertia == pytest.approx(250 * 500**3 / 12)
    assert len(section.longitudinal_rows("top")) == 1
    assert section.top_bars.count == 2
    assert section.longitudinal_row_depths("top") == pytest.approx([45.0])
    assert RCSection.from_dict(section.to_dict()) == section


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ("section_name,b\nB1,500\n", "missing required columns"),
        (
            EXAMPLE_CSV.read_text(encoding="utf-8")
            + "S250x500,250,500,35,2D25,2D22,2D25,2D22,0,4D10,100,1\n",
            "Duplicate RC section names",
        ),
        (
            EXAMPLE_CSV.read_text(encoding="utf-8").replace("2D20", "twoD20", 1),
            "Invalid reinforcement specification",
        ),
    ],
)
def test_csv_validation(tmp_path: Path, contents: str, message: str) -> None:
    path = tmp_path / "sections.csv"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_rc_sections_csv(path)


def test_arbitrary_section_names_and_undefined_reference_validation() -> None:
    frame = RCFrame("BadSections")
    geometry = frame.building_geometry
    geometry.story_height = [3600]
    geometry.bay_length = [6000]
    geometry.plane_dimensions = (12000, 6000)
    geometry.mf_number = 2
    geometry.exterior_column_tributary_area = (3000, 3000)
    geometry.interior_column_tributary_area = (6000, 3000)
    frame.finish_building_geometry()
    frame.structural_components.load_sections_csv(EXAMPLE_CSV)
    frame.structural_components.set_beams(2, ["S300x300"])
    frame.structural_components.set_columns(1, ["S300x300", "Missing"])
    with pytest.raises(ValueError, match="Undefined RC column"):
        frame.finish_structural_components()


def test_asymmetric_hinge_and_series_stiffness() -> None:
    section = RCSection(
        name="B_asymmetric",
        b=400,
        h=600,
        cover=35,
        top_corner=BarGroup.parse("2D28", field="top_corner"),
        top_inner=BarGroup.parse("3D25", field="top_inner"),
        bottom_corner=BarGroup.parse("2D20", field="bottom_corner"),
        bottom_inner=BarGroup.parse("1D20", field="bottom_inner"),
        side_each=BarGroup(),
        stirrup=BarGroup.parse("4D10", field="stirrup"),
        stirrup_spacing=100,
    )
    section.validate()
    parameters = calculate_rc_hinge(
        section, fc=40, ec=30000, fy=460, es=200000, length=5500, ei_ratio=0.35
    )
    assert parameters.my_negative > parameters.my_positive
    assert parameters.theta_p_positive > parameters.theta_p_negative
    expected_lambda = (
        30.0
        * 0.3**parameters.axial_ratio
        * min(parameters.theta_p_positive, parameters.theta_p_negative)
    )
    assert parameters.lambda_imk == pytest.approx(expected_lambda)

    forward = parameters.material_arguments()
    reverse = parameters.material_arguments(reverse=True)
    assert forward[1] == pytest.approx(parameters.theta_p_positive)
    assert forward[7] == pytest.approx(parameters.theta_p_negative)
    assert reverse[1] == pytest.approx(parameters.theta_p_negative)
    assert reverse[7] == pytest.approx(parameters.theta_p_positive)

    target = 6 * 30000 * section.gross_inertia * 0.35 / 5500
    elastic = 6 * 30000 * section.gross_inertia * 0.35 * 11 / 10 / 5500
    combined = 1 / (1 / elastic + 1 / parameters.ke)
    assert combined == pytest.approx(target)


def test_rc_hinge_subroutine_recalculates_precomputed_imk_parameters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rc_hinge = importlib.import_module("subroutines.RCHinge")
    frame = build_rc_frame()
    parameters = frame.beam_hinges[2][0]
    material_calls = []
    element_calls = []
    monkeypatch.setattr(rc_hinge.ops, "uniaxialMaterial", lambda *args: material_calls.append(args))
    monkeypatch.setattr(rc_hinge.ops, "element", lambda *args: element_calls.append(args))

    rc_hinge.RCHinge(1, 2, 3, *parameters.subroutine_arguments())

    assert material_calls[0][:2] == ("IMKPeakOriented", 1)
    assert material_calls[0][2:] == pytest.approx(parameters.material_arguments())
    assert element_calls[0][:4] == ("zeroLength", 1, 2, 3)


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    [("subroutines.RCHinge", "RCHinge"), ("subroutines.RCJoint2D", "RCJoint2D")],
)
def test_rc_subroutines_have_documentation_and_type_annotations(
    module_name: str, function_name: str
) -> None:
    function = getattr(importlib.import_module(module_name), function_name)
    signature = inspect.signature(function)
    assert function.__doc__
    assert signature.return_annotation is not inspect.Signature.empty
    assert all(
        parameter.annotation is not inspect.Parameter.empty
        for parameter in signature.parameters.values()
    )
    tcl_source = (PROJECT_ROOT / "subroutines" / f"{function_name}.tcl").read_text(encoding="utf-8")
    assert "Arguments:" in tcl_source


def test_column_axial_ratio_uses_gross_section_area() -> None:
    frame = build_rc_frame()
    section = frame.structural_components.column_sections[1][0]
    expected = frame.load_and_material.column_axial_forces[1][0] / (
        section.area * frame.load_and_material.fc_expected
    )
    assert frame.column_hinges[1][0].axial_ratio == pytest.approx(expected)
    assert frame.load_and_material.ppy["1b"][0] == pytest.approx(expected)
    unrestricted_ei_ratio = 0.75 * pow(0.1 + expected, 0.8)
    expected_ei_ratio = min(0.6, max(0.2, unrestricted_ei_ratio))
    assert frame.load_and_material.beam_ei_ratio == pytest.approx(0.3)
    assert frame.load_and_material.column_ei_ratios[1][0] == pytest.approx(expected_ei_ratio)
    assert frame.column_hinges[1][0].ei_ratio == pytest.approx(expected_ei_ratio)
    ratio_calculator = frame.load_and_material._column_effective_stiffness_ratio
    assert ratio_calculator(0.0) == pytest.approx(0.2)
    assert ratio_calculator(10.0) == pytest.approx(0.6)
    assert not hasattr(frame.load_and_material, "set_effective_stiffness")


def test_rc_axial_load_ratio_amplification_factor() -> None:
    baseline = build_rc_frame(axial_load_ratio_amplification_factor=1.0)
    default = build_rc_frame()
    amplified = build_rc_frame(axial_load_ratio_amplification_factor=1.4)

    base_loads = baseline.load_and_material
    default_loads = default.load_and_material
    amplified_loads = amplified.load_and_material
    assert default_loads.axial_load_ratio_amplification_factor == pytest.approx(1.25)
    assert default_loads.ppy["1b"] == pytest.approx(
        [1.25 * ratio for ratio in base_loads.ppy["1b"]]
    )
    assert (
        amplified_loads.moment_frame_node_vertical_load
        == base_loads.moment_frame_node_vertical_load
    )
    assert amplified_loads.column_gravity_axial_forces == base_loads.column_gravity_axial_forces
    assert amplified_loads.column_axial_forces[1] == pytest.approx(
        [1.4 * force for force in base_loads.column_gravity_axial_forces[1]]
    )
    assert amplified_loads.ppy["1b"] == pytest.approx(
        [1.4 * ratio for ratio in base_loads.ppy["1b"]]
    )
    assert amplified.column_hinges[1][0].axial_ratio == pytest.approx(
        1.4 * baseline.column_hinges[1][0].axial_ratio
    )
    assert amplified.dict_info["load_and_material"][
        "axial_load_ratio_amplification_factor"
    ] == pytest.approx(1.4)

    with pytest.raises(ValueError, match="at least 1.0"):
        amplified_loads.set_axial_load_ratio_amplification_factor(0.99)


def test_aci_beta_1_uses_correct_mpa_limits_and_ksi_conversion() -> None:
    assert _aci_beta_1(20.0) == pytest.approx(0.85)
    assert _aci_beta_1(27.6) == pytest.approx(0.85)
    assert _aci_beta_1(40.0) == pytest.approx(1.05 - 0.05 * 40.0 / 6.9)
    assert _aci_beta_1(60.0) == pytest.approx(0.65)

    rc_hinge = importlib.import_module("subroutines.RCHinge")
    assert rc_hinge._aci_beta_1(4.0, 6.895) == pytest.approx(0.85)
    assert rc_hinge._aci_beta_1(6.0, 6.895) == pytest.approx(1.05 - 0.05 * (6.0 * 6.895) / 6.9)
    assert rc_hinge._aci_beta_1(8.0, 6.895) == pytest.approx(0.65)


def test_joint_panel_provider_protocol() -> None:
    frame = build_rc_frame()
    elastic = frame.joint_materials["2:1"]
    assert elastic.panel_model == "Elastic"
    assert elastic.arguments == (250.0, 30000.0, 0.2)
    assert JointMaterialSpec.from_dict(elastic.to_dict()) == elastic

    frame.connection_and_boundary.set_joint_panel_provider(RigidJointPanel(500))
    frame.finalize()
    rigid = frame.joint_materials["2:1"]
    assert rigid.panel_model == "Rigid"
    assert rigid.arguments[-1] == 500

    frame.connection_and_boundary.set_joint_panel_provider(MCFTJointPanel(0.02, 25, 1000))
    frame.finalize()
    mcft = frame.joint_materials["2:1"]
    assert mcft.panel_model == "Pinching4"
    assert len(mcft.arguments) == 16
    assert mcft.arguments[8:] == pytest.approx(tuple(-value for value in mcft.arguments[:8]))
    assert mcft.metadata["steel_hardening_ratio"] == 0.02
    assert mcft.metadata["maximum_aggregate_size"] == 25.0
    assert mcft.metadata["horizontal_axial_force"] == 1000.0
    assert mcft.metadata["calculation_stage"] == "model_generation"


def test_joint_panel_model_user_interface_and_validation() -> None:
    frame = build_rc_frame()
    frame.connection_and_boundary.set_joint_panel_model("Elastic")
    assert frame.connection_and_boundary.joint_panel_provider.configuration() == {"type": "Elastic"}
    frame.connection_and_boundary.set_joint_panel_model("Rigid", stiffness_factor=2000)
    assert frame.connection_and_boundary.joint_panel_provider.configuration()["type"] == "Rigid"
    frame.connection_and_boundary.set_joint_panel_model(
        "MCFT", steel_hardening_ratio=0.015, maximum_aggregate_size=25
    )
    assert frame.connection_and_boundary.joint_panel_provider.configuration()["type"] == "MCFT"
    with pytest.raises(ValueError, match="MCFT, Elastic, Rigid"):
        frame.connection_and_boundary.set_joint_panel_model("unknown")


def test_mcft_backbone_and_generated_pinching4_arguments(tmp_path: Path) -> None:
    frame = build_rc_frame("MCFT")
    specification = frame.joint_materials["2:1"]
    backbone = _mcft_backbone(
        300,
        500,
        250,
        68400,
        0,
        375,
        180,
        0.02,
        0.03,
        40,
        30000,
        460,
        460,
        200000,
        0.01,
        20,
    )
    assert len(backbone) == 4
    assert all(rotation > 0 and moment > 0 for rotation, moment in backbone)
    assert [point[0] for point in backbone] == sorted(point[0] for point in backbone)

    paths = frame.generate_scripts(tmp_path)
    tcl = paths["tcl"].read_text(encoding="utf-8")
    python_source = paths["python"].read_text(encoding="utf-8")
    joint_line = next(line for line in tcl.splitlines() if line.startswith("RCJoint2D "))
    first_call = joint_line.split(";")[0]
    call_tokens = first_call.split()
    assert call_tokens[10] == "Pinching4"
    assert len(call_tokens) == 33
    assert call_tokens[-6:] == [
        "$RCPinchingReloadDisp",
        "$RCPinchingReloadForce",
        "$RCPinchingUnloadForce",
        "$RCPinchingDegradation",
        "$RCPinchingEnergyCapacity",
        "$RCPinchingDamageType",
    ]
    assert '300.0, 500.0, "Pinching4"' in python_source
    assert "set RCPinchingReloadDisp 0.25;" in tcl
    assert 'RCPinchingDamageType = "energy"' in python_source
    assert tuple(float(value) for value in call_tokens[11:27]) == pytest.approx(
        specification.arguments
    )
    joint_block = tcl[tcl.index("# RC beam-column joints") : tcl.index("# RC beam IMK hinges")]
    assert re.search(r"\d[eE][+-]?\d", joint_block) is None


def test_mcft_backbone_documents_every_parameter() -> None:
    documentation = inspect.getdoc(_mcft_backbone)
    assert documentation is not None
    assert "Returns:" in documentation
    for parameter in inspect.signature(_mcft_backbone).parameters:
        assert f"{parameter}:" in documentation


def test_tcl_rcjoint2d_uses_precomputed_pinching4_parameters(tmp_path: Path) -> None:
    opensas = Path("F:/Projects/OpenSAS")
    executable = opensas / "OS_terminal" / "OpenSees351.exe"
    if not executable.is_file():
        pytest.skip("OpenSAS OpenSees 3.5.1 is not available")

    frame = build_rc_frame("MCFT")
    arguments = frame.joint_materials["2:1"].arguments
    argument_text = " ".join(f"{value:.12f}" for value in arguments)
    python_subroutine = (PROJECT_ROOT / "subroutines" / "RCJoint2D.py").read_text(encoding="utf-8")
    tcl_subroutine = (PROJECT_ROOT / "subroutines" / "RCJoint2D.tcl").read_text(encoding="utf-8")
    assert "_mcft_backbone" not in python_subroutine
    assert "MCFTBackbone" not in tcl_subroutine
    assert "sqrt(200" not in tcl_subroutine
    script = tmp_path / "mcft_joint.tcl"
    script.write_text(
        "wipe\n"
        "model BasicBuilder -ndm 2 -ndf 3\n"
        f"source {{{(PROJECT_ROOT / 'subroutines' / 'RCJoint2D.tcl').as_posix()}}}\n"
        f"RCJoint2D 11020100 11020101 11020104 11020103 11020102 0 0 300 500 "
        f"Pinching4 {argument_text} 0.25 0.25 0.0 0.0 10.0 energy\n"
        'puts "PINCHING4_ELEMENT [getEleTags]"\n',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(executable), str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    assert "PINCHING4_ELEMENT 11020100" in output


def test_tcl_rchinge_accepts_integer_looking_material_arguments(tmp_path: Path) -> None:
    """Guard against Tcl integer division reducing RC yield moments to zero."""
    opensas = Path("F:/Projects/OpenSAS")
    executable = opensas / "OS_terminal" / "OpenSees351.exe"
    if not executable.is_file():
        pytest.skip("OpenSAS OpenSees 3.5.1 is not available")

    script = tmp_path / "rc_hinge_integer_arguments.tcl"
    script.write_text(
        "wipe\n"
        f"source {{{(PROJECT_ROOT / 'subroutines' / 'RCHinge.tcl').as_posix()}}}\n"
        "set yieldMoment [_RCYieldMoment 250 500 70.091119947 57.5 "
        "1742.013126375 2370.331657125 0 0 40 30000 460 200000 1] "
        "\n"
        'puts "RC_YIELD $yieldMoment"\n'
        "model BasicBuilder -ndm 2 -ndf 3\n"
        "node 1 0 0\n"
        "node 2 0 0\n"
        "fix 1 1 1 1\n"
        "fix 2 1 1 0\n"
        "uniaxialMaterial Elastic 99 1.e12\n"
        "RCHinge 1 1 2 40 30000 460 200000 250 500 70.091119947 57.5 "
        "100 0.018962653257 0.013936105011 0 0.012566370614 1 0 1 5650 0.3 10 0\n"
        "timeSeries Linear 1\n"
        "pattern Plain 1 1 {load 2 0 0 1000000}\n"
        "constraints Transformation\n"
        "numberer RCM\n"
        "system BandGeneral\n"
        "test NormDispIncr 1.e-12 50\n"
        "algorithm Newton\n"
        "integrator LoadControl 0.1\n"
        "analysis Static\n"
        "set status [analyze 10]\n"
        "set tangent [lindex [eleResponse 1 material 3 tangent] 0]\n"
        'puts "RC_HINGE_STATUS $status $tangent"\n',
        encoding="utf-8",
    )
    completed = subprocess.run(
        [str(executable), str(script)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    yield_match = re.search(r"RC_YIELD\s+([0-9.eE+-]+)", output)
    assert yield_match is not None, output
    assert float(yield_match.group(1)) == pytest.approx(311481297.42, rel=1.0e-8)
    status_match = re.search(r"RC_HINGE_STATUS\s+(-?\d+)\s+([0-9.eE+-]+)", output)
    assert status_match is not None, output
    assert int(status_match.group(1)) == 0
    assert float(status_match.group(2)) > 1.0e10


def test_two_story_two_bay_tcl_gravity_converges_with_integer_arguments(tmp_path: Path) -> None:
    """Reproduce the OpenSAS RC_2S2B gravity stage with OpenSees 3.5.1."""
    opensas = Path("F:/Projects/OpenSAS")
    executable = opensas / "OS_terminal" / "OpenSees351.exe"
    if not executable.is_file():
        pytest.skip("OpenSAS OpenSees 3.5.1 is not available")

    frame = from_json(PROJECT_ROOT / "examples" / "RCMRF_2s.json")
    generated = frame.generate_scripts(tmp_path / "generated")
    model = generated["tcl"].read_text(encoding="utf-8")
    replacements = {
        r'set MainFolder ".+";  # \$\$\$': (
            f'set MainFolder "{(tmp_path / "results").as_posix()}";  # $$$'
        ),
        r'set SubFolder ".+";  # \$\$\$': 'set SubFolder "gravity";  # $$$',
        r'set subroutines ".+";  # \$\$\$': (
            f'set subroutines "{(PROJECT_ROOT / "subroutines").as_posix()}";  # $$$'
        ),
    }
    for pattern, replacement in replacements.items():
        model, count = re.subn(pattern, lambda _match, value=replacement: value, model)
        assert count == 1
    gravity_tail = "loadConst -time 0.0;"
    model, count = (
        model.replace(
            gravity_tail,
            gravity_tail + '\nputs "RC_GRAVITY_STATUS $gravityStatus";\nexit;',
        ),
        model.count(gravity_tail),
    )
    assert count == 1
    diagnostic_model = tmp_path / "RC_2S2B_gravity.tcl"
    diagnostic_model.write_text(model, encoding="utf-8")

    completed = subprocess.run(
        [str(executable), str(diagnostic_model)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, output
    assert "RC_GRAVITY_STATUS 0" in output
    assert "failed to converge" not in output


def test_joint2d_is_drawn_as_rectangle() -> None:
    figure, axes = plt.subplots()
    builder = ScriptBuilder(axes)
    builder.node(0, 0, node_id=100)
    builder.node(0, -2, node_id=101)
    builder.node(3, 0, node_id=104)
    builder.node(0, 2, node_id=103)
    builder.node(-3, 0, node_id=102)
    builder.joint2d(100, 101, 104, 103, 102, element_id=100)
    panel_line = axes.lines[-1]
    assert list(panel_line.get_xdata()) == [-3, 3, 3, -3, -3]
    assert list(panel_line.get_ydata()) == [-2, -2, 2, 2, -2]
    plt.close(figure)


def test_json_round_trip_requires_external_section_csv(tmp_path: Path) -> None:
    frame = build_rc_frame()
    model_path = tmp_path / "rc.json"
    model_path.write_text(json.dumps(frame.dict_info), encoding="utf-8")

    loaded = from_json(model_path)
    assert isinstance(loaded, RCFrame)
    assert loaded.structural_components.section_library["S250x500"].b == 250
    assert loaded.structural_components.section_path == EXAMPLE_CSV.resolve()
    assert loaded.joint_materials["2:1"] == frame.joint_materials["2:1"]
    data = json.loads(model_path.read_text(encoding="utf-8"))
    components = data["structural_components"]
    assert "model_schema_version" not in data
    assert "section_csv" in components
    assert "effective_stiffness" not in data["load_and_material"]
    assert data["load_and_material"]["axial_load_ratio_amplification_factor"] == 1.25
    assert "dead_load" not in data["load_and_material"]
    assert data["load_and_material"]["nodal_mass"]["moment_frame"][0] == [7.5, 7.5]
    assert data["load_and_material"]["nodal_vertical_load"]["leaning_column"][0] == 20000
    assert "section_library" not in components
    assert "DerivedHinges" not in data
    assert "resolved_joint_materials" not in data["connection_and_boundary"]
    round_trip_paths = loaded.generate_scripts(tmp_path / "round_trip")
    compile(
        round_trip_paths["python"].read_text(encoding="utf-8"),
        str(round_trip_paths["python"]),
        "exec",
    )

    data["structural_components"]["section_csv"] = "missing_sections.csv"
    model_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="RC section CSV file not found"):
        from_json(model_path)


def test_two_story_two_bay_json_example_layout(tmp_path: Path) -> None:
    frame = from_json(PROJECT_ROOT / "examples" / "RCMRF_2s.json")
    assert isinstance(frame, RCFrame)
    assert (frame.N, frame.bays) == (2, 2)
    assert frame.load_and_material.moment_frame_node_mass[2] == pytest.approx(
        [7.4847, 14.9694, 7.4847]
    )
    assert frame.load_and_material.moment_frame_node_mass[3] == pytest.approx(
        [6.9337, 13.8673, 6.9337]
    )
    assert frame.structural_components.section_path == EXAMPLE_CSV.resolve()
    tcl = frame.generate_scripts(tmp_path)["tcl"].read_text(encoding="utf-8")

    def block(start: str, end: str) -> list[str]:
        contents = tcl[tcl.index(start) + len(start) : tcl.index(end)]
        return [line for line in contents.splitlines() if line.strip()]

    column_rows = block("# RC column elastic elements", "# RC beam elastic elements")
    beam_rows = block("# RC beam elastic elements", "# RC beam-column joints")
    joint_rows = [
        row
        for row in block("# RC beam-column joints", "# RC beam IMK hinges")
        if row.lstrip().startswith("RCJoint2D")
    ]
    beam_hinge_rows = block("# RC beam IMK hinges", "# RC column IMK hinges")
    column_hinge_rows = block("# RC column IMK hinges", "# Rigid links to leaning column")
    assert len(column_rows) == frame.N
    assert all(row.count("element elasticBeamColumn") == frame.axis for row in column_rows)
    assert len(beam_rows) == frame.N
    assert all(row.count("element elasticBeamColumn") == frame.bays for row in beam_rows)
    assert len(beam_hinge_rows) == frame.N
    assert all(row.count("RCHinge") == 2 * frame.bays for row in beam_hinge_rows)
    assert len(joint_rows) == frame.N
    assert all(row.count("RCJoint2D") == frame.axis for row in joint_rows)
    assert len(column_hinge_rows) == 2 * frame.N
    assert all(row.count("RCHinge") == frame.axis for row in column_hinge_rows)
    assert "[expr ($n+1)/$n*0.3*" in tcl
    for ratios in frame.load_and_material.column_ei_ratios.values():
        for ratio in ratios:
            formatted = f"{ratio:.12f}".rstrip("0").rstrip(".")
            assert f"[expr ($n+1)/$n*{formatted}*" in tcl


OPEN_SAS_PATTERNS = (
    r"(set maxRunTime )[0-9.]+(;  # \$\$\$)",
    r'(set analysis_type ")[THPOCP]+(";  # \$\$\$)',
    r'(set MainFolder ").+(";  # \$\$\$)',
    r'(set GMname ").+(";  # \$\$\$)',
    r'(set SubFolder ").+(";  # \$\$\$)',
    r"(set GMdt )[0-9.]+(;  # \$\$\$)",
    r"(set GMpoints )\d+(;  # \$\$\$)",
    r"(set GMduration )[0-9.]+(;  # \$\$\$)",
    r"(set FVduration )[0-9.]+(;  # \$\$\$)",
    r"(set EqSF )[0-9.]+(;  # \$\$\$)",
    r'(set GMFile ").+(";  # \$\$\$)',
    r'(set subroutines ").+(";  # \$\$\$)',
    r'(set temp ").+(";  # \$\$\$)',
    r"set ShowAnimation [01];  # \$\$\$",
    r"set MPCO [01];  # \$\$\$",
    r"(set maxRoofDrift )[01.]+(;  # \$\$\$)",
    r"(set CollapseDrift )[0-9.]+(;  # \$\$\$)",
    r"(set RDR_path \[list )[0-9. -]+(\];  # \$\$\$)",
)


def test_generated_rc_scripts_and_opensas_contract(tmp_path: Path) -> None:
    frame = build_rc_frame()
    paths = frame.generate_scripts(tmp_path)
    assert set(paths) == {"tcl", "python", "json", "image", "html", "information"}
    assert all(path.exists() for path in paths.values())
    html_source = paths["html"].read_text(encoding="utf-8")
    assert "S250x500" in html_source
    assert "模型正向屈服弯矩范围" in html_source
    assert "截面宽度 b" in html_source
    assert "连接与边界输入" in html_source
    assert "节点质量" in html_source
    assert "节点竖向荷载" in html_source
    assert "限于 0.2–0.6 的 0.75 × (0.1 + PPy)^0.8" in html_source
    assert "柱等效刚度计算结果" in html_source
    assert "<pre>" not in html_source
    assert "<svg" in html_source

    tcl = paths["tcl"].read_text(encoding="utf-8")
    python_source = paths["python"].read_text(encoding="utf-8")
    compile(python_source, str(paths["python"]), "exec")
    column_elements_start = tcl.index("# RC column elastic elements")
    beam_elements_start = tcl.index("# RC beam elastic elements")
    joints_start = tcl.index("# RC beam-column joints (nodes, material, and Joint2D element)")
    beam_hinges_start = tcl.index("# RC beam IMK hinges")
    column_hinges_start = tcl.index("# RC column IMK hinges")
    joint_call = "RCJoint2D 11020100 11020101 11020104 11020103 11020102"
    assert (
        column_elements_start
        < beam_elements_start
        < joints_start
        < tcl.index(joint_call, joints_start)
        < beam_hinges_start
        < column_hinges_start
    )
    assert tcl.count(joint_call) == 1
    python_column_elements_start = python_source.index("# RC column elastic elements")
    python_beam_elements_start = python_source.index("# RC beam elastic elements")
    python_joints_start = python_source.index(
        "# RC beam-column joints (nodes, material, and Joint2D element)"
    )
    python_beam_hinges_start = python_source.index("# RC beam IMK hinges")
    python_column_hinges_start = python_source.index("# RC column IMK hinges")
    python_joint_call = "RCJoint2D(11020100, 11020101, 11020104, 11020103, 11020102"
    assert (
        python_column_elements_start
        < python_beam_elements_start
        < python_joints_start
        < python_source.index(python_joint_call, python_joints_start)
        < python_beam_hinges_start
        < python_column_hinges_start
    )
    assert python_source.count(python_joint_call) == 1
    assert "RCHinge 10020109" in tcl
    assert "RCHinge 10010107" in tcl
    assert "RCHinge 10020109 11020104 10020104 40.0 30000.0 460.0 200000.0" in tcl
    element_definitions = tcl[
        tcl.index("# RC column elastic elements") : tcl.index("# Rigid links to leaning column")
    ]
    python_element_definitions = python_source[
        python_source.index("# RC column elastic elements") : python_source.index(
            "# Rigid links to leaning column"
        )
    ]
    assert re.search(r"\d[eE][+-]?\d", element_definitions) is None
    assert re.search(r"\d[eE][+-]?\d", python_element_definitions) is None
    assert "\n\n# Leaning column\n" in tcl
    assert "\n\n    # Leaning column\n" in python_source
    assert "# Moment frame mass" in tcl and "# Leaning column mass" in tcl
    assert "# Moment frame mass" in python_source and "# Leaning column mass" in python_source
    mass_block = tcl[tcl.index("# Moment frame mass") : tcl.index("# Leaning column mass")]
    mass_rows = [line for line in mass_block.splitlines() if line.startswith("mass ")]
    assert len(mass_rows) == frame.N
    assert all(row.count("mass ") == frame.axis for row in mass_rows)
    information_source = paths["information"].read_text(encoding="utf-8")
    for title in (
        "1. Building Geometry",
        "2. Structural Components",
        "3. Load and Material",
        "4. Connection and Boundary Condition",
    ):
        assert title in tcl
        assert title in information_source
    for omitted in (
        "RC section CSV",
        "effective-stiffness ratio",
        "Member self-weight is included",
        "Constraint handler",
    ):
        assert omitted not in information_source
    assert "source RCHinge.tcl" in tcl
    assert "RCBeamHinge" not in tcl and "RCColumnHinge" not in tcl
    assert "from subroutines.RCHinge import RCHinge" in python_source
    assert "element zeroLength" not in tcl
    assert 'ops.element("zeroLength"' not in python_source
    assert "material 5 stressStrain" in tcl
    assert "mass 11020100 " in tcl and "1.e-9 1.e-9 1.e-9" in tcl
    assert "# Rigid diaphragm on ordinary beam-end nodes" in tcl
    assert "equalDOF 10020104 10020205 1;" in tcl
    assert "equalDOF 11020100" not in tcl
    assert "ops.equalDOF(10020104, 10020205, 1)" in python_source
    assert "ops.equalDOF(11020100" not in python_source
    assert "load 10020104 $F2 0.0 0.0;" in tcl
    assert "constraints Transformation;" in tcl
    assert "constraints Plain" not in tcl
    assert "set gravityStatus [analyze 10];" in tcl
    assert "if {$gravityStatus != 0}" in tcl
    assert "Continuing with the last committed state." in tcl
    assert "gravity_status = ops.analyze(10)" in python_source
    assert "if gravity_status != 0:" in python_source
    assert "source TimeHistorySolver.tcl;" in tcl
    assert "source TimeHistorySolver_RC.tcl;" not in tcl
    assert "from subroutines.TimeHistorySolver import TimeHistorySolver" in python_source
    assert "TimeHistorySolver_RC" not in python_source
    assert all(len(re.findall(pattern, tcl)) == 1 for pattern in OPEN_SAS_PATTERNS)
    for name in ("TimeHistorySolver", "PushoverAnalysis", "CyclicPushover"):
        for suffix in ("py", "tcl"):
            helper_source = (PROJECT_ROOT / "subroutines" / f"{name}.{suffix}").read_text(
                encoding="utf-8"
            )
            assert "Transformation" in helper_source
            assert "constraints Plain" not in helper_source

    module = ast.parse(python_source)
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef))
    assert function.name == "run_openseespy"
    assert [argument.arg for argument in function.args.args] == [
        "maxRunTime",
        "analysis_type",
        "ShowAnimation",
        "MPCO",
        "MainFolder",
        "GMname",
        "SubFolder",
        "GMdt",
        "GMpoints",
        "GMduration",
        "FVduration",
        "EqSF",
        "GMFile",
        "maxRoofDrift",
        "CollapseDrift",
        "RDR_path",
    ]

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        frame.generate_scripts(tmp_path, overwrite=False)


def test_generated_openseespy_model_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if importlib.util.find_spec("openseespy") is None:
        pytest.skip("Install the `test` extra to run the OpenSeesPy integration test")

    generated = tmp_path / "generated"
    paths = build_rc_frame().generate_scripts(generated)
    mirror = tmp_path / "python_mirror"
    subroutines = mirror / "subroutines"
    shutil.copytree(PROJECT_ROOT / "subroutines", subroutines)
    monkeypatch.syspath_prepend(mirror)

    specification = importlib.util.spec_from_file_location("generated_rc_model", paths["python"])
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    result = module.run_openseespy(
        30.0,
        "PO",
        False,
        False,
        tmp_path / "python_results",
        "smoke",
        Path("po"),
        0.01,
        3,
        0.02,
        0.02,
        0.001,
        tmp_path / "none.th",
        0.0001,
        0.1,
        [0.0],
    )
    assert result[0] == 1


@pytest.mark.parametrize("analysis_type", ["TH", "PO", "CP"])
def test_opensees_351_rc_analysis_smoke(tmp_path: Path, analysis_type: str) -> None:
    opensas = Path("F:/Projects/OpenSAS")
    executable = opensas / "OS_terminal" / "OpenSees351.exe"
    if not executable.is_file():
        pytest.skip("OpenSAS OpenSees 3.5.1 is not available")

    output = tmp_path / "generated"
    paths = build_rc_frame().generate_scripts(output)
    mirror = tmp_path / "OpenSAS_mirror"
    subroutines = mirror / "subroutines"
    shutil.copytree(opensas / "subroutines", subroutines)
    shutil.copytree(PROJECT_ROOT / "subroutines", subroutines, dirs_exist_ok=True)

    model = paths["tcl"].read_text(encoding="utf-8")
    subfolder = analysis_type.lower()
    replacements = {
        r'set analysis_type "TH";  # \$\$\$': (f'set analysis_type "{analysis_type}";  # $$$'),
        r"set ShowAnimation 1;  # \$\$\$": "set ShowAnimation 0;  # $$$",
        r'set MainFolder ".+";  # \$\$\$': (
            f'set MainFolder "{(mirror / "results").as_posix()}";  # $$$'
        ),
        r'set SubFolder ".+";  # \$\$\$': f'set SubFolder "{subfolder}";  # $$$',
        r'set subroutines ".+";  # \$\$\$': (f'set subroutines "{subroutines.as_posix()}";  # $$$'),
        r'set temp ".+";  # \$\$\$': f'set temp "{mirror.as_posix()}";  # $$$',
    }
    if analysis_type == "PO":
        replacements[r"set maxRoofDrift [01.]+;  # \$\$\$"] = "set maxRoofDrift 0.0001;  # $$$"
    elif analysis_type == "CP":
        replacements[r"set RDR_path \[list [0-9. -]+\];  # \$\$\$"] = (
            "set RDR_path [list 0 0.0002 -0.0002 0];  # $$$"
        )
    else:
        ground_motion = mirror / "tiny.th"
        ground_motion.write_text("0\n0.1\n0\n", encoding="ascii")
        replacements.update(
            {
                r"set GMdt [0-9.]+;  # \$\$\$": "set GMdt 0.01;  # $$$",
                r"set GMpoints \d+;  # \$\$\$": "set GMpoints 3;  # $$$",
                r"set GMduration [0-9.]+;  # \$\$\$": "set GMduration 0.02;  # $$$",
                r"set FVduration [0-9.]+;  # \$\$\$": "set FVduration 0.02;  # $$$",
                r"set EqSF [0-9.]+;  # \$\$\$": "set EqSF 0.001;  # $$$",
                r'set GMFile ".+";  # \$\$\$': (f'set GMFile "{ground_motion.as_posix()}";  # $$$'),
            }
        )
    for pattern, replacement in replacements.items():
        model, count = re.subn(pattern, lambda _match, value=replacement: value, model)
        assert count == 1
    model_path = mirror / f"RC_Test_{analysis_type}.tcl"
    model_path.write_text(model, encoding="utf-8")

    completed = subprocess.run(
        [str(executable), str(model_path)],
        cwd=mirror,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    log = completed.stdout + completed.stderr
    assert completed.returncode == 0, log
    assert "PlainHandler" not in log
    assert "incompatible matrices" not in log
    assert "load to add of incorrect size" not in log
    assert (mirror / "results" / subfolder / "Status.dat").read_text().strip() == "1"
    panel_data = mirror / "results" / subfolder / "PZ2_1.out"
    first_row = next(line for line in panel_data.read_text().splitlines() if line.strip())
    assert len(first_row.split()) == 2
