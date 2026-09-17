from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mrf_helper import Frame

from . import validation


class LoadAndMaterial:
    """Direct nodal mass, gravity-load, and steel-material inputs.

    Masses are specified in tonnes. Vertical loads are specified in newtons as
    positive downward magnitudes; the script writers apply the OpenSees
    negative global-Y sign when creating the load pattern.
    """

    def __init__(self, frame: Frame) -> None:
        self.N = frame.N
        self.bays = frame.bays
        self.axis = frame.axis
        self.moment_frame_node_mass: dict[int, list[float]] = {}
        self.leaning_column_node_mass: dict[int, float] = {}
        self.moment_frame_node_vertical_load: dict[int, list[float]] = {}
        self.leaning_column_node_vertical_load: dict[int, float] = {}
        self.elastic_modulus = 206000
        self.fy_beam = None
        self.fy_column = None
        self.poisson_ratio = 0.3
        self.axial_load_ratio_amplification_factor = 1.25

    def _validate_nodal_values(
        self,
        moment_frame: list[list[int | float]],
        leaning_column: list[int | float],
    ) -> tuple[dict[int, list[float]], dict[int, float]]:
        validation.check_list(moment_frame, length=self.N, pos=False, name="moment_frame")
        validation.check_list(leaning_column, length=self.N, name="leaning_column")

        frame_values: dict[int, list[float]] = {}
        leaning_values: dict[int, float] = {}
        for floor, (row, leaning_value) in enumerate(zip(moment_frame, leaning_column), start=2):
            validation.check_list(row, length=self.axis, name=f"moment_frame[{floor}]")
            checked_row = []
            for axis, value in enumerate(row, start=1):
                checked_row.append(
                    self._finite_nonnegative(value, f"moment_frame[{floor}][{axis}]")
                )
            frame_values[floor] = checked_row
            leaning_values[floor] = self._finite_nonnegative(
                leaning_value, f"leaning_column[{floor}]"
            )
        return frame_values, leaning_values

    @staticmethod
    def _finite_nonnegative(value: int | float, name: str) -> float:
        validation.check_int_float(value, name=name)
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"Variable `{name}` must be finite")
        return result

    def set_masses(
        self,
        moment_frame: list[list[int | float]],
        leaning_column: list[int | float],
    ) -> None:
        """Set user-defined nodal masses for every elevated floor.

        Args:
            moment_frame: One row per elevated floor and one mass [t] per frame
                axis. Rows map in order to floors ``2`` through ``N + 1``.
            leaning_column: One leaning-column node mass [t] per elevated floor,
                in the same floor order.
        """
        frame_values, leaning_values = self._validate_nodal_values(moment_frame, leaning_column)
        self.moment_frame_node_mass = frame_values
        self.leaning_column_node_mass = leaning_values

    def set_loads(
        self,
        moment_frame: list[list[int | float]],
        leaning_column: list[int | float],
    ) -> None:
        """Set user-defined nodal vertical loads for every elevated floor.

        Args:
            moment_frame: Positive-downward nodal loads [N], one row per elevated
                floor and one value per frame axis. Rows map in order to floors
                ``2`` through ``N + 1``.
            leaning_column: Positive-downward leaning-column load [N] per
                elevated floor, in the same floor order.
        """
        frame_values, leaning_values = self._validate_nodal_values(moment_frame, leaning_column)
        self.moment_frame_node_vertical_load = frame_values
        self.leaning_column_node_vertical_load = leaning_values

    def set_material(
        self,
        elastic_modulus: int | float,
        fy_beam: int | float,
        fy_column: int | float,
        poisson_ratio: float = 0.3,
    ) -> None:
        """Set material properties for all steel components."""
        validation.check_int_float(elastic_modulus, name="elastic_modulus")
        validation.check_int_float(fy_beam, name="fy_beam")
        validation.check_int_float(fy_column, name="fy_column")
        validation.check_int_float(poisson_ratio, [0, 0.5], name="poisson_ratio")
        self.elastic_modulus = elastic_modulus
        self.fy_beam = fy_beam
        self.fy_column = fy_column
        self.poisson_ratio = poisson_ratio

    def set_axial_load_ratio_amplification_factor(self, factor: int | float) -> None:
        """Set the column axial-load-ratio multiplier for overturning effects."""
        validation.check_int_float(factor, name="axial_load_ratio_amplification_factor")
        if factor < 1.0:
            raise ValueError("axial_load_ratio_amplification_factor must be at least 1.0")
        self.axial_load_ratio_amplification_factor = float(factor)

    def _finished(self) -> None:
        if self.elastic_modulus is None:
            raise ValueError("Young's modulus has not been defined")
        if self.fy_beam is None:
            raise ValueError("Nominal yield strength of beams has not been defined")
        if self.fy_column is None:
            raise ValueError("Nominal yield strength of columns has not been defined")

        expected_floors = set(range(2, self.N + 2))
        definitions = (
            ("Moment-frame nodal mass", self.moment_frame_node_mass),
            ("Leaning-column nodal mass", self.leaning_column_node_mass),
            ("Moment-frame nodal vertical load", self.moment_frame_node_vertical_load),
            ("Leaning-column nodal vertical load", self.leaning_column_node_vertical_load),
        )
        for label, values in definitions:
            actual_floors = set(values)
            if actual_floors != expected_floors:
                missing = sorted(expected_floors - actual_floors)
                unexpected = sorted(actual_floors - expected_floors)
                raise ValueError(
                    f"{label} definition is incomplete; missing={missing}, unexpected={unexpected}"
                )

    def _calculate_ppy(self, frame: Frame) -> None:
        """Calculate unamplified steel-column ratios used with the hinge multiplier."""
        props_col = frame.structural_components.column_properties
        p_col = {}
        accumulated = [0.0] * self.axis
        for story in range(self.N, 0, -1):
            floor = story + 1
            accumulated = [
                current + floor_force
                for current, floor_force in zip(
                    accumulated, self.moment_frame_node_vertical_load[floor]
                )
            ]
            p_col[story] = list(accumulated)
        ppy = {}
        for story in range(1, self.N + 1):
            prop_floor = props_col[story]
            ppy_story_bottom, ppy_story_top = [], []
            for axis in range(1, self.axis + 1):
                id_axis = axis - 1
                area = prop_floor[id_axis][5]
                axial_force = p_col[story][id_axis]
                ppy_story_bottom.append(axial_force / (area * self.fy_column))
                if story not in frame.structural_components.column_splice:
                    ppy_story_top.append(axial_force / (area * self.fy_column))
                else:
                    area_top = props_col[story + 1][id_axis][5]
                    ppy_story_top.append(axial_force / (area_top * self.fy_column))
            ppy[f"{story}b"] = ppy_story_bottom
            ppy[f"{story}t"] = ppy_story_top
        self.ppy = ppy
