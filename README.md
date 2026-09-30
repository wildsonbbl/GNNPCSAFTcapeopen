# GNNPCSAFT CAPE-OPEN

GNNPCSAFT CAPE-OPEN is a Property Package [CAPE-OPEN](https://www.colan.org/) implementation of [our project](https://github.com/wildsonbbl/gnnepcsaft/) that focuses on using Graph Neural Networks ([GNN](https://en.wikipedia.org/wiki/Graph_neural_network)) to estimate the pure-component parameters of the Equation of State [PC-SAFT](https://en.wikipedia.org/wiki/PC-SAFT). We developed this app so the scientific community can access the model's results easily.

[FeOs](https://github.com/feos-org/feos) is used for PC-SAFT thermodynamic calculations such as VLE. [Comtypes](https://pypi.org/project/comtypes/) is used to implement the CAPE-OPEN COM interfaces. Only Windows is supported for now.

Other implementations with GNNPCSAFT:

- [GNNPCSAFT CLI](https://github.com/wildsonbbl/gnnepcsaftcli)
- [GNNPCSAFT APP](https://github.com/wildsonbbl/gnnpcsaftapp)
- [GNNPCSAFT MCP](https://github.com/wildsonbbl/gnnepcsaft_mcp_server)
- [GNNPCSAFT Webapp](https://github.com/wildsonbbl/gnnepcsaftwebapp)
- [GNNPCSAFT Chat](https://github.com/wildsonbbl/gnnpcsaftchat)

## How to Use

### Installation

You need [Python](https://www.python.org/) installed.

### Installing the GNNPCSAFT CAPE-OPEN Property Package Server

```bash
pip install GNNPCSAFTPropertyPackage
```

### Registering the Server

```bash
GNNPCSAFTPropertyPackage.exe -regserver
```

After registering the server, you can use it in any CAPE-OPEN compliant software.

### Unregistering the Server

```bash
GNNPCSAFTPropertyPackage.exe -unregserver
```

---

## License

GNU General Public License v3.0
