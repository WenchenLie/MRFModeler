from pathlib import Path
try:
    from MRFHelper.MRFhelper import Frame
except ImportError:
    raise ImportError('Run command "pip install mrfhelper" to install this package')


frame = Frame('Benchmark_3S')

# Step-1, set building geometry
frame.BuildingGeometry.story_height = [3960, 3960, 3960]
frame.BuildingGeometry.bay_length = [9150, 9150, 9150, 9150]
frame.BuildingGeometry.plane_dimensions = (9150*4, 9150*4)
frame.BuildingGeometry.MF_number = 5
frame.BuildingGeometry.exterior_column_tributary_area = (9150/2, 9150/2)
frame.BuildingGeometry.interior_column_tributary_area = (9150, 9150/2)
frame.step1_finished()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.StructuralComponents.set_beams(2, ['W33x118', 'W33x118', 'W33x118', 'W30x116'])
frame.StructuralComponents.set_beams(3, ['W30x116', 'W30x116', 'W30x116', 'W30x116'])
frame.StructuralComponents.set_beams(4, ['W24x68', 'W24x68', 'W24x68', 'W24x68'])
# (story, ['section1', 'section2', ...])
frame.StructuralComponents.set_columns(1, ['W14x257', 'W14x311', 'W14x311', 'W14x311', 'W14x257'])
frame.StructuralComponents.set_columns(2, ['W14x257', 'W14x311', 'W14x311', 'W14x311', 'W14x257'])
frame.StructuralComponents.set_columns(3, ['W14x257', 'W14x311', 'W14x311', 'W14x311', 'W14x257'])
frame.step2_finished()

# Step-3, set load and material property
frame.LoadAndMaterial.set_material(206000, 248, 345)
frame.step3_finished()

# Step-4, set connection and boundary condition
# Loads and masses are temporarily not specified
frame.ConnectionAndBoundary.set_base_support('Fixed')
frame.ConnectionAndBoundary.set_beam_column_connection('Full')
frame.ConnectionAndBoundary.set_panel_zone_deformation(True)
frame.ConnectionAndBoundary.rigid_disphragm = True
frame.step4_finished()

frame.all_steps_finished()

# Step-A, bacause none load was defined, additional cammands should added to directly define story mass and load
#                             floor  [mass on each axis]
frame.LoadAndMaterial.mass_node[2] = [479/5] * 5
frame.LoadAndMaterial.mass_node[3] = [479/5] * 5
frame.LoadAndMaterial.mass_node[4] = [520/5] * 5
#                          floor  [gravity load on each axis]
frame.LoadAndMaterial.F_node[2] = [479/5*1e4] * 5
frame.LoadAndMaterial.F_node[3] = [479/5*1e4] * 5
frame.LoadAndMaterial.F_node[4] = [520/5*1e4] * 5

frame.generate_tcl_script(Path(__file__).parent.parent/'output')
