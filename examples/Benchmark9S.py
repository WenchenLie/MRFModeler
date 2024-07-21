from pathlib import Path
try:
    from MRFHelper.MRFhelper import Frame
except ImportError:
    raise ImportError('Run command "pip install mrfhelper" to install this package')


frame = Frame('Benchmark_9S')

# Step-1, set building geometry
frame.BuildingGeometry.story_height = [3650, 5490, 3960, 3960, 3960, 3960, 3960, 3960, 3960, 3960]
frame.BuildingGeometry.bay_length = [9150, 9150, 9150, 9150, 9150]
frame.BuildingGeometry.plane_dimensions = (9150*5, 9150*5)
frame.BuildingGeometry.MF_number = 6
frame.BuildingGeometry.exterior_column_tributary_area = (9150/2, 9150/2)
frame.BuildingGeometry.interior_column_tributary_area = (9150, 9150/2)
frame.step1_finished()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.StructuralComponents.set_beams(2, ['W36x160', 'W36x160', 'W36x160', 'W36x160', 'W36x160'])
frame.StructuralComponents.set_beams(3, ['W36x160', 'W36x160', 'W36x160', 'W36x160', 'W36x160'])
frame.StructuralComponents.set_beams(4, ['W36x160', 'W36x160', 'W36x160', 'W36x160', 'W36x160'])
frame.StructuralComponents.set_beams(5, ['W36x135', 'W36x135', 'W36x135', 'W36x135', 'W36x135'])
frame.StructuralComponents.set_beams(6, ['W36x135', 'W36x135', 'W36x135', 'W36x135', 'W36x135'])
frame.StructuralComponents.set_beams(7, ['W36x135', 'W36x135', 'W36x135', 'W36x135', 'W36x135'])
frame.StructuralComponents.set_beams(8, ['W36x135', 'W36x135', 'W36x135', 'W36x135', 'W36x135'])
frame.StructuralComponents.set_beams(9, ['W30x99', 'W30x99', 'W30x99', 'W30x99', 'W30x99'])
frame.StructuralComponents.set_beams(10, ['W27x84', 'W27x84', 'W27x84', 'W27x84', 'W27x84'])
frame.StructuralComponents.set_beams(11, ['W24x68', 'W24x68', 'W24x68', 'W24x68', 'W24x68'])
# (story, ['section1', 'section2', ...])
frame.StructuralComponents.set_columns(1, ['W14x500', 'W14x500', 'W14x500', 'W14x500', 'W14x500', 'W14x500'])
frame.StructuralComponents.set_columns(2, ['W14x500', 'W14x500', 'W14x500', 'W14x500', 'W14x500', 'W14x500'])
frame.StructuralComponents.set_columns(3, ['W14x455', 'W14x455', 'W14x455', 'W14x455', 'W14x455', 'W14x455'])
frame.StructuralComponents.set_columns(4, ['W14x455', 'W14x455', 'W14x455', 'W14x455', 'W14x455', 'W14x455'])
frame.StructuralComponents.set_columns(5, ['W14x370', 'W14x370', 'W14x370', 'W14x370', 'W14x370', 'W14x370'])
frame.StructuralComponents.set_columns(6, ['W14x370', 'W14x370', 'W14x370', 'W14x370', 'W14x370', 'W14x370'])
frame.StructuralComponents.set_columns(7, ['W14x283', 'W14x283', 'W14x283', 'W14x283', 'W14x283', 'W14x283'])
frame.StructuralComponents.set_columns(8, ['W14x283', 'W14x283', 'W14x283', 'W14x283', 'W14x283', 'W14x283'])
frame.StructuralComponents.set_columns(9, ['W14x257', 'W14x257', 'W14x257', 'W14x257', 'W14x257', 'W14x257'])
frame.StructuralComponents.set_columns(10, ['W14x257', 'W14x257', 'W14x257', 'W14x257', 'W14x257', 'W14x257'])
# column splices
frame.StructuralComponents.set_column_splice(3, 5, 7, 9)
frame.step2_finished()

# Step-3, set load and material property
frame.LoadAndMaterial.set_material(206000, 248, 345)
frame.step3_finished()

# Step-4, set connection and boundary condition
# Loads and masses are temporarily not specified
frame.ConnectionAndBoundary.set_base_support('Pinned')
frame.ConnectionAndBoundary.set_beam_column_connection('Full')
frame.ConnectionAndBoundary.set_panel_zone_deformation(True)
frame.ConnectionAndBoundary.rigid_disphragm = True
frame.step4_finished()

frame.recorders['BeamHinge'] = False
frame.recorders['ColumnHinge'] = False
frame.recorders['PanelZone'] = False
frame.all_steps_finished()

# Step-A, bacause none load was defined, additional cammands should added to directly define story mass and load
#                             floor  [mass on each axis]
frame.LoadAndMaterial.mass_node[2] = [483/5] * 6
frame.LoadAndMaterial.mass_node[3] = [505/5] * 6
frame.LoadAndMaterial.mass_node[4] = [495/5] * 6
frame.LoadAndMaterial.mass_node[5] = [495/5] * 6
frame.LoadAndMaterial.mass_node[6] = [495/5] * 6
frame.LoadAndMaterial.mass_node[7] = [495/5] * 6
frame.LoadAndMaterial.mass_node[8] = [495/5] * 6
frame.LoadAndMaterial.mass_node[9] = [495/5] * 6
frame.LoadAndMaterial.mass_node[10] = [495/5] * 6
frame.LoadAndMaterial.mass_node[11] = [535/5] * 6
#                          floor  [gravity load on each axis]
frame.LoadAndMaterial.F_node[2] = [483/5*1e4] * 6
frame.LoadAndMaterial.F_node[3] = [505/5*1e4] * 6
frame.LoadAndMaterial.F_node[4] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[5] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[6] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[7] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[8] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[9] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[10] = [495/5*1e4] * 6
frame.LoadAndMaterial.F_node[11] = [535/5*1e4] * 6

frame.generate_tcl_script(Path(__file__).parent.parent/'output')
