from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .building_geometry import BuildingGeometry
from .connection_and_boundary import ConnectionAndBoundary
from .load_and_material import LoadAndMaterial
from .structural_components import StructuralComponents
from .user_command import UserCommand
from .write_info import write_info_to_dict, write_info_to_tcl
from .write_script import ScriptWriter

VERSION = __version__


class Frame:
    version = VERSION

    def __init__(self, frame_name: str, notes: str | None = None):
        """Use this class to define structural parameters of steel moment resisting frame (MRF)
        and write tcl script for analysis using OpenSees. Make sure all the units are [N, mm, t].

        Args:
            frame_name (str): Give a name for the considered frame
            notes (str, optional): Optional notes
        """
        if not isinstance(frame_name, str) or not frame_name.isidentifier():
            raise ValueError(f"Illegal frame name: {frame_name}")
        self.frame_name = frame_name
        self.notes = notes
        self.building_geometry = BuildingGeometry()
        self.structural_components: StructuralComponents | None = None
        self.load_and_material: LoadAndMaterial | None = None
        self.connection_and_boundary: ConnectionAndBoundary | None = None
        self.user_comment: UserCommand | None = None

    # Compatibility properties for model files written against versions <= 2.5.
    @property
    def BuildingGeometry(self) -> BuildingGeometry:
        return self.building_geometry

    @BuildingGeometry.setter
    def BuildingGeometry(self, value: BuildingGeometry) -> None:
        self.building_geometry = value

    @property
    def StructuralComponents(self) -> StructuralComponents | None:
        return self.structural_components

    @StructuralComponents.setter
    def StructuralComponents(self, value: StructuralComponents | None) -> None:
        self.structural_components = value

    @property
    def LoadAndMaterial(self) -> LoadAndMaterial | None:
        return self.load_and_material

    @LoadAndMaterial.setter
    def LoadAndMaterial(self, value: LoadAndMaterial | None) -> None:
        self.load_and_material = value

    @property
    def ConnectionAndBoundary(self) -> ConnectionAndBoundary | None:
        return self.connection_and_boundary

    @ConnectionAndBoundary.setter
    def ConnectionAndBoundary(self, value: ConnectionAndBoundary | None) -> None:
        self.connection_and_boundary = value

    @property
    def UserComment(self) -> UserCommand | None:
        return self.user_comment

    @UserComment.setter
    def UserComment(self, value: UserCommand | None) -> None:
        self.user_comment = value

    def finish_building_geometry(self) -> None:
        """Validate the building geometry and initialize component inputs."""
        self.building_geometry._finish()
        self.N = self.building_geometry.N  # number of stories
        self.bays = self.building_geometry.bays  # number of bays
        self.axis = self.building_geometry.axis  # number of axes
        self.structural_components = StructuralComponents(self)

    def finish_structural_components(self) -> None:
        """Validate member definitions and initialize load inputs."""
        self.structural_components._finish()
        self.load_and_material = LoadAndMaterial(self)

    def finish_load_and_material(self) -> None:
        """Validate loads/materials and initialize boundary inputs."""
        self.load_and_material._finished()
        self.connection_and_boundary = ConnectionAndBoundary(self)

    def finish_connection_and_boundary(self) -> None:
        """Validate boundary inputs and initialize output settings."""
        self.connection_and_boundary._finished()
        self.recorders = {
            "Reactions": True,
            "Drift": True,
            "FloorAccel": True,
            "FloorVel": True,
            "FloorDisp": True,
            "ColumnForce": True,
            "ColumnHinge": True,
            "BeamHinge": True,
            "PanelZone": True,
        }
        self.user_comment = UserCommand()

    def finalize(self) -> None:
        """Calculate derived section, panel-zone, load, and mass values."""
        self.structural_components._get_section_properties(self)
        self.structural_components._get_panel_zone_thickness()
        self.load_and_material._calculate_load(self)
        self.load_and_material._calculate_ppy(self)
        self.dict_info = write_info_to_dict(self)

    def generate_scripts(
        self, output_directory, *, overwrite: bool = True, show_plot: bool = False
    ):
        """Generate Tcl, OpenSeesPy, JSON, model-image, and information files.

        Args:
            output_directory: Directory receiving generated artifacts.
            overwrite: Whether existing artifacts may be replaced.
            show_plot: Whether to display the model figure interactively.
        """
        self.output_path = Path(output_directory)
        self.output_path.mkdir(parents=True, exist_ok=True)
        if not overwrite:
            names = (
                f"{self.frame_name}.tcl",
                f"{self.frame_name}.py",
                f"{self.frame_name}.json",
                f"{self.frame_name}.png",
                f"Model Information_{self.frame_name}.txt",
            )
            conflicts = [
                self.output_path / name for name in names if (self.output_path / name).exists()
            ]
            if conflicts:
                formatted = ", ".join(str(path) for path in conflicts)
                raise FileExistsError(f"Refusing to overwrite existing files: {formatted}")
        self.building_info = write_info_to_tcl(self)
        # Keep the misspelled attribute used by releases through 2.5.
        self.builiding_info = self.building_info
        writer = ScriptWriter(self, overwrite=True, show_plot=show_plot)
        return writer.generated_files

    # Compatibility methods for model scripts written against versions <= 2.5.
    def step1_finished(self):
        return self.finish_building_geometry()

    def step2_finished(self):
        return self.finish_structural_components()

    def step3_finished(self):
        return self.finish_load_and_material()

    def step4_finished(self):
        return self.finish_connection_and_boundary()

    def all_steps_finished(self):
        return self.finalize()

    def generate_tcl_script(self, dir_, *, overwrite: bool = True, show_plot: bool = False):
        return self.generate_scripts(dir_, overwrite=overwrite, show_plot=show_plot)


def _required(mapping: dict, key: str, section: str):
    try:
        return mapping[key]
    except KeyError as error:
        raise ValueError(f"Missing `{section}.{key}` in model JSON") from error


def from_json(file: str | Path) -> Frame:
    """Get an available model from json file

    Args:
        file (str | Path): file path

    Returns:
        Frame: Object of `Frame`
    """
    path = Path(file)
    if not path.is_file():
        raise FileNotFoundError(f"Model JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        dict_info = json.load(stream)

    frame = Frame(_required(dict_info, "name", "root"), dict_info.get("notes"))
    # Step 1
    geometry = _required(dict_info, "BuildingGeometry", "root")
    frame.building_geometry.story_height = _required(geometry, "story_height", "BuildingGeometry")
    frame.building_geometry.bay_length = _required(geometry, "bay_length", "BuildingGeometry")
    frame.building_geometry.plane_dimensions = tuple(
        _required(geometry, "plane_dimensions", "BuildingGeometry")
    )
    frame.building_geometry.mf_number = _required(geometry, "MF_number", "BuildingGeometry")
    frame.building_geometry.exterior_column_tributary_area = tuple(
        _required(geometry, "exterior_column_tributary_area", "BuildingGeometry")
    )
    frame.building_geometry.interior_column_tributary_area = tuple(
        _required(geometry, "interior_column_tributary_area", "BuildingGeometry")
    )
    frame.finish_building_geometry()
    # Step 2
    components = _required(dict_info, "StructuralComponents", "root")
    for floor, sections in _required(components, "beams", "StructuralComponents").items():
        frame.structural_components.set_beams(int(floor), sections)
    for story, sections in _required(components, "columns", "StructuralComponents").items():
        frame.structural_components.set_columns(int(story), sections)
    for floor, thickness in components.get("set_doubler_plate", {}).items():
        frame.structural_components.set_doubler_plate(int(floor), thickness)
    frame.structural_components.set_column_splice(*components.get("column_splice", []))
    frame.structural_components.set_beam_splice(*components.get("beam_splice", []))
    if components.get("RBS_length") is not None:
        frame.structural_components.set_rbs_length(components["RBS_length"])
    frame.finish_structural_components()
    # Step 3
    load_data = _required(dict_info, "LoadAndMaterial", "root")
    dead_load = _required(load_data, "dead_load", "LoadAndMaterial")
    live_load = _required(load_data, "live_load", "LoadAndMaterial")
    # ``clading_load`` is retained in saved v2.5 files; accept the corrected key too.
    cladding_load = load_data.get("cladding_load", load_data.get("clading_load"))
    if cladding_load is None:
        raise ValueError("Missing `LoadAndMaterial.cladding_load` in model JSON")
    frame.load_and_material.set_dead_load([int(key) for key in dead_load], list(dead_load.values()))
    frame.load_and_material.set_live_load([int(key) for key in live_load], list(live_load.values()))
    frame.load_and_material.set_cladding_load(
        [int(key) for key in cladding_load], list(cladding_load.values())
    )
    frame.load_and_material.set_weight_combination_coefficients(
        _required(load_data, "weight_combination_coefficients", "LoadAndMaterial")
    )
    frame.load_and_material.set_mass_combination_coefficients(
        _required(load_data, "mass_combination_coefficients", "LoadAndMaterial")
    )
    material = _required(load_data, "material", "LoadAndMaterial")
    frame.load_and_material.set_material(
        _required(material, "E", "LoadAndMaterial.material"),
        _required(material, "fy_beam", "LoadAndMaterial.material"),
        _required(material, "fy_column", "LoadAndMaterial.material"),
        material.get("miu", 0.3),
    )
    frame.finish_load_and_material()
    # Step 4
    boundary = _required(dict_info, "ConnectionAndBoundary", "root")
    frame.connection_and_boundary.set_base_support(boundary.get("base_support", "Fixed"))
    rbs_parameters = boundary.get("RBS_parameters", (0.625, 0.75, 0.25))
    frame.connection_and_boundary.set_beam_column_connection(
        boundary.get("beam_column_connection", "Full"), *rbs_parameters
    )
    frame.connection_and_boundary.set_panel_zone_deformation(
        boundary.get("panel_zone_deformation", True)
    )
    soil_constraints = boundary.get("soil_constraint", [])
    if isinstance(soil_constraints, int):
        soil_constraints = [soil_constraints]
    for floor in soil_constraints:
        frame.connection_and_boundary.set_soil_constraint(floor)
    frame.connection_and_boundary.rigid_diaphragm = boundary.get(
        "rigid_diaphragm", boundary.get("rigid_disphragm", True)
    )
    frame.finish_connection_and_boundary()
    # finish
    frame.finalize()
    frame.dict_info["References"] = dict_info.get("References")
    return frame
