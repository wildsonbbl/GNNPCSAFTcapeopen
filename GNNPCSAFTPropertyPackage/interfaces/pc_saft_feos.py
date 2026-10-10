"Temp pcsaft methods while gnnepcsaft is not updated"

from typing import List, Optional

import numpy as np
import si_units as si
from feos import Contributions  # type: ignore pylint: disable=no-name-in-module
from feos import PhaseEquilibrium  # type: ignore pylint: disable=no-name-in-module
from feos import State  # type: ignore pylint: disable=no-name-in-module
from gnnepcsaft.pcsaft.feos.core import pc_saft_mixture
from gnnepcsaft.pcsaft.feos.equilibria import (
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
    at fixed P and overall composition.

    The enthalpy function H(T) used here is continuous across the phase boundary:
      * T <= T_bubble : residual enthalpy of the single liquid phase
      * T_bubble < T < T_dew : phase-weighted sum from a TP flash,
            beta * h_vapor + (1 - beta) * h_liquid
      * T >= T_dew : residual enthalpy of the single vapor phase
    The two boundary values are computed once from single-phase states and are
    assigned analytically (never flashed), so the three regions are selected by
    comparing h with H(T_bubble) and H(T_dew). Each region is then solved with
    Brent's method on a bracket that is guaranteed to hold the root.

    Pure components / azeotropes (T_bubble == T_dew): any h between the saturated
    liquid and vapor enthalpies maps to T_sat, because T and P do not fix the
    vapor fraction there.

    Raises RuntimeError if no root can be bracketed (e.g. h is not reachable
    with a residual-only enthalpy, such as h >= 0 in the vapor region).
    """
    j_per_mol = si.JOULE / si.MOL

    def state_at(t: float) -> List[float]:
        return [t, pressure, *fractions]

    def single_h(t: float, init: Optional[str]) -> float:
        npt = state_npt_feos(
            parameters=parameters,
            state=state_at(t),
            kij_matrix=kij_matrix,
            density_initialization=init,
        )
        return npt.molar_enthalpy(Contributions.Residual) / j_per_mol

    def flash_h(t: float) -> float:
        flash = mix_tp_flash_feos(
            parameters=parameters, state=state_at(t), kij_matrix=kij_matrix
        )
        beta = min(1.0, max(0.0, flash.vapor_phase_fraction))
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

    def expand(fun, t0: float, direction: float, t_limit: float):
        """Walk from t0 (where fun*direction <= 0 side is known) until fun changes
        sign. Returns an ordered bracket [a, b]. direction = -1 walks down in T
        (fun(t0) >= 0 expected), +1 walks up (fun(t0) <= 0 expected)."""
        t_prev, step = t0, 5.0
        for _ in range(80):
            t_new = t_prev + direction * step
            if (t_new - t_limit) * direction > 0.0:
                t_new = t_limit
            try:
                f_new = fun(t_new)
            except RuntimeError as exc:
                raise RuntimeError(
                    f"Enthalpy evaluation failed at T={t_new:.2f} K while bracketing"
                    f" h={h} J/mol at P={pressure} Pa: {exc}"
                ) from exc
            if f_new * direction >= 0.0:  # crossed (or hit) the root
                return sorted((t_prev, t_new))
            if t_new == t_limit:
                break
            t_prev, step = t_new, step * 1.6
        raise RuntimeError(
            f"Could not bracket enthalpy h={h} J/mol at P={pressure} Pa. Residual-only"
            " enthalpy may not reach this value (no ideal-gas contribution)."
        )

    def brent(fun, bracket) -> float:
        return root_scalar(
            f=fun, method="brentq", bracket=bracket, xtol=1e-9, rtol=1e-10, maxiter=200
        ).root

    # --- phase boundaries at this P and composition ---------------------------
    t_bub = t_dew = None
    try:
        t_bub = mix_bp_at_fixed_pressure_feos(
            parameters=parameters, state=state_at(init_temp), kij_matrix=kij_matrix
        )
        t_dew = mix_dp_at_fixed_pressure_feos(
            parameters=parameters, state=state_at(init_temp), kij_matrix=kij_matrix
        )
    except RuntimeError:
        t_bub = t_dew = None  # no VLE at this P (e.g. supercritical)

    if t_bub is None or t_dew is None:
        # No phase split: single fluid, let FEOS pick the stable density root.
        def f_fluid(t):
            return single_h(t, None) - h

        lo_t, hi_t = 0.2 * init_temp, init_temp + 1500.0
        f0 = f_fluid(init_temp)
        if f0 == 0.0:
            return init_temp
        bracket = expand(
            f_fluid, init_temp, -1.0 if f0 > 0.0 else 1.0, lo_t if f0 > 0.0 else hi_t
        )
        return brent(f_fluid, bracket)

    t_bub, t_dew = min(t_bub, t_dew), max(t_bub, t_dew)
    h_bub = single_h(t_bub, "liquid")  # beta = 0 boundary
    h_dew = single_h(t_dew, "vapor")  # beta = 1 boundary

    # --- subcooled liquid ------------------------------------------------------
    if h <= h_bub:
        if h == h_bub:
            return t_bub

        def f_liq(t):
            return single_h(t, "liquid") - h

        bracket = expand(f_liq, t_bub, -1.0, 0.2 * t_bub)
        return brent(f_liq, bracket)

    # --- superheated vapor -----------------------------------------------------
    if h >= h_dew:
        if h == h_dew:
            return t_dew

        def f_vap(t):
            return single_h(t, "vapor") - h

        bracket = expand(f_vap, t_dew, 1.0, t_dew + 1500.0)
        return brent(f_vap, bracket)

    # --- two-phase region: h_bub < h < h_dew -----------------------------------
    if t_dew - t_bub < 1e-6:
        return t_bub  # pure component / azeotrope: T is not determined by (P, h)

    def f_two(t: float) -> float:
        if t <= t_bub:
            return h_bub - h  # < 0, analytic boundary
        if t >= t_dew:
            return h_dew - h  # > 0, analytic boundary
        return flash_h(t) - h

    return brent(f_two, [t_bub, t_dew])


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

    if prop in ("dewPointPressure", "bubblePointPressure"):
        bp, dp = mix_vp_feos(
            parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
        )
        if prop == "bubblePointPressure":
            return bp
        return dp
    if prop == "dewPointTemperature":
        return mix_dp_at_fixed_pressure_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    if prop == "bubblePointTemperature":
        return mix_bp_at_fixed_pressure_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    raise RuntimeError(f"Wrong prop ---> {prop}")


def compute_incipient_fracs(prop, pcsaft_parameters, state, kij_matrix) -> List[float]:
    "compute incipient fractions"

    if prop == "dewPointPressure":
        return mix_dp_liquid_fracs_at_t_feos(
            parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
        )
    if prop == "bubblePointPressure":
        return mix_bp_vapor_fracs_at_t_feos(
            parameters=pcsaft_parameters, state=state, kij_matrix=kij_matrix
        )
    if prop == "dewPointTemperature":
        return mix_dp_liquid_fracs_at_p_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    if prop == "bubblePointTemperature":
        return mix_bp_vapor_fracs_at_p_feos(
            parameters=pcsaft_parameters,
            state=state,
            kij_matrix=kij_matrix,
        )
    raise RuntimeError(f"Wrong prop ---> {prop}")
