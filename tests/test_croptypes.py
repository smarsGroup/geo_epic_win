"""Class codes from crop maps translated into EPIC crop codes.

The hazard these guard is silent and specific: CDL numbers corn 1, EPIC numbers
corn 2 and soybean 1. A missing translation does not raise - it grows soybeans
where the map said corn.
"""
import pytest

from geoEpic.epicfiles import croptypes, opc


def test_the_corn_soybean_swap_cannot_happen():
    # The whole reason the table exists.
    assert croptypes.to_epic(croptypes.CDL, 1) == 2       # CDL corn -> EPIC CORN
    assert croptypes.to_epic(croptypes.CDL, 5) == 1       # CDL soy  -> EPIC SOYB
    assert croptypes.to_epic(croptypes.CDL, 2) == 4       # CDL cotton -> EPIC COTS


def test_every_translated_code_is_a_crop_the_templates_declare():
    declared = set(opc.read_mapping())
    for source, table in croptypes.TABLES.items():
        for class_value, epic_code in table.items():
            assert epic_code in declared, (source, class_value, epic_code)


def test_an_unknown_class_is_reported_not_guessed():
    for value in (26, 241, 63, 176, 0, -1):
        assert croptypes.to_epic(croptypes.CDL, value) is None


def test_double_crops_are_left_out_deliberately():
    # A rotation is not a crop; it belongs in the per-year crop table.
    for double_crop in (26, 225, 236, 238, 239, 241, 254):
        assert double_crop not in croptypes.CDL_TO_EPIC


def test_sources_without_crop_classes_translate_nothing():
    for source in croptypes.WITHOUT_CROP_TYPES:
        assert not croptypes.supports_crop_types(source)
        assert croptypes.to_epic(source, 40) is None
    assert croptypes.supports_crop_types(croptypes.CDL)
    assert croptypes.supports_crop_types(croptypes.WORLDCEREAL)


def test_coverage_counts_what_would_be_left_out():
    mapped, unmapped = croptypes.coverage(croptypes.CDL, [1, 1, 1, 5, 26, 26, 63])
    assert mapped == {1: 2, 5: 1}
    assert unmapped == {26: 2, 63: 1}


def test_worldcereal_mixes_are_not_given_a_single_crop():
    assert croptypes.to_epic(croptypes.WORLDCEREAL, 1) == 2     # maize alone
    assert croptypes.to_epic(croptypes.WORLDCEREAL, 2) == 510   # winter cereals alone
    for mixed in (3, 5, 6, 7):                                  # overlapping detections
        assert croptypes.to_epic(croptypes.WORLDCEREAL, mixed) is None
    assert croptypes.to_epic(croptypes.WORLDCEREAL, 0) is None  # type unspecified


def test_a_bad_value_does_not_raise():
    assert croptypes.to_epic(croptypes.CDL, None) is None
    assert croptypes.to_epic(croptypes.CDL, "corn") is None
