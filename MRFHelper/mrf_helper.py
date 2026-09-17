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
        """Calculate derived section, panel-zone, and column axial-ratio values."""
        self.structural_components._get_section_properties(self)
        self.structural_components._get_panel_zone_thickness()
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
                f"{self.frame_name}.html",
                f"Model Information_{self.frame_name}.txt",
            )
            conflicts = [
                self.output_path / name for name in names if (self.output_path / name).exists()
            ]
            if conflicts:
                formatted = ", ".join(str(path) for path in conflicts)
                raise FileExistsError(f"Refusing to overwrite existing files: {formatted}")
        self.building_info = write_info_to_tcl(self)
        writer = ScriptWriter(self, overwrite=True, show_plot=show_plot)
        return writer.generated_files


def _required(mapping: dict, key: str, section: str):
    try:
        return mapping[key]
    except KeyError as error:
        raise ValueError(f"Missing `{section}.{key}` in model JSON") from error


def _set_direct_nodal_inputs(frame: Frame, load_data: dict) -> None:
    """Load direct floor-node mass and vertical-load definitions from JSON."""
    mass = _required(load_data, "nodal_mass", "load_and_material")
    mass_frame = _required(mass, "moment_frame", "load_and_material.nodal_mass")
    mass_leaning = _required(mass, "leaning_column", "load_and_material.nodal_mass")
    frame.load_and_material.set_masses(mass_frame, mass_leaning)

    vertical = _required(load_data, "nodal_vertical_load", "load_and_material")
    vertical_frame = _required(vertical, "moment_frame", "load_and_material.nodal_vertical_load")
    vertical_leaning = _required(
        vertical, "leaning_column", "load_and_material.nodal_vertical_load"
    )
    frame.load_and_material.set_loads(vertical_frame, vertical_leaning)


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

    if dict_info.get("frame_type") == "reinforced_concrete":
        from .rc_frame import rc_frame_from_dict

        return rc_frame_from_dict(dict_info, base_directory=path.parent)

    frame = Frame(_required(dict_info, "name", "root"), dict_info.get("notes"))
    # Step 1
    geometry = _required(dict_info, "building_geometry", "root")
    frame.building_geometry.story_height = _required(geometry, "story_height", "building_geometry")
    frame.building_geometry.bay_length = _required(geometry, "bay_length", "building_geometry")
    frame.finish_building_geometry()
    # Step 2
    components = _required(dict_info, "structural_components", "root")
    for floor, sections in _required(components, "beams", "structural_components").items():
        frame.structural_components.set_beams(int(floor), sections)
    for story, sections in _required(components, "columns", "structural_components").items():
        frame.structural_components.set_columns(int(story), sections)
    for floor, thickness in components.get("doubler_plate", {}).items():
        frame.structural_components.set_doubler_plate(int(floor), thickness)
    frame.structural_components.set_column_splice(*components.get("column_splice", []))
    frame.structural_components.set_beam_splice(*components.get("beam_splice", []))
    if components.get("rbs_length") is not None:
        frame.structural_components.set_rbs_length(components["rbs_length"])
    frame.finish_structural_components()
    # Step 3
    load_data = _required(dict_info, "load_and_material", "root")
    _set_direct_nodal_inputs(frame, load_data)
    frame.load_and_material.set_axial_load_ratio_amplification_factor(
        load_data.get("axial_load_ratio_amplification_factor", 1.25)
    )
    material = _required(load_data, "material", "load_and_material")
    frame.load_and_material.set_material(
        _required(material, "elastic_modulus", "load_and_material.material"),
        _required(material, "fy_beam", "load_and_material.material"),
        _required(material, "fy_column", "load_and_material.material"),
        material.get("poisson_ratio", 0.3),
    )
    frame.finish_load_and_material()
    # Step 4
    boundary = _required(dict_info, "connection_and_boundary", "root")
    frame.connection_and_boundary.set_base_support(boundary.get("base_support", "Fixed"))
    rbs_parameters = boundary.get("rbs_parameters", (0.625, 0.75, 0.25))
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
    frame.connection_and_boundary.rigid_diaphragm = boundary.get("rigid_diaphragm", True)
    frame.finish_connection_and_boundary()
    # finish
    frame.finalize()
    frame.dict_info["references"] = dict_info.get("references")
    return frame
