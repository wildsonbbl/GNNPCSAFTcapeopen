"Temp pcsaft methods while gnnepcsaft is not updated"

from typing import List, Optional

import numpy as np
import si_units as si
from feos import Contributions  # type: ignore pylint: disable=no-name-in-module
from feos import PhaseEquilibrium  # type: ignore pylint: disable=no-name-in-module
from feos import State  # type: ignore pylint: disable=no-name-in-module
from gnnepcsaft.pcsaft.feos.core import pc_saft_mixture
from gnnepcsaft.pcsaft.feos.equilibria import (
    is_stable_feos,
    mix_bp_at_fixed_pressure_feos,
    mix_dp_at_fixed_pressure_feos,
    mix_tp_flash_feos,
    mix_vp_feos,
    state_npt_feos,
)
from scipy.optimize import root_scalar

# from feos import Contributions  # type: ignore pylint: disable=no-name-in-module


def mix_bp_vapor_fracs_at_t_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
) -> List[float]:
    """
    Calculates composition of incipient phase at bubble point temperature with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, molefractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (List[float]): incipient phase mole fractions.
    """
    t = state[0]  # Temperature, K
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)
    vle_bubble_point = PhaseEquilibrium.bubble_point(
        eos,
        temperature_or_pressure=t * si.KELVIN,
        liquid_molefracs=x,
    )
    return vle_bubble_point.vapor.molefracs.tolist()


def mix_bp_vapor_fracs_at_p_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
) -> List[float]:
    """
    Calculates composition of incipient phase at bubble point pressure with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, molefractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (List[float]): incipient phase mole fractions.
    """

    temperature = state[0]  # Temperature, K
    pressure = state[1]  # Pressure, Pa
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)
    vle_bubble_point = PhaseEquilibrium.bubble_point(
        eos,
        temperature_or_pressure=pressure * si.PASCAL,
        liquid_molefracs=x,
        tp_init=temperature * si.KELVIN,
    )
    return vle_bubble_point.vapor.molefracs.tolist()


def mix_dp_liquid_fracs_at_t_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
) -> List[float]:
    """
    Calculates composition of incipient phase at dew point temperature with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, molefractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (List[float]): incipient phase mole fractions.
    """

    t = state[0]  # Temperature, K
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)
    vle_dew_point = PhaseEquilibrium.dew_point(
        eos,
        temperature_or_pressure=t * si.KELVIN,
        vapor_molefracs=x,
    )

    return vle_dew_point.liquid.molefracs.tolist()


def mix_dp_liquid_fracs_at_p_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
) -> List[float]:
    """
    Calculates composition of incipient phase at dew point pressure with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, molefractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (List[float]): incipient phase mole fractions.
    """

    t = state[0]  # Temperature, K
    p = state[1]  # Pressure, Pa
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)
    vle_dew_point = PhaseEquilibrium.dew_point(
        eos,
        temperature_or_pressure=p * si.PASCAL,
        vapor_molefracs=x,
        tp_init=t * si.KELVIN,
    )

    return vle_dew_point.liquid.molefracs.tolist()


def mix_bp_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
) -> float:
    """
    Calculates mixture `Bubble point (Pa)` with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, molefractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (float): Bubble-point pressure in Pascal.
    """
    t = state[0]  # Temperature, K
    _pressure = state[1]  # Pressure, Pa
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)
    vle_bubble_point = PhaseEquilibrium.bubble_point(
        eos, temperature_or_pressure=t * si.KELVIN, liquid_molefracs=x
    )
    return vle_bubble_point.liquid.pressure() / si.PASCAL


def mix_dp_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
) -> float:
    """
    Calculates mixture `Dew point (Pa)` with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, molefractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (float): Dew-point pressure in Pascal.
    """
    t = state[0]  # Temperature, K
    _pressure = state[1]  # Pressure, Pa
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)
    vle_dew_point = PhaseEquilibrium.dew_point(
        eos, temperature_or_pressure=t * si.KELVIN, vapor_molefracs=x
    )
    return vle_dew_point.vapor.pressure() / si.PASCAL


def state_nph_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
    density_initialization: Optional[str] = None,
) -> State:
    """
    Set up a thermodynamic state at NPH.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, mw]`
         for each component of the mixture
        state:
         A list with `[Temperature (K), Pressure (Pa), Enthalpy (kJ/mol),
         mole_fractions_1, mole_fractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters
        density_initialization: Initialization method for density ("liquid", "vapor", None)

    Returns:
        out (feos.State): State at NPH
    """
    t = state[0]  # Temperature, K
    p = state[1]  # Pressure, Pa
    h = state[2]  # Enthaply, kJ/mol
    x = np.asarray(state[3:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(
        parameters, kij_matrix=kij_matrix, epsilon_ab=epsilon_ab
    ).python_ideal_gas([PyPerfectGas()])

    statenph = State(
        eos,
        pressure=p * si.PASCAL,
        molar_enthalpy=h * si.KILO * si.JOULE / si.MOL,
        composition=x * si.MOL,
        density_initialization=density_initialization,
        initial_temperature=t * si.KELVIN,
    )
    return statenph


def critical_state_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
) -> State:
    """
    Set up a thermodynamic state at critical conditions.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, mw]`
         for each component of the mixture
        state:
         A list with `[Initial Temperature (K), mole_fractions_1, mole_fractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters

    Returns:
        out (feos.State): State at critical conditions
    """
    t = state[0]  # Temperature, K
    x = np.asarray(state[1:], dtype=np.float64)  # mole fractions
    eos = pc_saft_mixture(parameters, kij_matrix=kij_matrix)
    statenpt = State.critical_point(
        eos,
        initial_temperature=t * si.KELVIN,
        composition=x * si.MOL,
    )
    return statenpt


class PyPerfectGas:
    """Dummy implementation for an ideal gas with constant heat capacity"""

    def __init__(self):
        """Dummy implementation for an ideal gas with constant heat capacity"""

    def ln_lambda3(self, temperature):
        "ideal gas with constant heat capacity"
        return temperature / temperature

    def dummy(self):
        "dummy"


def solve_enthalpy(
    h: float, init_temp: float, pressure, fractions, parameters, kij_matrix
) -> float:
    """Find T such that the equilibrium *residual* molar enthalpy equals h (J/mol)
    at fixed P and overall composition. Works for VLE and LLE.

    H(T) follows the same logic as the TP CalcEquilibrium path:
      * stability analysis says stable -> residual enthalpy of the single stable
        phase (FEOS selects the stable density root, so no liquid/vapor guess)
      * unstable -> TP flash, H = beta * h_phase1 + (1 - beta) * h_phase2.
        Whether the split is vapor/liquid or liquid/liquid does not matter here:
        the mole-weighted sum is the same, so no phase labelling is needed.
    H(T) is continuous across phase-split onsets (beta -> 0 or 1), so the root is
    bracketed by walking away from init_temp in the direction implied by the sign
    of H(init_temp) - h, then solved with Brent's method. Because the phase
    structure is never assumed (no bubble/dew boundaries), a liquid-liquid split
    below the bubble point, a VLE region, or both along the same isobar are handled
    alike.

    Pure components: H jumps at T_sat; any h inside the jump returns T_sat.

    Raises RuntimeError if no root can be bracketed (e.g. h >= 0 in the vapor
    region, which a residual-only enthalpy cannot reach).
    """
    j_per_mol = si.JOULE / si.MOL

    def equilibrium_h(t: float) -> float:
        state = [t, pressure, *fractions]
        try:
            is_stable = is_stable_feos(
                parameters=parameters, state=state, kij_matrix=kij_matrix
            )
        except RuntimeError:
            is_stable = True  # no phase boundary exists -> single fluid
        if is_stable:
            npt = state_npt_feos(
                parameters=parameters,
                state=state,
                kij_matrix=kij_matrix,
                density_initialization=None,
            )
            return npt.molar_enthalpy(Contributions.Residual) / j_per_mol
        flash = mix_tp_flash_feos(
            parameters=parameters, state=state, kij_matrix=kij_matrix
        )
        beta = min(1.0, max(0.0, flash.vapor_phase_fraction))  # fraction of .vapor
        total = 0.0
        if beta > 0.0:
            total += (
                beta * flash.vapor.molar_enthalpy(Contributions.Residual) / j_per_mol
            )
        if beta < 1.0:
            total += (
                (1.0 - beta)
                * flash.liquid.molar_enthalpy(Contributions.Residual)
                / j_per_mol
            )
        return total

    def f(t: float) -> float:
        """H(T) - h. If FEOS fails exactly at t (e.g. on a phase boundary or near
        a spinodal), evaluate at a tiny nearby T; H is continuous so this is safe."""
        last_exc: Optional[Exception] = None
        for dt in (0.0, 0.05, -0.05, 0.5, -0.5):
            try:
                val = equilibrium_h(t + dt) - h
            except RuntimeError as exc:
                last_exc = exc
                continue
            if np.isfinite(val):
                return val
        raise RuntimeError(f"Enthalpy evaluation failed near T={t:.2f} K: {last_exc}")

    t_min, t_max = 0.2 * init_temp, init_temp + 1500.0

    def bracket_from(t0: float, f0: float, direction: float):
        t_prev, f_prev, step = t0, f0, 5.0
        t_limit = t_max if direction > 0 else t_min
        for _ in range(80):
            t_new = t_prev + direction * step
            if (t_new - t_limit) * direction > 0.0:
                t_new = t_limit
            f_new = f(t_new)
            if f_prev * f_new <= 0.0:
                return sorted((t_prev, t_new))
            if t_new == t_limit:
                return None
            t_prev, f_prev, step = t_new, f_new, step * 1.6
        return None

    f0 = f(init_temp)
    if f0 == 0.0:
        return init_temp

    # H normally increases with T: f0 > 0 means the root is at lower T.
    first = -1.0 if f0 > 0.0 else 1.0
    bracket = None
    last_exc: Optional[Exception] = None
    for direction in (first, -first):
        try:
            bracket = bracket_from(init_temp, f0, direction)
        except RuntimeError as exc:
            last_exc = exc
            bracket = None
        if bracket is not None:
            break
    if bracket is None:
        raise RuntimeError(
            f"Could not bracket enthalpy h={h} J/mol at P={pressure} Pa near"
            f" T0={init_temp} K (residual-only enthalpy may not reach this value)."
            + (f" Last error: {last_exc}" if last_exc else "")
        )

    return root_scalar(
        f=f, method="brentq", bracket=bracket, xtol=1e-9, rtol=1e-10, maxiter=200
    ).root


def solve_entropy(
    entropy: float, init_temp: float, pressure, fractions, parameters, kij_matrix
) -> float:
    """Find T such that residual molar entropy equals ``entropy`` (J/mol/K).

    The calculation deliberately requests ``Contributions.Residual`` because
    FEOS requires an ideal-gas model for total entropy, which this package does
    not provide yet.
    """
    j_per_mol_kelvin = si.JOULE / si.MOL / si.KELVIN

    def equilibrium_s(t: float) -> float:
        state = [t, pressure, *fractions]
        try:
            is_stable = is_stable_feos(
                parameters=parameters, state=state, kij_matrix=kij_matrix
            )
        except RuntimeError:
            is_stable = True
        if is_stable:
            npt = state_npt_feos(
                parameters=parameters,
                state=state,
                kij_matrix=kij_matrix,
                density_initialization=None,
            )
            return npt.molar_entropy(Contributions.Residual) / j_per_mol_kelvin
        flash = mix_tp_flash_feos(
            parameters=parameters, state=state, kij_matrix=kij_matrix
        )
        beta = min(1.0, max(0.0, flash.vapor_phase_fraction))
        total = 0.0
        if beta > 0.0:
            total += (
                beta
                * flash.vapor.molar_entropy(Contributions.Residual)
                / j_per_mol_kelvin
            )
        if beta < 1.0:
            total += (
                (1.0 - beta)
                * flash.liquid.molar_entropy(Contributions.Residual)
                / j_per_mol_kelvin
            )
        return total

    def f(t: float) -> float:
        last_exc: Optional[Exception] = None
        for dt in (0.0, 0.05, -0.05, 0.5, -0.5):
            try:
                value = equilibrium_s(t + dt) - entropy
            except RuntimeError as exc:
                last_exc = exc
                continue
            if np.isfinite(value):
                return value
        raise RuntimeError(f"Entropy evaluation failed near T={t:.2f} K: {last_exc}")

    t_min, t_max = 0.2 * init_temp, init_temp + 1500.0

    def bracket_from(t0: float, f0: float, direction: float):
        t_prev, f_prev, step = t0, f0, 5.0
        t_limit = t_max if direction > 0 else t_min
        for _ in range(80):
            t_new = t_prev + direction * step
            if (t_new - t_limit) * direction > 0.0:
                t_new = t_limit
            f_new = f(t_new)
            if f_prev * f_new <= 0.0:
                return sorted((t_prev, t_new))
            if t_new == t_limit:
                return None
            t_prev, f_prev, step = t_new, f_new, step * 1.6
        return None

    f0 = f(init_temp)
    if f0 == 0.0:
        return init_temp

    first = -1.0 if f0 > 0.0 else 1.0
    bracket = None
    last_exc: Optional[Exception] = None
    for direction in (first, -first):
        try:
            bracket = bracket_from(init_temp, f0, direction)
        except RuntimeError as exc:
            last_exc = exc
            bracket = None
        if bracket is not None:
            break
    if bracket is None:
        raise RuntimeError(
            f"Could not bracket entropy s={entropy} J/mol/K at P={pressure} Pa near"
            f" T0={init_temp} K (residual-only entropy may not reach this value)."
            + (f" Last error: {last_exc}" if last_exc else "")
        )

    return root_scalar(
        f=f, method="brentq", bracket=bracket, xtol=1e-9, rtol=1e-10, maxiter=200
    ).root


def solve_phase_fraction(
    beta_of,
    x_beta0: float,
    x_beta1: float,
    phasefraction: float,
) -> float:
    """
    Solve beta_of(x) = phasefraction for x between the two single-phase
    boundaries x_beta0 (where beta = 0, i.e. the bubble point) and
    x_beta1 (where beta = 1, i.e. the dew point).

    The boundary values are assigned analytically instead of being
    flashed, so f(x_beta0) = phasefraction > 0 and
    f(x_beta1) = phasefraction - 1 < 0 always hold. Every phasefraction
    strictly inside (0, 1) is therefore guaranteed to be bracketed, no
    matter how close to 0 or 1 it is or how narrow the boiling range.
    Only the interior points are flashed.
    """
    lo, hi = sorted((x_beta0, x_beta1))
    direction = 1.0 if x_beta1 > x_beta0 else -1.0  # +1 for T, -1 for P

    def residual(x: float) -> float:
        if (x - x_beta0) * direction <= 0.0:
            return phasefraction  # at or beyond the beta = 0 boundary
        if (x - x_beta1) * direction >= 0.0:
            return phasefraction - 1.0  # at or beyond the beta = 1 boundary
        beta = beta_of(x)
        # clip: single-phase results from the flash are beta = 0 or 1
        return phasefraction - min(1.0, max(0.0, beta))

    return root_scalar(
        f=residual,
        method="brentq",
        bracket=[lo, hi],
        xtol=1e-9,
        rtol=1e-10,
        maxiter=200,
    ).root


def find_t_from_phase_fraction(
    state_temperature,
    state_pressure,
    overall_fractions,
    pcsaft_parameters,
    kij_matrix,
    phasefraction,
) -> float:
    "find temperature from phase fraction"

    state = [state_temperature, state_pressure, *overall_fractions]
    t_bubble = mix_bp_at_fixed_pressure_feos(
        parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
    )
    t_dew = mix_dp_at_fixed_pressure_feos(
        parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
    )
    return solve_phase_fraction(
        beta_of=lambda temperature: mix_tp_flash_feos(
            parameters=pcsaft_parameters,
            state=[temperature, state_pressure, *overall_fractions],
            kij_matrix=kij_matrix,
        ).vapor_phase_fraction,
        x_beta0=t_bubble,
        x_beta1=t_dew,
        phasefraction=phasefraction,
    )


def find_p_from_phase_fraction(
    state_temperature,
    state_pressure,
    overall_fractions,
    pcsaft_parameters,
    kij_matrix,
    phasefraction,
) -> float:
    "find pressure from phase fraction"

    state = [state_temperature, state_pressure, *overall_fractions]
    p_bubble, p_dew = mix_vp_feos(
        parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
    )
    return solve_phase_fraction(
        beta_of=lambda pressure: mix_tp_flash_feos(
            parameters=pcsaft_parameters,
            state=[state_temperature, pressure, *overall_fractions],
            kij_matrix=kij_matrix,
        ).vapor_phase_fraction,
        x_beta0=p_bubble,
        x_beta1=p_dew,
        phasefraction=phasefraction,
    )


def compute_bp_or_dp(prop, pcsaft_parameters, state, kij_matrix) -> float:
    "compute bubble point or dew point depending on `prop`"
    overall_temperature = state[0]
    overall_pressure = state[1]
    overall_fractions = state[2:]
    critical_state = critical_state_feos(
        parameters=pcsaft_parameters,
        state=[overall_temperature, *overall_fractions],
        kij_matrix=kij_matrix,
    )
    critical_temperature = critical_state.temperature / si.KELVIN
    critical_pressure = critical_state.pressure() / si.PASCAL

    if prop in ("dewPointPressure", "bubblePointPressure"):
        if overall_temperature >= critical_temperature:
            return critical_pressure
        if prop == "bubblePointPressure":
            bp = mix_bp_feos(
                parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
            )
            return bp
        dp = mix_dp_feos(
            parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
        )
        return dp
    if prop == "dewPointTemperature":
        if overall_pressure >= critical_pressure:
            return critical_temperature
        return mix_dp_at_fixed_pressure_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    if prop == "bubblePointTemperature":
        if overall_pressure >= critical_pressure:
            return critical_temperature
        return mix_bp_at_fixed_pressure_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    raise RuntimeError(f"Wrong prop ---> {prop}")


def compute_incipient_fracs(prop, pcsaft_parameters, state, kij_matrix) -> List[float]:
    "compute incipient fractions"
    overall_temperature = state[0]
    overall_pressure = state[1]
    overall_fractions = state[2:]
    critical_state = critical_state_feos(
        parameters=pcsaft_parameters,
        state=[overall_temperature, *overall_fractions],
        kij_matrix=kij_matrix,
    )
    critical_temperature = critical_state.temperature / si.KELVIN
    critical_pressure = critical_state.pressure() / si.PASCAL

    if prop == "dewPointPressure":
        if overall_temperature >= critical_temperature:
            return overall_fractions
        return mix_dp_liquid_fracs_at_t_feos(
            parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
        )
    if prop == "bubblePointPressure":
        if overall_temperature >= critical_temperature:
            return overall_fractions
        return mix_bp_vapor_fracs_at_t_feos(
            parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
        )
    if prop == "dewPointTemperature":
        if overall_pressure >= critical_pressure:
            return overall_fractions
        return mix_dp_liquid_fracs_at_p_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    if prop == "bubblePointTemperature":
        if overall_pressure >= critical_pressure:
            return overall_fractions
        return mix_bp_vapor_fracs_at_p_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    raise RuntimeError(f"Wrong prop ---> {prop}")
