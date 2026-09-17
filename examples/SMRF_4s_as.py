from pathlib import Path

from MRFHelper import Frame

frame = Frame("MRF4S")

# Step-1, set building geometry
frame.building_geometry.story_height = [4300, 4000, 4000, 4000]
frame.building_geometry.bay_length = [6100, 6100, 6100]
frame.building_geometry.plane_dimensions = (42700, 30500)
frame.building_geometry.mf_number = 2
frame.building_geometry.exterior_column_tributary_area = (9150, 3050)
frame.building_geometry.interior_column_tributary_area = (6100, 3050)
frame.finish_building_geometry()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.structural_components.set_beams(2, ["W24x76", "W24x76", "W24x76"])
frame.structural_components.set_beams(3, ["W24x76", "W24x76", "W24x76"])
frame.structural_components.set_beams(4, ["W18x60", "W18x60", "W18x60"])
frame.structural_components.set_beams(5, ["W18x60", "W18x60", "W18x60"])
# (story, ['section1', 'section2', ...])
frame.structural_components.set_columns(1, ["W24x103", "W24x146", "W24x146", "W24x103"])
frame.structural_components.set_columns(2, ["W24x103", "W24x146", "W24x146", "W24x103"])
frame.structural_components.set_columns(3, ["W24x103", "W24x146", "W24x146", "W24x103"])
frame.structural_components.set_columns(4, ["W24x76", "W24x84", "W24x84", "W24x76"])
# (floor, ['thickness1', 'thickness2', ...])
frame.structural_components.set_doubler_plate(2, [6.35, 23.8125, 23.8125, 6.35])
frame.structural_components.set_doubler_plate(3, [6.35, 23.8125, 23.8125, 6.35])
frame.structural_components.set_doubler_plate(4, [6.35, 22.225, 22.225, 6.35])
frame.structural_components.set_doubler_plate(5, [6.35, 22.225, 22.225, 6.35])
frame.structural_components.set_column_splice(
    3
)  # Floor numbers where the column splices are located
frame.structural_components.set_beam_splice(2)  # Bay numbers where the beam splices are located
frame.finish_structural_components()

# Step-3, set nodal mass, vertical load, and material properties
frame_mass = [
    [16.8948, 11.2632, 11.2632, 16.8948],
    [16.7268, 11.1512, 11.1512, 16.7268],
    [16.7268, 11.1512, 11.1512, 16.7268],
    [14.4859, 9.6573, 9.6573, 14.4859],
]
frame_vertical_load = [
    [190592.2125, 127061.475, 127061.475, 190592.2125],
    [188862.8625, 125908.575, 125908.575, 188862.8625],
    [188862.8625, 125908.575, 125908.575, 188862.8625],
    [155758.1625, 103838.775, 103838.775, 155758.1625],
]
frame.load_and_material.set_masses(frame_mass, [266.6011, 265.8168, 265.8168, 255.3597])
frame.load_and_material.set_loads(
    frame_vertical_load, [3078215.55, 3070145.25, 3070145.25, 2761607.25]
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
