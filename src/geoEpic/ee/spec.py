"""Dataset specifications shared by every Earth Engine backend.

This module is part of the dependency-light core: standard library plus
``ruamel.yaml``, which is present both in a GeoEPIC install and inside QGIS.
It must never import ``ee``, ``pandas`` or ``geopandas`` - it only *describes*
what to fetch, so that the QGIS plugin and the CLI agree on the definition of a
source without sharing a client.

See ``design/q-epic-integration.md``.
"""
import re
from pathlib import Path

#: Earth Engine asset ids are slash-separated tokens; a pasted browser URL is
#: the common mistake, so reject anything with a scheme, host or query.
ASSET_ID = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\Z")

SPEC_DIR = Path(__file__).with_name("specs")


class SpecError(ValueError):
    pass


class LinkedCollection:
    """A second collection whose bands are joined onto the primary one.

    This is how Daymet borrows wind speed from gridMET.
    """

    def __init__(self, collection, bands):
        self.collection = collection
        self.bands = list(bands)


class SourceCollection:
    """One Earth Engine ImageCollection and the EPIC variables it supplies."""

    def __init__(self, name, collection, variables, select=None, link=None,
                 time_range=None, resolution=None):
        self.name = name
        self.collection = collection
        # variable name -> Earth Engine expression, e.g. "b('tmax') - 273.15"
        self.variables = dict(variables)
        self.select = select
        self.link = link
        self.time_range = tuple(time_range) if time_range else None
        #: Native scale for this collection, when it differs from the dataset's
        #: (a spec may draw one variable from a coarser product).
        self.resolution = int(resolution) if resolution else None

    @property
    def bands(self):
        """Band names the expressions reference, in first-seen order."""
        seen = []
        for expression in self.variables.values():
            for band in _referenced_bands(expression):
                if band not in seen:
                    seen.append(band)
        return seen


class DatasetSpec:
    """A named, versionable description of one fetchable dataset."""

    def __init__(self, name, resolution, variables, collections,
                 time_range=None, derived=None, description="", scope="global",
                 calendar=None):
        if not collections:
            raise SpecError("A dataset spec needs at least one collection.")
        self.name = name
        self.resolution = int(resolution)
        self.variables = list(variables)
        self.collections = list(collections)
        self.time_range = tuple(time_range) if time_range else None
        self.derived = dict(derived or {})
        self.description = description
        self.scope = scope
        #: A declared calendar quirk of the source, repaired when building a
        #: continuous daily series. See geoEpic.epicfiles.dly.repair_calendar.
        self.calendar = calendar

    # ------------------------------------------------------------------ load

    @classmethod
    def from_dict(cls, data, name=None):
        scope = data.get("global_scope") or {}
        raw = data.get("collections")
        if not raw:
            raise SpecError("Spec has no 'collections' section.")
        collections = []
        for key, config in raw.items():
            if "collection" not in config:
                raise SpecError("Collection {!r} has no 'collection' asset id.".format(key))
            if not config.get("variables"):
                raise SpecError("Collection {!r} defines no variables.".format(key))
            link = config.get("linkcollection")
            collections.append(SourceCollection(
                name=key,
                collection=str(config["collection"]),
                variables={str(k): str(v) for k, v in config["variables"].items()},
                select=str(config["select"]) if config.get("select") else None,
                link=LinkedCollection(link["collection"], link["bands"]) if link else None,
                time_range=config.get("time_range"),
                resolution=config.get("resolution"),
            ))
        return cls(
            name=name or data.get("name") or "unnamed",
            resolution=scope.get("resolution", 1000),
            variables=scope.get("variables") or sorted(
                {v for c in collections for v in c.variables}),
            collections=collections,
            time_range=scope.get("time_range"),
            derived=data.get("derived_variables") or {},
            description=data.get("description", ""),
            scope=data.get("scope", "global"),
            calendar=data.get("calendar"),
        )

    @classmethod
    def from_yaml(cls, path):
        from ruamel.yaml import YAML
        path = Path(path)
        with open(path, "r") as handle:
            data = YAML(typ="safe").load(handle)
        if not isinstance(data, dict):
            raise SpecError("{} is not a mapping.".format(path))
        return cls.from_dict(data, name=path.stem)

    @classmethod
    def bundled(cls, name):
        """Load one of the specs shipped with GeoEPIC."""
        path = SPEC_DIR / (name + ".yml")
        if not path.is_file():
            raise SpecError("No bundled spec named {!r}. Available: {}".format(
                name, ", ".join(available())))
        return cls.from_yaml(path)

    # ------------------------------------------------------------- behaviour

    def window(self, date_range=None):
        """Resolve the date range to use, preferring an explicit argument."""
        window = tuple(date_range) if date_range else self.time_range
        if not window or len(window) != 2:
            raise SpecError("No time range given for spec {!r}.".format(self.name))
        start, end = str(window[0]), str(window[1])
        if start > end:
            raise SpecError("Start date {} is after end date {}.".format(start, end))
        return start, end

    def scale_for(self, source):
        """The scale to reduce one of this spec's collections at."""
        return source.resolution or self.resolution

    def missing_variables(self, produced):
        """Which declared variables a set of produced columns does not cover."""
        produced = {str(p) for p in produced}
        return [v for v in self.variables if v not in produced]

    def __repr__(self):
        return "DatasetSpec({!r}, {} collections, {} m)".format(
            self.name, len(self.collections), self.resolution)


def _referenced_bands(expression):
    """Band names inside b('...') references, without a regex dependency."""
    bands, marker = [], "b('"
    index = expression.find(marker)
    while index >= 0:
        start = index + len(marker)
        end = expression.find("'", start)
        if end < 0:
            break
        bands.append(expression[start:end])
        index = expression.find(marker, end)
    # Also accept double-quoted references.
    marker = 'b("'
    index = expression.find(marker)
    while index >= 0:
        start = index + len(marker)
        end = expression.find('"', start)
        if end < 0:
            break
        bands.append(expression[start:end])
        index = expression.find(marker, end)
    return bands


def is_asset_id(text):
    """Whether a string looks like an Earth Engine asset id rather than a URL."""
    return bool(ASSET_ID.match(str(text).strip()))


def available():
    """Names of the bundled dataset specs."""
    if not SPEC_DIR.is_dir():
        return []
    return sorted(path.stem for path in SPEC_DIR.glob("*.yml"))
