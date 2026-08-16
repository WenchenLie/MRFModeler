from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .mrf_helper import Frame
from . import validation


class ConnectionAndBoundary:
    def __init__(self, frame: Frame) -> None:
        """Step-4:
        Connection and boundary condition
        """
        self.frame = frame
        self.base_support = "Fixed"
        self.beam_column_connection = "Full"
        self.rbs_parameters = (0.625, 0.75, 0.25)
        self.panel_zone_deformation = True
        self.soil_constraint = []
        self.rigid_diaphragm = True

    @property
    def rigid_disphragm(self) -> bool:
        """Backward-compatible alias for the original misspelled attribute."""
        return self.rigid_diaphragm

    @rigid_disphragm.setter
    def rigid_disphragm(self, value: bool) -> None:
        validation.check_boolean(value, name="rigid_disphragm")
        self.rigid_diaphragm = value

    @property
    def RBS_paras(self) -> tuple[float, float, float]:
        """Backward-compatible alias for :attr:`rbs_parameters`."""
        return self.rbs_parameters

    @RBS_paras.setter
    def RBS_paras(self, value: tuple[float, float, float]) -> None:
        self.rbs_parameters = value

    def set_base_support(self, type: Literal["Fixed", "Pinned"] = "Fixed"):
        """Defined column base support

        Args:
            type (str, optional):
            * "Fixed": Full constrained conncetion
            * "Pinned", Pinned connection
        """
        validation.check_string(type, ["Fixed", "Pinned"], name="type")
        self.base_support = type

    def set_beam_column_connection(
        self,
        type: Literal["Full", "RBS", "Hinged"] = "Full",
        a=0.625,
        b=0.75,
        c=0.25,
    ):
        """Define beam to column connection

        Args:
            type (str, optional):
            * "Full" - Full restrained
            * "RBS" - Reduced beam section
            * "Hinged" - Hinged connection

            a, b, c: RBS parameters, default to 0.625, 0.75, and 0.25, respectively
        """
        validation.check_int_float(a, [0, 10], name="a")
        validation.check_int_float(b, [0, 10], name="b")
        validation.check_int_float(c, [0, 1], name="c")
        validation.check_string(type, ["Full", "RBS", "Hinged"], name="type")
        self.beam_column_connection = type
        self.rbs_parameters = (a, b, c)

    def set_panel_zone_deformation(self, type: bool = True):
        """Define whether the panel zone deformation is consdiered

        Args:
            type (bool, optional):
            * True - Use a parrallelogram model
            * False - Use a cruciform model
        """
        validation.check_boolean(type, name="type")
        self.panel_zone_deformation = type

    def set_soil_constraint(self, floor: int):
        """Set soil constraint at specified floor

        Args:
            floor (int): floor number with soil constraint
        """
        validation.check_int(floor, [1, self.frame.N + 1], name="floor")
        if floor not in self.soil_constraint:
            self.soil_constraint.append(floor)

    def _finished(self):
        validation.check_boolean(self.rigid_diaphragm, name="rigid_diaphragm")
