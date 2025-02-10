import json
from pathlib import Path
from .BuildingGeometry import BuildingGeometry
from .StructuralComponents import StructuralComponents
from .ConnectionAndBoundary import ConnectionAndBoundary
from .LoadAndMaterial import LoadAndMaterial
from .UserCommand import UserCommand
from . import WriteInfo
from . import WriteScript
from . import __version__


VERSION = __version__

class Frame:
    version = VERSION

    def __init__(self, frame_name: str, notes: str=None):
        """Use this class to define structural parameters of steel moment resisting frame (MRF)
        and write tcl script for analysis using OpenSees. Make sure all the units are [N, mm, t].

        Args:
            frame_name (str): Give a name for the considered frame
            notes (str, optional): Optional notes
        """
        if not frame_name.isidentifier():
            raise ValueError(f'Illegal frame name: {frame_name}')
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
        self.dict_info = WriteInfo.write_info_to_dict(self)

    def generate_tcl_script(self, dir_):
        """Write tcl script"""
        self.output_path = Path(dir_)
        if not self.output_path.exists():
            Path.mkdir(self.output_path)
        self.builiding_info = WriteInfo.write_info_to_tcl(self)
        WriteScript.WriteScript(self)


def from_json(file: str | Path) -> Frame:
    """Get an available model from json file

    Args:
        file (str | Path): file path

    Returns:
        Frame: Object of `Frame`
    """
    file = Path(file)
    if not file.exists():
        raise FileExistsError(f'file not found')
    with open(file, 'r') as f:
        dict_info = json.load(f)
    frame = Frame(dict_info['name'])
    # Step 1
    frame.BuildingGeometry.story_height = dict_info['BuildingGeometry']['story_height']
    frame.BuildingGeometry.bay_length = dict_info['BuildingGeometry']['bay_length']
    frame.BuildingGeometry.plane_dimensions = tuple(dict_info['BuildingGeometry']['plane_dimensions'])
    frame.BuildingGeometry.MF_number = dict_info['BuildingGeometry']['MF_number']
    frame.BuildingGeometry.exterior_column_tributary_area = tuple(dict_info['BuildingGeometry']['exterior_column_tributary_area'])
    frame.BuildingGeometry.interior_column_tributary_area = tuple(dict_info['BuildingGeometry']['interior_column_tributary_area'])
    frame.step1_finished()
    # Step 2
    for FF, sections in dict_info['StructuralComponents']['beams'].items():
        frame.StructuralComponents.set_beams(int(FF), sections)
    for SS, sections in dict_info['StructuralComponents']['columns'].items():
        frame.StructuralComponents.set_columns(int(SS), sections)
    for FF, thickness in dict_info['StructuralComponents']['set_doubler_plate'].items():
        frame.StructuralComponents.set_doubler_plate(int(FF), thickness)
    frame.StructuralComponents.set_column_splice(*dict_info['StructuralComponents']['column_splice'])
    frame.StructuralComponents.set_beam_splice(*dict_info['StructuralComponents']['beam_splice'])
    if dict_info['StructuralComponents']['RBS_length']:
        frame.StructuralComponents.set_RBS_length(dict_info['StructuralComponents']['RBS_length'])
    frame.step2_finished()
    # Step 3
    FF_ls = list(int(i) for i in dict_info['LoadAndMaterial']['dead_load'].keys())
    SS_ls = list(int(i) for i in dict_info['LoadAndMaterial']['clading_load'].keys())
    frame.LoadAndMaterial.set_dead_load(FF_ls, list(dict_info['LoadAndMaterial']['dead_load'].values()))
    frame.LoadAndMaterial.set_live_load(FF_ls, list(dict_info['LoadAndMaterial']['live_load'].values()))
    frame.LoadAndMaterial.set_cladding_load(SS_ls, list(dict_info['LoadAndMaterial']['clading_load'].values()))
    frame.LoadAndMaterial.set_weight_combination_coefficients(dict_info['LoadAndMaterial']['weight_combination_coefficients'])
    frame.LoadAndMaterial.set_mass_combination_coefficients(dict_info['LoadAndMaterial']['mass_combination_coefficients'])
    material = dict_info['LoadAndMaterial']['material']
    frame.LoadAndMaterial.set_material(material['E'], material["fy_beam"], material["fy_column"], material["miu"])
    frame.step3_finished()
    # Step 4
    frame.ConnectionAndBoundary.set_base_support(dict_info['ConnectionAndBoundary']['base_support'])
    frame.ConnectionAndBoundary.set_beam_column_connection(dict_info['ConnectionAndBoundary']['beam_column_connection'])
    frame.ConnectionAndBoundary.set_panel_zone_deformation(dict_info['ConnectionAndBoundary']['panel_zone_deformation'])
    if dict_info['ConnectionAndBoundary']['soil_constraint']:
        frame.ConnectionAndBoundary.set_soil_constraint(dict_info['ConnectionAndBoundary']['soil_constraint'])
    frame.step4_finished()
    # finish
    frame.all_steps_finished()
    frame.dict_info['References'] = dict_info['References']
    return frame