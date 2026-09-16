"""Irrigation sources, and irrigated variants of the crop templates.

The class values and coverage asserted here were confirmed against the live
Earth Engine service, not read from documentation: WorldCereal's irrigation
product marks irrigated ground 100, IrrMapper marks it 0, and IrrMapper spans
1985-2025 across eleven western states.
"""
import pytest

from geoEpic.epicfiles import irrigation as irr
from geoEpic.epicfiles import opc


def folder_with(root, templates, mapping="epic_code,template_code\n2,CORN\n1,SOYB\n9,FALLOW\n"):
    for name in templates:
        (root / "{}.OPC".format(name)).write_text("stub\n")
    (root / "MAPPING").write_text(mapping)
    return root


# ------------------------------------------------------------------- sources

def test_each_source_knows_which_value_means_irrigated():
    assert irr.is_irrigated(irr.WORLDCEREAL, 100) is True
    assert irr.is_irrigated(irr.WORLDCEREAL, 0) is False
    # IrrMapper inverts it: 0 is irrigated, 1 dryland, 2 uncultivated, 3 wetland.
    assert irr.is_irrigated(irr.IRRMAPPER, 0) is True
    for other in (1, 2, 3):
        assert irr.is_irrigated(irr.IRRMAPPER, other) is False


def test_the_coarse_global_source_reads_its_middle_class_as_unknown():
    # Class 1 is "up to 2000 ha irrigated somewhere in an 86 sq km block",
    # which says nothing about one cell inside it. Reading it as irrigated
    # would flood rainfed states: Iowa is class 1 across most of its area.
    assert irr.is_irrigated(irr.GLOBAL_COARSE, 2) is True
    assert irr.is_irrigated(irr.GLOBAL_COARSE, 0) is False
    assert irr.is_irrigated(irr.GLOBAL_COARSE, 1) is None


def test_the_coarse_source_is_annual_within_its_span():
    assert irr.covers_year(irr.GLOBAL_COARSE, 2001)
    assert irr.covers_year(irr.GLOBAL_COARSE, 2015)
    assert not irr.covers_year(irr.GLOBAL_COARSE, 2020)
    assert irr.year_for(irr.GLOBAL_COARSE, 2020) == 2015
    assert "9 km" in irr.describe(irr.GLOBAL_COARSE)


def test_no_data_is_unknown_not_rainfed():
    # The difference matters: a cell outside IrrMapper's states has no answer,
    # which is not the same as an answer of "not irrigated".
    for source in (irr.WORLDCEREAL, irr.IRRMAPPER, irr.GLOBAL_COARSE, irr.QGIS_LAYER):
        assert irr.is_irrigated(source, None) is None
        assert irr.is_irrigated(source, float("nan")) is None


def test_a_user_raster_is_read_as_non_zero_irrigated():
    for source in irr.LOCAL_SOURCES:
        assert irr.is_irrigated(source, 1) is True
        assert irr.is_irrigated(source, 7) is True
        assert irr.is_irrigated(source, 0) is False


def test_worldcereal_has_one_year_and_says_so():
    assert irr.covers_year(irr.WORLDCEREAL, 2021)
    assert not irr.covers_year(irr.WORLDCEREAL, 2016)
    assert irr.year_for(irr.WORLDCEREAL, 2016) == 2021
    assert irr.year_for(irr.WORLDCEREAL, 2030) == 2021
    note = irr.describe(irr.WORLDCEREAL, 2016, 2020)
    assert "2021" in note and "every year" in note


def test_irrmapper_covers_the_period_it_claims():
    assert irr.covers_year(irr.IRRMAPPER, 1985)
    assert irr.covers_year(irr.IRRMAPPER, 2025)
    assert not irr.covers_year(irr.IRRMAPPER, 1984)
    assert irr.year_for(irr.IRRMAPPER, 2016) == 2016
    assert len(irr.IRRMAPPER_STATES) == 11


def test_lanid_is_offered_only_as_a_custom_asset():
    assert not any("LANID" in source for source in irr.SOURCES)
    assert "LANID" in irr.describe(irr.CUSTOM_ASSET)


def test_the_default_is_rainfed():
    assert irr.SOURCES[0] == irr.NONE
    assert not irr.uses_earth_engine(irr.NONE)
    assert irr.uses_earth_engine(irr.WORLDCEREAL)
    assert irr.uses_earth_engine(irr.CUSTOM_ASSET)
    assert not irr.uses_earth_engine(irr.QGIS_LAYER)


# ---------------------------------------------------------- template variants

def test_an_irrigated_variant_is_used_when_present(tmp_path):
    folder = folder_with(tmp_path, ("CORN", "CORN_IRR", "SOYB", "FALLOW"))
    wet = opc.resolve_schedule(2, folder, irrigated=True)
    assert wet["template_code"] == "CORN_IRR"
    assert wet["irrigated_applied"] and not wet["irrigation_dropped"]
    dry = opc.resolve_schedule(2, folder, irrigated=False)
    assert dry["template_code"] == "CORN" and not dry["irrigated_applied"]


def test_a_missing_variant_is_reported_not_silently_rainfed(tmp_path):
    folder = folder_with(tmp_path, ("CORN", "SOYB", "FALLOW"))
    result = opc.resolve_schedule(1, folder, irrigated=True)
    assert result["template_code"] == "SOYB"
    assert result["irrigation_dropped"] and not result["irrigated_applied"]


def test_a_crop_with_no_template_still_falls_back_when_irrigated(tmp_path):
    folder = folder_with(tmp_path, ("CORN", "FALLOW"))
    result = opc.resolve_schedule(1, folder, irrigated=True)
    assert result["template_code"] == "FALLOW" and result["fell_back"]


def test_the_catalogue_names_the_variant(tmp_path):
    folder = folder_with(tmp_path, ("CORN", "CORN_IRR", "SOYB", "FALLOW"))
    entries = {e["template_code"]: e for e in opc.catalogue(folder)}
    assert entries["CORN"]["irrigated"] == "CORN_IRR"
    assert entries["SOYB"]["irrigated"] is None
    assert opc.irrigated_templates(folder) == {"CORN": "CORN_IRR"}
    # A variant is not itself a declared crop.
    assert "CORN_IRR" not in entries


def test_the_bundled_folder_has_no_variants_yet_and_says_so():
    note = opc.irrigation_note()
    assert "_IRR" in note and "rainfed schedule" in note


def test_the_note_names_crops_still_missing_a_variant(tmp_path):
    folder = folder_with(tmp_path, ("CORN", "CORN_IRR", "SOYB", "FALLOW"))
    note = opc.irrigation_note(folder)
    assert "Corn" in note and "Soybean" in note
