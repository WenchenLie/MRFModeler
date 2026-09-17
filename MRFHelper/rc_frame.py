"""Public reinforced-concrete frame workflow."""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd

from .mrf_helper import Frame, _required, _set_direct_nodal_inputs
from .rc_components import (
    RCConnectionAndBoundary,
    RCLoadAndMaterial,
    RCStructuralComponents,
)
from .rc_hinge import calculate_rc_hinge
from .rc_joint import JointMaterialSpec, JointPanelContext
from .user_command import UserCommand


class RCFrame(Frame):
    """Parameterized two-dimensional reinforced-concrete moment frame."""

    # OpenSAS parses this value as its model-script contract version.
    version = "2.6.1"
    frame_type = "reinforced_concrete"

    def finish_building_geometry(self) -> None:
        self.building_geometry._finish()
        self.N = self.building_geometry.N
        self.bays = self.building_geometry.bays
        self.axis = self.building_geometry.axis
        self.structural_components = RCStructuralComponents(self)

    def finish_structural_components(self) -> None:
        self.structural_components._finish()
        self.load_and_material = RCLoadAndMaterial(self)

    def finish_load_and_material(self) -> None:
        self.load_and_material._finished()
        self.connection_and_boundary = RCConnectionAndBoundary(self)

    def finish_connection_and_boundary(self) -> None:
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
        self.structural_components._get_section_properties(self)
        self.load_and_material._calculate_ppy(self)
        self._resolve_hinges()
        self._resolve_joint_materials()
        self.dict_info = write_rc_info_to_dict(self)

    def _resolve_hinges(self) -> None:
        loads = self.load_and_material
        components = self.structural_components
        self.beam_hinges = {}
        for floor in range(2, self.N + 2):
            self.beam_hinges[floor] = []
            for bay, section in enumerate(components.beam_sections[floor], start=1):
                left_column = components.column_sections[floor - 1][bay - 1]
                right_column = components.column_sections[floor - 1][bay]
                length = self.building_geometry.bay_length[bay - 1]
                length -= (left_column.h + right_column.h) / 2
                parameters = calculate_rc_hinge(
                    section,
                    fc=loads.fc_expected,
                    ec=loads.elastic_modulus,
                    fy=loads.fy_expected,
                    es=loads.es,
                    length=length,
                    ei_ratio=loads.beam_ei_ratio,
                )
                self.beam_hinges[floor].append(parameters)

        self.column_hinges = {}
        for story in range(1, self.N + 1):
            self.column_hinges[story] = []
            floor_bottom, floor_top = story, story + 1
            for axis, section in enumerate(components.column_sections[story], start=1):
                lower_beam_depth = self._joint_beam_depth(floor_bottom, axis) if story > 1 else 0
                upper_beam_depth = self._joint_beam_depth(floor_top, axis)
                length = self.building_geometry.story_height[story - 1]
                length -= (lower_beam_depth + upper_beam_depth) / 2
                parameters = calculate_rc_hinge(
                    section,
                    fc=loads.fc_expected,
                    ec=loads.elastic_modulus,
                    fy=loads.fy_expected,
                    es=loads.es,
                    length=length,
                    ei_ratio=loads.column_ei_ratios[story][axis - 1],
                    axial_force=loads.column_axial_forces[story][axis - 1],
                )
                self.column_hinges[story].append(parameters)

    def _joint_beam_depth(self, floor: int, axis: int) -> float:
        sections = self.structural_components.beam_sections[floor]
        if axis == 1:
            return sections[0].h
        if axis == self.axis:
            return sections[-1].h
        return (sections[axis - 2].h + sections[axis - 1].h) / 2

    @staticmethod
    def _maximum_longitudinal_spacing(section) -> float:
        """Infer the largest bar-layer spacing from the CSV reinforcement layout."""

        top_positions = section.longitudinal_row_depths("top")
        bottom_positions = [
            section.h - depth for depth in section.longitudinal_row_depths("bottom")
        ]
        positions = top_positions + bottom_positions
        side_count = section.side_each.count
        if side_count:
            outer_top = min(top_positions)
            outer_bottom = max(bottom_positions)
            positions.extend(
                outer_top + (outer_bottom - outer_top) * index / (side_count + 1)
                for index in range(1, side_count + 1)
            )
        positions = sorted(set(positions))
        return max(right - left for left, right in zip(positions, positions[1:]))

    def _resolve_joint_materials(self) -> None:
        provider = self.connection_and_boundary.joint_panel_provider
        loads = self.load_and_material
        components = self.structural_components
        self.joint_materials: dict[str, JointMaterialSpec] = {}
        for floor in range(2, self.N + 2):
            story = floor - 1
            for axis in range(1, self.axis + 1):
                stiffnesses = [
                    self.column_hinges[story][axis - 1].ke,
                ]
                if story < self.N:
                    stiffnesses.append(self.column_hinges[story + 1][axis - 1].ke)
                if axis > 1:
                    stiffnesses.append(self.beam_hinges[floor][axis - 2].ke)
                if axis <= self.bays:
                    stiffnesses.append(self.beam_hinges[floor][axis - 1].ke)
                column = components.column_sections[story][axis - 1]
                adjacent_beams = []
                if axis > 1:
                    adjacent_beams.append(components.beam_sections[floor][axis - 2])
                if axis <= self.bays:
                    adjacent_beams.append(components.beam_sections[floor][axis - 1])
                beam_depth = self._joint_beam_depth(floor, axis)
                joint_width = min([column.b, *(beam.b for beam in adjacent_beams)])
                horizontal_steel_area = sum(
                    beam.top_bars.area + beam.bottom_bars.area + beam.side_area_total
                    for beam in adjacent_beams
                ) / len(adjacent_beams)
                horizontal_spacing = max(
                    self._maximum_longitudinal_spacing(beam) for beam in adjacent_beams
                )
                vertical_steel_area = (
                    column.top_bars.area + column.bottom_bars.area + column.side_area_total
                )
                vertical_spacing = self._maximum_longitudinal_spacing(column)
                context = JointPanelContext(
                    floor=floor,
                    axis=axis,
                    beam_depth=beam_depth,
                    column_depth=column.h,
                    joint_width=joint_width,
                    adjacent_rotational_stiffness=tuple(stiffnesses),
                    vertical_compression=loads.column_axial_forces[story][axis - 1],
                    horizontal_reinforcement_spacing=horizontal_spacing,
                    vertical_reinforcement_spacing=vertical_spacing,
                    horizontal_reinforcement_ratio=(
                        horizontal_steel_area / (joint_width * beam_depth)
                    ),
                    vertical_reinforcement_ratio=(vertical_steel_area / (joint_width * column.h)),
                    fc=loads.fc_expected,
                    ec=loads.elastic_modulus,
                    fy_horizontal=loads.fy_expected,
                    fy_vertical=loads.fy_expected,
                    es=loads.es,
                    poisson_ratio=loads.poisson_ratio,
                )
                self.joint_materials[f"{floor}:{axis}"] = provider.resolve(context)

    def generate_scripts(
        self, output_directory, *, overwrite: bool = True, show_plot: bool = False
    ):
        from .rc_write_script import RCScriptWriter

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
        self.building_info = write_rc_info_to_text(self)
        writer = RCScriptWriter(self, overwrite=overwrite, show_plot=show_plot)
        return writer.generated_files


def write_rc_info_to_dict(frame: RCFrame) -> dict:
    components = frame.structural_components
    loads = frame.load_and_material
    return {
        "//": "All units are in 'N', 'mm', and 't'; RC strengths are expected values",
        "frame_type": frame.frame_type,
        "name": frame.frame_name,
        "notes": frame.notes,
        "building_geometry": {
            "story_height": frame.building_geometry.story_height,
            "bay_length": frame.building_geometry.bay_length,
        },
        "structural_components": {
            "section_csv": components.section_source,
            "beams": components.beams,
            "columns": components.columns,
        },
        "load_and_material": {
            "nodal_mass": {
                "moment_frame": [
                    loads.moment_frame_node_mass[floor] for floor in range(2, frame.N + 2)
                ],
                "leaning_column": [
                    loads.leaning_column_node_mass[floor] for floor in range(2, frame.N + 2)
                ],
            },
            "nodal_vertical_load": {
                "moment_frame": [
                    loads.moment_frame_node_vertical_load[floor] for floor in range(2, frame.N + 2)
                ],
                "leaning_column": [
                    loads.leaning_column_node_vertical_load[floor]
                    for floor in range(2, frame.N + 2)
                ],
            },
            "axial_load_ratio_amplification_factor": (loads.axial_load_ratio_amplification_factor),
            "material": {
                "fc_expected": loads.fc_expected,
                "ec": loads.elastic_modulus,
                "fy_expected": loads.fy_expected,
                "es": loads.es,
                "poisson_ratio": loads.poisson_ratio,
            },
        },
        "connection_and_boundary": {
            "base_support": frame.connection_and_boundary.base_support,
            "soil_constraint": frame.connection_and_boundary.soil_constraint,
            "rigid_diaphragm": frame.connection_and_boundary.rigid_diaphragm,
            "joint_panel_model": (
                frame.connection_and_boundary.joint_panel_provider.configuration()
            ),
        },
        "references": None,
    }


def write_rc_info_to_text(frame: RCFrame) -> str:
    geometry = frame.building_geometry
    components = frame.structural_components
    loads = frame.load_and_material
    boundary = frame.connection_and_boundary
    text = "Reinforced-concrete moment resisting frame model information\n"
    text += f"Frame name: {frame.frame_name}\n"
    text += f"Generation time: {datetime.datetime.now()}\n"
    if frame.notes:
        text += f"Notes: {frame.notes}\n"
    text += "All units are in [N, mm, t]; strengths are expected values\n\n\n"

    # 1 Building geometry
    text += "-" * 15 + " 1. Building Geometry " + "-" * 15 + "\n\n"
    text += f"Building height: {geometry.building_height}\n"
    text += f"Number of story: {frame.N}\n"
    text += f"Number of bays: {frame.bays}\n"
    text += "\n\n"

    # 2 Structural components
    text += "-" * 15 + " 2. Structural Components " + "-" * 15 + "\n\n"
    text += "Beam sections:\n"
    beam_table = pd.DataFrame.from_dict(
        components.beams,
        orient="index",
        columns=[f"Bay-{bay}" for bay in range(1, frame.bays + 1)],
    )
    beam_table.insert(0, "Floor", range(2, frame.N + 2))
    text += beam_table.to_string(index=False) + "\n\n"
    text += "Column sections:\n"
    column_table = pd.DataFrame.from_dict(
        components.columns,
        orient="index",
        columns=[f"Axis-{axis}" for axis in range(1, frame.axis + 1)],
    )
    column_table.insert(0, "Story", range(1, frame.N + 1))
    text += column_table.to_string(index=False) + "\n\n\n"

    # 3 Load and material
    text += "-" * 15 + " 3. Load and Material " + "-" * 15 + "\n\n"
    text += "Expected material properties:\n"
    text += f"\tConcrete compressive strength fc [MPa]: {loads.fc_expected}\n"
    text += f"\tConcrete elastic modulus Ec [MPa]: {loads.elastic_modulus}\n"
    text += f"\tReinforcement yield strength fy [MPa]: {loads.fy_expected}\n"
    text += f"\tReinforcement elastic modulus Es [MPa]: {loads.es}\n"
    text += f"\tPoisson ratio: {loads.poisson_ratio}\n\n"
    text += (
        "Column axial-load-ratio amplification factor: "
        f"{loads.axial_load_ratio_amplification_factor}\n\n"
    )
    axis_columns = [f"Axis-{axis}" for axis in range(1, frame.axis + 1)]
    text += "User-defined moment-frame nodal mass [t]:\n"
    table = pd.DataFrame.from_dict(
        loads.moment_frame_node_mass, orient="index", columns=axis_columns
    )
    table.insert(0, "Floor", list(loads.moment_frame_node_mass))
    text += table.to_string(index=False) + "\n\n"
    text += "User-defined leaning-column nodal mass [t]:\n"
    table = pd.DataFrame(sorted(loads.leaning_column_node_mass.items()), columns=["Floor", "Mass"])
    text += table.to_string(index=False) + "\n\n"
    text += "User-defined moment-frame nodal vertical load [kN, downward positive]:\n"
    table = pd.DataFrame.from_dict(
        loads.moment_frame_node_vertical_load, orient="index", columns=axis_columns
    )
    table[axis_columns] /= 1000.0
    table.insert(0, "Floor", list(loads.moment_frame_node_vertical_load))
    text += table.to_string(index=False) + "\n\n"
    text += "User-defined leaning-column nodal vertical load [kN, downward positive]:\n"
    table = pd.DataFrame(
        sorted(loads.leaning_column_node_vertical_load.items()),
        columns=["Floor", "Vertical load"],
    )
    table["Vertical load"] /= 1000.0
    text += table.to_string(index=False) + "\n\n"
    text += "Amplified axial compressive ratio PPy of columns:\n"
    ppy_table = pd.DataFrame.from_dict(
        loads.ppy,
        orient="index",
        columns=[f"Axis-{axis}" for axis in range(1, frame.axis + 1)],
    )
    ppy_table.insert(0, "Story", list(loads.ppy))
    text += ppy_table.to_string(index=False) + "\n\n"
    total_vertical_load = sum(
        sum(values) for values in loads.moment_frame_node_vertical_load.values()
    ) + sum(loads.leaning_column_node_vertical_load.values())
    total_mass = sum(sum(values) for values in loads.moment_frame_node_mass.values()) + sum(
        loads.leaning_column_node_mass.values()
    )
    text += f"Total user-defined vertical load: {total_vertical_load / 1000:.2f} kN\n"
    text += f"Total user-defined mass: {total_mass:.2f} t\n\n\n"

    # 4 Connection and boundary condition
    text += "-" * 15 + " 4. Connection and Boundary Condition " + "-" * 15 + "\n\n"
    text += f"Base support: {boundary.base_support}\n"
    text += "Beam-to-column connection: Concentrated RC hinges with Joint2D panel zones\n"
    provider = boundary.joint_panel_provider.configuration()
    text += f"Joint panel model: {provider['type']}\n"
    if provider["type"] == "Rigid":
        text += f"Joint panel stiffness factor: {provider['stiffness_factor']}\n"
    elif provider["type"] == "MCFT":
        text += (
            "MCFT steel hardening ratio / maximum aggregate size [mm]: "
            f"{provider['steel_hardening_ratio']} / {provider['maximum_aggregate_size']}\n"
        )
    text += f"Rigid diaphragm constraint: {'Yes' if boundary.rigid_diaphragm else 'No'}\n"
    text += f"Soil constraints at floors: {boundary.soil_constraint or 'None'}\n"
    output = frame.output_path / f"Model Information_{frame.frame_name}.txt"
    output.write_text(text, encoding="utf-8")
    return text


def rc_frame_from_dict(data: dict, *, base_directory: str | Path = ".") -> RCFrame:
    frame = RCFrame(_required(data, "name", "root"), data.get("notes"))
    geometry = _required(data, "building_geometry", "root")
    frame.building_geometry.story_height = _required(geometry, "story_height", "building_geometry")
    frame.building_geometry.bay_length = _required(geometry, "bay_length", "building_geometry")
    frame.finish_building_geometry()

    components = _required(data, "structural_components", "root")
    section_csv = Path(_required(components, "section_csv", "structural_components"))
    if not section_csv.is_absolute():
        section_csv = Path(base_directory) / section_csv
    frame.structural_components.load_sections_csv(section_csv)
    for floor, names in _required(components, "beams", "structural_components").items():
        frame.structural_components.set_beams(int(floor), names)
    for story, names in _required(components, "columns", "structural_components").items():
        frame.structural_components.set_columns(int(story), names)
    frame.finish_structural_components()

    load_data = _required(data, "load_and_material", "root")
    _set_direct_nodal_inputs(frame, load_data)
    frame.load_and_material.set_axial_load_ratio_amplification_factor(
        load_data.get("axial_load_ratio_amplification_factor", 1.25)
    )
    material = _required(load_data, "material", "load_and_material")
    frame.load_and_material.set_material(
        material["fc_expected"],
        material["ec"],
        material["fy_expected"],
        material.get("es", 200000),
        material.get("poisson_ratio", 0.2),
    )
    frame.finish_load_and_material()

    boundary = _required(data, "connection_and_boundary", "root")
    frame.connection_and_boundary.set_base_support(boundary.get("base_support", "Fixed"))
    for floor in boundary.get("soil_constraint", []):
        frame.connection_and_boundary.set_soil_constraint(int(floor))
    frame.connection_and_boundary.rigid_diaphragm = boundary.get("rigid_diaphragm", True)
    joint_panel_model = boundary.get("joint_panel_model", {})
    if joint_panel_model:
        from .rc_joint import joint_panel_provider_from_configuration

        frame.connection_and_boundary.set_joint_panel_provider(
            joint_panel_provider_from_configuration(joint_panel_model)
        )
    frame.finish_connection_and_boundary()
    frame.finalize()
    frame.dict_info["references"] = data.get("references")
    return frame
