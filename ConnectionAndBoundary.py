import func
from typing import Literal


class ConnectionAndBoundary:

    def __init__(self) -> None:
        """Step-4:
        Connection and boundary condition
        """
        self.base_support = 'Fixed'
        self.beam_column_connection = 'Full'
        self.RBS_paras = (0.625, 0.75, 0.25)
        self.panel_zone_deformation = True


    def set_base_support(self, type: Literal['Fixed', 'Pinned']='Fixed'):
        """Defined column base support

        Args:
            type (str, optional):
            * "Fixed": Full constrained conncetion
            * "Pinned", Pinned connection
        """
        func.check_string(type, ['Fixed', 'Pinned'], 'type')
        self.base_support = type


    def set_beam_column_connection(self, type: Literal['Full', 'RBS', 'Hinged']='Full', a=0.625, b=0.75, c=0.25):
        """Define beam to column connection  

        Args:
            type (str, optional):
            * "Full" - Full restrained
            * "RBS" - Reduced beam section
            * "Hinged" - Hinged connection

            a, b, c: RBS parameters, default to 0.625, 0.75, and 0.25, respectively
        """
        func.check_int_float(a, [0, 10], name='a')
        func.check_int_float(b, [0, 10], name='b')
        func.check_int_float(c, [0, 1], name='c')
        func.check_string(type, ['Full', 'RBS', 'Hinged'], 'type')
        self.beam_column_connection = type
        self.RBS_paras = (a, b, c)


    def set_panel_zone_deformation(self, type: Literal[True, False]=True):
        """Define whether the panel zone deformation is consdiered

        Args:
            type (bool, optional): 
            * True - Use a parrallelogram model
            * False - Use a cruciform model
        """
        func.check_boolean(type, name='type')
        self.panel_zone_deformation = type


    def _finished(self):
        pass
