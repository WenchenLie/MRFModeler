from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .mrf_helper import Frame

from wsection import GBSection, WSection

from . import validation


class StructuralComponents:
    def __init__(self, frame: Frame):
        """Step-2:
        Structural components parameters
        """
        self.N = frame.N
        self.bays = frame.bays
        self.axis = frame.axis
        self.beams: dict[int, list[str]] = {}
        self.columns: dict[int, list[str]] = {}
        self.column_splice: tuple[int, ...] = ()
        self.beam_splice: tuple[int, ...] = ()
        self.rbs_length_all: int | float | None = None
        self.doubler_plate: dict[int, list[int | float]] = {
            floor: [0] * self.axis for floor in range(2, self.N + 2)
        }

    def set_beams(self, floor: int, sections: list[str]):
        """Set beam sizes

        Args:
            floor (int): floor number, must be larger than 2
            sections (list[str]): A list including all w-section types for the floor

        Example:
            >>> set_beams(2, ['W24x64', 'W24x64', 'W24x64'])
            The beam section for the 2rd floor is designated as W24x64
        """
        validation.check_int(floor, min_max=[2, self.N + 1], name="floor")
        validation.check_list(sections, length=self.bays, pos=False, name="beam section")
        self.beams[floor] = list(sections)

    def set_columns(self, story: int, sections: list[str]):
        """Set column sizes, if there is a column splice, input according to the
           cross-section at the bottom of the column

        Args:
            story (int): story number
            sections (list[str]): A list including all w-section types for the story

        """
        validation.check_int(story, min_max=[1, self.N], name="story")
        validation.check_list(sections, length=self.axis, pos=False, name="column section")
        self.columns[story] = list(sections)

    def set_column_splice(self, *story: int):
        """Set the stories where column splices are located.

        Args:
            story (list): Defaults to ().
        """
        if story:
            validation.check_tuple(story, min_length=1, max_length=self.N, name="story")
            for val in story:
                validation.check_int(val, [1, self.N], name="story")
                if val == self.N:
                    raise ValueError(f"Column splice cannot be placed at the top story ({self.N})")
            self.column_splice = tuple(dict.fromkeys(story))

    def set_beam_splice(self, *bay: int):
        """Set the stories where beam splices are located.

        Args:
            bay (list): Defaults to ().
        """
        if bay:
            validation.check_tuple(bay, min_length=1, max_length=self.bays, name="bay")
            for val in bay:
                validation.check_int(val, [1, self.bays], name="bay")
            self.beam_splice = tuple(dict.fromkeys(bay))

    def set_doubler_plate(self, floor: int, thicknesses: list[int | float]):
        """(Optional) Set doubler plate (if any) thickness for the panel zone

        Args:
            floor (int): Floor number of the panel zone
            thicknesses (list[int | float]): Doubler-plate thickness at each axis
        """
        validation.check_int(floor, [2, self.N + 1], name="floor")
        validation.check_list(thicknesses, length=self.axis, name="doubler plate thickness")
        self.doubler_plate[floor] = list(thicknesses)

    @property
    def RBS_length_all(self):
        """Backward-compatible alias for :attr:`rbs_length_all`."""
        return self.rbs_length_all

    @RBS_length_all.setter
    def RBS_length_all(self, value) -> None:
        self.rbs_length_all = value

    @property
    def RBS_length(self):
        """Backward-compatible alias for :attr:`rbs_length`."""
        return self.rbs_length

    @RBS_length.setter
    def RBS_length(self, value) -> None:
        self.rbs_length = value

    def set_rbs_length(self, rbs_length: int | float):
        """(Optional) Set RBS length (distance from beam hinge to panel zone edge)

        Args:
            rbs_length (int | float): Offset distance of the beam hinge
        """
        validation.check_int_float(rbs_length, name="rbs_length")
        self.rbs_length_all = rbs_length

    def set_RBS_length(self, rbs_length: int | float | None = None, **legacy_keywords):
        """Backward-compatible alias for :meth:`set_rbs_length`."""
        rbs_length = legacy_keywords.pop("RBS_length", rbs_length)
        if legacy_keywords:
            names = ", ".join(sorted(legacy_keywords))
            raise TypeError(f"Unexpected keyword argument(s): {names}")
        self.set_rbs_length(rbs_length)

    @staticmethod
    def _validate_complete_definition(
        *, expected: set[int], actual: set[int], component: str
    ) -> None:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing:
            raise ValueError(f"{component} at {missing} have not been defined")
        if unexpected:
            raise ValueError(f"{component} at {unexpected} do not exist")

    def _finish(self):
        self._validate_complete_definition(
            expected=set(range(2, self.N + 2)),
            actual=set(self.beams),
            component="Beams on floors",
        )
        self._validate_complete_definition(
            expected=set(range(1, self.N + 1)),
            actual=set(self.columns),
            component="Columns on stories",
        )

    @staticmethod
    def _section_properties(section: str, yield_strength: float, member: str) -> list:
        """Return the property layout expected by the script generator."""
        if section.startswith(("W", "w")):
            properties: Any = WSection(section, yield_strength)
        elif section.startswith(("HW", "HM", "HN")):
            properties = GBSection(section, yield_strength)
        else:
            raise ValueError(f"Invalid {member} section: {section}")
        return [
            properties.bf,
            properties.d,
            properties.tw,
            properties.tf,
            properties.ry,
            properties.A,
            properties.Ix,
            properties.My,
            properties.h,
        ]

    def _get_section_properties(self, frame: Frame):
        """Get beam and column properties
        * beam_properties (dict): {floor, [[bf, h, ...], [bf, h, ...], ...(x bays)]}
        * column_properties (dict): {story, [[bf, h, ...], [bf, h, ...], ...(x N)]}
        * RBS_length (dict): {floor: [l1, l2, ...(x 2*bays)]}
        """
        fy_beam = frame.load_and_material.fy_beam
        fy_column = frame.load_and_material.fy_column
        beam_column_connection = frame.connection_and_boundary.beam_column_connection
        rbs_parameters = frame.connection_and_boundary.rbs_parameters
        self.beam_properties = {}
        for floor, sections in self.beams.items():
            self.beam_properties[floor] = [
                self._section_properties(section, fy_beam, "beam") for section in sections
            ]

        # column properties
        self.column_properties = {}
        for story, sections in self.columns.items():
            self.column_properties[story] = [
                self._section_properties(section, fy_column, "column") for section in sections
            ]

        # RBS length
        self.rbs_length = {}
        for floor in range(2, self.N + 2):
            if self.rbs_length_all is not None:
                self.rbs_length[floor] = [self.rbs_length_all, self.rbs_length_all] * self.bays
            elif beam_column_connection in ["Full", "Hinged"]:
                self.rbs_length[floor] = [0, 0] * self.bays
            elif beam_column_connection == "RBS":
                a, b, c = rbs_parameters
                rbs_length_floor = []
                for id_bay in range(self.bays):  # Index for bay
                    bf_beam = self.beam_properties[floor][id_bay][0]
                    h_beam = self.beam_properties[floor][id_bay][1]
                    hinge_distance = a * bf_beam + 0.5 * b * h_beam
                    rbs_length_floor.extend((hinge_distance, hinge_distance))
                self.rbs_length[floor] = rbs_length_floor
            else:
                raise ValueError(f"Unsupported beam-column connection: {beam_column_connection}")

    def _get_panel_zone_thickness(self):
        self.pz_thickness = {}  # panel zone thickness (column web + doubler plate)
        for floor in range(2, self.N + 2):
            story = floor - 1
            pz_floor = []  # panel zone thickness of the floor
            for axis in range(1, self.axis + 1):
                id_axis = axis - 1
                if story not in self.column_splice:
                    tw = self.column_properties[story][id_axis][2]  # column web thickness
                else:
                    tw = self.column_properties[story + 1][id_axis][2]
                db_plate = self.doubler_plate[floor][id_axis]  # doubler plate thickness
                pz_floor.append(tw + db_plate)
            self.pz_thickness[floor] = pz_floor
