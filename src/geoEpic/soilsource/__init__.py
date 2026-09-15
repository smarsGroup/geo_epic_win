"""Soil sources, dependency-light.

Query building and response interpretation only: no HTTP client, so the QGIS
plugin posts through QGIS networking and the CLI through requests, against one
definition of the query and the unit conversions.
"""
from . import sda

__all__ = ["sda"]
