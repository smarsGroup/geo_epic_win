"""Building a cell's schedule from templates: stitching, fallow, irrigation, nitrogen.

The builder never moves a date. What it decides is which template each year
uses, how their years line up, and how much nitrogen a fertilizer row applies.
"""
from pathlib import Path

import pytest

from geoEpic.epicfiles import opc, opcbuild

MODEL = (Path(__file__).resolve().parents[1] / "src" / "geoEpic" / "assets"
         / "workspace_win" / "model")

CORN = opcbuild.read_template(opc.path_for("CORN"))[2]


def rows_of(text):
    return [row for row in (opcbuild._split(line) for line in text.splitlines()[2:])
            if row is not None]


def test_a_template_row_reads_as_its_fixed_width_fields():
    # "  1  4 24   71    0    2   52 160.000": urea solution at 160 kg/ha.
    fertilizer = [row for row in CORN if row[opcbuild.OPERATION] == 71][0]
    assert fertilizer[:8] == [1, 4, 24, 71, 0, 2, 52, 160.0]
    planting = [row for row in CORN if row[opcbuild.OPERATION] == 2][0]
    assert planting[opcbuild.AMOUNT] == 1700.0          # "    01700.000" run together


def test_a_row_is_written_back_exactly_as_the_heavy_writer_does():
    line = opcbuild.ROW_FORMAT % tuple(CORN[2])
    assert line.startswith("  1  4 24   71    0    2   52 160.000")
    assert opcbuild._split(line) == CORN[2]


def test_years_follow_one_another():
    text, report = opcbuild.build("10000", 2016, [(2, False), (1, False), (2, False)])
    rows = rows_of(text)
    assert sorted({int(row[0]) for row in rows}) == [1, 2, 3]
    crops = {int(row[0]): int(row[opcbuild.CROP]) for row in rows}
    assert crops == {1: 2, 2: 1, 3: 2}                 # corn, soybean, corn
    assert text.splitlines()[0] == "10000 : 2016"
    assert report["years"] == 3 and report["fallow"] == 0


def test_dates_are_the_templates_own():
    text, _ = opcbuild.build("10000", 2016, [(2, False), (2, False)])
    rows = rows_of(text)
    first = [row[1:4] for row in rows if row[0] == 1]
    second = [row[1:4] for row in rows if row[0] == 2]
    assert first == second == [row[1:4] for row in CORN]


def test_a_year_with_no_crop_is_fallow_and_counted():
    text, report = opcbuild.build("10000", 2016, [(2, False), (None, False)])
    rows = rows_of(text)
    assert {int(row[opcbuild.CROP]) for row in rows if row[0] == 2} == {9}
    assert report["fallow"] == 1


def test_a_crop_without_a_template_is_fallow_and_named():
    # Rice (18) is declared in MAPPING but has no RICE.OPC in the bundled set.
    _, report = opcbuild.build("10000", 2016, [(18, False)])
    assert report["fell_back"] == [18]


def test_a_two_year_template_pushes_the_next_crop_along(tmp_path):
    (tmp_path / "MAPPING").write_text("epic_code,template_code\n10,WWHT\n2,CORN\n9,FALLOW\n")
    for name in ("CORN", "FALLOW"):
        (tmp_path / "{}.OPC".format(name)).write_bytes(opc.path_for(name).read_bytes())
    # Winter wheat: sown in year 1's autumn, harvested in year 2.
    (tmp_path / "WWHT.OPC").write_text(
        "Winter wheat\n   3  0\n"
        "  1 10  1    2    0   10    0   0.000    0.00    0.00   0.000\n"
        "  2  7  1  650    0   10    0   0.000    0.00    0.00   0.000\n")
    text, _ = opcbuild.build("10000", 2016, [(10, False), (2, False)], folder=tmp_path)
    years = {int(row[0]): int(row[opcbuild.CROP]) for row in rows_of(text)}
    assert years[1] == 10 and years[2] in (10,) and years[3] == 2


def test_an_irrigated_cell_uses_the_irrigated_variant_where_there_is_one(tmp_path):
    (tmp_path / "MAPPING").write_text("epic_code,template_code\n2,CORN\n9,FALLOW\n")
    for name in ("CORN", "FALLOW"):
        (tmp_path / "{}.OPC".format(name)).write_bytes(opc.path_for(name).read_bytes())
    irrigated = opc.path_for("CORN").read_text().replace("Corn", "Corn irrigated", 1)
    irrigated += "  1  6 15   72    0    2    0  25.000    0.00    0.00   0.000\n"
    (tmp_path / "CORN_IRR.OPC").write_text(irrigated)
    text, report = opcbuild.build("10000", 2016, [(2, True), (2, False)], folder=tmp_path)
    operations = [(int(row[0]), int(row[opcbuild.OPERATION])) for row in rows_of(text)]
    assert (1, 72) in operations and (2, 72) not in operations
    assert report["irrigated"] == 1


def test_an_irrigated_cell_without_a_variant_runs_rainfed_and_says_so():
    _, report = opcbuild.build("10000", 2016, [(2, True)])
    assert report["irrigation_dropped"] == ["CORN"] and report["irrigated"] == 0


# ------------------------------------------------------------------- nitrogen

def test_the_model_tables_name_fertilizer_applicators_and_nitrogen():
    types, nitrogen = opcbuild.model_tables(MODEL)
    assert types[71] == opcbuild.FERTILIZE           # FERTILIZER APP
    assert types[2] != opcbuild.FERTILIZE            # a planter
    assert nitrogen[21] == pytest.approx(1.0)        # Elem-N
    assert nitrogen[52] == pytest.approx(0.2)        # urea solution
    assert nitrogen[22] == pytest.approx(0.0)        # Elem-P carries none


def test_the_rate_is_nitrogen_delivered_not_product():
    text, report = opcbuild.build("10000", 2016, [(2, False)], rates={2: 180}, model=MODEL)
    fertilizer = [row for row in rows_of(text) if row[opcbuild.OPERATION] == 71][0]
    assert fertilizer[opcbuild.MATERIAL] == 52                        # same fertilizer
    assert fertilizer[opcbuild.AMOUNT] == pytest.approx(900.0)        # 180 / 0.20
    assert report["nitrogen_rows"] == 1


def test_a_split_application_keeps_its_proportions():
    rows = [[1, 4, 1, 71, 0, 2, 21, 50.0] + [0.0] * 7,
            [1, 6, 1, 71, 0, 2, 21, 150.0] + [0.0] * 7]
    opcbuild.set_nitrogen(rows, {2: 100}, {71: 9}, {21: 1.0})
    assert [row[opcbuild.AMOUNT] for row in rows] == pytest.approx([25.0, 75.0])


def test_crops_without_a_rate_and_non_nitrogen_rows_are_left_alone():
    rows = [[1, 4, 1, 71, 0, 2, 22, 40.0] + [0.0] * 7,       # Elem-P on corn
            [1, 5, 1, 71, 0, 1, 21, 30.0] + [0.0] * 7,       # N on soybean, no rate
            [1, 5, 2, 30, 0, 2, 21, 10.0] + [0.0] * 7]       # not an applicator
    changed = opcbuild.set_nitrogen(rows, {2: 100}, {71: 9, 30: 0}, {21: 1.0, 22: 0.0})
    assert changed == 0
    assert [row[opcbuild.AMOUNT] for row in rows] == [40.0, 30.0, 10.0]


def test_each_year_of_a_crop_gets_its_own_rate():
    text, _ = opcbuild.build("10000", 2016, [(2, False), (2, False)],
                             rates={2: 120}, model=MODEL)
    amounts = [row[opcbuild.AMOUNT] for row in rows_of(text) if row[opcbuild.OPERATION] == 71]
    assert amounts == pytest.approx([600.0, 600.0])


def test_a_rate_without_a_model_folder_is_refused():
    with pytest.raises(opcbuild.BuildError):
        opcbuild.build("10000", 2016, [(2, False)], rates={2: 180})
