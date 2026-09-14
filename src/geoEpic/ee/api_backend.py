"""EarthEngineBackend implemented with the ``earthengine-api`` package.

This is the backend for the CLI and notebook users. It carries the heavy
dependency, so ``ee`` is imported lazily: importing this module inside QGIS,
where ``earthengine-api`` is absent, must not raise - ``available()`` simply
returns False and Q-EPIC uses its own backend instead.

It reproduces the behaviour of ``geoEpic.gee.core.CompositeCollection`` against
the shared DatasetSpec, so both backends fetch from the same definition.
"""
from .backend import (CollectionReport, EarthEngineBackend, EarthEngineError,
                      TimeSeries, cadence_from)


def _ee():
    try:
        import ee
    except ImportError as error:  # pragma: no cover - depends on environment
        raise EarthEngineError(
            "earthengine-api is not installed in this interpreter. Inside QGIS use "
            "Q-EPIC's QgisEeBackend instead.") from error
    return ee


class EarthEngineApiBackend(EarthEngineBackend):
    name = "earthengine-api"

    def __init__(self, project=None):
        self.project = project
        self._ready = False

    # ---------------------------------------------------------------- set-up

    def available(self):
        try:
            import ee  # noqa: F401
        except ImportError:
            return False
        return True

    def initialize(self, project=None):
        ee = _ee()
        self.project = project or self.project
        try:
            ee.Initialize(project=self.project) if self.project else ee.Initialize()
        except Exception as error:
            raise EarthEngineError("Could not initialize Earth Engine: {}".format(error))
        self._ready = True

    def _ensure(self):
        if not self._ready:
            self.initialize()

    # ------------------------------------------------------------- geometry

    def _geometry(self, geometry):
        ee = _ee()
        if not isinstance(geometry, dict) or "type" not in geometry:
            raise EarthEngineError("Geometry must be GeoJSON-shaped with a 'type'.")
        kind = geometry["type"]
        coordinates = geometry.get("coordinates")
        if kind == "Point":
            # Sample the point itself, at the spec's native resolution. A buffer
            # smaller than the source pixel reduces to nothing at that scale, and
            # one large enough to contain a pixel makes the reducer average
            # neighbours - both verified against gridMET. Q-EPIC's backend does
            # the same, so the two return identical series.
            return ee.Geometry.Point(coordinates)
        if kind == "Polygon":
            return ee.Geometry.Polygon(coordinates)
        if kind == "MultiPolygon":
            return ee.Geometry.MultiPolygon(coordinates)
        raise EarthEngineError("Unsupported geometry type {!r}.".format(kind))

    # ------------------------------------------------------------- extraction

    def _collection(self, source, window):
        ee = _ee()
        collection = ee.ImageCollection(source.collection)
        if source.link:
            collection = collection.linkCollection(
                ee.ImageCollection(source.link.collection), source.link.bands)
        start, end = source.time_range or window
        collection = collection.filterDate(start, end)
        if source.select:
            mask = source.select
            collection = collection.map(lambda image: image.updateMask(image.expression(mask)))
        names = list(source.variables)
        for variable, formula in source.variables.items():
            collection = collection.map(_add_band(variable, formula))
        return collection.select(names), names

    def extract(self, spec, geometry, date_range=None):
        self._ensure()
        ee = _ee()
        window = spec.window(date_range)
        area = self._geometry(geometry)
        point_like = geometry.get("type") == "Point"

        merged = {}
        dates = []
        for source in spec.collections:
            collection, names = self._collection(source, window)
            scale = spec.scale_for(source)

            def reduce_image(image, names=names, scale=scale):
                reducer = ee.Reducer.first() if point_like else ee.Reducer.mean()
                values = image.reduceRegion(reducer=reducer, geometry=area,
                                            scale=scale, maxPixels=int(1e9))
                return ee.Feature(None, values).set("date", image.date().format("YYYY-MM-dd"))

            try:
                features = collection.map(reduce_image).getInfo()
            except Exception as error:
                raise EarthEngineError("Extraction failed for {}: {}".format(
                    source.collection, error))
            for feature in features.get("features", []):
                properties = feature.get("properties", {})
                date = properties.get("date")
                if date is None:
                    continue
                row = merged.setdefault(date, {})
                for name in names:
                    if properties.get(name) is not None:
                        row[name] = properties[name]
        dates = sorted(merged)
        columns = {name: [merged[d].get(name) for d in dates] for name in spec.variables
                   if any(name in merged[d] for d in dates)}
        return TimeSeries(dates, columns, spec_name=spec.name, source=self.name)

    # ------------------------------------------------------------ inspection

    def inspect(self, asset, date_range=None, geometry=None, limit=200):
        self._ensure()
        ee = _ee()
        collection = ee.ImageCollection(asset)
        if date_range:
            collection = collection.filterDate(str(date_range[0]), str(date_range[1]))
        if geometry:
            collection = collection.filterBounds(self._geometry(geometry))
        sample = collection.sort("system:time_start").limit(int(limit))
        try:
            count = sample.size().getInfo()
            bands = sample.first().bandNames().getInfo() if count else []
            stamps = sample.aggregate_array("system:time_start").getInfo() if count else []
        except Exception as error:
            raise EarthEngineError("Could not inspect {}: {}".format(asset, error))
        interval, regular = cadence_from(stamps)
        return CollectionReport(asset, count, bands or [], stamps or [],
                                interval_hours=interval, regular=regular)


def _add_band(variable, formula):
    """Return a mapper adding one computed band, mirroring gee.core.apply_formula."""
    def mapper(image):
        computed = image.expression(formula).rename(variable)
        computed = computed.set("system:time_start", image.get("system:time_start"))
        return image.addBands(computed).toFloat()
    return mapper
