from pathlib import Path
try:
    from MRFHelper.MRFhelper import Frame
except ImportError:
    raise ImportError('Run command "pip install mrfhelper" to install this package')


frame = Frame('MRF8S')

# Step-1, set building geometry
frame.BuildingGeometry.story_height = [4200, 4000, 4000, 4000, 4000, 4000, 4000, 4000]
frame.BuildingGeometry.bay_length = [6100, 6100, 6100]
frame.BuildingGeometry.plane_dimensions = (42700, 30500)
frame.BuildingGeometry.MF_number = 2
frame.BuildingGeometry.exterior_column_tributary_area = (9150, 3050)
frame.BuildingGeometry.interior_column_tributary_area = (6100, 3050)
frame.step1_finished()

# Step-2, set structural component sections
# (floor, ['section1', 'section2', ...])
frame.StructuralComponents.set_beams(2, ['W27x102', 'W27x102', 'W27x102'])
frame.StructuralComponents.set_beams(3, ['W27x102', 'W27x102', 'W27x102'])
frame.StructuralComponents.set_beams(4, ['W27x94', 'W27x94', 'W27x94'])
frame.StructuralComponents.set_beams(5, ['W27x94', 'W27x94', 'W27x94'])
frame.StructuralComponents.set_beams(6, ['W24x76', 'W24x76', 'W24x76'])
frame.StructuralComponents.set_beams(7, ['W24x76', 'W24x76', 'W24x76'])
frame.StructuralComponents.set_beams(8, ['W21x68', 'W21x68', 'W21x68'])
frame.StructuralComponents.set_beams(9, ['W21x68', 'W21x68', 'W21x68'])
# (story, ['section1', 'section2', ...])
frame.StructuralComponents.set_columns(1, ['W24x162', 'W24x192', 'W24x192', 'W24x162'])
frame.StructuralComponents.set_columns(2, ['W24x162', 'W24x192', 'W24x192', 'W24x162'])
frame.StructuralComponents.set_columns(3, ['W24x162', 'W24x192', 'W24x192', 'W24x162'])
frame.StructuralComponents.set_columns(4, ['W24x131', 'W24x176', 'W24x176', 'W24x131'])
frame.StructuralComponents.set_columns(5, ['W24x131', 'W24x176', 'W24x176', 'W24x131'])
frame.StructuralComponents.set_columns(6, ['W24x103', 'W24x131', 'W24x131', 'W24x103'])
frame.StructuralComponents.set_columns(7, ['W24x103', 'W24x131', 'W24x131', 'W24x103'])
frame.StructuralComponents.set_columns(8, ['W24x94', 'W24x94', 'W24x94', 'W24x94'])
# (floor, ['thickness1', 'thickness2', ...])
frame.StructuralComponents.set_doubler_plate(2, [i * 25.4 for i in [5/16, 20/16, 20/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(3, [i * 25.4 for i in [5/16, 20/16, 20/16, 5/16]])
frame.StructuralComponents.set_doubler_plate(4, [i * 25.4 for i in [6/16, 18/16, 18/16, 6/16]])
frame.StructuralComponents.set_doubler_plate(5, [i * 25.4 for i in [6/16, 18/16, 18/16, 6/16]])
frame.StructuralComponents.set_doubler_plate(6, [i * 25.4 for i in [4/16, 16/16, 16/16, 4/16]])
frame.StructuralComponents.set_doubler_plate(7, [i * 25.4 for i in [4/16, 16/16, 16/16, 4/16]])
frame.StructuralComponents.set_doubler_plate(8, [i * 25.4 for i in [4/16, 15/16, 15/16, 4/16]])
frame.StructuralComponents.set_doubler_plate(9, [i * 25.4 for i in [4/16, 15/16, 15/16, 4/16]])
frame.StructuralComponents.set_column_splice(3, 5, 7)  # Floor numbers where the column splices are located
frame.StructuralComponents.set_beam_splice(2)  # Bay numbers where the beam splices are located
frame.step2_finished()

# Step-3, set load and material property
# ([numbers of floor or story], [load values])
frame.LoadAndMaterial.set_dead_load([2, 3, 4, 5, 6, 7, 8, 9], [4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3])
frame.LoadAndMaterial.set_live_load([2, 3, 4, 5, 6, 7, 8, 9], [2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 2.4e-3, 0.96e-3])
frame.LoadAndMaterial.set_cladding_load([1, 2, 3, 4, 5, 6, 7, 8], [1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3])
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
