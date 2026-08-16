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
    geometry.plane_dimensions = (12000, 6000)
    geometry.mf_number = 2
    geometry.exterior_column_tributary_area = (3000, 3000)
    geometry.interior_column_tributary_area = (6000, 3000)
    frame.finish_building_geometry()

    frame.structural_components.set_beams(2, ["W21x73"])
    frame.structural_components.set_columns(1, ["W24x103", "W24x103"])
    frame.finish_structural_components()

    loads = frame.load_and_material
    loads.set_dead_load([2], [0.004])
    loads.set_live_load([2], [0.002])
    loads.set_cladding_load([1], [0.001])
    loads.set_weight_combination_coefficients({"Dead": 1.0, "Live": 0.0, "Cladding": 2.0})
    loads.set_mass_combination_coefficients({"Dead": 0.0, "Live": 0.0, "Cladding": 2.0})
    loads.set_material(206000, 300, 400)
    frame.finish_load_and_material()

    frame.connection_and_boundary.set_base_support("Fixed")
    frame.connection_and_boundary.set_beam_column_connection("Full")
    frame.connection_and_boundary.set_panel_zone_deformation(True)
    frame.finish_connection_and_boundary()
    if finish:
        frame.finalize()
    return frame


def test_load_coefficients_are_multiplied() -> None:
    frame = build_one_story_frame()
    loads = frame.load_and_material

    assert loads.F_node[2] == pytest.approx([45000.0, 45000.0])
    assert loads.mass_node[2] == pytest.approx([9000 / loads.g, 9000 / loads.g])
    assert loads.F_grav[2] == pytest.approx(108000.0)


def test_columns_use_column_yield_strength() -> None:
    frame = build_one_story_frame()
    expected = WSection("W24x103", 400).My
    beam_strength_value = WSection("W24x103", 300).My

    actual = frame.structural_components.column_properties[1][0][7]
    assert actual == pytest.approx(expected)
    assert actual != pytest.approx(beam_strength_value)


def test_legacy_names_remain_compatible() -> None:
    from MRFHelper.MRFhelper import Frame as LegacyFrame

    frame = build_one_story_frame()
    assert LegacyFrame is Frame
    assert frame.BuildingGeometry is frame.building_geometry
    assert frame.StructuralComponents is frame.structural_components
    assert frame.LoadAndMaterial is frame.load_and_material
    assert frame.ConnectionAndBoundary is frame.connection_and_boundary
    assert frame.UserComment is frame.user_comment

    frame.building_geometry.MF_number = 3
    assert frame.building_geometry.mf_number == 3
    frame.structural_components.set_RBS_length(125)
    assert frame.structural_components.rbs_length_all == 125


def test_missing_column_story_is_reported() -> None:
    frame = Frame("MissingColumn")
    frame.building_geometry.story_height = [3000, 3000]
    frame.building_geometry.bay_length = [6000]
    frame.building_geometry.plane_dimensions = (12000, 6000)
    frame.building_geometry.mf_number = 2
    frame.building_geometry.exterior_column_tributary_area = (3000, 3000)
    frame.building_geometry.interior_column_tributary_area = (6000, 3000)
    frame.finish_building_geometry()
    frame.structural_components.set_beams(2, ["W21x73"])
    frame.structural_components.set_beams(3, ["W21x73"])
    frame.structural_components.set_columns(1, ["W24x103", "W24x103"])

    with pytest.raises(ValueError, match="Columns on stories"):
        frame.finish_structural_components()


@pytest.mark.parametrize("cladding_key", ["clading_load", "cladding_load"])
def test_json_loader_accepts_legacy_and_corrected_keys(tmp_path: Path, cladding_key: str) -> None:
    frame = build_one_story_frame()
    data = frame.dict_info
    legacy_load = data["LoadAndMaterial"].pop("clading_load")
    data["LoadAndMaterial"][cladding_key] = legacy_load
    data["ConnectionAndBoundary"]["soil_constraint"] = [1]
    data["ConnectionAndBoundary"]["rigid_diaphragm"] = False
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(data), encoding="utf-8")

    loaded = from_json(model_file)

    assert loaded.notes == "regression model"
    assert loaded.load_and_material.cladding_load == {1: 0.001}
    assert loaded.connection_and_boundary.soil_constraint == [1]
    assert loaded.connection_and_boundary.rigid_diaphragm is False
    assert loaded.connection_and_boundary.rigid_disphragm is False


def test_generation_is_headless_and_returns_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = build_one_story_frame()

    def fake_savefig(_figure, path, **_kwargs):
        Path(path).write_bytes(b"test image")

    monkeypatch.setattr("matplotlib.figure.Figure.savefig", fake_savefig)
    paths = frame.generate_scripts(tmp_path)

    assert set(paths) == {"tcl", "python", "json", "image", "information"}
    assert all(path.exists() for path in paths.values())
    python_source = paths["python"].read_text(encoding="utf-8")
    tcl_source = paths["tcl"].read_text(encoding="utf-8")
    compile(python_source, str(paths["python"]), "exec")
    assert "mass_Ids = [11020104, 11020204, 10020300]" in python_source
    assert "from subroutines.BeamHinge import BeamHinge" in python_source
    assert "source BeamHinge.tcl" in tcl_source

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        frame.generate_scripts(tmp_path, overwrite=False)


def test_refactored_module_filenames_are_snake_case() -> None:
    project_root = Path(__file__).parents[1]
    directories = ("MRFHelper", "examples")
    source_files = [
        path
        for directory in directories
        for path in (project_root / directory).iterdir()
        if path.suffix in {".py", ".tcl"}
    ]

    assert all(path.stem == path.stem.lower() for path in source_files)


def test_legacy_keyword_arguments_remain_compatible() -> None:
    from MRFHelper.func import check_string

    frame = build_one_story_frame()

    frame.load_and_material.set_material(E=200_000, fy_beam=300, fy_column=400)
    assert frame.load_and_material.elastic_modulus == 200_000
    frame.load_and_material._calculate_PPy(frame, PPy_scale=1.5)
    assert frame.load_and_material.ppy_scale == 1.5
    frame.structural_components.set_RBS_length(RBS_length=126)
    assert frame.structural_components.rbs_length_all == 126
    check_string(None, isNone=True)

    commands = frame.user_comment
    commands.add_material(matType="Elastic", Id=1)
    commands.add_node(Id=1, x=0, y=0)
    commands.add_element(eleType="elasticBeamColumn", Id=1, inode=1, jnode=2)

    assert commands.additional_commands_py[-3:] == [
        {"mat": 'ops.uniaxialMaterial("Elastic", 1)'},
        {"node": "ops.node(1, 0, 0)"},
        {"ele": 'ops.element("elasticBeamColumn", 1, 1, 2)'},
    ]
