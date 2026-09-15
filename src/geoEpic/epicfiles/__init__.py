"""EPIC input and output files, written without pandas.

Dependency-light: importable inside QGIS, vendored into the Q-EPIC plugin, and
used by the heavy ``geoEpic.io`` classes so both surfaces emit identical bytes.
"""
from . import dly, opc, sit, sol

__all__ = ["dly", "opc", "sit", "sol"]
