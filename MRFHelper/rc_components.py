"""Input stages used by :class:`MRFHelper.RCFrame`."""

from __future__ import annotations

from pathlib import Path

from . import validation
from .connection_and_boundary import ConnectionAndBoundary
from .load_and_material import LoadAndMaterial
from .rc_joint import (
    ElasticJointPanel,
    JointPanelProvider,
    MCFTJointPanel,
    RigidJointPanel,
)
from .rc_sections import RCSection, load_rc_sections_csv


class RCStructuralComponents:
    def __init__(self, frame) -> None:
        self.N = frame.N
        self.bays = frame.bays
        self.axis = frame.axis
        self.beams: dict[int, list[str]] = {}
        self.columns: dict[int, list[str]] = {}
        self.section_library: dict[str, RCSection] = {}
        self.section_source: str | None = None
        self.section_path: Path | None = None
        # Common member-layout fields consumed by the shared script writer.
        self.column_splice: tuple[int, ...] = ()
        self.beam_splice: tuple[int, ...] = ()
        self.rbs_length_all = None
        self.doubler_plate = {}

    def load_sections_csv(self, path: str | Path) -> None:
        csv_path = Path(path)
        self.section_library = load_rc_sections_csv(csv_path)
        self.section_source = str(csv_path)
        self.section_path = csv_path.resolve()

    def set_beams(self, floor: int, sections: list[str]) -> None:
        validation.check_int(floor, [2, self.N + 1], name="floor")
        validation.check_list(sections, length=self.bays, pos=False, name="beam section")
        self.beams[floor] = list(sections)

    def set_columns(self, story: int, sections: list[str]) -> None:
        validation.check_int(story, [1, self.N], name="story")
        validation.check_list(sections, length=self.axis, pos=False, name="column section")
        self.columns[story] = list(sections)

    @staticmethod
    def _validate_complete(expected: set[int], actual: set[int], label: str) -> None:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        if missing:
            raise ValueError(f"{label} at {missing} have not been defined")
        if unexpected:
            raise ValueError(f"{label} at {unexpected} do not exist")

    def _finish(self) -> None:
        if not self.section_library:
            raise ValueError("RC section library has not been loaded")
        self._validate_complete(set(range(2, self.N + 2)), set(self.beams), "Beams on floors")
        self._validate_complete(set(range(1, self.N + 1)), set(self.columns), "Columns on stories")
        for component, mapping in (("beam", self.beams), ("column", self.columns)):
            for level, names in mapping.items():
                for name in names:
                    if name not in self.section_library:
                        raise ValueError(f"Undefined RC {component} section `{name}` at {level}")

    @staticmethod
    def _properties(section: RCSection) -> list[float]:
        # Layout matches the subset consumed by the existing node/analysis writer:
        # [width, depth, tw, tf, ry, A, Ix, My, clear-depth]
        return [
            section.b,
            section.h,
            0.0,
            0.0,
            0.0,
            section.area,
            section.gross_inertia,
            0.0,
            section.h,
        ]

    def _get_section_properties(self, frame) -> None:
        self.beam_sections = {
            floor: [self.section_library[name] for name in names]
            for floor, names in self.beams.items()
        }
        self.column_sections = {
            story: [self.section_library[name] for name in names]
            for story, names in self.columns.items()
        }
        self.beam_properties = {
            floor: [self._properties(section) for section in sections]
            for floor, sections in self.beam_sections.items()
        }
        self.column_properties = {
            story: [self._properties(section) for section in sections]
            for story, sections in self.column_sections.items()
        }
        self.rbs_length = {floor: [0.0, 0.0] * self.bays for floor in range(2, self.N + 2)}


class RCLoadAndMaterial(LoadAndMaterial):
    BEAM_EI_RATIO = 0.3
    COLUMN_EI_RATIO_MIN = 0.2
    COLUMN_EI_RATIO_MAX = 0.6

    def __init__(self, frame) -> None:
        super().__init__(frame)
        self.axial_load_ratio_amplification_factor = 1.25
        self.fc_expected: float | None = None
        self.fy_expected: float | None = None
        self.es = 200000.0
        self.poisson_ratio = 0.2
        self.beam_ei_ratio = self.BEAM_EI_RATIO
        self.column_ei_ratios: dict[int, list[float]] = {}
        # Steel and RC materials expose these common writer-facing fields.
        self.elastic_modulus = None
        self.fy_beam = None
        self.fy_column = None

    def set_material(
        self,
        fc_expected: int | float,
        ec: int | float,
        fy_expected: int | float,
        es: int | float = 200000,
        poisson_ratio: int | float = 0.2,
    ) -> None:
        for value, name in (
            (fc_expected, "fc_expected"),
            (ec, "ec"),
            (fy_expected, "fy_expected"),
            (es, "es"),
        ):
            validation.check_int_float(value, name=name)
            if value <= 0:
                raise ValueError(f"RC material property `{name}` must be greater than zero")
        validation.check_int_float(poisson_ratio, [0, 0.5], name="poisson_ratio")
        self.fc_expected = float(fc_expected)
        self.elastic_modulus = float(ec)
        self.fy_expected = float(fy_expected)
        self.fy_beam = self.fy_expected
        self.fy_column = self.fy_expected
        self.es = float(es)
        self.poisson_ratio = float(poisson_ratio)

    def _finished(self) -> None:
        super()._finished()
        if self.fc_expected is None or self.fy_expected is None:
            raise ValueError("RC expected concrete and reinforcement strengths must be defined")

    @classmethod
    def _column_effective_stiffness_ratio(cls, axial_ratio: float) -> float:
        calculated = 0.75 * pow(0.1 + axial_ratio, 0.8)
        return min(cls.COLUMN_EI_RATIO_MAX, max(cls.COLUMN_EI_RATIO_MIN, calculated))

    def _calculate_ppy(self, frame) -> None:
        accumulated = [0.0] * self.axis
        gravity_axial_forces: dict[int, list[float]] = {}
        for story in range(self.N, 0, -1):
            floor = story + 1
            accumulated = [
                current + floor_force
                for current, floor_force in zip(
                    accumulated, self.moment_frame_node_vertical_load[floor]
                )
            ]
            gravity_axial_forces[story] = list(accumulated)
        factor = self.axial_load_ratio_amplification_factor
        axial_forces = {
            story: [force * factor for force in forces]
            for story, forces in gravity_axial_forces.items()
        }
        self.column_gravity_axial_forces = gravity_axial_forces
        self.column_axial_forces = axial_forces
        self.ppy = {}
        self.column_ei_ratios = {}
        for story in range(1, self.N + 1):
            ratios = [
                axial_forces[story][axis] / (section.area * self.fc_expected)
                for axis, section in enumerate(frame.structural_components.column_sections[story])
            ]
            self.ppy[f"{story}b"] = list(ratios)
            self.ppy[f"{story}t"] = list(ratios)
            self.column_ei_ratios[story] = [
                self._column_effective_stiffness_ratio(axial_ratio) for axial_ratio in ratios
            ]


class RCConnectionAndBoundary(ConnectionAndBoundary):
    def __init__(self, frame) -> None:
        super().__init__(frame)
        self.beam_column_connection = "Full"
        self.panel_zone_deformation = True
        self.joint_panel_provider: JointPanelProvider = ElasticJointPanel()

    def set_joint_panel_provider(self, provider: JointPanelProvider) -> None:
        if not isinstance(provider, JointPanelProvider):
            raise TypeError("provider must implement resolve(context) and configuration()")
        self.joint_panel_provider = provider

    def set_joint_panel_model(self, model: str, **parameters: float) -> None:
        """Select ``Elastic``, ``Rigid``, or ``MCFT`` joint-panel behavior."""

        normalized = str(model).strip().lower()
        if normalized == "elastic":
            if parameters:
                raise TypeError("Elastic joint panels do not accept additional parameters")
            provider: JointPanelProvider = ElasticJointPanel()
        elif normalized == "rigid":
            unexpected = set(parameters) - {"stiffness_factor"}
            if unexpected:
                raise TypeError(f"Unexpected Rigid joint-panel parameters: {sorted(unexpected)}")
            provider = RigidJointPanel(parameters.get("stiffness_factor", 1000.0))
        elif normalized == "mcft":
            allowed = {
                "steel_hardening_ratio",
                "maximum_aggregate_size",
                "horizontal_axial_force",
            }
            unexpected = set(parameters) - allowed
            if unexpected:
                raise TypeError(f"Unexpected MCFT joint-panel parameters: {sorted(unexpected)}")
            provider = MCFTJointPanel(
                parameters.get("steel_hardening_ratio", 0.01),
                parameters.get("maximum_aggregate_size", 20.0),
                parameters.get("horizontal_axial_force", 0.0),
            )
        else:
            raise ValueError("joint panel model must be one of: MCFT, Elastic, Rigid")
        self.joint_panel_provider = provider

    def set_beam_column_connection(self, *args, **kwargs) -> None:
        raise AttributeError("RCFrame always uses concentrated member hinges and Joint2D joints")

    def set_panel_zone_deformation(self, enabled: bool = True) -> None:
        if enabled is not True:
            raise ValueError("RCFrame requires Joint2D panel-zone modeling")
        self.panel_zone_deformation = True
