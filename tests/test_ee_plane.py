"""The Earth Engine plane: specs, the backend contract, and QGIS-safety.

These tests deliberately import no pandas and no ee, so they also run under
QGIS's interpreter. That is the property the whole design depends on.
"""
import subprocess
import sys

import pytest

from geoEpic.ee import (CollectionReport, DatasetSpec, EarthEngineBackend, SpecError,
                        TimeSeries, available, cadence_from, review_warnings)


# ------------------------------------------------------------------- specs

def test_every_bundled_spec_loads_and_declares_its_variables():
    names = available()
    assert {"daymet", "gridmet", "agera5", "soilgrids"} <= set(names)
    for name in names:
        spec = DatasetSpec.bundled(name)
        assert spec.collections, name
        produced = {v for c in spec.collections for v in c.variables}
        # Everything the spec advertises must actually be produced somewhere.
        assert not spec.missing_variables(produced), (name, spec.missing_variables(produced))


def test_weather_specs_agree_on_the_epic_variable_set():
    epic = ["srad", "tmax", "tmin", "prcp", "rh", "ws"]
    for name in ("daymet", "gridmet", "agera5"):
        assert DatasetSpec.bundled(name).variables == epic, name


def test_daymet_borrows_wind_from_gridmet_as_a_second_collection():
    """Daymet carries no wind speed, so gridMET supplies it.

    It is a separate collection rather than an Image.linkCollection: the link
    joins per image and measured 70.5 s for one year against 7.7 s without it,
    and results from several collections are merged on date anyway.
    """
    daymet = DatasetSpec.bundled("daymet")
    assert len(daymet.collections) == 2
    primary, wind = daymet.collections
    assert primary.collection == "NASA/ORNL/DAYMET_V4"
    assert "ws" not in primary.variables
    assert wind.collection == "IDAHO_EPSCOR/GRIDMET"
    assert "vs" in wind.variables["ws"]
    # gridMET is sampled at its own pixel, not Daymet's finer one.
    assert daymet.scale_for(wind) == 4000
    assert daymet.scale_for(primary) == 1000


def test_daymet_declares_the_calendar_gap_it_needs_repaired():
    daymet = DatasetSpec.bundled("daymet")
    assert daymet.calendar == "drops-dec-31-in-leap-years"
    for other in ("gridmet", "agera5"):
        assert DatasetSpec.bundled(other).calendar is None, other


def test_relative_humidity_is_a_fraction_in_every_weather_spec():
    """geoEpic stores rh as a fraction, not a percentage.

    geoEpic.weather.formule.rh_vappr returns vp/es, and weather/daymet.py
    divides rmax/rmin percentages by 100. A spec emitting percentages produced
    values above 1.0 on 37-51 days of a fetched year before this was fixed.
    """
    for name in ("daymet", "gridmet", "agera5"):
        spec = DatasetSpec.bundled(name)
        expression = next(c.variables["rh"] for c in spec.collections if "rh" in c.variables)
        assert "/ 200" in expression or "611" in expression, (name, expression)


def test_band_references_are_extracted_from_expressions():
    spec = DatasetSpec.bundled("gridmet")
    bands = spec.collections[0].bands
    assert {"tmmx", "tmmn", "pr", "srad", "vs"} <= set(bands)
    # Order is first-seen and deduplicated.
    assert len(bands) == len(set(bands))


def test_window_prefers_the_argument_and_rejects_reversed_ranges():
    spec = DatasetSpec.bundled("agera5")
    assert spec.window(("2016-01-01", "2020-12-31")) == ("2016-01-01", "2020-12-31")
    with pytest.raises(SpecError):
        spec.window(("2020-01-01", "2016-12-31"))
    with pytest.raises(SpecError):
        spec.window(None)


def test_malformed_specs_are_rejected_with_a_reason():
    with pytest.raises(SpecError):
        DatasetSpec.from_dict({"collections": {}})
    with pytest.raises(SpecError):
        DatasetSpec.from_dict({"collections": {"x": {"variables": {"a": "b('a')"}}}})
    with pytest.raises(SpecError):
        DatasetSpec.from_dict({"collections": {"x": {"collection": "A/B"}}})
    with pytest.raises(SpecError):
        DatasetSpec.bundled("no_such_source")


# ---------------------------------------------------------------- contract

def test_timeseries_rejects_ragged_columns_and_reports_records():
    series = TimeSeries(["2016-01-01", "2016-01-02"], {"tmax": [1.0, 2.0], "tmin": [-1.0, 0.0]})
    assert len(series) == 2
    assert series.variables == ["tmax", "tmin"]
    assert series.column("tmax") == [1.0, 2.0]
    assert list(series.rows())[0] == {"date": "2016-01-01", "tmax": 1.0, "tmin": -1.0}
    with pytest.raises(Exception):
        TimeSeries(["2016-01-01"], {"tmax": [1.0, 2.0]})


def test_cadence_detection_matches_what_backends_must_report():
    day = 86400000
    assert cadence_from([0, day, 2 * day]) == (24.0, True)
    assert cadence_from([0, 3600000, 7200000]) == (1.0, True)
    interval, regular = cadence_from([0, day, 5 * day])
    assert interval == 24.0 and regular is False
    assert cadence_from([]) == (None, False)
    assert cadence_from([42]) == (None, False)


def test_review_warnings_never_claim_more_than_band_names_prove():
    report = CollectionReport("A/B", 10, ["tmax", "tmin"], [], interval_hours=24, regular=True)
    warnings = review_warnings(report, required=["tmax", "tmin", "prcp"])
    assert any("prcp" in w for w in warnings)
    assert any("do not verify units" in w for w in warnings)
    assert report.cadence == "daily"
    assert report.usable_as_daily


def test_coarser_than_daily_is_not_usable_as_daily():
    report = CollectionReport("A/B", 4, ["t"], [], interval_hours=168, regular=True)
    assert not report.usable_as_daily
    assert "coarser than daily" in report.cadence
    assert any("Coarser-than-daily" in w for w in review_warnings(report))


def test_point_geometries_are_sampled_not_buffered():
    """A point must stay a point.

    Verified live against gridMET at (41.20, -96.60) on 2020-01-01, where the
    pixel holds 280.79998779296875 K: sampling the point returns exactly that,
    a 90 m buffer returns null at the source's 4 km scale, and a buffer wide
    enough to contain a pixel averages neighbours into 280.74918156376594.
    Both backends therefore sample the point itself.
    """
    from geoEpic.ee.api_backend import EarthEngineApiBackend
    backend = EarthEngineApiBackend()
    if not backend.available():
        pytest.skip("earthengine-api is not installed in this interpreter")
    try:
        geometry = backend._geometry({"type": "Point", "coordinates": [-96.60, 41.20]})
        geojson = geometry.toGeoJSON()
    except Exception as error:               # noqa: BLE001
        # Constructing an ee.Geometry needs an initialized client, which means
        # credentials; Q-EPIC's suite asserts the same contract offline.
        pytest.skip("Earth Engine client not initialized: {}".format(error))
    assert geojson["type"] == "Point"
    assert geojson["coordinates"] == [-96.60, 41.20]


def test_the_interface_is_abstract_until_a_backend_implements_it():
    backend = EarthEngineBackend()
    assert backend.available() is False
    for call in (lambda: backend.initialize(),
                 lambda: backend.extract(None, None),
                 lambda: backend.inspect("A/B")):
        with pytest.raises(NotImplementedError):
            call()


# ------------------------------------------------------------- QGIS-safety

def test_api_backend_imports_and_degrades_without_earthengine_api():
    from geoEpic.ee.api_backend import EarthEngineApiBackend
    backend = EarthEngineApiBackend()
    assert isinstance(backend, EarthEngineBackend)
    if not backend.available():
        from geoEpic.ee.backend import EarthEngineError
        with pytest.raises(EarthEngineError):
            backend.initialize()


QGIS_PYTHON = "/usr/bin/python3"


@pytest.mark.skipif(sys.executable == QGIS_PYTHON, reason="already the QGIS interpreter")
def test_the_plane_imports_under_a_pandas_free_interpreter():
    """The core promise: this package works where pandas and ee do not exist."""
    probe = (
        "import sys, importlib.util as u;"
        "sys.path.insert(0, %r);"
        "from geoEpic.ee import DatasetSpec, available;"
        "import geoEpic.ee.api_backend;"
        "assert available(), 'no bundled specs';"
        "DatasetSpec.bundled('daymet');"
        "assert 'pandas' not in sys.modules, 'pandas leaked into the light core';"
        "assert 'ee' not in sys.modules, 'ee leaked into the light core';"
        "print('ok')" % _src_dir()
    )
    result = subprocess.run([QGIS_PYTHON, "-c", probe], capture_output=True, text=True)
    if result.returncode != 0 and "No such file" in (result.stderr or ""):
        pytest.skip("no system python3 to probe with")
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def _src_dir():
    import os
    import geoEpic
    return os.path.dirname(os.path.dirname(os.path.abspath(geoEpic.__file__)))
