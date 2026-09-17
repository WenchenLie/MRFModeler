"""Generation-time Modified Compression Field Theory calculations."""

from __future__ import annotations

import math


def _steel_stress(strain: float, fy: float, es: float, hardening_ratio: float) -> float:
    trial = es * strain
    if abs(trial) <= fy:
        return trial
    return math.copysign(fy + hardening_ratio * es * (abs(strain) - fy / es), strain)


def _mcft_backbone(
    column_depth: float,
    beam_depth: float,
    joint_width: float,
    vertical_compression: float,
    horizontal_axial_force: float,
    sx: float,
    sy: float,
    rho_x: float,
    rho_y: float,
    fc: float,
    ec: float,
    fy_x: float,
    fy_y: float,
    es: float,
    steel_hardening_ratio: float,
    maximum_aggregate_size: float,
) -> tuple[tuple[float, float], ...]:
    """Calculate four positive moment-rotation points using the MCFT algorithm.

    Args:
        column_depth: Horizontal joint-core dimension, equal to the column
            section depth, in mm.
        beam_depth: Vertical joint-core dimension, equal to the effective depth
            of the adjacent beam sections, in mm.
        joint_width: Effective out-of-plane joint width in mm. The modeler uses
            the minimum width of the column and adjacent beams.
        vertical_compression: Column gravity compression transferred through
            the joint in N, using a positive-compression convention.
        horizontal_axial_force: Beam axial force transferred through the joint
            in N; tension is positive and the default model input is zero.
        sx: Maximum spacing of horizontal beam-longitudinal reinforcement
            layers crossing the joint, in mm.
        sy: Maximum spacing of vertical column-longitudinal reinforcement
            layers crossing the joint, in mm.
        rho_x: Horizontal reinforcement ratio in the joint core, defined using
            ``joint_width * beam_depth``.
        rho_y: Vertical reinforcement ratio in the joint core, defined using
            ``joint_width * column_depth``.
        fc: Expected concrete compressive strength in MPa.
        ec: Concrete elastic modulus in MPa.
        fy_x: Expected yield strength of horizontal reinforcement in MPa.
        fy_y: Expected yield strength of vertical reinforcement in MPa.
        es: Reinforcement elastic modulus in MPa.
        steel_hardening_ratio: Post-yield reinforcement tangent divided by
            ``es``.
        maximum_aggregate_size: Maximum concrete aggregate size in mm, used by
            the MCFT crack-slip limit.

    Returns:
        Four ``(rotation, moment)`` points defining the positive Pinching4
        envelope. Rotation is dimensionless and moment is in N-mm.

    Notes:
        Compression is converted internally to the negative stress/strain
        convention used by the dissertation equations. Shear stress is
        converted to the Joint2D center-spring moment using virtual work:
        ``M = tau * joint_width * column_depth * beam_depth`` and
        ``rotation = gamma``. This function runs while MRFHelper generates the
        model; OpenSees receives only the resulting Pinching4 parameters.
    """
    if min(column_depth, beam_depth, joint_width, sx, sy, fc, ec, fy_x, fy_y, es) <= 0:
        raise ValueError("MCFT geometry and material properties must be positive")
    if not 0 < rho_x < 1 or not 0 < rho_y < 1:
        raise ValueError("MCFT reinforcement ratios must be between zero and one")
    if vertical_compression < 0:
        raise ValueError("vertical_compression uses a positive-compression convention")

    area_x = joint_width * beam_depth
    area_y = joint_width * column_depth
    target_fx = horizontal_axial_force / area_x
    target_fy = -vertical_compression / area_y
    tangent_x = (1.0 - rho_x) * ec + rho_x * es
    tangent_y = (1.0 - rho_y) * ec + rho_y * es
    eps_x = target_fx / tangent_x
    eps_y = target_fy / tangent_y
    eps_c = -0.002
    eps_cr = 0.5e-4
    fcr = ec * eps_cr
    gamma_increment = 0.00005
    gamma_limit = 0.04
    curve: list[tuple[float, float]] = [(0.0, 0.0)]

    gamma = gamma_increment
    while gamma <= gamma_limit + 0.5 * gamma_increment:
        converged = False
        for _iteration in range(100):
            radius = math.sqrt(((eps_x - eps_y) / 2.0) ** 2 + (gamma / 2.0) ** 2)
            eps_1 = (eps_x + eps_y) / 2.0 + radius
            eps_2 = (eps_x + eps_y) / 2.0 - radius
            theta = 0.5 * math.atan2(gamma, eps_x - eps_y)

            if eps_1 <= eps_cr:
                fc_1 = ec * eps_1
            else:
                fc_1 = fcr / (1.0 + math.sqrt(200.0 * eps_1))

            softening = min(1.0, 1.0 / (0.8 - 0.34 * eps_1 / eps_c))
            fc_2max = -fc * softening
            compression_ratio = eps_2 / eps_c
            fc_2 = fc_2max * (2.0 * compression_ratio - compression_ratio**2)

            fs_x = _steel_stress(eps_x, fy_x, es, steel_hardening_ratio)
            fs_y = _steel_stress(eps_y, fy_y, es, steel_hardening_ratio)
            cosine = math.cos(2.0 * theta)
            fcx = (fc_1 + fc_2) / 2.0 + (fc_1 - fc_2) / 2.0 * cosine
            fcy = (fc_1 + fc_2) / 2.0 - (fc_1 - fc_2) / 2.0 * cosine
            trial_fx = fcx + rho_x * fs_x
            trial_fy = fcy + rho_y * fs_y
            residual_x = target_fx - trial_fx
            residual_y = target_fy - trial_fy
            tolerance = max(1.0e-6, 1.0e-5 * fc)
            if abs(residual_x) <= tolerance and abs(residual_y) <= tolerance:
                converged = True
                break
            eps_x += 0.5 * residual_x / tangent_x
            eps_y += 0.5 * residual_y / tangent_y

        if not converged:
            break

        tau = max(0.0, (fc_1 - fc_2) / 2.0 * math.sin(2.0 * theta))
        curve.append((gamma, tau))

        tan_theta = max(math.tan(theta), 1.0e-9)
        smx = 1.5 * sx
        smy = 1.5 * sy
        crack_spacing = 1.0 / (
            max(math.sin(theta), 1.0e-9) / smx + max(math.cos(theta), 1.0e-9) / smy
        )
        crack_width = max(0.0, eps_1 * crack_spacing)
        k = max(0.0, 1.64 - 1.0 / tan_theta)
        tau_ci_max = math.sqrt(fc) / (0.31 + 21.0 * crack_width / (maximum_aggregate_size + 16.0))

        delta_fc1 = fc_1 - rho_x * (fy_x - fs_x)
        if delta_fc1 <= 0.0:
            fci = 0.0
            tau_ci = 0.0
        else:
            crack_equilibrium = delta_fc1 / tan_theta - 0.18 * tau_ci_max
            if crack_equilibrium <= 0.0:
                fci = 0.0
                tau_ci = delta_fc1 / tan_theta
            else:
                coefficient_a = 0.82 / tau_ci_max
                coefficient_b = 1.0 / tan_theta - 1.64
                discriminant = max(
                    0.0,
                    coefficient_b**2 - 4.0 * coefficient_a * crack_equilibrium,
                )
                fci = (-coefficient_b - math.sqrt(discriminant)) / (2.0 * coefficient_a)
                tau_ci = (fc_1 + delta_fc1) / tan_theta

        fs_x_crack = fs_x + (fc_1 + fci - tau_ci / tan_theta) / rho_x
        fs_y_crack = fs_y + (fc_1 + fci + tau_ci * tan_theta) / rho_y
        reinforcement_failure = abs(fs_x_crack) >= fy_x or abs(fs_y_crack) >= fy_y
        compression_failure = eps_2 <= eps_c
        slip_capacity = tau_ci_max * (0.18 + 0.3 * k**2) * tan_theta + rho_x * (fy_x - fs_x)
        slip_failure = fc_1 >= slip_capacity
        if reinforcement_failure or compression_failure or slip_failure:
            break
        gamma += gamma_increment

    volume = joint_width * column_depth * beam_depth
    if len(curve) < 5 or curve[-1][1] <= 0:
        shear_modulus = ec / (2.0 * (1.0 + 0.2))
        return tuple(
            (rotation, shear_modulus * volume * rotation)
            for rotation in (0.00005, 0.0005, 0.002, 0.01)
        )

    end_gamma = curve[-1][0]
    selected: list[tuple[float, float]] = []
    for fraction in (0.1, 0.4, 0.7, 1.0):
        target = fraction * end_gamma
        point = min(curve[1:], key=lambda item: abs(item[0] - target))
        rotation = point[0]
        moment = max(point[1] * volume, 1.0e-9)
        if selected and rotation <= selected[-1][0]:
            rotation = selected[-1][0] + gamma_increment
        selected.append((rotation, moment))
    return tuple(selected)


def pinching4_envelope(backbone: tuple[tuple[float, float], ...]) -> tuple[float, ...]:
    """Convert four positive ``(rotation, moment)`` points to Pinching4 order."""

    if len(backbone) != 4:
        raise ValueError("Pinching4 requires exactly four positive backbone points")
    positive = tuple(value for rotation, moment in backbone for value in (moment, rotation))
    negative = tuple(value for rotation, moment in backbone for value in (-moment, -rotation))
    return positive + negative
