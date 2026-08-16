from typing import Literal

from . import validation

Command = dict[Literal["node", "ele", "mat", "any"], str]


class UserCommand:
    buildin_mat = [9, 99]  # Original public attribute retained for compatibility.
    built_in_material_tags = buildin_mat

    def __init__(self) -> None:
        self.additional_commands_py: list[Command] = []
        self.additional_commands_tcl: list[Command] = []

    @staticmethod
    def _format_parameters(parameters: tuple) -> tuple[str, str]:
        tcl_parameters = " ".join(str(item) for item in parameters)
        python_parameters = ", ".join(
            repr(item) if isinstance(item, str) else str(item) for item in parameters
        )
        return tcl_parameters, python_parameters

    @staticmethod
    def _reject_unknown_keywords(keywords: dict) -> None:
        if keywords:
            names = ", ".join(sorted(keywords))
            raise TypeError(f"Unexpected keyword argument(s): {names}")

    def add_material(
        self,
        mat_type: str | None = None,
        material_id: int | None = None,
        *parameters,
        **legacy_keywords,
    ):
        """Add material

        Args:
            mat_type (str): Material type
            material_id (int): Material tag
            parameters (tuple[any]): Material parameters
        """
        mat_type = legacy_keywords.pop("matType", mat_type)
        material_id = legacy_keywords.pop("Id", material_id)
        self._reject_unknown_keywords(legacy_keywords)
        validation.check_int(material_id, [1, 10000], name="material_id")
        validation.check_string(mat_type, name="mat_type")
        if material_id in self.built_in_material_tags:
            raise ValueError(f"Material tag {material_id} is reserved for a built-in material")
        text_paras_tcl, text_paras_py = self._format_parameters(parameters)
        suffix_tcl = f" {text_paras_tcl}" if text_paras_tcl else ""
        suffix_py = f", {text_paras_py}" if text_paras_py else ""
        text_tcl = f"uniaxialMaterial {mat_type} {material_id}{suffix_tcl};"
        self.additional_commands_tcl.append({"mat": text_tcl})
        text_py = f'ops.uniaxialMaterial("{mat_type}", {material_id}{suffix_py})'
        self.additional_commands_py.append({"mat": text_py})

    def add_node(
        self,
        node_id: int | None = None,
        x: int | float | None = None,
        y: int | float | None = None,
        **legacy_keywords,
    ):
        """Add node

        Args:
            node_id (int): Node tag
            x (int | float): x coordinate
            y (int | float): y coordinate
        """
        node_id = legacy_keywords.pop("Id", node_id)
        self._reject_unknown_keywords(legacy_keywords)
        validation.check_int(node_id, [1, 10000], name="node_id")
        validation.check_int_float(x, pos=False, name="x")
        validation.check_int_float(y, pos=False, name="y")
        text_tcl = f"node {node_id} {x} {y};"
        self.additional_commands_tcl.append({"node": text_tcl})
        text_py = f"ops.node({node_id}, {x}, {y})"
        self.additional_commands_py.append({"node": text_py})

    def add_element(
        self,
        element_type: str | None = None,
        element_id: int | None = None,
        i_node: int | None = None,
        j_node: int | None = None,
        *parameters,
        **legacy_keywords,
    ):
        """Add element

        Args:
            element_type (str): Element type
            element_id (int): Element tag
            parameters (tuple[any]): Element parameters
        """
        element_type = legacy_keywords.pop("eleType", element_type)
        element_id = legacy_keywords.pop("Id", element_id)
        i_node = legacy_keywords.pop("inode", i_node)
        j_node = legacy_keywords.pop("jnode", j_node)
        self._reject_unknown_keywords(legacy_keywords)
        validation.check_string(element_type, name="element_type")
        validation.check_int(element_id, [1, 10000], name="element_id")
        validation.check_int(i_node, name="i_node")
        validation.check_int(j_node, name="j_node")
        text_paras_tcl, text_paras_py = self._format_parameters(parameters)
        suffix_tcl = f" {text_paras_tcl}" if text_paras_tcl else ""
        suffix_py = f", {text_paras_py}" if text_paras_py else ""
        text_tcl = f"element {element_type} {element_id} {i_node} {j_node}{suffix_tcl};"
        self.additional_commands_tcl.append({"ele": text_tcl})
        text_py = f'ops.element("{element_type}", {element_id}, {i_node}, {j_node}{suffix_py})'
        self.additional_commands_py.append({"ele": text_py})

    def add_tcl_command(self, command: str = None):
        """Add any command line

        Args:
            command (str): command
        """
        if command is None:
            return
        validation.check_string(command, is_none=True, name="command")
        self.additional_commands_tcl.append({"any": command})

    def add_py_command(self, command: str = None):
        """Add any command line

        Args:
            command (str): command
        """
        if command is None:
            return
        validation.check_string(command, is_none=True, name="command")
        self.additional_commands_py.append({"any": command})
