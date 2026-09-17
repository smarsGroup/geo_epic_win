"""Reading which output files an EPIC build can write, and which are on."""
import pytest

from geoEpic.epicfiles import printfile

WINDOWS = "src/geoEpic/assets/workspace_win/model/PRNT1102.DAT"

BODY = "\n".join(["line{}".format(i) for i in range(14)])
TOGGLES = "   0   0   1\n   1   0"
EXTENSIONS = " out acm dgn\n acy run"


def make(tmp_path, toggles=TOGGLES, extensions=EXTENSIONS, tail=""):
    path = tmp_path / "PRNT.DAT"
    path.write_text("{}\n{}\n note\n{}\n{}".format(BODY, toggles, extensions, tail))
    return path


def test_the_shipped_windows_build_reports_acy_and_dgn():
    # What the binary in this repo's assets actually writes.
    assert printfile.enabled(WINDOWS) == ["DGN", "ACY"]
    supported = printfile.supported(WINDOWS)
    assert "ACY" in supported and "DGN" in supported
    assert len(supported) > 20


def test_non_file_extensions_are_not_offered_as_outputs():
    # The print file's own footnote says the last few entries are not files.
    # ERX is one of them in the shipped Windows build.
    assert "ERX" in printfile.supported(WINDOWS, include_non_files=True)
    assert "ERX" not in printfile.supported(WINDOWS)


def test_extensions_are_found_by_content_not_by_counting_from_the_end(tmp_path):
    # A real Linux PRNT0810.DAT ends with a spaces-only line; counting back
    # from the end then reads the wrong lines and reports the wrong types.
    assert printfile.enabled(make(tmp_path)) == ["DGN", "ACY"]
    assert printfile.enabled(make(tmp_path, tail="      \n   \n")) == ["DGN", "ACY"]


def test_asterisks_are_documentation_not_state(tmp_path):
    # Some builds mark selected extensions with an asterisk; the toggles decide.
    path = make(tmp_path, extensions="*out acm*dgn\n acy run")
    assert printfile.enabled(path) == ["DGN", "ACY"]
    assert printfile.supported(path) == ["OUT", "ACM", "DGN", "ACY"]


def test_enabling_a_type_switches_exactly_that_one(tmp_path):
    path = make(tmp_path)
    assert printfile.set_enabled(path, ["ACM"]) == ["ACM"]
    assert printfile.enabled(path) == ["ACM"]
    # And the extensions themselves are untouched.
    assert printfile.supported(path) == ["OUT", "ACM", "DGN", "ACY"]


def test_enabling_nothing_turns_everything_off(tmp_path):
    path = make(tmp_path)
    assert printfile.set_enabled(path, []) == []
    assert printfile.enabled(path) == []


def test_a_type_the_build_cannot_write_is_refused_with_the_list(tmp_path):
    path = make(tmp_path)
    with pytest.raises(printfile.PrintFileError) as error:
        printfile.set_enabled(path, ["ZZZ"])
    assert "ZZZ" in str(error.value)
    assert "OUT" in str(error.value)


def test_a_missing_print_file_is_refused(tmp_path):
    with pytest.raises(printfile.PrintFileError):
        printfile.enabled(tmp_path / "nope.DAT")


def test_mismatched_toggles_are_refused_rather_than_zipped_short(tmp_path):
    # Silently truncating would report a confident, wrong selection.
    path = make(tmp_path, toggles="   0\n")
    with pytest.raises(printfile.PrintFileError):
        printfile.enabled(path)
