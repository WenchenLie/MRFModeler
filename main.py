from MRFHelper import MRFhelper


# frame = MRFhelper.Repository('3S_Benchmark')
# frame.generate_tcl_script('output')


# frame = MRFhelper.Repository('MRF_4S_AS')
frame = MRFhelper.Repository('MRF_4S_AE')
frame.generate_tcl_script('test')




frame = MRFhelper.Frame('RCF6S')

# # Step-1, set building geometry
# frame.BuildingGeometry.story_height = [4300, 4000, 4000, 4000, 4000, 4000]
# frame.BuildingGeometry.bay_length = [6000, 3000, 6000]
# frame.BuildingGeometry.plane_dimensions = (15000, 45000)
# frame.BuildingGeometry.MF_number = 5
# frame.BuildingGeometry.exterior_column_tributary_area = (6100+6100/2, 6100/2)
# frame.BuildingGeometry.interior_column_tributary_area = (6100, 6100/2)
# frame.step1_finished()

# # Step-2, set structural component sections
# # (floor, ['section1', 'section2', ...])
# frame.StructuralComponents.set_beams(2, ['W21x73', 'W21x73', 'W21x73'])
# frame.StructuralComponents.set_beams(3, ['W21x73', 'W21x73', 'W21x73'])
# frame.StructuralComponents.set_beams(4, ['W21x57', 'W21x57', 'W21x57'])
# frame.StructuralComponents.set_beams(5, ['W21x57', 'W21x57', 'W21x57'])
# frame.StructuralComponents.set_beams(6, ['W21x57', 'W21x57', 'W21x57'])
# frame.StructuralComponents.set_beams(7, ['W21x57', 'W21x57', 'W21x57'])
# # (story, ['section1', 'section2', ...])
# frame.StructuralComponents.set_columns(1, ['W24x103', 'W24x103', 'W24x103', 'W24x103'])
# frame.StructuralComponents.set_columns(2, ['W24x103', 'W24x103', 'W24x103', 'W24x103'])
# frame.StructuralComponents.set_columns(3, ['W24x103', 'W24x103', 'W24x103', 'W24x103'])
# frame.StructuralComponents.set_columns(4, ['W24x62', 'W24x62', 'W24x62', 'W24x62'])
# frame.StructuralComponents.set_columns(5, ['W24x62', 'W24x62', 'W24x62', 'W24x62'])
# frame.StructuralComponents.set_columns(6, ['W24x62', 'W24x62', 'W24x62', 'W24x62'])
# # (floor, [thickness1, thickness2, ...])
# frame.StructuralComponents.set_doubler_plate(2, [0, 7.9, 7.9, 0])
# frame.StructuralComponents.set_doubler_plate(3, [0, 7.9, 7.9, 0])
# frame.StructuralComponents.set_doubler_plate(4, [0, 7.9, 7.9, 0])
# frame.StructuralComponents.set_doubler_plate(5, [0, 7.9, 7.9, 0])
# frame.step2_finished()

# # Step-3, set load and material property
# # ([numbers of floor or story], [load values])
# frame.LoadAndMaterial.set_dead_load([2, 3, 4, 5, 6, 7], [4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3])
# frame.LoadAndMaterial.set_live_load([2, 3, 4, 5, 6, 7], [2.4e-3, 2.4e-3, 2.4e-3, 0.96e-3, 0.96e-3, 0.96e-3])
# frame.LoadAndMaterial.set_cladding_load([1, 2, 3, 4, 5, 6], [1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3])
# # ({load type: combination coefficient})
# frame.LoadAndMaterial.set_weight_combination_coefficients({'Dead': 1.05, 'Live': 0.25, 'Cladding': 1.05})
# frame.LoadAndMaterial.set_mass_combination_coefficients({'Dead': 1, 'Live': 0, 'Cladding': 1})
# frame.LoadAndMaterial.set_material(206000, 345, 345)
# frame.step3_finished()

# # Step-4, set connection and boundary condition
# # Loads and masses are temporarily not specified
# frame.ConnectionAndBoundary.set_base_support('Fixed')
# frame.ConnectionAndBoundary.set_beam_column_connection('Hinged')
# frame.ConnectionAndBoundary.set_panel_zone_deformation(False)
# frame.ConnectionAndBoundary.rigid_disphragm = True
# frame.step4_finished()

# frame.all_steps_finished()
# frame.generate_tcl_script('output')