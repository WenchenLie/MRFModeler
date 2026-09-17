from pathlib import Path

from MRFHelper import Frame

frame = Frame("Benchmark_3S")

# Step-1, set building geometry
frame.building_geometry.story_height = [3960, 3960, 3960]
frame.building_geometry.bay_length = [9150, 9150, 9150, 9150]
frame.building_geometry.plane_dimensions = (9150 * 4, 9150 * 4)
frame.building_geometry.mf_number = 5
frame.building_geometry.exterior_column_tributary_area = (9150 / 2, 9150 / 2)
frame.building_geometry.interior_column_tributary_area = (9150, 9150 / 2)
frame.finish_building_geometry()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.structural_components.set_beams(2, ["W33x118", "W33x118", "W33x118", "W30x116"])
frame.structural_components.set_beams(3, ["W30x116", "W30x116", "W30x116", "W30x116"])
frame.structural_components.set_beams(4, ["W24x68", "W24x68", "W24x68", "W24x68"])
# (story, ['section1', 'section2', ...])
frame.structural_components.set_columns(1, ["W14x257", "W14x311", "W14x311", "W14x311", "W14x257"])
frame.structural_components.set_columns(2, ["W14x257", "W14x311", "W14x311", "W14x311", "W14x257"])
frame.structural_components.set_columns(3, ["W14x257", "W14x311", "W14x311", "W14x311", "W14x257"])
frame.finish_structural_components()

# Step-3, set load and material property
frame.load_and_material.set_masses(
    moment_frame=[[479 / 5] * 5, [479 / 5] * 5, [520 / 5] * 5],
    leaning_column=[0, 0, 0],
)
frame.load_and_material.set_loads(
    moment_frame=[[479 / 5 * 1e4] * 5, [479 / 5 * 1e4] * 5, [520 / 5 * 1e4] * 5],
    leaning_column=[0, 0, 0],
)
frame.load_and_material.set_material(206000, 248, 345)
frame.finish_load_and_material()

# Step-4, set connection and boundary condition
frame.connection_and_boundary.set_base_support("Fixed")
frame.connection_and_boundary.set_beam_column_connection("Full")
frame.connection_and_boundary.set_panel_zone_deformation(True)
frame.connection_and_boundary.rigid_diaphragm = True
frame.finish_connection_and_boundary()

frame.finalize()

frame.generate_scripts(Path(__file__).parent.parent / "output", show_plot=True)
