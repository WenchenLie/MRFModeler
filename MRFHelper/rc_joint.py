"""Joint-panel model configuration and generated-script arguments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .rc_mcft import _mcft_backbone, pinching4_envelope


@dataclass(frozen=True)
class JointPanelContext:
    """Physical properties available when resolving one RC beam-column joint."""

    floor: int
    axis: int
    beam_depth: float
    column_depth: float
    joint_width: float
    adjacent_rotational_stiffness: tuple[float, ...]
    vertical_compression: float
    horizontal_reinforcement_spacing: float
    vertical_reinforcement_spacing: float
    horizontal_reinforcement_ratio: float
    vertical_reinforcement_ratio: float
    fc: float
    ec: float
    fy_horizontal: float
    fy_vertical: float
    es: float
    poisson_ratio: float


@dataclass(frozen=True)
class JointMaterialSpec:
    """Model name and already-resolved material arguments passed to ``RCJoint2D``."""

    panel_model: str
    arguments: tuple[float, ...]
    metadata: dict[str, float | str]

    def to_dict(self) -> dict:
        return {
            "panel_model": self.panel_model,
            "arguments": list(self.arguments),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> JointMaterialSpec:
        return cls(
            panel_model=str(data["panel_model"]),
            arguments=tuple(float(value) for value in data["arguments"]),
            metadata=dict(data.get("metadata", {})),
        )


@runtime_checkable
class JointPanelProvider(Protocol):
    def resolve(self, context: JointPanelContext) -> JointMaterialSpec: ...

    def configuration(self) -> dict: ...


class ElasticJointPanel:
    """Elastic joint-core shear response."""

    def resolve(self, context: JointPanelContext) -> JointMaterialSpec:
        return JointMaterialSpec(
            panel_model="Elastic",
            arguments=(context.joint_width, context.ec, context.poisson_ratio),
            metadata={"model": "elastic"},
        )

    def configuration(self) -> dict:
        return {"type": "Elastic"}


class RigidJointPanel:
    """Numerically rigid elastic joint core."""

    def __init__(self, stiffness_factor: float = 1000.0) -> None:
        if stiffness_factor <= 1:
            raise ValueError("Rigid joint-panel stiffness_factor must be greater than one")
        self.stiffness_factor = float(stiffness_factor)

    def resolve(self, context: JointPanelContext) -> JointMaterialSpec:
        return JointMaterialSpec(
            panel_model="Rigid",
            arguments=(
                context.joint_width,
                context.ec,
                context.poisson_ratio,
                self.stiffness_factor,
            ),
            metadata={"model": "rigid", "stiffness_factor": self.stiffness_factor},
        )

    def configuration(self) -> dict:
        return {"type": "Rigid", "stiffness_factor": self.stiffness_factor}


class MCFTJointPanel:
    """Modified Compression Field Theory joint-core model.

    MRFHelper performs the strain-controlled MCFT iteration while generating
    the model. ``RCJoint2D`` receives the resulting Pinching4 envelope and does
    not repeat the MCFT calculation during an OpenSees analysis.
    """

    def __init__(
        self,
        steel_hardening_ratio: float = 0.01,
        maximum_aggregate_size: float = 20.0,
        horizontal_axial_force: float = 0.0,
    ) -> None:
        if not 0 <= steel_hardening_ratio < 1:
            raise ValueError("steel_hardening_ratio must be in [0, 1)")
        if maximum_aggregate_size <= 0:
            raise ValueError("maximum_aggregate_size must be positive")
        self.steel_hardening_ratio = float(steel_hardening_ratio)
        self.maximum_aggregate_size = float(maximum_aggregate_size)
        self.horizontal_axial_force = float(horizontal_axial_force)

    def resolve(self, context: JointPanelContext) -> JointMaterialSpec:
        backbone = _mcft_backbone(
            context.column_depth,
            context.beam_depth,
            context.joint_width,
            context.vertical_compression,
            self.horizontal_axial_force,
            context.horizontal_reinforcement_spacing,
            context.vertical_reinforcement_spacing,
            context.horizontal_reinforcement_ratio,
            context.vertical_reinforcement_ratio,
            context.fc,
            context.ec,
            context.fy_horizontal,
            context.fy_vertical,
            context.es,
            self.steel_hardening_ratio,
            self.maximum_aggregate_size,
        )
        return JointMaterialSpec(
            panel_model="Pinching4",
            arguments=pinching4_envelope(backbone),
            metadata={
                "model": "mcft_pinching4",
                "steel_hardening_ratio": self.steel_hardening_ratio,
                "maximum_aggregate_size": self.maximum_aggregate_size,
                "horizontal_axial_force": self.horizontal_axial_force,
                "calculation_stage": "model_generation",
            },
        )

    def configuration(self) -> dict:
        return {
            "type": "MCFT",
            "steel_hardening_ratio": self.steel_hardening_ratio,
            "maximum_aggregate_size": self.maximum_aggregate_size,
            "horizontal_axial_force": self.horizontal_axial_force,
        }


def joint_panel_provider_from_configuration(configuration: dict) -> JointPanelProvider:
    """Recreate a built-in provider from serialized user input."""

    model = str(configuration.get("type", "Elastic")).strip().lower()
    if model == "elastic":
        return ElasticJointPanel()
    if model == "rigid":
        return RigidJointPanel(configuration.get("stiffness_factor", 1000.0))
    if model == "mcft":
        return MCFTJointPanel(
            configuration.get("steel_hardening_ratio", 0.01),
            configuration.get("maximum_aggregate_size", 20.0),
            configuration.get("horizontal_axial_force", 0.0),
        )
    raise ValueError("joint panel model must be one of: MCFT, Elastic, Rigid")
