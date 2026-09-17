"""Generation-time IMK calculations for reinforced-concrete members."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .rc_sections import RCSection


@dataclass(frozen=True)
class RCHingeParameters:
    ke: float
    theta_p_positive: float
    theta_p_negative: float
    theta_pc: float
    theta_u: float
    my_positive: float
    my_negative: float
    mc_my: float
    residual_ratio: float
    lambda_imk: float
    axial_ratio: float
    fc: float
    ec: float
    fy: float
    es: float
    b: float
    h: float
    top_cover: float
    bottom_cover: float
    stirrup_spacing: float
    rho_top: float
    rho_bottom: float
    rho_middle: float
    rho_sh: float
    bond_slip: int
    length: float
    ei_ratio: float
    stiffness_multiplier: float

    def material_arguments(self, *, reverse: bool = False) -> tuple[float, ...]:
        my_pos, my_neg = self.my_positive, self.my_negative
        theta_p_pos, theta_p_neg = self.theta_p_positive, self.theta_p_negative
        if reverse:
            my_pos, my_neg = my_neg, my_pos
            theta_p_pos, theta_p_neg = theta_p_neg, theta_p_pos
        return (
            self.ke,
            theta_p_pos,
            self.theta_pc,
            self.theta_u,
            my_pos,
            self.mc_my,
            self.residual_ratio,
            theta_p_neg,
            self.theta_pc,
            self.theta_u,
            my_neg,
            self.mc_my,
            self.residual_ratio,
            self.lambda_imk,
            self.lambda_imk,
            self.lambda_imk,
            self.lambda_imk,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
            1.0,
        )

    def subroutine_arguments(self, *, reverse: bool = False) -> tuple[float, ...]:
        """Return physical inputs consumed by the shared RCHinge subroutine."""
        return (
            self.fc,
            self.ec,
            self.fy,
            self.es,
            self.b,
            self.h,
            self.top_cover,
            self.bottom_cover,
            self.stirrup_spacing,
            self.rho_top,
            self.rho_bottom,
            self.rho_middle,
            self.rho_sh,
            float(self.bond_slip),
            self.axial_ratio,
            1.0,
            self.length,
            self.ei_ratio,
            self.stiffness_multiplier,
            float(reverse),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "ke": self.ke,
            "theta_p_positive": self.theta_p_positive,
            "theta_p_negative": self.theta_p_negative,
            "theta_pc": self.theta_pc,
            "theta_u": self.theta_u,
            "my_positive": self.my_positive,
            "my_negative": self.my_negative,
            "mc_my": self.mc_my,
            "residual_ratio": self.residual_ratio,
            "lambda_imk": self.lambda_imk,
            "axial_ratio": self.axial_ratio,
            "subroutine_arguments": list(self.subroutine_arguments()),
        }


def _aci_beta_1(fc: float, *, unit_factor: float = 1.0) -> float:
    """Return the ACI rectangular-block factor for ``fc``.

    ``unit_factor`` converts the supplied stress to MPa.  It is 1.0 for
    MPa and 6.895 for ksi.
    """
    fc_mpa = fc * unit_factor
    if fc_mpa <= 27.6:
        return 0.85
    if fc_mpa >= 55.16:
        return 0.65
    return 1.05 - 0.05 * fc_mpa / 6.9


def _asymmetric_rotation_factor(
    *, rho_compression: float, rho_tension: float, fy: float, fc: float
) -> float:
    """Return the Fardis--Biskinis correction in Haselton et al. Eq. (7)."""
    normalized_compression = max(0.01, rho_compression * fy / fc)
    normalized_tension = max(0.01, rho_tension * fy / fc)
    return (normalized_compression / normalized_tension) ** 0.225


def _yield_moment(
    *,
    b: float,
    h: float,
    compression_cover: float,
    tension_cover: float,
    area_tension: float,
    area_compression: float,
    area_middle: float,
    axial_force: float,
    fc: float,
    ec: float,
    fy: float,
    es: float,
) -> float:
    d = h - tension_cover
    if d <= compression_cover:
        raise ValueError("Effective section depth is not positive")
    rho_t = area_tension / (b * d)
    rho_c = area_compression / (b * d)
    rho_i = area_middle / (b * d)
    delta_1 = compression_cover / d
    effective_depth_axial_ratio = axial_force / (b * d * fc)
    modular_ratio = es / ec
    steel_yield_strain = fy / es
    concrete_ultimate_strain = 0.003

    beta_1 = _aci_beta_1(fc)
    compression_depth = (area_tension * fy - area_compression * fy + axial_force) / (
        0.85 * fc * beta_1 * b
    )
    balanced_depth = concrete_ultimate_strain * d / (concrete_ultimate_strain + steel_yield_strain)
    if compression_depth < balanced_depth:
        value_a = rho_t + rho_c + rho_i + effective_depth_axial_ratio * fc / fy
        value_b = (
            rho_t
            + rho_c * delta_1
            + 0.5 * rho_i * (1 + delta_1)
            + effective_depth_axial_ratio * fc / fy
        )
        k_y = math.sqrt(modular_ratio**2 * value_a**2 + 2 * modular_ratio * value_b)
        k_y -= modular_ratio * value_a
        curvature_y = steel_yield_strain / ((1 - k_y) * d)
    else:
        value_a = rho_t + rho_c + rho_i - effective_depth_axial_ratio / (1.8 * modular_ratio)
        value_b = rho_t + rho_c * delta_1 + 0.5 * rho_i * (1 + delta_1)
        radicand = modular_ratio**2 * value_a**2 + 2 * modular_ratio * value_b
        if radicand <= 0:
            raise ValueError("RC yield-moment equation produced an invalid neutral axis")
        k_y = math.sqrt(radicand) - modular_ratio * value_a
        curvature_y = 1.8 * fc / (ec * d * k_y)
    if not 0 < k_y < 1:
        raise ValueError(f"RC yield-moment neutral-axis ratio is outside (0, 1): {k_y}")

    term_1 = ec * k_y**2 / 2 * (0.5 * (1 + delta_1) - k_y / 3)
    term_2 = (
        es
        / 2
        * ((1 - k_y) * rho_t + (k_y - delta_1) * rho_c + rho_i / 6 * (1 - delta_1))
        * (1 - delta_1)
    )
    moment = b * d**3 * curvature_y * (term_1 + term_2)
    if not math.isfinite(moment) or moment <= 0:
        raise ValueError("RC yield-moment calculation produced a non-positive value")
    return moment


def calculate_rc_hinge(
    section: RCSection,
    *,
    fc: float,
    ec: float,
    fy: float,
    es: float,
    length: float,
    ei_ratio: float,
    axial_force: float = 0.0,
    stiffness_multiplier: float = 10.0,
) -> RCHingeParameters:
    """Calculate asymmetric IMK parameters using the bundled RC spring equations."""
    if min(fc, ec, fy, es, length, ei_ratio) <= 0:
        raise ValueError("RC hinge material, length, and stiffness values must be positive")
    top_cover = section.longitudinal_centroid_from_face("top")
    bottom_cover = section.longitudinal_centroid_from_face("bottom")
    positive_moment = _yield_moment(
        b=section.b,
        h=section.h,
        compression_cover=top_cover,
        tension_cover=bottom_cover,
        area_tension=section.bottom_bars.area,
        area_compression=section.top_bars.area,
        area_middle=section.side_area_total,
        axial_force=axial_force,
        fc=fc,
        ec=ec,
        fy=fy,
        es=es,
    )
    negative_moment = _yield_moment(
        b=section.b,
        h=section.h,
        compression_cover=bottom_cover,
        tension_cover=top_cover,
        area_tension=section.top_bars.area,
        area_compression=section.bottom_bars.area,
        area_middle=section.side_area_total,
        axial_force=axial_force,
        fc=fc,
        ec=ec,
        fy=fy,
        es=es,
    )
    rho_top = section.top_bars.area / section.area
    rho_bottom = section.bottom_bars.area / section.area
    rho_middle = section.side_area_total / section.area
    axial_ratio = axial_force / (section.area * fc)
    rho_sh = section.transverse_ratio
    theta_p_symmetric = (
        0.1
        * (1 + 0.55 * section.bond_slip)
        * 0.16**axial_ratio
        * (0.02 + 40 * rho_sh) ** 0.43
        * 0.54 ** (0.01 * fc)
    )
    positive_depth = section.h - bottom_cover
    negative_depth = section.h - top_cover
    theta_p_positive = theta_p_symmetric * _asymmetric_rotation_factor(
        rho_compression=section.top_bars.area / (section.b * positive_depth),
        rho_tension=section.bottom_bars.area / (section.b * positive_depth),
        fy=fy,
        fc=fc,
    )
    theta_p_negative = theta_p_symmetric * _asymmetric_rotation_factor(
        rho_compression=section.bottom_bars.area / (section.b * negative_depth),
        rho_tension=section.top_bars.area / (section.b * negative_depth),
        fy=fy,
        fc=fc,
    )
    theta_pc = min(0.76 * 0.031**axial_ratio * (0.02 + 40 * rho_sh) ** 1.02, 0.10)
    lambda_prime = 30.0 * 0.3**axial_ratio
    # IMKPeakOriented accepts one reference-energy deformation for both
    # directions.  Use the smaller directional capacity for asymmetric
    # sections; this is exact for symmetric sections and conservative otherwise.
    lambda_imk = lambda_prime * min(theta_p_positive, theta_p_negative)
    ke = (stiffness_multiplier + 1) * 6 * ec * section.gross_inertia * ei_ratio / length
    if min(theta_p_positive, theta_p_negative, theta_pc, lambda_imk, ke) <= 0:
        raise ValueError("RC IMK parameter calculation produced a non-positive value")
    return RCHingeParameters(
        ke=ke,
        theta_p_positive=theta_p_positive,
        theta_p_negative=theta_p_negative,
        theta_pc=theta_pc,
        theta_u=0.2,
        my_positive=positive_moment,
        my_negative=negative_moment,
        mc_my=1.13,
        residual_ratio=0.01,
        lambda_imk=lambda_imk,
        axial_ratio=axial_ratio,
        fc=fc,
        ec=ec,
        fy=fy,
        es=es,
        b=section.b,
        h=section.h,
        top_cover=top_cover,
        bottom_cover=bottom_cover,
        stirrup_spacing=section.stirrup_spacing,
        rho_top=rho_top,
        rho_bottom=rho_bottom,
        rho_middle=rho_middle,
        rho_sh=rho_sh,
        bond_slip=section.bond_slip,
        length=length,
        ei_ratio=ei_ratio,
        stiffness_multiplier=stiffness_multiplier,
    )
