from . import func
from typing import Dict, Tuple, List, Literal


class UserCommand:
    buildin_mat = [9, 99]

    def __init__(self) -> None:
        self.additional_commands: List[Dict[Literal['node', 'ele', 'mat', 'any'], str]] = []


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
        text_paras = ' '.join([str(i) for i in paras])
        text = f'uniaxialMaterial {matType} {Id} {text_paras};'
        self.additional_commands.append({'mat': text})
        

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
        text = f'node {Id} {x} {y};'
        self.additional_commands.append({'node': text})


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
        text_paras = ' '.join([str(i) for i in paras])
        text = f'element {eleType} {Id} {inode} {jnode} {text_paras};'
        self.additional_commands.append({'ele': text})


    def add_command(self, command: str=None):
        """Add any command line

        Args:
            command (str): command
        """
        if command is None:
            return
        func.check_string(command, isNone=True, name='command')
        self.additional_commands.append({'any': command})
