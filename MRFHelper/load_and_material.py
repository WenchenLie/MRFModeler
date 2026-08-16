from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mrf_helper import Frame

from . import validation


class LoadAndMaterial:
    g = 9800
    LOAD_TYPES = ("Dead", "Live", "Cladding")

    def __init__(self, frame: Frame) -> None:
        self.N = frame.N
        self.bays = frame.bays
        self.axis = frame.axis
        self.dead_load = {}
        self.live_load = {}
        self.cladding_load = {}
        self.elastic_modulus = 206000
        self.fy_beam = None  # Necessary
        self.fy_column = None  # Necessary
        self.miu = 0.3  # Unnecessary
        # Combination coefficients for seismic weight and mass.
        self.cc_weight = {"Dead": 1.05, "Live": 0.25, "Cladding": 1.05}
        self.cc_mass = {"Dead": 1, "Live": 0, "Cladding": 1}
        for floor in range(2, frame.N + 2):
            self.dead_load[floor] = 1e-9
            self.live_load[floor] = 1e-9
            self.cladding_load[floor - 1] = 1e-9

    def _set_load_values(
        self,
        target: dict[int, int | float],
        indices: list[int],
        values: list[int | float],
        *,
        minimum: int,
        maximum: int,
        index_name: str,
    ) -> None:
        validation.check_list(indices, length=self.N, name=index_name)
        validation.check_list(values, length=self.N, name="load_per_area")
        if len(set(indices)) != len(indices):
            raise ValueError(f"Variable `{index_name}` contains duplicate values")
        for index in indices:
            validation.check_int(index, [minimum, maximum], name=index_name)
        target.update(zip(indices, values))

    def set_dead_load(self, floor: list[int], load_per_area: list[int | float]):
        """Step-3:
        Set dead load for each floor

        Args:
            floor (list[int]): Numbers of floor
            load_per_area (list[int | float]): Values of dead load (surface load)
        """
        self._set_load_values(
            self.dead_load,
            floor,
            load_per_area,
            minimum=2,
            maximum=self.N + 1,
            index_name="floor",
        )

    def set_live_load(self, floor: list[int], load_per_area: list[int | float]):
        """Set live load for each floor

        Args:
            floor (list[int]): Numbers of floor
            load_per_area (list[int | float]): Values of live load (surface load)
        """
        self._set_load_values(
            self.live_load,
            floor,
            load_per_area,
            minimum=2,
            maximum=self.N + 1,
            index_name="floor",
        )

    def set_cladding_load(self, story: list[int], load_per_area: list[int | float]):
        """Set cladding load for each story

        Args:
            story (list[int]): Numbers of story
            load_per_area (list[int | float]): Values of cladding load (surface load)
        """
        self._set_load_values(
            self.cladding_load,
            story,
            load_per_area,
            minimum=1,
            maximum=self.N,
            index_name="story",
        )

    @property
    def E(self):
        """Backward-compatible alias for :attr:`elastic_modulus`."""
        return self.elastic_modulus

    @E.setter
    def E(self, value) -> None:
        self.elastic_modulus = value

    def set_material(
        self,
        elastic_modulus: int | float | None = None,
        fy_beam: int | float | None = None,
        fy_column: int | float | None = None,
        miu: float = 0.3,
        **legacy_keywords,
    ):
        """Set material properties for all steel components

        Args:
            elastic_modulus (int | float): Young's modulus
            fy_beam (int | float): Nominal yield strength of beams
            fy_column (int | float): Nominal yield strength of column
            miu (float, optional): possion ratio
        """
        elastic_modulus = legacy_keywords.pop("E", elastic_modulus)
        if legacy_keywords:
            names = ", ".join(sorted(legacy_keywords))
            raise TypeError(f"Unexpected keyword argument(s): {names}")
        validation.check_int_float(elastic_modulus, name="elastic_modulus")
        validation.check_int_float(fy_beam, name="fy_beam")
        validation.check_int_float(fy_column, name="fy_column")
        validation.check_int_float(miu, [0, 0.5], name="miu")
        self.elastic_modulus = elastic_modulus
        self.fy_beam = fy_beam
        self.fy_column = fy_column
        self.miu = miu

    def set_weight_combination_coefficients(self, coefficients: dict):
        """Set seicmic weight combination coefficients
        Note: Load type should be within ['Dead', 'Live', 'Cladding']

        Args:
            coefficients (dict): {load type: combination coefficient}
        """
        validation.check_dict(coefficients, name="coefficients")
        for key, val in coefficients.items():
            if key not in self.LOAD_TYPES:
                raise ValueError(f"Load type should be within {list(self.LOAD_TYPES)}")
            validation.check_int_float(val, name="coefficient")
            self.cc_weight[key] = val

    def set_mass_combination_coefficients(self, coefficients: dict):
        """Set seicmic mass combination coefficients
        Note: Load type should be within ['Dead', 'Live', 'Cladding']

        Args:
            coefficients (dict): {load type: combination coefficient}
        """
        validation.check_dict(coefficients, name="coefficients")
        for key, val in coefficients.items():
            if key not in self.LOAD_TYPES:
                raise ValueError(f"Load type should be within {list(self.LOAD_TYPES)}")
            validation.check_int_float(val, name="coefficient")
            self.cc_mass[key] = val

    def _finished(self):
        if self.elastic_modulus is None:
            raise ValueError("Young's modulus has not been defined")
        if self.fy_beam is None:
            raise ValueError("Nominal yield strength of beams has not been defined")
        if self.fy_column is None:
            raise ValueError("Nominal yield strength of columns has not been defined")
        if not self.cc_weight:
            raise ValueError("Combination coefficients of seismic weight have not been defined")
        if not self.cc_mass:
            raise ValueError("Combination coefficients of seismic mass have not been defined")

        expected_floors = set(range(2, self.N + 2))
        expected_stories = set(range(1, self.N + 1))
        definitions = (
            ("Dead load", set(self.dead_load), expected_floors),
            ("Live load", set(self.live_load), expected_floors),
            ("Cladding load", set(self.cladding_load), expected_stories),
        )
        for label, actual, expected in definitions:
            if actual != expected:
                missing = sorted(expected - actual)
                unexpected = sorted(actual - expected)
                raise ValueError(
                    f"{label} definition is incomplete; missing={missing}, unexpected={unexpected}"
                )

    def _distribute_floor_load(
        self, frame: Frame, loads: dict[int, int | float]
    ) -> tuple[dict[int, list[float]], dict[int, float]]:
        """Distribute floor surface loads between frame and leaning-column nodes."""
        geometry = frame.building_geometry
        building_area = geometry.plane_dimensions[0] * geometry.plane_dimensions[1]
        frame_area = building_area / geometry.mf_number
        exterior_area = (
            geometry.exterior_column_tributary_area[0] * geometry.exterior_column_tributary_area[1]
        )
        interior_area = (
            geometry.interior_column_tributary_area[0] * geometry.interior_column_tributary_area[1]
        )
        tributary_areas = [exterior_area] + [interior_area] * (self.axis - 2) + [exterior_area]

        node_loads: dict[int, list[float]] = {}
        gravity_loads: dict[int, float] = {}
        for floor, surface_load in loads.items():
            total_frame_load = frame_area * surface_load
            node_loads[floor] = [area * surface_load for area in tributary_areas]
            gravity_loads[floor] = total_frame_load - sum(node_loads[floor])
        return node_loads, gravity_loads

    def _distribute_cladding_load(
        self, frame: Frame
    ) -> tuple[dict[int, list[float]], dict[int, float]]:
        """Distribute facade loads to floor nodes and the leaning column."""
        geometry = frame.building_geometry
        heights = geometry.story_height
        exterior_width = geometry.exterior_column_tributary_area[0]
        interior_width = geometry.interior_column_tributary_area[0]
        widths = [exterior_width] + [interior_width] * (self.axis - 2) + [exterior_width]

        node_loads: dict[int, list[float]] = {}
        gravity_loads: dict[int, float] = {}
        for story, surface_load in self.cladding_load.items():
            floor = story + 1
            lower_height = heights[story - 1]
            tributary_height = (
                lower_height / 2 if floor == self.N + 1 else (lower_height + heights[story]) / 2
            )
            node_areas = [width * tributary_height for width in widths]
            node_loads[floor] = [area * surface_load for area in node_areas]

            x_facade_area = geometry.plane_dimensions[0] * tributary_height
            y_facade_area = geometry.plane_dimensions[1] * tributary_height
            gravity_area = x_facade_area - sum(node_areas) + y_facade_area
            gravity_loads[floor] = gravity_area * surface_load
        return node_loads, gravity_loads

    @staticmethod
    def _combine_node_loads(
        dead: list[float],
        live: list[float],
        cladding: list[float],
        coefficients: dict[str, int | float],
    ) -> list[float]:
        return [
            dead_value * coefficients["Dead"]
            + live_value * coefficients["Live"]
            + cladding_value * coefficients["Cladding"]
            for dead_value, live_value, cladding_value in zip(dead, live, cladding)
        ]

    @staticmethod
    def _combine_gravity_loads(
        dead: float,
        live: float,
        cladding: float,
        coefficients: dict[str, int | float],
    ) -> float:
        return (
            dead * coefficients["Dead"]
            + live * coefficients["Live"]
            + cladding * coefficients["Cladding"]
        )

    def _calculate_load(self, frame: Frame):
        """Calculate nodal/leaning-column seismic weight and mass."""
        dead_node, dead_gravity = self._distribute_floor_load(frame, self.dead_load)
        live_node, live_gravity = self._distribute_floor_load(frame, self.live_load)
        cladding_node, cladding_gravity = self._distribute_cladding_load(frame)

        self.F_node = {}
        self.F_grav = {}
        self.mass_node = {}
        self.mass_grav = {}
        for floor in range(2, self.N + 2):
            self.F_node[floor] = self._combine_node_loads(
                dead_node[floor],
                live_node[floor],
                cladding_node[floor],
                self.cc_weight,
            )
            mass_forces = self._combine_node_loads(
                dead_node[floor],
                live_node[floor],
                cladding_node[floor],
                self.cc_mass,
            )
            self.mass_node[floor] = [force / self.g for force in mass_forces]
            self.F_grav[floor] = self._combine_gravity_loads(
                dead_gravity[floor],
                live_gravity[floor],
                cladding_gravity[floor],
                self.cc_weight,
            )
            mass_force = self._combine_gravity_loads(
                dead_gravity[floor],
                live_gravity[floor],
                cladding_gravity[floor],
                self.cc_mass,
            )
            self.mass_grav[floor] = mass_force / self.g

        # Component self-mass is intentionally excluded to preserve the model assumption.

    def _calculate_ppy(self, frame: Frame, ppy_scale: float = 1.25):
        """Calculate the axial compression ratio of columns
        * PPy (dict): Compression ratio ({story: ratio})
        * PPy_scale (float): Scale factor of compression ratio to consider the overturning effect,
        defaults to 1.25

        Args:
            PPy_scale (float, optional): Scale factor of compression ratio, defaults to 1.25.
        """
        props_col = frame.structural_components.column_properties
        p_col = {}  # Axial forces of columns
        p_temp = [0.0] * self.axis
        for story in range(self.N, 0, -1):
            floor = story + 1
            p_temp = [
                accumulated + floor_force
                for accumulated, floor_force in zip(p_temp, self.F_node[floor])
            ]
            p_col[story] = list(p_temp)
        ppy = {}  # Column axial compression ratio
        for story in range(1, self.N + 1):
            prop_floor = props_col[story]  # column properties for each story
            ppy_story_bottom, ppy_story_top = [], []
            for axis in range(1, self.axis + 1):
                id_axis = axis - 1
                area = prop_floor[id_axis][5]  # Cross-sectional area of column
                axial_force = p_col[story][id_axis]
                ppy_story_bottom.append(axial_force / (area * self.fy_column))
                if story not in frame.structural_components.column_splice:
                    ppy_story_top.append(axial_force / (area * self.fy_column))
                else:
                    area_top = props_col[story + 1][id_axis][5]  # Cross-sectional area of column
                    ppy_story_top.append(axial_force / (area_top * self.fy_column))
            ppy[f"{story}b"] = ppy_story_bottom
            ppy[f"{story}t"] = ppy_story_top
        self.ppy, self.ppy_scale = ppy, ppy_scale

    def _calculate_PPy(self, frame: Frame, ppy_scale: float = 1.25, **legacy_keywords):
        """Backward-compatible alias for :meth:`_calculate_ppy`."""
        ppy_scale = legacy_keywords.pop("PPy_scale", ppy_scale)
        if legacy_keywords:
            names = ", ".join(sorted(legacy_keywords))
            raise TypeError(f"Unexpected keyword argument(s): {names}")
        self._calculate_ppy(frame, ppy_scale)

    @property
    def PPy(self):
        """Backward-compatible alias for :attr:`ppy`."""
        return self.ppy

    @PPy.setter
    def PPy(self, value) -> None:
        self.ppy = value

    @property
    def PPy_scale(self):
        """Backward-compatible alias for :attr:`ppy_scale`."""
        return self.ppy_scale

    @PPy_scale.setter
    def PPy_scale(self, value) -> None:
        self.ppy_scale = value
