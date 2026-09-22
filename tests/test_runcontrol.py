"""The control files EPIC reads to run one site."""
import pytest

from geoEpic.epicfiles import runcontrol


def model_folder(tmp_path, text=None):
    (tmp_path / "EPICFILE.DAT").write_text(text if text is not None else
        " FSITE    ieSite.DAT\n FSOIL    ieSllist.DAT\n FOPSC    ieOplist.DAT\n"
        " FWLST    ieWedlst.DAT\n FWPM1    ieWealst.DAT\n FWIND    ieWndlst.DAT\n")
    return tmp_path


def test_the_run_line_names_the_site_and_the_list_entries():
    assert runcontrol.run_line("10500014") == "10500014 1  0  0  0  1  1  1/"


def test_file_names_come_from_the_model_folder(tmp_path):
    folder = model_folder(tmp_path, " FSITE    myPlaces.DAT\n FSOIL    mySoils.DAT\n")
    names = runcontrol.read_file_names(folder)
    assert names["FSITE"] == "myPlaces.DAT"
    assert names["FSOIL"] == "mySoils.DAT"
    # Roles the folder does not list keep their conventional names.
    assert names["FWIND"] == "ieWndlst.DAT"


def test_a_folder_without_epicfile_is_refused(tmp_path):
    with pytest.raises(runcontrol.RunControlError):
        runcontrol.read_file_names(tmp_path)


def test_every_file_a_run_needs_is_written(tmp_path):
    folder = model_folder(tmp_path)
    written = runcontrol.write(folder, "10000", "10000.SIT", "10000.SOL", "10000.OPC",
                               41.0, -96.5, 350.0)
    assert {path.name for path in written} == {
        "EPICRUN.DAT", "ieSite.DAT", "ieSllist.DAT", "ieOplist.DAT",
        "ieWedlst.DAT", "ieWealst.DAT", "ieWndlst.DAT"}


def test_inputs_are_referenced_by_name_beside_the_run(tmp_path):
    folder = model_folder(tmp_path)
    runcontrol.write(folder, "10000", "/elsewhere/10000.SIT", "/far/10000.SOL",
                     "/away/10000.OPC", 41.0, -96.5, 350.0)
    # EPIC resolves these relative to its working directory, so only the base
    # name may appear - an absolute path from the workspace would not be found.
    assert (folder / "ieSite.DAT").read_text() == '1    "./10000.SIT"\n'
    assert "/elsewhere" not in (folder / "ieSite.DAT").read_text()


def test_weather_is_always_presented_as_run_one(tmp_path):
    folder = model_folder(tmp_path)
    runcontrol.write(folder, "10000", "a.SIT", "b.SOL", "c.OPC", 41.0, -96.5, 350.0)
    assert (folder / "ieWedlst.DAT").read_text() == "1    1.DLY\n"
    assert (folder / "ieWealst.DAT").read_text().startswith("1    1.WP1")
    assert (folder / "ieWndlst.DAT").read_text().startswith("1    1.WND")


def test_the_station_lines_carry_the_site_coordinates(tmp_path):
    folder = model_folder(tmp_path)
    runcontrol.write(folder, "10000", "a.SIT", "b.SOL", "c.OPC", 41.1651, -96.4766, 362.0)
    assert (folder / "ieWealst.DAT").read_text() == "1    1.WP1   41.17   -96.48    362.00\n"


def test_acy_is_always_expected_even_when_not_asked_for():
    # EPIC writes it regardless, and its absence is how a silent failure is
    # told apart from a run that produced no rows for the chosen outputs.
    assert runcontrol.expected_outputs("10000", ["DGN"]) == ["10000.DGN", "10000.ACY"]
    assert runcontrol.expected_outputs("10000", ["ACY"]) == ["10000.ACY"]


# ----------------------------------------------------------------- run period

FREE = "   5 2015   1   1   3 2345   0   0   1   4\r\nsecond line\r\n"
FIXED = "  202001   1   1   32345   0   0   0   1\nsecond line\n"


def test_both_layouts_of_the_first_line_are_recognised():
    assert runcontrol.period_style(FREE.splitlines()[0]) == "free"
    # Fortran I4 fields: a 20-year run from 2001 reads "  202001", which a
    # whitespace split takes for the single number 202001.
    assert runcontrol.period_style(FIXED.splitlines()[0]) == "fixed"


def test_the_period_is_read_in_the_files_own_layout():
    assert runcontrol.read_period(FREE) == (5, 2015, 1, 1)
    assert runcontrol.read_period(FIXED) == (20, 2001, 1, 1)


def test_a_new_period_keeps_the_fixed_layout():
    updated = runcontrol.with_period(FIXED, 2005, 12)
    assert updated.splitlines()[0].startswith("  122005   1   1")
    assert runcontrol.read_period(updated) == (12, 2005, 1, 1)


def test_a_new_period_keeps_free_columns_aligned():
    updated = runcontrol.with_period(FREE, 2005, 20)
    line = updated.splitlines()[0]
    assert line.startswith("  20 2005   1   1")
    # Everything after the period is where it was.
    assert line[16:] == FREE.splitlines()[0][16:]


def test_line_endings_and_the_rest_of_the_file_are_untouched():
    for text in (FREE, FIXED):
        updated = runcontrol.with_period(text, 2005, 3)
        assert updated.splitlines(True)[0][-2:] == text.splitlines(True)[0][-2:]
        assert updated.splitlines(True)[1:] == text.splitlines(True)[1:]


def test_an_implausible_period_is_refused():
    with pytest.raises(runcontrol.RunControlError):
        runcontrol.with_period(FREE, 2005, 0)
    with pytest.raises(runcontrol.RunControlError):
        runcontrol.with_period(FREE, 205, 3)


def test_a_first_line_with_no_date_is_refused():
    with pytest.raises(runcontrol.RunControlError):
        runcontrol.read_period("garbage here\n")


def test_the_shipped_windows_control_file_round_trips():
    path = "src/geoEpic/assets/workspace_win/model/EPICCONT.DAT"
    text = runcontrol.read_text(path)
    assert "\r\n" in text                               # read without translation
    assert runcontrol.read_period(runcontrol.with_period(text, 2010, 7)) == (7, 2010, 1, 1)
