"""Where a cell's irrigation status comes from, and what each source's codes mean.

EPIC needs to know whether a cell is irrigated so it can run the irrigated
variant of that crop's schedule. No single map answers that everywhere, so the
source is a choice, and each one numbers its classes differently:

  ESA WorldCereal   global, 10 m, 2021 only. The `irrigation` product marks
                    actively irrigated temporary cropland with 100.
  IrrMapper         eleven western US states, 30 m, 1985-2025, one image per
                    state per year. `classification` is 0 irrigated, 1 dryland,
                    2 uncultivated, 3 wetland.
  a raster you supply  read as 1 irrigated / 0 rainfed unless you say otherwise.

All three were confirmed against the live service rather than taken from
documentation; the coverage and class figures in the tests come from those
probes. LANID is deliberately absent: it is not published as an Earth Engine
asset, so it is reachable only by uploading it and naming it as a custom asset.

Dependency-light, like the rest of ``epicfiles``: the plugin and the CLI read
one definition of what "irrigated" means for each source.
"""

NONE = "None · every cell rainfed"
WORLDCEREAL = "ESA WorldCereal · global, 2021"
IRRMAPPER = "IrrMapper · western US, 1985-2025"
CUSTOM_ASSET = "Earth Engine asset"
QGIS_LAYER = "QGIS raster layer"
LOCAL_FILE = "Local raster file"

#: Offered in this order; NONE is the default because assuming irrigation where
#: there is none changes yields more than the reverse.
SOURCES = [NONE, WORLDCEREAL, IRRMAPPER, CUSTOM_ASSET, QGIS_LAYER, LOCAL_FILE]

#: Sources read from a raster the user supplies rather than Earth Engine.
LOCAL_SOURCES = (QGIS_LAYER, LOCAL_FILE)

SPECS = {
    WORLDCEREAL: {
        "asset": "ESA/WorldCereal/2021/MODELS/v100",
        "band": "classification",
        "product": "irrigation",
        "irrigated_values": (100,),
        "scale": 10,
        "years": (2021, 2021),
        "credit": "ESA WorldCereal Consortium",
        "coverage": "global",
        "note": ("Global, but a single 2021 season and confined to WorldCereal's "
                 "temporary-crop extent. Published as a lower-confidence product "
                 "than the cereal maps."),
    },
    IRRMAPPER: {
        "asset": "projects/ee-dgketchum/assets/IrrMapper/IrrMapperComp",
        "band": "classification",
        "product": None,
        "irrigated_values": (0,),
        "scale": 30,
        "years": (1985, 2025),
        "credit": "Ketchum et al. · IrrMapper",
        "coverage": "AZ CA CO ID MT NM NV OR UT WA WY",
        "note": ("Annual, 1985-2025, but only the eleven western states. Outside "
                 "them there is no data and no cell is marked irrigated."),
    },
}

#: The states IrrMapper covers, for refusing an ROI it cannot answer for.
IRRMAPPER_STATES = ("AZ", "CA", "CO", "ID", "MT", "NM", "NV", "OR", "UT", "WA", "WY")

#: A raster the user supplies carries no published scheme, so this is the
#: assumption, stated rather than hidden: anything non-zero is irrigated.
USER_RASTER_IRRIGATED = "any value other than 0 or no-data"


def spec_for(source):
    """The dataset definition behind a source, or None for local and custom ones."""
    return SPECS.get(source)


def uses_earth_engine(source):
    return source in SPECS or source == CUSTOM_ASSET


def is_irrigated(source, value):
    """Whether one sampled pixel value means irrigated. None when unknown."""
    if value is None or value != value:              # no data, or NaN
        return None
    spec = SPECS.get(source)
    if spec is not None:
        return int(value) in spec["irrigated_values"]
    if source in LOCAL_SOURCES or source == CUSTOM_ASSET:
        return float(value) != 0.0
    return None


def covers_year(source, year):
    """Whether a source has data for a simulation year."""
    spec = SPECS.get(source)
    if spec is None:
        return True
    first, last = spec["years"]
    return first <= int(year) <= last


def year_for(source, year):
    """The nearest year a source can answer for, which may not be the one asked.

    WorldCereal has only 2021; asking it about 2016 gets 2021 and the caller is
    expected to say so rather than imply the year was honoured.
    """
    spec = SPECS.get(source)
    if spec is None:
        return int(year)
    first, last = spec["years"]
    return min(max(int(year), first), last)


def describe(source, first_year=None, last_year=None):
    """One line on what a source can and cannot answer, for the UI."""
    if source == NONE:
        return "Every cell is simulated as rainfed."
    if source in LOCAL_SOURCES:
        return ("Pixels are read as irrigated where the value is {}. "
                "Cells outside the raster are rainfed.".format(USER_RASTER_IRRIGATED))
    if source == CUSTOM_ASSET:
        return ("Give an Earth Engine image or collection id. Non-zero pixels are "
                "read as irrigated. Use this for LANID or another map you have "
                "uploaded - LANID is not published as an Earth Engine asset.")
    spec = SPECS[source]
    note = spec["note"]
    if first_year is not None and last_year is not None:
        outside = [year for year in (first_year, last_year) if not covers_year(source, year)]
        if outside:
            first, last = spec["years"]
            note += (" The simulation period {}-{} is outside {}-{}, so irrigation is "
                     "taken from {} for every year.".format(
                         first_year, last_year, first, last, year_for(source, first_year)))
    return note
