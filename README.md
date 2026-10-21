# GNNPCSAFT CAPE-OPEN

GNNPCSAFT CAPE-OPEN is a [CAPE-OPEN](https://www.colan.org/) property-package
implementation based on [GNNPCSAFT](https://github.com/wildsonbbl/gnnepcsaft/).
It uses Graph Neural Networks ([GNN](https://en.wikipedia.org/wiki/Graph_neural_network))
to estimate pure-component parameters for the
[PC-SAFT](https://en.wikipedia.org/wiki/PC-SAFT) equation of state.

[FeOs](https://github.com/feos-org/feos) performs the PC-SAFT thermodynamic
calculations, including VLE/LLE. [Comtypes](https://pypi.org/project/comtypes/)
implements the CAPE-OPEN COM interfaces. The property package is currently
supported on Windows only.

The thermodynamic calculations currently use residual properties only.
Ideal-gas contributions are not implemented and are outside the current scope.
The residual PH and PS equilibrium paths are implemented without ideal-gas
contributions; calculations that require ideal-gas properties are not
supported yet.

Other implementations with GNNPCSAFT:

- [GNNPCSAFT CLI](https://github.com/wildsonbbl/gnnepcsaftcli)
- [GNNPCSAFT APP](https://github.com/wildsonbbl/gnnpcsaftapp)
- [GNNPCSAFT MCP](https://github.com/wildsonbbl/gnnepcsaft_mcp_server)
- [GNNPCSAFT Webapp](https://github.com/wildsonbbl/gnnepcsaftwebapp)
- [GNNPCSAFT Chat](https://github.com/wildsonbbl/gnnpcsaftchat)

## How to Use

### Installation

You need [Python](https://www.python.org/) 3.10 or newer on Windows.

### Installing the GNNPCSAFT CAPE-OPEN Property Package Server

```bash
pip install GNNPCSAFTPropertyPackage
```

The package installs the `GNNPCSAFTPropertyPackage` command and its CAPE-OPEN
type library.

### Registering the Server

```bash
GNNPCSAFTPropertyPackage.exe -regserver
```

After registering the server, you can use it in any CAPE-OPEN compliant software.

### Unregistering the Server

```bash
GNNPCSAFTPropertyPackage.exe -unregserver
```

### Running the Python tests

Install the development test tools, then run the Python test suite:

```powershell
python.exe -m pip install -e ".[dev]"
python.exe -m pytest -q
```

The test suite includes unit and CAPE-OPEN interface tests. It also discovers
the supplied `.fsd` fixtures through `tests/test_coco.py`. Those integration
tests are skipped when `COFEStand.exe` is not installed.

### Running the COCO integration tests

The flowsheet fixtures are solved headlessly with
[COFEStand](https://www.cocosimulator.org/). They cover flash and LLE
scenarios, CO2 mixtures, absorber cases, and a distillation case. The fixtures
that use ChemSep also require [ChemSep](https://www.cocosimulator.org/) to be
installed and available to COCO.

The default COFEStand locations are:

```text
C:\Program Files\COCO\x64\COFEStand.exe
C:\Program Files\COCO\win32\COFEStand.exe
```

For another installation location, set `COFE_STAND` to the full path of
`COFEStand.exe` before running:

```powershell
$env:COFE_STAND = "C:\path\to\COFEStand.exe"
python.exe -m pytest tests/test_coco.py -v
```

---

## License

GNU General Public License v3.0
