"""The dependency-light .DLY writer must match the pandas writer byte-for-byte.

The fixture was captured from the pandas implementation before it was ported;
it is the evidence that swapping the backend changed nothing EPIC can see.
"""
import csv
import hashlib
from pathlib import Path

import pytest

from geoEpic.epicfiles import dly

FIXTURES = Path(__file__).with_name("fixtures")
EXPECTED_SHA = "c7d5b583ae35c0a45e77d5f2a038414d4112ad4326ed85e9ab529f9918252901"


def sample_rows():
    rows = []
    with open(FIXTURES / "weather_2016_input.csv") as handle:
        for row in csv.DictReader(handle):
            rows.append({k: (int(v) if k in ("year", "month", "day") else float(v))
                         for k, v in row.items()})
    return rows


def test_light_writer_reproduces_the_captured_pandas_output_exactly():
    produced = dly.dumps(sample_rows()).encode()
    assert hashlib.sha256(produced).hexdigest() == EXPECTED_SHA
    assert produced == (FIXTURES / "weather_2016.DLY").read_bytes()


def test_the_awkward_formatting_cases_are_preserved_not_fixed():
    # A value needing seven characters runs into its neighbour, as it always has.
    line = dly.format_row({"year": 2016, "month": 1, "day": 2, "srad": 100.0,
                           "tmax": -99.99, "tmin": -100.0, "prcp": 999.99,
                           "rh": 0.0, "ws": 9.995})
    assert line == "  2016   1   2100.00-99.99-100.00999.99  0.00  9.99"
    # Ties round half to even, and negative zero survives.
    assert dly.format_row({"year": 1, "month": 1, "day": 1, "srad": -0.005, "tmax": -0.0,
                           "tmin": 55.555, "prcp": 0.0, "rh": 0.0, "ws": 0.0}
                          ).endswith(" -0.01 -0.00 55.55  0.00  0.00  0.00")


def test_rows_may_be_mappings_or_sequences_and_bad_rows_are_named():
    mapping = {"year": 2016, "month": 3, "day": 1, "srad": 1.0, "tmax": 2.0,
               "tmin": 0.0, "prcp": 0.0, "rh": 50.0, "ws": 1.0}
    sequence = [2016, 3, 1, 1.0, 2.0, 0.0, 0.0, 50.0, 1.0]
    assert dly.format_row(mapping) == dly.format_row(sequence)
    with pytest.raises(dly.DlyError):
        dly.format_row({"year": 2016})
    with pytest.raises(dly.DlyError):
        dly.format_row([2016, 1])
    with pytest.raises(dly.DlyError):
        dly.format_row({**mapping, "srad": "wet"})


def test_duplicate_dates_keep_the_first_row():
    first = {"year": 2016, "month": 1, "day": 1, "srad": 1.0, "tmax": 1.0,
             "tmin": 1.0, "prcp": 1.0, "rh": 1.0, "ws": 1.0}
    second = dict(first, srad=9.0)
    assert dly.dumps([first, second]).count("\n") == 1
    assert " 1.00" in dly.dumps([first, second]).split("\n")[0]


def test_round_trip_through_a_file_recovers_the_values(tmp_path):
    # Rows whose values fit their fields; overflow is covered separately below.
    rows = [r for r in sample_rows() if all(-99.99 <= r[c] <= 999.99
                                            for c in ("srad", "tmax", "tmin", "prcp", "rh", "ws"))][:10]
    assert len(rows) == 10
    path = dly.write(tmp_path / "site", rows)
    assert path.endswith(".DLY")
    recovered = dly.read(path)
    assert len(recovered) == 10
    for original, parsed in zip(rows, recovered):
        assert parsed["year"] == original["year"]
        assert abs(parsed["ws"] - round(original["ws"], 2)) < 0.005
    # Nothing is left behind by the atomic write.
    assert not list(tmp_path.glob("*.partial"))


def test_an_overflowing_line_is_refused_rather_than_silently_mis_parsed(tmp_path):
    """A value too wide for its field shifts every column after it.

    The pandas reader (``read_fwf``) accepts such a line and returns corrupted
    values - 999.99 truncated to 999.9, and the trailing fields as strings like
    ``'9  0.0'``. Reading positionally cannot recover them, so this reader stops
    instead of handing EPIC numbers nobody wrote.
    """
    overflowing = {"year": 2016, "month": 1, "day": 2, "srad": 100.0, "tmax": -99.99,
                   "tmin": -100.0, "prcp": 999.99, "rh": 0.0, "ws": 9.995}
    path = dly.write(tmp_path / "wide", [overflowing])
    with pytest.raises(dly.DlyError) as caught:
        dly.read(path)
    assert "wide.DLY" in str(caught.value)


def test_missing_dates_and_covered_years_drive_the_incremental_rule():
    rows = [{"year": 2016, "month": m, "day": d, "srad": 0.0, "tmax": 0.0, "tmin": 0.0,
             "prcp": 0.0, "rh": 0.0, "ws": 0.0}
            for m in range(1, 13) for d in range(1, dly.days_in(2016, m) + 1)]
    assert dly.covered_years(rows) == [2016]
    assert dly.missing_dates(rows, 2016, 2016) == []
    # 2016 is a leap year; a year without its 29 February is not complete.
    incomplete = [r for r in rows if not (r["month"] == 2 and r["day"] == 29)]
    assert dly.covered_years(incomplete) == []
    assert dly.missing_dates(incomplete, 2016, 2016) == [(2016, 2, 29)]
    assert len(dly.missing_dates(rows, 2016, 2017)) == 365


def test_leap_years_follow_the_gregorian_rule():
    assert dly.is_leap(2016) and dly.is_leap(2000)
    assert not dly.is_leap(1900) and not dly.is_leap(2017)
    assert dly.days_in(2016, 2) == 29 and dly.days_in(2017, 2) == 28


# ------------------------------------------------------- monthly companions

WP1_SHA = "19f2c769304a542153ddfc8b36f56aa5a5752c3218c6f46d8265e97ab31b0555"
WND_SHA = "30fbd4402df0ce0da0058f587b2211e0bafe15505cf0c2ac52fb56bafc270ea8"


def test_monthly_companions_reproduce_the_captured_pandas_output():
    rows = sample_rows()
    assert hashlib.sha256(dly.dumps_monthly(rows, "weather_2016").encode()).hexdigest() == WP1_SHA
    assert hashlib.sha256(dly.dumps_wind(rows, "weather_2016").encode()).hexdigest() == WND_SHA
    assert dly.dumps_monthly(rows, "weather_2016").encode() == (FIXTURES / "weather_2016.WP1").read_bytes()
    assert dly.dumps_wind(rows, "weather_2016").encode() == (FIXTURES / "weather_2016.WND").read_bytes()


def test_the_wp1_layout_is_fourteen_named_rows_over_twelve_months():
    lines = dly.dumps_monthly(sample_rows(), "site").splitlines()
    assert lines[0] == "Monthly Weather Statistics : site"
    assert len(lines) == 2 + len(dly.WP1_ROWS)
    for line, label in zip(lines[2:], dly.WP1_ROWS):
        assert line.endswith(label.rjust(8))
        assert len(line) == 12 * 10 + 8


def test_prw1_is_always_zero_which_is_an_upstream_bug_not_a_port_error():
    """to_monthly asks `np.diff(prcp > 0.5) == -1`, but np.diff on a boolean
    array yields booleans, so the comparison is never true.

    The port reproduces the zeros deliberately: PRW1 feeds EPIC's precipitation
    occurrence model, so silently correcting it would change results. If this
    test ever fails, upstream has changed the behaviour and the decision in
    epicfiles/dly.py needs revisiting.
    """
    months, stats = dly.monthly_statistics(sample_rows())
    assert stats["PRW1"] == [0.0] * len(months)
    # What the expression was evidently reaching for, for comparison.
    wet_days = [row for row in sample_rows() if row["month"] == 1]
    wet = [row["prcp"] > dly.WET_MM for row in wet_days]
    intended = sum(1 for a, b in zip(wet, wet[1:]) if a and not b) / len(wet)
    assert intended > 0, "the fixture must actually contain a wet-to-dry day"


def test_prw2_counts_wet_days_that_follow_a_wet_day():
    rows = [{"year": 2016, "month": 1, "day": d, "srad": 0.0, "tmax": 0.0, "tmin": 0.0,
             "prcp": p, "rh": 0.0, "ws": 0.0}
            for d, p in enumerate([1.0, 1.0, 0.0, 1.0], start=1)]
    months, stats = dly.monthly_statistics(rows)
    assert stats["PRW2"] == [0.25]          # only day 2 follows a wet day
    assert stats["DAYP"] == [0.75 * 31]     # three wet days of four, scaled


def test_writing_the_companions_leaves_no_partial_files(tmp_path):
    written = dly.write_monthly(tmp_path / "site.DLY", sample_rows())
    assert [Path(p).name for p in written] == ["site.WP1", "site.WND"]
    assert not list(tmp_path.glob("*.partial"))
    assert (tmp_path / "site.WP1").read_text().startswith("Monthly Weather Statistics : site")
