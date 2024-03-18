from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .MRFhelper import Frame
from typing import Dict
from wsection import WSection
from . import func


class StructuralComponents:

    def __init__(self, frame: Frame):
        """Step-2:
        Structural components parameters  
        """
        self.N = frame.N
        self.bays = frame.bays
        self.axis = frame.axis
        self.beams: Dict[int, str] = dict()  # Necessary
        self.columns: Dict[int, str] = dict()  # Necessary
        self.column_splice = tuple()  # Unecessary
        self.beam_splice = tuple()  # Unecessary
        self.RBS_length_all = None  # Use same RBS length for all beams
        self.doubler_plate = dict()  # Unecessary
        # initialize doubler plate thickness
        for floor in range(2, self.N + 2):
            self.doubler_plate[floor] = [0] * self.axis

    def set_beams(self, floor: int, sections: list[str]):
        """Set beam sizes

        Args:
            floor (int): floor number, must be larger than 2
            sections (list[str]): A list including all w-section types for the floor

        Example:
            >>> set_beams(2, ['W24x64', 'W24x64', 'W24x64'])
            The beam section for the 2rd floor is designated as W24x64
        """
        func.check_int(floor, min_max=[2, self.N + 1], name='floor')
        func.check_list(sections, length=self.bays, pos=False, name=' beam section')
        self.beams[floor] = sections


    def set_columns(self, story: int, sections: list[str]):
        """Set column sizes, if there is a column splice, input according to the
           cross-section at the bottom of the column

        Args:
            story (int): story number
            sections (list[str]): A list including all w-section types for the story
            
        """
        func.check_int(story, min_max=[1, self.N], name='axis')
        func.check_list(sections, length=self.axis, pos=False, name='column section')
        self.columns[story] = sections


    def set_column_splice(self, *story: int):
        """Set the stories where column splices are located.

        Args:
            story (list): Defaults to ().
        """
        if story:
            func.check_tuple(story, min_length=1, max_length=self.N)
            for val in story:
                func.check_int(val, [1, self.N], 'story')
                if val == self.N:
                    raise ValueError(f'Column splice cannot be placed at the top story ({self.N})')
            self.column_splice = story


    def set_beam_splice(self, *bay: int):
        """Set the stories where beam splices are located.

        Args:
            bay (list): Defaults to ().
        """
        if bay:
            func.check_tuple(bay, min_length=1, max_length=self.bays)
            for val in bay:
                func.check_int(val, [1, self.bays], 'bay')
            self.beam_splice = bay


    def set_doubler_plate(self, floor: int, thicknesses: list[int | float]):
        """(Optional) Set doubler plate (if any) thickness for the panel zone

        Args:
            floor (int): Floor number of the panel zone
            thicknesses (list[int  |  float]): A list including all doubler plate thickness values for the floor
        """
        func.check_int(floor, [2, 99], name='floor')
        func.check_list(thicknesses, length=self.axis, name='doubler plate thickness')
        self.doubler_plate[floor] = thicknesses


    def set_RBS_length(self, RBS_length: int | float):
        """(Optional) Set RBS length (distance from beam hinge to panel zone edge)

        Args:
            RBS_length (int | float): Offset distance of the beam hinge
        """
        func.check_int_float(RBS_length, name='RBS_length')
        self.RBS_length_all = RBS_length


    def _finish(self):
        floor_set = set([2 + i for i in range(self.N)])
        floor_defined_beam = set(self.beams.keys())
        if floor_set == floor_defined_beam:
            pass
        else:
            if floor_set - floor_defined_beam:
                raise ValueError(f'Beams on the floor {floor_set - floor_defined_beam} have not been defined')
            if floor_defined_beam - floor_set:
                raise ValueError(f'Beams on the floor {floor_defined_beam - floor_set} are not existed')
        for key, val in self.columns.items():
            if len(val) != self.axis:
                raise ValueError(f'Number of defined column of stort {key} is less than the axis number ({self.axis})')


    def _get_section_properties(self, frame: Frame):
        """Get beam and column properties
        * beam_properties (dict): {floor, [[bf, h, ...], [bf, h, ...], ...(x bays)]}
        * column_properties (dict): {story, [[bf, h, ...], [bf, h, ...], ...(x N)]}
        * RBS_length (dict): {floor: [l1, l2, ...(x 2*bays)]}
        """
        fy_beam = frame.LoadAndMaterial.fy_beam
        fy_column = frame.LoadAndMaterial.fy_column
        BC_connection = frame.ConnectionAndBoundary.beam_column_connection
        RBS_paras = frame.ConnectionAndBoundary.RBS_paras
        self.beam_properties = dict()
        for floor, sections in self.beams.items():
            props = []
            for section in sections:
                prop = WSection(section, fy_beam)
                #                  0        1       2        3        4        5       6        7       8
                props.append([prop.bf, prop.d, prop.tw, prop.tf, prop.ry, prop.A, prop.Ix, prop.My, prop.h])
            self.beam_properties[floor] = props

        # column properties
        self.column_properties = dict()
        for story, sections in self.columns.items():
            props = []
            for section in sections:
                prop = WSection(section, fy_column)
                #                  0        1       2        3        4        5       6        7       8
                props.append([prop.bf, prop.d, prop.tw, prop.tf, prop.ry, prop.A, prop.Ix, prop.My, prop.h])
            self.column_properties[story] = props

        # RBS length
        self.RBS_length = dict()
        for floor in range(2, self.N + 2):
            if self.RBS_length_all:
                self.RBS_length[floor] = [self.RBS_length_all, self.RBS_length_all] * self.bays
            elif BC_connection in ['Full', 'Hinged']:
                self.RBS_length[floor] = [0, 0] * self.bays
            elif BC_connection == 'RBS':
                a, b, c = RBS_paras
                RBS_length_floor = []
                for id_bay in range(self.bays):  # Index for bay
                    bf_beam = self.beam_properties[floor][id_bay][0]
                    h_beam = self.beam_properties[floor][id_bay][1]
                    RBS_length_floor.append(a*bf_beam + 0.5*b*h_beam)
                    RBS_length_floor.append(a*bf_beam + 0.5*b*h_beam)
                    self.RBS_length[floor] = RBS_length_floor
            else:
                raise ValueError('[Error] 1')

    def _get_panel_zone_thickness(self):
        self.pz_thickness = dict()  # panel zone thickness (column web + doubler plate)
        for floor in range(2, self.N + 2):
            story = floor - 1
            pz_floor = []  # panel zone thickness of the floor
            for axis in range(1, self.axis + 1):
                id_axis = axis - 1
                if story not in self.column_splice:
                    tw = self.column_properties[story][id_axis][2]  # column web thickness
                else:
                    tw = self.column_properties[story+1][id_axis][2]
                db_plate = self.doubler_plate[floor][id_axis]  # doubler plate thickness
                pz_floor.append(tw + db_plate)
            self.pz_thickness[floor] = pz_floor


