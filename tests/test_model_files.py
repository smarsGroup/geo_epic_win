"""EPICModel's control-file edits on layouts other than the bundled one."""
import os
import shutil

import pytest

import geoEpic
from geoEpic.core import model as model_module
from geoEpic.core.model import EPICModel, launch_command
from geoEpic.epicfiles import printfile

MODEL = os.path.join(os.path.dirname(geoEpic.__file__), "assets", "workspace_win", "model")


@pytest.fixture
def model_dir(tmp_path):
    target = tmp_path / "model"
    shutil.copytree(MODEL, target)
    return target


def open_model(folder):
    return EPICModel(str(folder / "EPIC1102.exe"))


def first_line(folder):
    with open(folder / "EPICCONT.DAT", encoding="ISO-8859-1", newline="") as handle:
        return handle.readline()


def test_fixed_width_period_is_read_and_written_in_place(model_dir):
    # Fortran I4 fields that touch: 20 years from 2001.
    path = model_dir / "EPICCONT.DAT"
    lines = path.read_text(encoding="ISO-8859-1").splitlines(True)
    lines[0] = "  202001   1   1   32345   0   0   0   1   0\r\n"
    path.write_text("".join(lines), encoding="ISO-8859-1")
    model = open_model(model_dir)
    try:
        assert model.duration == 20
        assert str(model.start_date) == "2001-01-01"
        model.duration = 29
        model.start_date = "1995-01-01"
        line = first_line(model_dir)
        assert line.startswith("  291995   1   1   32345")
        assert line.endswith("\r\n")
        assert (model.duration, str(model.start_date)) == (29, "1995-01-01")
    finally:
        model.close()


def test_free_format_period_keeps_its_columns(model_dir):
    model = open_model(model_dir)
    try:
        model.duration = 12
        model.start_date = "2003-01-01"
        line = first_line(model_dir)
        assert line.split()[:4] == ["12", "2003", "1", "1"]
        # The fifth field (and everything after) has not moved.
        assert line[16:] == open(MODEL + "/EPICCONT.DAT", encoding="ISO-8859-1",
                                 newline="").readline()[16:]
    finally:
        model.close()


def test_output_types_survive_a_print_file_ending_in_a_blank_line(model_dir):
    model = open_model(model_dir)
    try:
        name = model.file_names["FPRNT"]
        with open(model_dir / name, "a", encoding="ISO-8859-1") as handle:
            handle.write("    \n")
        model.set_output_types(["ACY", "DGN"])
        assert sorted(printfile.enabled(str(model_dir / name))) == ["ACY", "DGN"]
        assert sorted(model.get_output_types()) == ["ACY", "DGN"]
    finally:
        model.close()


def test_a_windows_build_runs_under_wine_elsewhere(monkeypatch):
    monkeypatch.setattr(model_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(model_module.shutil, "which",
                        lambda name: "/usr/bin/wine" if name == "wine" else None)
    assert launch_command("/m/EPIC1102_7.exe") == ["/usr/bin/wine", "/m/EPIC1102_7.exe"]
    assert launch_command("/m/EPIC1102_7") == ["/m/EPIC1102_7"]


def test_missing_wine_is_named(monkeypatch):
    monkeypatch.setattr(model_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(model_module.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="needs Wine"):
        launch_command("/m/EPIC1102.exe")


def test_windows_runs_the_build_directly(monkeypatch):
    monkeypatch.setattr(model_module.platform, "system", lambda: "Windows")
    assert launch_command(r"C:\m\EPIC1102.exe") == [r"C:\m\EPIC1102.exe"]
