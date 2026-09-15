"""The Earth Engine interface the GeoEPIC core talks to.

One interface, several backends (``design/q-epic-integration.md``):

    geoEpic.core ──calls──▶ EarthEngineBackend
                             ├── EarthEngineApiBackend  (CLI, earthengine-api)
                             └── QgisEeBackend          (Q-EPIC, QGIS networking)

Nothing here imports ``ee``. The operation set is deliberately the small number
of things the core actually needs, derived from the existing call sites, rather
than a general Earth Engine wrapper - a wide interface would become a second
client to maintain, which is the problem this exists to avoid.

Results are plain Python. No pandas crosses this boundary.
"""


class EarthEngineError(RuntimeError):
    """A backend could not satisfy a request."""


class TimeSeries:
    """Columnar result of an extraction: dates plus one list per variable."""

    def __init__(self, dates, columns, spec_name="", source=""):
        self.dates = list(dates)
        self.columns = {name: list(values) for name, values in columns.items()}
        self.spec_name = spec_name
        self.source = source
        for name, values in self.columns.items():
            if len(values) != len(self.dates):
                raise EarthEngineError(
                    "Column {!r} has {} values for {} dates.".format(
                        name, len(values), len(self.dates)))

    def __len__(self):
        return len(self.dates)

    @property
    def variables(self):
        return sorted(self.columns)

    def column(self, name):
        if name not in self.columns:
            raise EarthEngineError("No column {!r}; have {}.".format(name, self.variables))
        return self.columns[name]

    def rows(self):
        """Iterate as dicts, for callers that prefer records."""
        names = sorted(self.columns)
        for i, date in enumerate(self.dates):
            row = {"date": date}
            row.update({name: self.columns[name][i] for name in names})
            yield row

    def is_empty(self):
        return not self.dates


class Sample:
    """One set of values at a place, from sources with no time axis.

    Static products such as SoilGrids and HiHydroSoil answer "what is here",
    not "what happened when", so a TimeSeries would be the wrong shape.
    """

    def __init__(self, values, spec_name="", source=""):
        self.values = dict(values)
        self.spec_name = spec_name
        self.source = source

    def __len__(self):
        return len(self.values)

    def get(self, name, default=None):
        return self.values.get(name, default)

    def require(self, names):
        """Names with no value, so a caller can refuse rather than guess."""
        return [name for name in names if self.values.get(name) is None]

    def is_empty(self):
        return not any(value is not None for value in self.values.values())


class CollectionReport:
    """What inspecting an arbitrary ImageCollection told us.

    Deliberately conservative: recognising a band name is evidence of a
    candidate variable, never proof of its units, scaling or completeness.
    """

    def __init__(self, asset, image_count, bands, timestamps, interval_hours=None,
                 regular=False, warnings=None):
        self.asset = asset
        self.image_count = image_count
        self.bands = list(bands)
        self.timestamps = list(timestamps)
        self.interval_hours = interval_hours
        self.regular = regular
        self.warnings = list(warnings or [])

    @property
    def cadence(self):
        if self.interval_hours is None:
            return "unknown"
        if self.interval_hours == 24:
            return "daily"
        if self.interval_hours < 24:
            return "sub-daily ({:g} h)".format(self.interval_hours)
        return "coarser than daily ({:g} h)".format(self.interval_hours)

    @property
    def usable_as_daily(self):
        """Whether a daily EPIC weather series could be built from this."""
        return (self.interval_hours is not None
                and self.interval_hours <= 24
                and self.regular)


class EarthEngineBackend:
    """Implement these four operations to plug a client into GeoEPIC."""

    name = "abstract"

    def initialize(self, project=None):
        """Prepare credentials. Backends may treat this as a no-op."""
        raise NotImplementedError

    def extract(self, spec, geometry, date_range=None):
        """Evaluate a DatasetSpec over a geometry and return a TimeSeries.

        ``geometry`` is GeoJSON-shaped: ``{"type": "Point"|"Polygon"|
        "MultiPolygon", "coordinates": ...}``. No shapely.
        """
        raise NotImplementedError

    def sample(self, spec, geometry):
        """Evaluate a static DatasetSpec over a geometry and return a Sample.

        SoilGrids and HiHydroSoil have no time axis, so a TimeSeries is the
        wrong shape. Timed specs should use ``extract``.
        """
        raise NotImplementedError

    def inspect(self, asset, date_range=None, geometry=None, limit=200):
        """Return a CollectionReport for an arbitrary ImageCollection id."""
        raise NotImplementedError

    def available(self):
        """Whether this backend can run right now (client present, signed in)."""
        return False


def cadence_from(timestamps):
    """Modal spacing of sorted epoch-millisecond timestamps, and regularity.

    Shared by backends so both report cadence identically.
    """
    times = sorted({int(t) for t in timestamps if isinstance(t, (int, float))})
    gaps = [round((b - a) / 3600000.0, 6) for a, b in zip(times, times[1:]) if b > a]
    if not gaps:
        return None, False
    counts = {}
    for gap in gaps:
        counts[gap] = counts.get(gap, 0) + 1
    interval = max(counts, key=counts.get)
    return interval, counts[interval] == len(gaps)


def review_warnings(report, required=()):
    """Plain-language cautions shared by every backend's validation path."""
    warnings = []
    if not report.bands:
        warnings.append("No bands were returned; this collection cannot be used as input.")
    missing = [name for name in required if name not in report.bands]
    if missing:
        warnings.append("Required variables absent or unrecognized: " + ", ".join(missing) + ".")
    if report.interval_hours is None:
        warnings.append("Insufficient distinct timestamps to establish a frequency.")
    elif report.interval_hours > 24:
        warnings.append("Coarser-than-daily observations cannot be converted into a "
                        "complete daily weather series.")
    elif report.interval_hours < 24:
        warnings.append("Daily aggregation is required before DLY generation: temperature "
                        "extrema, precipitation and radiation totals, mean humidity and wind. "
                        "Accumulation intervals must be checked.")
    if report.interval_hours is not None and not report.regular:
        warnings.append("Timestamp gaps or irregular sampling require review.")
    warnings.append("Band-name checks do not verify units, scaling, full-period coverage, "
                    "or pixel completeness.")
    return warnings
