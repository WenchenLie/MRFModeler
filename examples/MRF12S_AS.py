from pathlib import Path
try:
    from MRFHelper.MRFhelper import Frame
except ImportError:
    raise ImportError('Run command "pip install mrfhelper" to install this package')


frame = Frame('MRF12S')

# Step-1, set building geometry
frame.BuildingGeometry.story_height = [4200, 4000, 4000, 4000, 4000, 4000, 4000, 4000, 4000, 4000, 4000, 4000]
frame.BuildingGeometry.bay_length = [6100, 6100, 6100]
frame.BuildingGeometry.plane_dimensions = (42700, 30500)
frame.BuildingGeometry.MF_number = 2
frame.BuildingGeometry.exterior_column_tributary_area = (9150, 3050)
frame.BuildingGeometry.interior_column_tributary_area = (6100, 3050)
frame.step1_finished()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.StructuralComponents.set_beams(2, ['W30x132', 'W30x132', 'W30x132'])
frame.StructuralComponents.set_beams(3, ['W30x132', 'W30x132', 'W30x132'])
frame.StructuralComponents.set_beams(4, ['W30x132', 'W30x132', 'W30x132'])
frame.StructuralComponents.set_beams(5, ['W30x132', 'W30x132', 'W30x132'])
frame.StructuralComponents.set_beams(6, ['W30x124', 'W30x124', 'W30x124'])
frame.StructuralComponents.set_beams(7, ['W30x124', 'W30x124', 'W30x124'])
frame.StructuralComponents.set_beams(8, ['W30x108', 'W30x108', 'W30x108'])
frame.StructuralComponents.set_beams(9, ['W30x108', 'W30x108', 'W30x108'])
frame.StructuralComponents.set_beams(10, ['W27x94', 'W27x94', 'W27x94'])
frame.StructuralComponents.set_beams(11, ['W27x94', 'W27x94', 'W27x94'])
frame.StructuralComponents.set_beams(12, ['W24x76', 'W24x76', 'W24x76'])
frame.StructuralComponents.set_beams(13, ['W24x76', 'W24x76', 'W24x76'])
# (story, ['section1', 'section2', ...])
frame.StructuralComponents.set_columns(1, ['W27x235', 'W27x281', 'W27x281', 'W27x235'])
frame.StructuralComponents.set_columns(2, ['W27x235', 'W27x281', 'W27x281', 'W27x235'])
frame.StructuralComponents.set_columns(3, ['W27x235', 'W27x281', 'W27x281', 'W27x235'])
frame.StructuralComponents.set_columns(4, ['W27x217', 'W27x258', 'W27x258', 'W27x217'])
frame.StructuralComponents.set_columns(5, ['W27x217', 'W27x258', 'W27x258', 'W27x217'])
frame.StructuralComponents.set_columns(6, ['W27x178', 'W27x217', 'W27x217', 'W27x178'])
frame.StructuralComponents.set_columns(7, ['W27x178', 'W27x217', 'W27x217', 'W27x178'])
frame.StructuralComponents.set_columns(8, ['W27x129', 'W27x194', 'W27x194', 'W27x129'])
frame.StructuralComponents.set_columns(9, ['W27x129', 'W27x194', 'W27x194', 'W27x129'])
frame.StructuralComponents.set_columns(10, ['W27x114', 'W27x129', 'W27x129', 'W27x114'])
frame.StructuralComponents.set_columns(11, ['W27x114', 'W27x129', 'W27x129', 'W27x114'])
frame.StructuralComponents.set_columns(12, ['W27x94', 'W27x102', 'W27x102', 'W27x94'])
# (floor, ['thickness1', 'thickness2', ...])
frame.StructuralComponents.set_doubler_plate(2, [i * 25.4 for i in [4/16, 19/16, 19/16, 4/16]])
frame.StructuralComponents.set_doubler_plate(3, [i * 25.4 for i in [4/16, 18/16, 18/16, 4/16]])
frame.StructuralComponents.set_doubler_plate(4, [i * 25.4 for i in [5/16, 21/16, 21/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(5, [i * 25.4 for i in [5/16, 21/16, 21/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(6, [i * 25.4 for i in [6/16, 21/16, 21/16, 6/16]])
frame.StructuralComponents.set_doubler_plate(7, [i * 25.4 for i in [6/16, 21/16, 21/16, 6/16]])
frame.StructuralComponents.set_doubler_plate(8, [i * 25.4 for i in [5/16, 17/16, 17/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(9, [i * 25.4 for i in [5/16, 17/16, 17/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(10, [i * 25.4 for i in [5/16, 17/16, 17/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(11, [i * 25.4 for i in [5/16, 17/16, 17/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(12, [i * 25.4 for i in [4/16, 15/16, 15/16, 4/16]])
frame.StructuralComponents.set_doubler_plate(13, [i * 25.4 for i in [4/16, 15/16, 15/16, 4/16]])
frame.StructuralComponents.set_column_splice(3, 5, 7, 9, 11)  # Floor numbers where the column splices are located
frame.StructuralComponents.set_beam_splice(2)  # Bay numbers where the beam splices are located
frame.step2_finished()

# Step-3, set load and material property
# ([numbers of floor or story], [load values])
frame.LoadAndMaterial.set_dead_load([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], [4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3])
frame.LoadAndMaterial.set_live_load([2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], [2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 0.96e-3])
frame.LoadAndMaterial.set_cladding_load([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], [1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3])
# ({load type: combination coefficient})
frame.LoadAndMaterial.set_weight_combination_coefficients({'Dead': 1.05, 'Live': 0.25, 'Cladding': 1.05})
frame.LoadAndMaterial.set_mass_combination_coefficients({'Dead': 1, 'Live': 0, 'Cladding': 1})
frame.LoadAndMaterial.set_material(206000, 345, 345)
frame.step3_finished()

# Step-4, set connection and boundary condition
frame.ConnectionAndBoundary.set_base_support('Fixed')
frame.ConnectionAndBoundary.set_beam_column_connection('Full')
frame.ConnectionAndBoundary.set_panel_zone_deformation(True)
frame.step4_finished()

frame.all_steps_finished()
frame.dict_info['References'] = [
    "Archetype 4-story steel moment resisting frame",
    "[1] Andronikos Skiadopoulos, Dimitrios Lignos. Design summaries of steel moment resisting frames with elastic and dissipative panel zones. National Conference on Earthquake Engineering. Zenodo (2022). https://doi.org/10.5281/zenodo.5962407",
    "[2] Andronikos Skiadopoulos, Dimitrios Lignos. Seismic demands of steel moment resisting frames with inelastic beam‐to‐column web panel zones. Earthquake Engineering & Structural Dynamics 51.7 (2022): 1591-1609."
]
frame.generate_tcl_script(Path(__file__).parent.parent/'output')
