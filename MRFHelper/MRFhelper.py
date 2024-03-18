from pathlib import Path
from typing import Literal
from .BuildingGeometry import BuildingGeometry
from .StructuralComponents import StructuralComponents
from .ConnectionAndBoundary import ConnectionAndBoundary
from .LoadAndMaterial import LoadAndMaterial
from .UserCommand import UserCommand
from . import WriteInfo
from . import WriteScript


class Frame:
    def __init__(self, frame_name: str, notes: str=None):
        """Use this class to define structural parameters of steel moment resisting frame (MRF)
        and write tcl script for analysis using OpenSees. Make sure all the units are [N, mm, t].

        Args:
            frame_name (str): Give a name for the considered frame
            notes (str, optional): Optional notes
        """
        self.frame_name = frame_name
        self.notes = notes
        self.BuildingGeometry = BuildingGeometry()

    def step1_finished(self):
        """Complete define building geometry"""
        self.BuildingGeometry._finish()
        self.N = self.BuildingGeometry.N  # number of stories
        self.bays = self.BuildingGeometry.bays  # number of bays
        self.axis = self.BuildingGeometry.axis  # number of axes
        self.StructuralComponents = StructuralComponents(self)

    def step2_finished(self):
        """Complete define structural components"""
        self.StructuralComponents._finish()
        self.LoadAndMaterial = LoadAndMaterial(self)

    def step3_finished(self):
        """Complete define load and material"""
        self.LoadAndMaterial._finished()
        self.ConnectionAndBoundary = ConnectionAndBoundary(self)

    def step4_finished(self):
        """Complete define connection and boundary"""
        self.ConnectionAndBoundary._finished()
        self.recorders = {
            'Reactions': True,
            'Drift': True,
            'FloorAccel': True,
            'FloorVel': True,
            'FloorDisp': True,
            'ColumnForce': True,
            'ColumnHinge': True,
            'BeamHinge': True,
            'PanelZone': True
        }
        self.UserComment = UserCommand()

    def all_steps_finished(self):
        """Calculate simulation parameters and write them into tcl script"""
        self.StructuralComponents._get_section_properties(self)
        self.StructuralComponents._get_panel_zone_thickness()
        self.LoadAndMaterial._calculate_load(self)
        self.LoadAndMaterial._calculate_PPy(self)

    def generate_tcl_script(self, dir_):
        """Write tcl script"""
        self.output_path = Path(dir_)
        if not self.output_path.exists():
            Path.mkdir(self.output_path)
        self.builiding_info = WriteInfo.write_info(self)
        WriteScript.WriteScript(self)



def Repository(model: Literal['4SMRF', '3S_Benchmark', '9S_Benchmark']) -> Frame:
    """Get an available model from the repository

    Args:
        model (str, optional): Model name

    Returns:
        Frame: Object of `Frame`
    """
    model_repository = ['4SMRF', '3S_Benchmark', '9S_Benchmark']
    if model not in model_repository:
        error = f'Model {model} is not available\n'
        error += f'Available models:\n'
        available_models = ','.join(model_repository)
        error += f'    {available_models}'
        raise ValueError(error)
    frame = _extract_model(model)
    return frame


def _extract_model(model):
    if model == '4SMRF':
        frame = Frame('4SMRF')

        # Step-1, set building geometry
        frame.BuildingGeometry.story_height = [4300, 4000, 4000, 4000]
        frame.BuildingGeometry.bay_length = [6100, 6100, 6100]
        frame.BuildingGeometry.plane_dimensions = (42700, 30500)
        frame.BuildingGeometry.MF_number = 2
        frame.BuildingGeometry.exterior_column_tributary_area = (9150, 3050)
        frame.BuildingGeometry.interior_column_tributary_area = (6100, 3050)
        frame.step1_finished()

        # Step-2, set structural component sections
        # (floor, ['section1', 'section2', ...])
        frame.StructuralComponents.set_beams(2, ['W24x76', 'W24x76', 'W24x76'])
        frame.StructuralComponents.set_beams(3, ['W24x76', 'W24x76', 'W24x76'])
        frame.StructuralComponents.set_beams(4, ['W18x60', 'W18x60', 'W18x60'])
        frame.StructuralComponents.set_beams(5, ['W18x60', 'W18x60', 'W18x60'])
        # (story, ['section1', 'section2', ...])
        frame.StructuralComponents.set_columns(1, ['W24x103', 'W24x146', 'W24x146', 'W24x103'])
        frame.StructuralComponents.set_columns(2, ['W24x103', 'W24x146', 'W24x146', 'W24x103'])
        frame.StructuralComponents.set_columns(3, ['W24x103', 'W24x146', 'W24x146', 'W24x103'])
        frame.StructuralComponents.set_columns(4, ['W24x76', 'W24x84', 'W24x84', 'W24x76'])
        # (floor, ['thickness1', 'thickness2', ...])
        frame.StructuralComponents.set_doubler_plate(2, [6.35, 23.8125, 23.8125, 6.35])
        frame.StructuralComponents.set_doubler_plate(3, [6.35, 23.8125, 23.8125, 6.35])
        frame.StructuralComponents.set_doubler_plate(4, [6.35, 22.225, 22.225, 6.35])
        frame.StructuralComponents.set_doubler_plate(5, [6.35, 22.225, 22.225, 6.35])
        frame.StructuralComponents.set_column_splice(3)  # Floor numbers where the column splices are located
        # frame.StructuralComponents.set_beam_splice(2)  # Bay numbers where the beam splices are located
        frame.step2_finished()

        # Step-3, set load and material property
        # ([numbers of floor or story], [load values])
        frame.LoadAndMaterial.set_dead_load([2, 3, 4, 5], [4.3e-3, 4.3e-3, 4.3e-3, 4.3e-3])
        frame.LoadAndMaterial.set_live_load([2, 3, 4, 5], [2.4e-3, 2.4e-3, 2.4e-3, 0.96e-3])
        frame.LoadAndMaterial.set_cladding_load([1, 2, 3, 4], [1.2e-3, 1.2e-3, 1.2e-3, 1.2e-3])
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

        print('Archetype 4-story steel moment resisting frame:')
        print('[1] Skiadopoulos Andronikos, Dimitrios Lignos. Design summaries of steel moment resisting frames with elastic and dissipative panel zones. National Conference on Earthquake Engineering. Zenodo (2022). https://doi.org/10.5281/zenodo.5962407')
        print('[2] Skiadopoulos Andronikos, Dimitrios Lignos. Seismic demands of steel moment resisting frames with inelastic beam‐to‐column web panel zones. Earthquake Engineering & Structural Dynamics 51.7 (2022): 1591-1609.')
        return frame

    if model == '3S_Benchmark':
        frame = Frame('3S_Benchmark')

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

        print('3-story benchmark steel moment resisting frame')
        return frame


    if model == '9S_Benchmark':
        frame = Frame('9S_Benchmark')

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

        print('9-story benchmark steel moment resisting frame')
        return frame