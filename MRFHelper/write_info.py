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
        "BuildingGeometry": {},
        "StructuralComponents": {},
        "LoadAndMaterial": {},
        "ConnectionAndBoundary": {},
    }
    info["BuildingGeometry"] = {
        "//": "Step 1",
        "story_height": frame.building_geometry.story_height,
        "bay_length": frame.building_geometry.bay_length,
        "plane_dimensions": frame.building_geometry.plane_dimensions,
        "MF_number": frame.building_geometry.mf_number,
        "exterior_column_tributary_area": frame.building_geometry.exterior_column_tributary_area,
        "interior_column_tributary_area": frame.building_geometry.interior_column_tributary_area,
    }
    info["StructuralComponents"] = {
        "//": "Step 2",
        "beams": frame.structural_components.beams,
        "columns": frame.structural_components.columns,
        "set_doubler_plate": frame.structural_components.doubler_plate,
        "column_splice": frame.structural_components.column_splice,
        "//column_splice": "The story number where column splices locate",
        "beam_splice": frame.structural_components.beam_splice,
        "//beam_splice": "The bay number where beam splices locate",
        "RBS_length": frame.structural_components.rbs_length_all,
        "//RBS_length": "Fix the distance from beam hinge to panel zone edge (optional)",
    }
    info["LoadAndMaterial"] = {
        "//": "Step 3",
        "//rule": "floor/story number: load",
        "dead_load": frame.load_and_material.dead_load,
        "live_load": frame.load_and_material.live_load,
        "clading_load": frame.load_and_material.cladding_load,
        "weight_combination_coefficients": frame.load_and_material.cc_weight,
        "mass_combination_coefficients": frame.load_and_material.cc_mass,
        "material": {
            "E": frame.load_and_material.elastic_modulus,
            "fy_beam": frame.load_and_material.fy_beam,
            "fy_column": frame.load_and_material.fy_column,
            "miu": frame.load_and_material.miu,
        },
    }
    info["ConnectionAndBoundary"] = {
        "//": "Step 4",
        "base_support": frame.connection_and_boundary.base_support,
        "//base_support": "Fixed or Pinned",
        "beam_column_connection": frame.connection_and_boundary.beam_column_connection,
        "//beam_column_connection": "Full, RBS, or Hinged",
        "RBS_parameters": frame.connection_and_boundary.rbs_parameters,
        "panel_zone_deformation": frame.connection_and_boundary.panel_zone_deformation,
        "//panel_zone_deformation": "true or false",
        "soil_constraint": frame.connection_and_boundary.soil_constraint,
        "//soil_constraint": "Set soil constraint at specified floor (optional)",
        "rigid_diaphragm": frame.connection_and_boundary.rigid_diaphragm,
    }
    info["References"] = None
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
    text += (
        f"Plane dimensions [mm]: {geometry.plane_dimensions[0]} x {geometry.plane_dimensions[1]}\n"
    )
    text += f"Number of moment frames: {geometry.mf_number}\n"
    text += (
        "External column tributary area [mm]: "
        f"{geometry.exterior_column_tributary_area[0]} x "
        f"{geometry.exterior_column_tributary_area[1]}\n"
    )
    text += (
        "Internal column tributary area [mm]: "
        f"{geometry.interior_column_tributary_area[0]} x "
        f"{geometry.interior_column_tributary_area[1]}\n\n\n"
    )

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
    text += f"\tPossion ratio: {loads.miu}\n\n"
    text += "Load [MPa]:\n"
    story_floor = [f"{i - 1}/{i}" for i in range(2, frame.N + 2)]
    df = pd.DataFrame(story_floor, columns=["Story/Floor"])
    dead_loads, live_loads, cladding_loads = [], [], []
    for floor in range(2, frame.N + 2):
        story = floor - 1
        dead_loads.append(loads.dead_load[floor])
        live_loads.append(loads.live_load[floor])
        cladding_loads.append(loads.cladding_load[story])
    df["Dead"] = dead_loads
    df["Live"] = live_loads
    df["Cladding"] = cladding_loads
    text += f"{df.to_string(index=False)}\n\n"
    text += "Load and mass combination coefficients:\n"
    df = pd.DataFrame()
    df["Dead"] = [loads.cc_weight["Dead"], loads.cc_mass["Dead"]]
    df["Live"] = [loads.cc_weight["Live"], loads.cc_mass["Live"]]
    df["Cladding"] = [loads.cc_weight["Cladding"], loads.cc_mass["Cladding"]]
    df.index = ["Weight", "Mass"]
    text += f"{df.to_string()}\n\n"
    text += "Axial compressive ratio of columns:\n"
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
    total_weight, total_mass = 0, 0
    for floor in range(2, frame.N + 2):
        for axis in range(1, frame.axis + 1):
            id_axis = axis - 1
            total_weight += loads.F_node[floor][id_axis]
            total_mass += loads.mass_node[floor][id_axis]
        total_weight += loads.F_grav[floor]
        total_mass += loads.mass_grav[floor]
    text += f"Seiemic weight of considered 2D frame: {total_weight / 1000:.2f} kN\n"
    text += f"Seiemic mass of considered 2D frame: {total_mass:.2f} t\n\n\n"

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
