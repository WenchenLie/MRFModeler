from pathlib import Path

from MRFHelper import Frame

frame = Frame("Benchmark_9S")

# Step-1, set building geometry
frame.building_geometry.story_height = [3650, 5490, 3960, 3960, 3960, 3960, 3960, 3960, 3960, 3960]
frame.building_geometry.bay_length = [9150, 9150, 9150, 9150, 9150]
frame.building_geometry.plane_dimensions = (9150 * 5, 9150 * 5)
frame.building_geometry.mf_number = 6
frame.building_geometry.exterior_column_tributary_area = (9150 / 2, 9150 / 2)
frame.building_geometry.interior_column_tributary_area = (9150, 9150 / 2)
frame.finish_building_geometry()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.structural_components.set_beams(2, ["W36x160", "W36x160", "W36x160", "W36x160", "W36x160"])
frame.structural_components.set_beams(3, ["W36x160", "W36x160", "W36x160", "W36x160", "W36x160"])
frame.structural_components.set_beams(4, ["W36x160", "W36x160", "W36x160", "W36x160", "W36x160"])
frame.structural_components.set_beams(5, ["W36x135", "W36x135", "W36x135", "W36x135", "W36x135"])
frame.structural_components.set_beams(6, ["W36x135", "W36x135", "W36x135", "W36x135", "W36x135"])
frame.structural_components.set_beams(7, ["W36x135", "W36x135", "W36x135", "W36x135", "W36x135"])
frame.structural_components.set_beams(8, ["W36x135", "W36x135", "W36x135", "W36x135", "W36x135"])
frame.structural_components.set_beams(9, ["W30x99", "W30x99", "W30x99", "W30x99", "W30x99"])
frame.structural_components.set_beams(10, ["W27x84", "W27x84", "W27x84", "W27x84", "W27x84"])
frame.structural_components.set_beams(11, ["W24x68", "W24x68", "W24x68", "W24x68", "W24x68"])
# (story, ['section1', 'section2', ...])
frame.structural_components.set_columns(
    1, ["W14x500", "W14x500", "W14x500", "W14x500", "W14x500", "W14x500"]
)
frame.structural_components.set_columns(
    2, ["W14x500", "W14x500", "W14x500", "W14x500", "W14x500", "W14x500"]
)
frame.structural_components.set_columns(
    3, ["W14x455", "W14x455", "W14x455", "W14x455", "W14x455", "W14x455"]
)
frame.structural_components.set_columns(
    4, ["W14x455", "W14x455", "W14x455", "W14x455", "W14x455", "W14x455"]
)
frame.structural_components.set_columns(
    5, ["W14x370", "W14x370", "W14x370", "W14x370", "W14x370", "W14x370"]
)
frame.structural_components.set_columns(
    6, ["W14x370", "W14x370", "W14x370", "W14x370", "W14x370", "W14x370"]
)
frame.structural_components.set_columns(
    7, ["W14x283", "W14x283", "W14x283", "W14x283", "W14x283", "W14x283"]
)
frame.structural_components.set_columns(
    8, ["W14x283", "W14x283", "W14x283", "W14x283", "W14x283", "W14x283"]
)
frame.structural_components.set_columns(
    9, ["W14x257", "W14x257", "W14x257", "W14x257", "W14x257", "W14x257"]
)
frame.structural_components.set_columns(
    10, ["W14x257", "W14x257", "W14x257", "W14x257", "W14x257", "W14x257"]
)
# column splices
frame.structural_components.set_column_splice(3, 5, 7, 9)
frame.finish_structural_components()

# Step-3, set load and material property
floor_values = [483, 505, 495, 495, 495, 495, 495, 495, 495, 535]
frame.load_and_material.set_masses(
    moment_frame=[[value / 5] * 6 for value in floor_values],
    leaning_column=[0] * 10,
)
frame.load_and_material.set_loads(
    moment_frame=[[value / 5 * 1e4] * 6 for value in floor_values],
    leaning_column=[0] * 10,
)
frame.load_and_material.set_material(206000, 248, 345)
frame.finish_load_and_material()

# Step-4, set connection and boundary condition
frame.connection_and_boundary.set_base_support("Pinned")
frame.connection_and_boundary.set_beam_column_connection("Full")
frame.connection_and_boundary.set_panel_zone_deformation(True)
frame.connection_and_boundary.rigid_diaphragm = True
frame.finish_connection_and_boundary()

frame.recorders["BeamHinge"] = False
frame.recorders["ColumnHinge"] = False
frame.recorders["PanelZone"] = False
frame.finalize()

frame.generate_scripts(Path(__file__).parent.parent / "output", show_plot=True)
