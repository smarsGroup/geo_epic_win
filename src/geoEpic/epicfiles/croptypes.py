"""Crop-class codes from land-cover products, translated into EPIC crop codes.

Every crop map numbers its classes its own way, and none of them number them the
way EPIC does. The USDA CDL calls corn 1; EPIC calls it 2, and calls 1 soybean.
So feeding CDL codes straight into a MAPPING keyed by EPIC codes does not fail -
it quietly grows the wrong crop. This module is the translation that stops that.

The rule throughout is the same one :mod:`geoEpic.epicfiles.opc` follows: a class
this table does not cover is *reported*, never guessed at. :func:`to_epic`
returns None rather than a default, and :func:`coverage` counts what was left
out, so a caller can say "9 % of cells have no EPIC crop for their CDL class"
instead of silently simulating them as fallow.

Only classes with an unambiguous single EPIC crop are mapped. Double crops
(CDL 26 winter wheat/soybeans, 241 corn/soybeans) are deliberately absent: they
are a rotation, not a crop, and belong in the per-year crop table rather than in
a one-crop-per-cell lookup.
"""

CDL = "USDA Cropland Data Layer"
WORLDCEREAL = "ESA WorldCereal"

#: USDA NASS CDL class value -> EPIC crop code.
#:
#: Sweet corn and pop/ornamental corn are folded into CORN, which is an
#: approximation and the only one in this table.
CDL_TO_EPIC = {
    1: 2,        # Corn                  -> CORN
    2: 4,        # Cotton                -> COTS
    3: 18,       # Rice                  -> RICE
    4: 3,        # Sorghum               -> GRSG
    5: 1,        # Soybeans              -> SOYB
    12: 2,       # Sweet corn            -> CORN   (approximate)
    13: 2,       # Pop or ornamental corn-> CORN   (approximate)
    23: 11,      # Spring wheat          -> SWHT
    24: 510,     # Winter wheat          -> WWHT
    27: 19,      # Rye                   -> RYE
    61: 9,       # Fallow / idle cropland-> FALLOW
}

#: The composite classes :func:`q_epic.ui.cropland_sources.worldcereal` builds,
#: numbered by which seasonal detections overlap. Only the unmixed ones can name
#: a single crop; a pixel flagged as both maize and winter cereals is a rotation.
WORLDCEREAL_TO_EPIC = {
    1: 2,        # Maize                 -> CORN
    2: 510,      # Winter cereals        -> WWHT
    4: 11,       # Spring cereals        -> SWHT
}

TABLES = {CDL: CDL_TO_EPIC, WORLDCEREAL: WORLDCEREAL_TO_EPIC}

#: Sources whose classes carry no crop identity at all - a single "cropland"
#: class. Assigning crops from these is not approximate, it is impossible.
WITHOUT_CROP_TYPES = ("ESA WorldCover", "Google Dynamic World")


def supports_crop_types(source):
    """Whether a mask source can say which crop a cell grows."""
    return source in TABLES


def to_epic(source, code):
    """The EPIC crop code for one class value, or None if it has no single crop."""
    table = TABLES.get(source)
    if table is None:
        return None
    try:
        return table.get(int(code))
    except (TypeError, ValueError):
        return None


def coverage(source, codes):
    """Split class values into those that translate and those that do not.

    ``codes`` may repeat; the counts are what a caller needs to report a share
    of cells. Returns ``(mapped, unmapped)`` where ``mapped`` is
    ``{class value: epic code}`` and ``unmapped`` is ``{class value: count}``.
    """
    mapped, unmapped = {}, {}
    for code in codes:
        epic = to_epic(source, code)
        if epic is None:
            unmapped[code] = unmapped.get(code, 0) + 1
        else:
            mapped[code] = epic
    return mapped, unmapped
