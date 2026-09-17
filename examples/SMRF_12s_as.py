from pathlib import Path

from MRFHelper import Frame

frame = Frame("MRF12S")

# Step-1, set building geometry
frame.building_geometry.story_height = [
    4200,
    4000,
    4000,
    4000,
    4000,
    4000,
    4000,
    4000,
    4000,
    4000,
    4000,
    4000,
]
frame.building_geometry.bay_length = [6100, 6100, 6100]
frame.building_geometry.plane_dimensions = (42700, 30500)
frame.building_geometry.mf_number = 2
frame.building_geometry.exterior_column_tributary_area = (9150, 3050)
frame.building_geometry.interior_column_tributary_area = (6100, 3050)
frame.finish_building_geometry()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.structural_components.set_beams(2, ["W30x132", "W30x132", "W30x132"])
frame.structural_components.set_beams(3, ["W30x132", "W30x132", "W30x132"])
frame.structural_components.set_beams(4, ["W30x132", "W30x132", "W30x132"])
frame.structural_components.set_beams(5, ["W30x132", "W30x132", "W30x132"])
frame.structural_components.set_beams(6, ["W30x124", "W30x124", "W30x124"])
frame.structural_components.set_beams(7, ["W30x124", "W30x124", "W30x124"])
frame.structural_components.set_beams(8, ["W30x108", "W30x108", "W30x108"])
frame.structural_components.set_beams(9, ["W30x108", "W30x108", "W30x108"])
frame.structural_components.set_beams(10, ["W27x94", "W27x94", "W27x94"])
frame.structural_components.set_beams(11, ["W27x94", "W27x94", "W27x94"])
frame.structural_components.set_beams(12, ["W24x76", "W24x76", "W24x76"])
frame.structural_components.set_beams(13, ["W24x76", "W24x76", "W24x76"])
# (story, ['section1', 'section2', ...])
frame.structural_components.set_columns(1, ["W27x235", "W27x281", "W27x281", "W27x235"])
frame.structural_components.set_columns(2, ["W27x235", "W27x281", "W27x281", "W27x235"])
frame.structural_components.set_columns(3, ["W27x235", "W27x281", "W27x281", "W27x235"])
frame.structural_components.set_columns(4, ["W27x217", "W27x258", "W27x258", "W27x217"])
frame.structural_components.set_columns(5, ["W27x217", "W27x258", "W27x258", "W27x217"])
frame.structural_components.set_columns(6, ["W27x178", "W27x217", "W27x217", "W27x178"])
frame.structural_components.set_columns(7, ["W27x178", "W27x217", "W27x217", "W27x178"])
frame.structural_components.set_columns(8, ["W27x129", "W27x194", "W27x194", "W27x129"])
frame.structural_components.set_columns(9, ["W27x129", "W27x194", "W27x194", "W27x129"])
frame.structural_components.set_columns(10, ["W27x114", "W27x129", "W27x129", "W27x114"])
frame.structural_components.set_columns(11, ["W27x114", "W27x129", "W27x129", "W27x114"])
frame.structural_components.set_columns(12, ["W27x94", "W27x102", "W27x102", "W27x94"])
# (floor, ['thickness1', 'thickness2', ...])
frame.structural_components.set_doubler_plate(
    2, [i * 25.4 for i in [4 / 16, 19 / 16, 19 / 16, 4 / 16]]
)
frame.structural_components.set_doubler_plate(
    3, [i * 25.4 for i in [4 / 16, 18 / 16, 18 / 16, 4 / 16]]
)
frame.structural_components.set_doubler_plate(
    4, [i * 25.4 for i in [5 / 16, 21 / 16, 21 / 16, 5 / 16]]
)
frame.structural_components.set_doubler_plate(
    5, [i * 25.4 for i in [5 / 16, 21 / 16, 21 / 16, 5 / 16]]
)
frame.structural_components.set_doubler_plate(
    6, [i * 25.4 for i in [6 / 16, 21 / 16, 21 / 16, 6 / 16]]
)
frame.structural_components.set_doubler_plate(
    7, [i * 25.4 for i in [6 / 16, 21 / 16, 21 / 16, 6 / 16]]
)
frame.structural_components.set_doubler_plate(
    8, [i * 25.4 for i in [5 / 16, 17 / 16, 17 / 16, 5 / 16]]
)
frame.structural_components.set_doubler_plate(
    9, [i * 25.4 for i in [5 / 16, 17 / 16, 17 / 16, 5 / 16]]
)
frame.structural_components.set_doubler_plate(
    10, [i * 25.4 for i in [5 / 16, 17 / 16, 17 / 16, 5 / 16]]
)
frame.structural_components.set_doubler_plate(
    11, [i * 25.4 for i in [5 / 16, 17 / 16, 17 / 16, 5 / 16]]
)
frame.structural_components.set_doubler_plate(
    12, [i * 25.4 for i in [4 / 16, 15 / 16, 15 / 16, 4 / 16]]
)
frame.structural_components.set_doubler_plate(
    13, [i * 25.4 for i in [4 / 16, 15 / 16, 15 / 16, 4 / 16]]
)
frame.structural_components.set_column_splice(
    3, 5, 7, 9, 11
)  # Floor numbers where the column splices are located
frame.structural_components.set_beam_splice(2)  # Bay numbers where the beam splices are located
frame.finish_structural_components()

# Step-3, set nodal mass, vertical load, and material properties
typical_mass = [16.7268, 11.1512, 11.1512, 16.7268]
typical_load = [188862.8625, 125908.575, 125908.575, 188862.8625]
moment_frame_mass = [
    [16.8388, 11.2259, 11.2259, 16.8388],
    *[typical_mass for _ in range(10)],
    [14.4859, 9.6573, 9.6573, 14.4859],
]
moment_frame_vertical_load = [
    [190015.7625, 126677.175, 126677.175, 190015.7625],
    *[typical_load for _ in range(10)],
    [155758.1625, 103838.775, 103838.775, 155758.1625],
]
frame.load_and_material.set_masses(
    moment_frame_mass,
    [266.3397, *[265.8168 for _ in range(10)], 255.3597],
)
frame.load_and_material.set_loads(
    moment_frame_vertical_load,
    [3075525.45, *[3070145.25 for _ in range(10)], 2761607.25],
)
frame.load_and_material.set_material(206000, 345, 345)
frame.finish_load_and_material()

# Step-4, set connection and boundary condition
frame.connection_and_boundary.set_base_support("Fixed")
frame.connection_and_boundary.set_beam_column_connection("Full")
frame.connection_and_boundary.set_panel_zone_deformation(True)
frame.finish_connection_and_boundary()

frame.finalize()
frame.dict_info["references"] = [
    "Archetype 4-story steel moment resisting frame",
    "[1] Andronikos Skiadopoulos, Dimitrios Lignos. Design summaries of steel moment resisting frames with elastic and dissipative panel zones. National Conference on Earthquake Engineering. Zenodo (2022). https://doi.org/10.5281/zenodo.5962407",
    "[2] Andronikos Skiadopoulos, Dimitrios Lignos. Seismic demands of steel moment resisting frames with inelastic beam‐to‐column web panel zones. Earthquake Engineering & Structural Dynamics 51.7 (2022): 1591-1609.",
]
frame.generate_scripts(Path(__file__).parent.parent / "output", show_plot=True)
