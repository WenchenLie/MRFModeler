from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mrf_helper import Frame

import pandas as pd


def _ordered_values(mapping: dict, start: int, stop: int) -> dict:
    """Return an integer-keyed mapping in engineering floor/story order."""
    return {index: mapping[index] for index in range(start, stop)}


def write_info_to_dict(frame: Frame) -> dict:
    info = {
        "//": "All units are in 'N', 'mm', and 't'",
        "name": frame.frame_name,
        "notes": frame.notes,
        "building_geometry": {},
        "structural_components": {},
        "load_and_material": {},
        "connection_and_boundary": {},
    }
    info["building_geometry"] = {
        "//": "Step 1",
        "story_height": frame.building_geometry.story_height,
        "bay_length": frame.building_geometry.bay_length,
    }
    info["structural_components"] = {
        "//": "Step 2",
        "beams": frame.structural_components.beams,
        "columns": frame.structural_components.columns,
        "doubler_plate": frame.structural_components.doubler_plate,
        "column_splice": frame.structural_components.column_splice,
        "//column_splice": "The story number where column splices locate",
        "beam_splice": frame.structural_components.beam_splice,
        "//beam_splice": "The bay number where beam splices locate",
        "rbs_length": frame.structural_components.rbs_length_all,
        "//rbs_length": "Fix the distance from beam hinge to panel zone edge (optional)",
    }
    info["load_and_material"] = {
        "//": "Step 3",
        "nodal_mass": {
            "moment_frame": [
                frame.load_and_material.moment_frame_node_mass[floor]
                for floor in range(2, frame.N + 2)
            ],
            "leaning_column": [
                frame.load_and_material.leaning_column_node_mass[floor]
                for floor in range(2, frame.N + 2)
            ],
        },
        "nodal_vertical_load": {
            "moment_frame": [
                frame.load_and_material.moment_frame_node_vertical_load[floor]
                for floor in range(2, frame.N + 2)
            ],
            "leaning_column": [
                frame.load_and_material.leaning_column_node_vertical_load[floor]
                for floor in range(2, frame.N + 2)
            ],
        },
        "axial_load_ratio_amplification_factor": (
            frame.load_and_material.axial_load_ratio_amplification_factor
        ),
        "material": {
            "elastic_modulus": frame.load_and_material.elastic_modulus,
            "fy_beam": frame.load_and_material.fy_beam,
            "fy_column": frame.load_and_material.fy_column,
            "poisson_ratio": frame.load_and_material.poisson_ratio,
        },
    }
    info["connection_and_boundary"] = {
        "//": "Step 4",
        "base_support": frame.connection_and_boundary.base_support,
        "//base_support": "Fixed or Pinned",
        "beam_column_connection": frame.connection_and_boundary.beam_column_connection,
        "//beam_column_connection": "Full, RBS, or Hinged",
        "rbs_parameters": frame.connection_and_boundary.rbs_parameters,
        "panel_zone_deformation": frame.connection_and_boundary.panel_zone_deformation,
        "//panel_zone_deformation": "true or false",
        "soil_constraint": frame.connection_and_boundary.soil_constraint,
        "//soil_constraint": "Set soil constraint at specified floor (optional)",
        "rigid_diaphragm": frame.connection_and_boundary.rigid_diaphragm,
    }
    info["references"] = None
    return info


def write_info_to_tcl(frame: Frame, file_name="Model Information") -> str:
    geometry = frame.building_geometry
    components = frame.structural_components
    loads = frame.load_and_material
    boundary = frame.connection_and_boundary
    text = "Moment resisting frame model information\n"
    text += f"Frame name: {frame.frame_name}\n"
    text += f"Generation time: {datetime.datetime.now()}\n"
    if frame.notes:
        text += f"Notes: {frame.notes}\n"
    text += "All units are in [N, mm, t]\n\n\n"

    # 1 building geometry
    text += "-" * 15 + " 1. Building Geometry " + "-" * 15 + "\n\n"
    text += f"Building height: {geometry.building_height}\n"
    text += f"Number of story: {frame.N}\n"
    text += f"Number of bays: {frame.bays}\n"
    text += "\n\n"

    # 2 structural components
    text += "-" * 15 + " 2. Structural Components " + "-" * 15 + "\n\n"
    text += "Beam sections:\n"
    beam_sections = _ordered_values(components.beams, 2, frame.N + 2)
    df_beam = pd.DataFrame.from_dict(
        beam_sections,
        orient="index",
        columns=[f"Bay-{i}" for i in range(1, frame.bays + 1)],
    )
    df_beam.insert(0, "Floor", range(2, frame.N + 2))
    text += f"{df_beam.to_string(index=False)}\n\n"
    text += "Column sections:\n"
    col_sections = _ordered_values(components.columns, 1, frame.N + 1)
    df_col = pd.DataFrame.from_dict(
        col_sections,
        orient="index",
        columns=[f"Axis-{i}" for i in range(1, frame.bays + 2)],
    )
    df_col.insert(0, "Story", range(1, frame.N + 1))
    text += f"{df_col.to_string(index=False)}\n\n"
    text += "Stories with column splices: "
    if len(components.column_splice) == 0:
        text += "None\n\n"
    else:
        splices = ", ".join(str(item) for item in components.column_splice) + "\n\n"
        text += splices
    text += "Doubler plate thickness [mm]:\n"
    doubler_plate = _ordered_values(components.doubler_plate, 2, frame.N + 2)
    df_dp = pd.DataFrame.from_dict(
        doubler_plate,
        orient="index",
        columns=[f"Axis-{i}" for i in range(1, frame.bays + 2)],
    )
    df_dp.insert(0, "Floor", range(2, frame.N + 2))
    text += f"{df_dp.to_string(index=False)}\n\n\n"

    # 3 load and material
    text += "-" * 15 + " 3. Load and Material " + "-" * 15 + "\n\n"
    text += "Material properties:\n"
    text += f"\tYoung's modulus [MPa]: {loads.elastic_modulus}\n"
    text += f"\tNominal yield strength of beams [MPa]: {loads.fy_beam}\n"
    text += f"\tNominal yield strength of columns [MPa]: {loads.fy_column}\n"
    text += f"\tPoisson ratio: {loads.poisson_ratio}\n\n"
    text += (
        "Column axial-load-ratio amplification factor: "
        f"{loads.axial_load_ratio_amplification_factor}\n\n"
    )
    axis_columns = [f"Axis-{axis}" for axis in range(1, frame.axis + 1)]
    text += "User-defined moment-frame nodal mass [t]:\n"
    df = pd.DataFrame.from_dict(loads.moment_frame_node_mass, orient="index", columns=axis_columns)
    df.insert(0, "Floor", list(loads.moment_frame_node_mass))
    text += f"{df.to_string(index=False)}\n\n"
    text += "User-defined leaning-column nodal mass [t]:\n"
    df = pd.DataFrame(sorted(loads.leaning_column_node_mass.items()), columns=["Floor", "Mass"])
    text += f"{df.to_string(index=False)}\n\n"
    text += "User-defined moment-frame nodal vertical load [kN, downward positive]:\n"
    df = pd.DataFrame.from_dict(
        loads.moment_frame_node_vertical_load, orient="index", columns=axis_columns
    )
    df[axis_columns] /= 1000.0
    df.insert(0, "Floor", list(loads.moment_frame_node_vertical_load))
    text += f"{df.to_string(index=False)}\n\n"
    text += "User-defined leaning-column nodal vertical load [kN, downward positive]:\n"
    df = pd.DataFrame(
        sorted(loads.leaning_column_node_vertical_load.items()),
        columns=["Floor", "Vertical load"],
    )
    df["Vertical load"] /= 1000.0
    text += f"{df.to_string(index=False)}\n\n"
    text += "Unamplified axial compressive ratio of columns:\n"
    df = pd.DataFrame.from_dict(
        loads.ppy,
        orient="index",
        columns=[f"Axis-{i}" for i in range(1, frame.bays + 2)],
    )
    df_col = []
    for i in range(1, frame.N + 1):
        df_col.append(f"{i}b")
        df_col.append(f"{i}t")
    df.insert(0, "Story", df_col)
    text += f"{df.to_string(index=False)}\n\n"
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
    connection_type = boundary.beam_column_connection
    if connection_type == "Full":
        s = "Fully constrained connection"
    elif connection_type == "RBS":
        s = "Reduced beam section (RBS)"
    elif connection_type == "Hinged":
        s = "Hinged connection"
    text += f"Beam-to-column connection: {s}\n"
    a, b, c = boundary.rbs_parameters
    if boundary.beam_column_connection == "RBS":
        text += f"Reduced beam section (RBS) parameters: {a}, {b}, {c}\n"
    s = "Yes (Parallelogram)" if boundary.panel_zone_deformation else "No (Cruciform)"
    text += f"Consider panel zone deformation: {s}\n"

    output_file = frame.output_path / f"{file_name}_{frame.frame_name}.txt"
    output_file.write_text(text, encoding="utf-8")
    return text
