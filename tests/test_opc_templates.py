"""The crop template catalogue: what is declared, what is actually shipped.

The point of this module is that an absent template is *reported* rather than
silently simulated as fallow, so the tests are mostly about the absent case.
"""
import pytest

from geoEpic.epicfiles import opc


def write_folder(root, mapping_text, templates=("FALLOW",)):
    for name in templates:
        (root / "{}.OPC".format(name)).write_text("stub\n")
    (root / "MAPPING").write_text(mapping_text)
    return root


def test_bundled_folder_is_usable():
    ok, message = opc.validate()
    assert ok, message
    codes = {entry["epic_code"]: entry["template_code"] for entry in opc.catalogue()}
    assert codes[2] == "CORN" and codes[1] == "SOYB" and codes[9] == "FALLOW"


def test_bundled_folder_declares_more_than_it_ships():
    # Not an assertion about which are missing - only that the gap is visible,
    # and closes on its own as template files are added.
    absent = {code for code, _ in opc.missing()}
    shipped = {entry["template_code"] for entry in opc.catalogue() if entry["available"]}
    assert absent.isdisjoint(shipped)
    assert "FALLOW" in shipped


def test_catalogue_keeps_mapping_order(tmp_path):
    folder = write_folder(tmp_path, "epic_code,template_code\n2,CORN\n1,SOYB\n9,FALLOW\n")
    assert [e["template_code"] for e in opc.catalogue(folder)] == ["CORN", "SOYB", "FALLOW"]


def test_either_column_spelling_is_accepted(tmp_path):
    folder = write_folder(tmp_path, "crop_code,name\n2,CORN\n9,FALLOW\n")
    assert opc.read_mapping(folder) == {2: "CORN", 9: "FALLOW"}


def test_unreadable_row_does_not_hide_the_rest(tmp_path):
    folder = write_folder(tmp_path, "epic_code,template_code\n2,CORN\nxx,RICE\n9,FALLOW\n")
    assert opc.read_mapping(folder) == {2: "CORN", 9: "FALLOW"}


def test_resolve_reports_the_fallback(tmp_path):
    folder = write_folder(tmp_path, "epic_code,template_code\n2,CORN\n18,RICE\n9,FALLOW\n",
                          templates=("FALLOW", "CORN"))
    assert opc.resolve(2, folder) == ("CORN", False)
    assert opc.resolve(9, folder) == ("FALLOW", False)      # fallow was asked for
    assert opc.resolve(18, folder) == ("FALLOW", True)      # declared, not shipped
    assert opc.resolve(777, folder) == ("FALLOW", True)     # not declared at all


def test_validate_names_the_missing_crops(tmp_path):
    folder = write_folder(tmp_path, "epic_code,template_code\n18,RICE\n9,FALLOW\n")
    ok, message = opc.validate(folder)
    assert ok and "Rice" in message and "fallow" in message


def test_validate_refuses_a_folder_without_fallow(tmp_path):
    (tmp_path / "CORN.OPC").write_text("stub\n")
    (tmp_path / "MAPPING").write_text("epic_code,template_code\n2,CORN\n")
    ok, message = opc.validate(tmp_path)
    assert not ok and "FALLOW.OPC is missing" in message


def test_missing_mapping_is_an_error(tmp_path):
    with pytest.raises(opc.TemplateError):
        opc.read_mapping(tmp_path)


def test_mapping_without_a_code_column_is_an_error(tmp_path):
    (tmp_path / "MAPPING").write_text("template_code\nCORN\n")
    with pytest.raises(opc.TemplateError):
        opc.read_mapping(tmp_path)
