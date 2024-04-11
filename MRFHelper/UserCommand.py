from . import func
from typing import Dict, Tuple, List, Literal


class UserCommand:
    buildin_mat = [9, 99]

    def __init__(self) -> None:
        self.additional_commands_py: List[Dict[Literal['node', 'ele', 'mat', 'any'], str]] = []
        self.additional_commands_tcl: List[Dict[Literal['node', 'ele', 'mat', 'any'], str]] = []


    def add_material(self, matType: str, Id: int, *paras):
        """Add material

        Args:
            matType (str): Material type
            Id (int): Matirial tag
            paras (tuple[any]): Material parameters
        """
        func.check_int(Id, [1, 10000], name='Id')
        func.check_string(matType, name='matType')
        if Id in self.buildin_mat:
            raise ValueError(f'Material tag {Id} cannot be used since it has been used as a built-in material tag')
        text_paras_tcl = ' '.join([str(i) for i in paras])
        text_tcl = f'uniaxialMaterial {matType} {Id} {text_paras_tcl};'
        self.additional_commands_tcl.append({'mat': text_tcl})
        paras_temp = []
        for item in paras:
            if isinstance(item, str):
                paras_temp.append(f'"{item}"')
            else:
                paras_temp.append(item)
        text_paras_py = ', '.join([str(i) for i in paras_temp])
        text_py = f'ops.uniaxialMaterial("{matType}", {Id}, {text_paras_py})'
        self.additional_commands_py.append({'mat': text_py})
        

    def add_node(self, Id: int, x: int | float, y: int | float):
        """Add node

        Args:
            Id (int): Node tag
            x (int | float): x coordinate
            y (int | float): y coordinate
        """
        func.check_int(Id, [1, 10000], name='Id')
        func.check_int_float(x, pos=False, name='x')
        func.check_int_float(y, pos=False, name='y')
        text_tcl = f'node {Id} {x} {y};'
        self.additional_commands_tcl.append({'node': text_tcl})
        text_py = f'ops.node({Id}, {x}, {y})'
        self.additional_commands_py.append({'node': text_py})


    def add_element(self, eleType: str, Id: int, inode: int, jnode: int, *paras):
        """Add element

        Args:
            eleType (str): Element type
            Id (int): Element tag
            paras (tuple[any]): Element parameters
        """
        func.check_string(eleType, name='eleType')
        func.check_int(Id, [1, 10000], name='Id')
        func.check_int(inode, name='inode')
        func.check_int(jnode, name='jnode')
        text_paras_tcl = ' '.join([str(i) for i in paras])
        text_tcl = f'element {eleType} {Id} {inode} {jnode} {text_paras_tcl};'
        self.additional_commands_tcl.append({'ele': text_tcl})
        paras_temp = []
        for item in paras:
            if isinstance(item, str):
                paras_temp.append(f'"{item}"')
            else:
                paras_temp.append(item)
        text_paras_py = ', '.join([str(i) for i in paras_temp])
        text_py = f'ops.element("{eleType}", {Id}, {inode}, {jnode}, {text_paras_py})'
        self.additional_commands_py.append({'ele': text_py})


    def add_tcl_command(self, command: str=None):
        """Add any command line

        Args:
            command (str): command
        """
        if command is None:
            return
        func.check_string(command, isNone=True, name='command')
        self.additional_commands_tcl.append({'any': command})


    def add_py_command(self, command: str=None):
        """Add any command line

        Args:
            command (str): command
        """
        if command is None:
            return
        func.check_string(command, isNone=True, name='command')
        self.additional_commands_py.append({'any': command})
