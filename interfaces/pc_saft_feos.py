"Temp pcsaft methods while gnnepcsaft is not updated"

from typing import List, Optional

import numpy as np
import si_units as si
from feos import State  # type: ignore pylint: disable=no-name-in-module
from gnnepcsaft.pcsaft.feos.core import pc_saft_mixture

# from feos import Contributions  # type: ignore pylint: disable=no-name-in-module


def mix_den_feos(
    parameters: List[List[float]],
    state: List[float],
    kij_matrix: Optional[List[List[float]]] = None,
    epsilon_ab: Optional[List[List[float]]] = None,
    density_initialization: str = "liquid",
) -> float:
    """
    Calculates mixture liquid density (mol/m³) with PCSAFT.

    Args:
        parameters: A list of
         `[m, sigma, epsilon/kB, kappa_ab, epsilon_ab/kB, dipole moment, na, nb, MW]`
         for each component of the mixture
        state: A list with
         `[Temperature (K), Pressure (Pa), mole_fractions_1, mole_fractions_2, ...]`
        kij_matrix: A matrix of binary interaction parameters
        epsilon_ab: A matrix of cross association energy parameters

    Returns:
        out (float): Mixture liquid density in mol/m^3.
    """

    t = state[0]  # Temperature, K
    p = state[1]  # Pa
    x = np.asarray(state[2:], dtype=np.float64)  # mole fractions

    eos = pc_saft_mixture(parameters, kij_matrix, epsilon_ab)

    statenpt = State(
        eos,
        temperature=t * si.KELVIN,
        pressure=p * si.PASCAL,
        molefracs=x,
        density_initialization=density_initialization,
    )

    den = statenpt.density * (si.METER**3) / si.MOL

    return den
