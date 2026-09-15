"""USDA Soil Data Access: the query and the transform, without pandas or HTTP.

Dependency-light half of `geoEpic.soil.sda`. It builds the SQL and turns the
service's JSON into EPIC soil layers; it deliberately does **not** make the
request, so the QGIS plugin can post it through QGIS networking and the CLI
through requests, against one definition of the query and the unit conversions.

The SQL, the conversions and the median-per-rounded-depth aggregation are
carried over from `SoilDataAccess.fetch_properties` unchanged in meaning.
"""

URL = "https://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService/post.rest"

#: Columns the properties query returns, in order.
PROPERTY_COLUMNS = (
    "mukey", "cokey", "chkey", "musym", "desgnvert", "hzdepb_r", "dbthirdbar_r",
    "wfifteenbar_r", "wthirdbar_r", "sandtotal_r", "silttotal_r", "ph1to1h2o_r",
    "awc_r", "sumbases_r", "om_r", "caco3_r", "cec7_r", "sieveno10_r", "fraggt10_r",
    "frag3to10_r", "dbovendry_r", "ksat_r", "compname", "hydgrp", "comppct_r",
    "slope_r", "slopelenusle_r", "albedodry_r",
)


class SdaError(ValueError):
    pass


def _quote(text):
    """Escape a value for inlining into SDA's SQL, which takes no parameters."""
    return str(text).replace("'", "''")


def mukey_condition(target):
    """The mukey sub-condition for either a numeric mukey or a WKT geometry."""
    if isinstance(target, bool):
        raise SdaError("Expected a mukey or a WKT string.")
    if isinstance(target, int):
        return "'{}'".format(target)
    text = str(target).strip()
    if not text:
        raise SdaError("Expected a mukey or a WKT string.")
    if text.isdigit():
        return "'{}'".format(text)
    return ("SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{}')"
            .format(_quote(text)))


def mukey_query(wkt):
    """SQL returning the map unit keys intersecting a WKT geometry."""
    return ("SELECT mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{}')"
            .format(_quote(wkt)))


def properties_query(target):
    """SQL returning every horizon of every series component for a map unit."""
    return """
        SELECT DISTINCT mu.mukey,co.cokey,ch.chkey,mu.musym, desgnvert,hzdepb_r,dbthirdbar_r,
        wfifteenbar_r,wthirdbar_r,sandtotal_r,silttotal_r,ph1to1h2o_r,awc_r,sumbases_r,om_r,
        caco3_r,cec7_r,sieveno10_r,fraggt10_r,frag3to10_r,dbovendry_r,ksat_r,compname,hydgrp,
        comppct_r,slope_r,slopelenusle_r, albedodry_r
        FROM sacatalog sc
        LEFT JOIN legend lg ON sc.areasymbol = lg.areasymbol
        LEFT JOIN (
        SELECT * FROM mapunit
        WHERE mukey in ({})
        ) mu ON lg.lkey = mu.lkey
        LEFT JOIN component co ON mu.mukey = co.mukey
        LEFT JOIN chorizon ch ON co.cokey = ch.cokey
        WHERE mu.mukey IS NOT NULL
        AND compkind='Series'
        AND wthirdbar_r > 0
        """.format(mukey_condition(target))


def request_body(query):
    """The POST body SDA expects, with column names in the first row."""
    return {"format": "JSON+COLUMNNAME", "query": query}


def parse_table(payload):
    """Turn SDA's `Table` (header row then data rows) into a list of dicts."""
    if not isinstance(payload, dict):
        raise SdaError("Soil Data Access returned an unreadable response.")
    table = payload.get("Table")
    if not table:
        raise SdaError("Soil Data Access found no soil data for this location. "
                       "It covers the United States only.")
    header, rows = table[0], table[1:]
    if not rows:
        raise SdaError("Soil Data Access found no soil data for this location.")
    return [dict(zip(header, row)) for row in rows]


def _float(value):
    """SDA sends numbers as strings and gaps as null or ''; both become zero."""
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if number != number else number


def _median(values):
    ordered = sorted(values)
    count = len(ordered)
    if not count:
        return 0.0
    middle = count // 2
    if count % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


#: Derived layer properties, in the names the .SOL writer expects.
def _layer_from(row):
    return {
        "Layer_depth": _float(row.get("hzdepb_r")) * 0.01,        # cm -> m
        "Bulk_Density": _float(row.get("dbthirdbar_r")),
        "Wilting_capacity": _float(row.get("wfifteenbar_r")) * 0.01,
        "Field_Capacity": _float(row.get("wthirdbar_r")) * 0.01,
        "Sand_content": _float(row.get("sandtotal_r")),
        "Silt_content": _float(row.get("silttotal_r")),
        "N_concen": 0.0,
        "pH": _float(row.get("ph1to1h2o_r")),
        "Sum_Bases": _float(row.get("sumbases_r")),
        "Organic_Carbon": _float(row.get("om_r")) * 0.58,          # OM -> OC
        "Calcium_Carbonate": _float(row.get("caco3_r")),
        "Cation_exchange": _float(row.get("cec7_r")),
        "Course_Fragment": 100.0 - (_float(row.get("sieveno10_r"))
                                    + _float(row.get("fraggt10_r"))
                                    + _float(row.get("frag3to10_r"))),
        "cnds": 0.0, "pkrz": 0.0, "rsd": 0.0,
        "Bulk_density_dry": _float(row.get("dbovendry_r")),
        "psp": 0.0,
        "Saturated_conductivity": _float(row.get("ksat_r")) * 3.6,  # um/s -> mm/h
    }


def soil_from_rows(rows):
    """Aggregate SDA horizons into one EPIC profile.

    Components of a map unit are collapsed by taking the median of every
    property at each depth, after rounding depth to a decimetre - the same rule
    `SoilDataAccess.fetch_properties` applies.
    """
    if not rows:
        raise SdaError("Soil Data Access returned no horizons.")
    buckets, metadata = {}, []
    for row in rows:
        layer = _layer_from(row)
        key = round(layer["Layer_depth"] * 10.0) / 10.0
        buckets.setdefault(key, []).append(layer)
        metadata.append(row)

    layers = []
    for key in sorted(buckets):
        group = buckets[key]
        layers.append({name: round(_median([item[name] for item in group]), 4)
                       for name in group[0]})

    hydgrp = ""
    for row in metadata:
        text = str(row.get("hydgrp") or "").strip()
        if text:
            hydgrp = text[0].upper()
            break
    albedo = round(_median([_float(row.get("albedodry_r")) * 0.625 for row in metadata]), 4)
    slope_length = _median([_float(row.get("slopelenusle_r")) for row in metadata])
    mukey = next((str(row.get("mukey")).strip() for row in metadata
                  if str(row.get("mukey") or "").strip()), "")
    return {"mukey": mukey, "albedo": albedo, "hydgrp": hydgrp or "C",
            "slope_length": slope_length, "layers": layers}


def point_wkt(latitude, longitude):
    """WKT for a location, in the axis order SDA expects."""
    return "POINT({:.8f} {:.8f})".format(float(longitude), float(latitude))
