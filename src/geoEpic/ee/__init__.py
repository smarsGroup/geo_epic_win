"""Earth Engine access for GeoEPIC: one interface, several backends.

The dataset specs and the interface are dependency-light and safe to import
inside QGIS. Backends are imported lazily so that importing this package never
requires ``earthengine-api``.
"""
from .backend import (CollectionReport, EarthEngineBackend, EarthEngineError,
                      Sample, TimeSeries, cadence_from, review_warnings)
from .spec import DatasetSpec, SourceCollection, SpecError, available, is_asset_id
from .variables import EPIC_VARIABLES, looks_meteorological, recognise

__all__ = ["CollectionReport", "EarthEngineBackend", "EarthEngineError", "Sample", "TimeSeries",
           "cadence_from", "review_warnings", "DatasetSpec", "SourceCollection",
           "SpecError", "available", "is_asset_id", "api_backend", "EPIC_VARIABLES", "recognise",
           "looks_meteorological", "WEATHER_SPECS", "spec_for_source"]

#: The weather sources Q-EPIC offers, mapped to their bundled specs. One
#: definition of what "Daymet V4" means, shared by the plugin and the CLI.
WEATHER_SPECS = {"Daymet V4": "daymet", "gridMET": "gridmet", "AgERA5": "agera5"}


def spec_for_source(label):
    """Resolve a user-facing source label to its DatasetSpec."""
    name = WEATHER_SPECS.get(label, label)
    return DatasetSpec.bundled(name)


def api_backend(project=None):
    """Construct the earthengine-api backend, importing it only on demand.

    Absent in the QGIS profile, where the module is not vendored: Q-EPIC
    supplies its own backend against the same interface.
    """
    try:
        from .api_backend import EarthEngineApiBackend
    except ImportError as error:
        raise EarthEngineError(
            "The earthengine-api backend is not part of this installation. "
            "Inside QGIS, use Q-EPIC's QgisEeBackend.") from error
    return EarthEngineApiBackend(project=project)
