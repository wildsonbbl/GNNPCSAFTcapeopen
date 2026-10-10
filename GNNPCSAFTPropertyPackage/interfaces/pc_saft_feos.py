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
    """Find T such that the residual molar enthalpy equals h at fixed P and composition.

    The direct Newton solver is unstable because FEOS can fail when it steps into a
    spinodal region. Instead, we sample the residual on a temperature grid, locate a
    sign change in a valid bracket, and use Brent's method for the final solve.
    """
    bp = mix_bp_at_fixed_pressure_feos(
        parameters=parameters,
        state=[init_temp, pressure, *fractions],
        kij_matrix=kij_matrix,
    )

    def residual(t: float) -> float:
        phase_init = "liquid" if t <= bp else "vapor"
        try:
            npt = state_npt_feos(
                parameters=parameters,
                state=[t, pressure, *fractions],
                kij_matrix=kij_matrix,
                density_initialization=phase_init,
            )
        except RuntimeError:
            return np.nan

        value = npt.molar_enthalpy(Contributions.Residual) / (si.JOULE / si.MOL)
        return h - value

    lo = max(150.0, init_temp - 150.0)
    hi = init_temp + 250.0
    sample_t = np.linspace(lo, hi, 400)
    values = []
    for t in sample_t:
        val = residual(t)
        if np.isfinite(val):
            values.append((t, val))

    if len(values) < 2:
        raise RuntimeError(f"Could not bracket an enthalpy root near T0={init_temp} K")

    for (t1, v1), (t2, v2) in zip(values, values[1:]):
        if abs(v1) < 1e-10:
            return t1
        if v1 * v2 <= 0.0:
            return root_scalar(
                f=residual,
                method="brentq",
                bracket=[t1, t2],
                xtol=1e-9,
                rtol=1e-10,
                maxiter=200,
            ).root

    raise RuntimeError(
        f"No valid enthalpy root found for h={h} kJ/mol near T0={init_temp} K"
    )


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
