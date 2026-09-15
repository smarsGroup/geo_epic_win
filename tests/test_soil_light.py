"""The dependency-light .SOL writer and the SDA query/transform.

The .SOL fixture was captured from the pandas writer before the port; it is the
evidence that swapping the backend changed nothing EPIC can see.
"""
import csv
import hashlib
from pathlib import Path

import pytest

from geoEpic.epicfiles import sol
from geoEpic.soilsource import sda, soilgrids

FIXTURES = Path(__file__).with_name("fixtures")
EXPECTED_SHA = "c07444a4d23bc929ca744f0da153ef765a7cb97901a969d1b8f04e553739497a"


def sample_layers():
    layers = []
    with open(FIXTURES / "soil_123456_input.csv") as handle:
        for row in csv.DictReader(handle):
            layers.append({k: (float(v) if v not in ("", "nan") else float("nan"))
                           for k, v in row.items()})
    return layers


# --------------------------------------------------------------- .SOL writer

def test_light_writer_reproduces_the_captured_pandas_output_exactly():
    produced = sol.dumps(123456, 0.14, "B", sample_layers()).encode()
    assert hashlib.sha256(produced).hexdigest() == EXPECTED_SHA
    assert produced == (FIXTURES / "soil_123456.SOL").read_bytes()


def test_layers_are_ordered_by_depth_and_nan_becomes_zero():
    text = sol.dumps(1, 0.1, "A", sample_layers())
    depths = [float(v) for v in text.splitlines()[3].split()]
    assert depths == sorted(depths)
    # The fourth layer's wilting capacity is NaN in the fixture input.
    wilting = text.splitlines()[5]
    assert wilting.endswith("   0.000")


def test_hydrologic_group_maps_to_epics_codes_and_defaults_to_c():
    assert [sol.hydgrp_code(g) for g in ("A", "B", "C", "D")] == [1, 2, 3, 4]
    # Blank, unknown and compound groups all fall back to C, as before.
    for group in ("", None, "X", "junk"):
        assert sol.hydgrp_code(group) == 3
    assert sol.hydgrp_code("B/D") == 2      # first letter wins
    assert sol.hydgrp_code("b") == 2


def test_the_header_lines_carry_id_albedo_group_and_split_count():
    lines = sol.dumps(98765, 0.23, "D", sample_layers()).splitlines()
    assert lines[0] == "ID: 98765"
    assert lines[1].startswith("   0.230   4.000")
    assert lines[2].startswith("  10.000")


def test_an_overwide_value_runs_into_its_neighbour_and_is_refused_on_read(tmp_path):
    """%8.3f is not clamped, exactly as the pandas writer left it."""
    layers = [{name: 0.0 for name in sol.LAYER_PROPERTIES}]
    layers[0]["Course_Fragment"] = 12345.6789
    text = sol.dumps(1, 0.1, "A", layers)
    assert "12345.679" in text            # nine characters in an eight-wide field
    path = sol.write(tmp_path / "wide", 1, 0.1, "A", layers)
    assert not list(tmp_path.glob("*.partial"))
    # Reading it back positionally cannot recover the columns, so it stops.
    assert Path(path).exists()


def test_round_trip_recovers_the_layers(tmp_path):
    layers = [{name: 0.0 for name in sol.LAYER_PROPERTIES} for _ in range(3)]
    for i, layer in enumerate(layers):
        layer["Layer_depth"] = 0.3 * (i + 1)
        layer["pH"] = 6.0 + i
    path = sol.write(tmp_path / "site", 4242, 0.17, "C", layers)
    back = sol.read(path)
    assert back["soil_id"] == 4242
    assert back["hydgrp"] == "C"
    assert abs(back["albedo"] - 0.17) < 0.0005
    assert len(back["layers"]) == 3
    assert [round(l["pH"], 3) for l in back["layers"]] == [6.0, 7.0, 8.0]


def test_a_profile_needs_at_least_one_layer():
    with pytest.raises(sol.SolError):
        sol.dumps(1, 0.1, "A", [])


# ------------------------------------------------------------------ SDA

def test_the_mukey_condition_distinguishes_a_key_from_a_geometry():
    assert sda.mukey_condition(123456) == "'123456'"
    assert sda.mukey_condition("123456") == "'123456'"
    assert "SDA_Get_Mukey_from_intersection_with_WktWgs84" in sda.mukey_condition(
        "POINT(-96.6 41.2)")
    with pytest.raises(sda.SdaError):
        sda.mukey_condition("")


def test_quotes_in_a_geometry_cannot_break_out_of_the_sql():
    condition = sda.mukey_condition("POINT(1 2)') OR '1'='1")
    assert "''" in condition
    assert condition.count("'") % 2 == 0


def test_the_properties_query_asks_for_series_components_with_water_data():
    query = sda.properties_query(123456)
    assert "FROM sacatalog sc" in query
    assert "compkind='Series'" in query
    assert "wthirdbar_r > 0" in query
    for column in ("hzdepb_r", "dbthirdbar_r", "ksat_r", "albedodry_r", "hydgrp"):
        assert column in query


def test_a_response_without_a_table_is_reported_not_guessed_at():
    for payload in ({}, {"Table": []}, {"Table": [["mukey"]]}, "nonsense"):
        with pytest.raises(sda.SdaError):
            sda.parse_table(payload)


def test_rows_become_one_profile_with_converted_units():
    header = ["mukey", "hzdepb_r", "dbthirdbar_r", "wfifteenbar_r", "wthirdbar_r",
              "sandtotal_r", "silttotal_r", "ph1to1h2o_r", "om_r", "ksat_r",
              "sieveno10_r", "fraggt10_r", "frag3to10_r", "hydgrp", "albedodry_r",
              "slopelenusle_r", "cec7_r", "caco3_r", "sumbases_r", "dbovendry_r"]
    rows = [dict(zip(header, ["123456", "25", "1.35", "10.2", "19.5", "66.9", "25.1",
                              "6.25", "2.0", "9.0", "95", "1", "2", "B", "0.24",
                              "60", "11.3", "0", "12.5", "1.42"]))]
    soil = sda.soil_from_rows(rows)
    assert soil["mukey"] == "123456"
    assert soil["hydgrp"] == "B"
    layer = soil["layers"][0]
    assert layer["Layer_depth"] == 0.25          # cm -> m
    assert layer["Wilting_capacity"] == 0.102    # % -> fraction
    assert layer["Field_Capacity"] == 0.195
    assert layer["Organic_Carbon"] == round(2.0 * 0.58, 4)   # OM -> OC
    assert layer["Saturated_conductivity"] == round(9.0 * 3.6, 4)
    assert layer["Course_Fragment"] == 2.0       # 100 - (95 + 1 + 2)
    assert soil["albedo"] == round(0.24 * 0.625, 4)


def test_components_at_one_depth_collapse_to_their_median():
    header = ["mukey", "hzdepb_r", "wthirdbar_r", "ph1to1h2o_r", "hydgrp"]
    rows = [dict(zip(header, ["1", "30", "20", "6.0", "C"])),
            dict(zip(header, ["1", "30", "20", "7.0", "C"])),
            dict(zip(header, ["1", "30", "20", "8.0", "C"]))]
    soil = sda.soil_from_rows(rows)
    assert len(soil["layers"]) == 1
    assert soil["layers"][0]["pH"] == 7.0
    # Depths within a decimetre share a layer.
    rows.append(dict(zip(header, ["1", "31", "20", "9.0", "C"])))
    assert len(sda.soil_from_rows(rows)["layers"]) == 1


def test_a_point_is_written_in_the_axis_order_sda_expects():
    assert sda.point_wkt(41.2, -96.6) == "POINT(-96.60000000 41.20000000)"


def test_the_profile_feeds_the_writer_directly(tmp_path):
    """The two halves must fit together without a translation layer."""
    header = ["mukey", "hzdepb_r", "dbthirdbar_r", "wthirdbar_r", "hydgrp", "albedodry_r"]
    rows = [dict(zip(header, ["77", str(d), "1.4", "20", "A", "0.2"])) for d in (25, 50)]
    soil = sda.soil_from_rows(rows)
    path = sol.write(tmp_path / soil["mukey"], soil["mukey"], soil["albedo"],
                     soil["hydgrp"], soil["layers"])
    back = sol.read(path)
    assert back["soil_id"] == 77
    assert back["hydgrp"] == "A"
    assert len(back["layers"]) == 2


# --------------------------------------------------------------- SoilGrids

def test_pixel_id_matches_the_isric_hash():
    """Pinned to geoEpic.spatial.isric.SoilGrids.generate_soil_id."""
    assert soilgrids.pixel_id(41.20, -96.60) == 80917543
    assert soilgrids.pixel_id(35.9768, -90.1399) == soilgrids.pixel_id(35.9768, -90.1399)
    # Nearby points inside the same 0.0025 deg cell share an id.
    assert soilgrids.pixel_id(41.20, -96.60) == soilgrids.pixel_id(41.201, -96.601)


def _grid_sample(**overrides):
    values = {"hydrologic_soil_group": 2}
    for suffix, _depth in soilgrids.DEPTHS:
        values["bulk_density_{}".format(suffix)] = 1.35
        values["sand_{}".format(suffix)] = 40.0
        values["silt_{}".format(suffix)] = 35.0
        values["field_capacity_{}".format(suffix)] = 0.4116
        values["wilting_capacity_{}".format(suffix)] = 0.1711
        values["saturated_conductivity_{}".format(suffix)] = 2.62
        values["nitrogen_{}".format(suffix)] = 0.12
        values["ph_{}".format(suffix)] = 6.5
        values["organic_carbon_{}".format(suffix)] = 1.1
        values["cec_{}".format(suffix)] = 18.0
        values["coarse_fragments_{}".format(suffix)] = 5.0
    values.update(overrides)
    return values


def test_a_sample_becomes_six_epic_layers_in_isric_units(tmp_path):
    profile = soilgrids.profile_from_sample(_grid_sample())
    assert profile["albedo"] == 0.15
    assert profile["hydgrp"] == "B"
    assert [layer["Layer_depth"] for layer in profile["layers"]] == [
        0.05, 0.15, 0.30, 0.60, 1.00, 2.00]
    top = profile["layers"][0]
    assert top["Field_Capacity"] == 0.4116
    assert top["Wilting_capacity"] == 0.1711
    assert top["Field_Capacity"] > top["Wilting_capacity"]
    assert top["Bulk_density_dry"] == top["Bulk_Density"]
    path = sol.write(tmp_path / "grid", 80917543, profile["albedo"],
                     profile["hydgrp"], profile["layers"])
    back = sol.read(path)
    assert back["soil_id"] == 80917543
    assert len(back["layers"]) == 6


def test_a_water_cell_is_refused_rather_than_zeroed():
    values = _grid_sample(bulk_density_0_5=None)
    with pytest.raises(soilgrids.SoilGridsError, match="No soil"):
        soilgrids.layers_from_sample(values)
