"""Parsing EPIC output tables."""
import pytest

from geoEpic.epicfiles import outputs

ANNUAL = """
    EPIC1102v1, build #1
         10000
         ./10000.SIT
  YR   RT# CPNM    YLDG     BIOM
 1995    1 CORN    5.000   12.000
 1996    1 SOYB    2.000    6.000
"""

DAILY = """
    EPIC1102v1
    Y   M   D        ET       LAI
 1995   1   1     0.100     0.000
 1995   1   2     0.300     0.500
"""


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text.lstrip("\n"))
    return path


def test_the_header_is_found_by_content_not_line_number(tmp_path):
    # The preamble's length varies with how many input paths a run records.
    short = write(tmp_path, "a.ACY", ANNUAL)
    long = write(tmp_path, "b.ACY", ANNUAL.replace("         ./10000.SIT\n",
                                                   "         ./10000.SIT\n" * 6))
    assert outputs.read(short).columns == outputs.read(long).columns


def test_resolution_follows_the_time_columns(tmp_path):
    assert outputs.read(write(tmp_path, "a.ACY", ANNUAL)).resolution == "annual"
    assert outputs.read(write(tmp_path, "a.DGN", DAILY)).resolution == "daily"


def test_label_columns_are_not_variables(tmp_path):
    table = outputs.read(write(tmp_path, "a.ACY", ANNUAL))
    assert table.value_columns == ["YLDG", "BIOM"]


def test_periods_carry_the_resolution(tmp_path):
    annual = outputs.read(write(tmp_path, "a.ACY", ANNUAL))
    daily = outputs.read(write(tmp_path, "a.DGN", DAILY))
    assert annual.series("YLDG")[0][0] == (1995,)
    assert daily.series("ET")[0][0] == (1995, 1, 1)


def test_a_row_that_does_not_line_up_is_skipped(tmp_path):
    # Zipping it short would put every later value under the wrong column.
    table = outputs.read(write(tmp_path, "a.ACY", ANNUAL + " 1997    1 CORN    9.0\n"))
    assert table.skipped == 1
    assert len(table.rows) == 2


def test_a_missing_column_is_named_with_what_is_there(tmp_path):
    table = outputs.read(write(tmp_path, "a.ACY", ANNUAL))
    with pytest.raises(outputs.OutputError) as error:
        table.column("NOPE")
    assert "YLDG" in str(error.value)


def test_prose_is_not_mistaken_for_a_table(tmp_path):
    with pytest.raises(outputs.OutputError):
        outputs.read(write(tmp_path, "a.ACY", "no table here\njust prose\n"))


def test_every_aggregation():
    values = [1.0, 2.0, 3.0, 4.0]
    assert outputs.aggregate(values, "mean") == 2.5
    assert outputs.aggregate(values, "sum") == 10.0
    assert outputs.aggregate(values, "min") == 1.0
    assert outputs.aggregate(values, "max") == 4.0
    assert outputs.aggregate(values, "median") == 2.5
    assert round(outputs.aggregate(values, "std"), 6) == 1.290994


def test_aggregating_nothing_gives_nothing_rather_than_zero():
    assert outputs.aggregate([]) is None


def test_an_unknown_aggregation_names_the_ones_that_exist():
    with pytest.raises(outputs.OutputError) as error:
        outputs.aggregate([1.0], "average")
    assert "median" in str(error.value)
