"Temp pcsaft methods while gnnepcsaft is not updated"

from typing import List, Optional

import numpy as np
import si_units as si
from feos import PhaseEquilibrium  # type: ignore pylint: disable=no-name-in-module
from feos import State  # type: ignore pylint: disable=no-name-in-module
from gnnepcsaft.pcsaft.feos.core import pc_saft_mixture

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
