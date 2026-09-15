"""Crop operation templates: which ones exist, and which crop each one serves.

A management schedule in EPIC is a .OPC file. GeoEPIC ships one template per
crop, named by a short code (CORN.OPC, SOYB.OPC), and a MAPPING file that says
which EPIC crop code each template serves. ``generate_opc`` stitches a
per-cell schedule together from those templates, one entry per simulated year,
falling back to FALLOW for any crop the folder does not cover.

That fallback is silent, which is the reason this module exists: a user
choosing "Rice" in the plugin has no way to know the rice template is absent
and the run will be fallow. :func:`catalogue` reports what is declared and what
is actually present, so the caller can say so before anything is written.

Dependency-light on purpose - stdlib only, so the QGIS plugin and the CLI read
one catalogue and cannot disagree about which crops are available. A custom
template folder is read by exactly the same rules as the bundled one.
"""
import csv
import os
from pathlib import Path

TEMPLATE_DIR = Path(__file__).with_name("templates") / "crop"

#: The template every unmatched crop code falls back to. generate_opc refuses a
#: folder without it, because an unmatched year still needs a schedule.
FALLBACK = "FALLOW"

#: Readable names for the templates GeoEPIC ships. A folder may carry codes
#: that are not here; those are shown by their own code rather than hidden.
LABELS = {"CORN": "Corn", "SOYB": "Soybean", "COTS": "Cotton", "RICE": "Rice",
          "GRSG": "Grain sorghum", "SWHT": "Spring wheat", "WWHT": "Winter wheat",
          "RYE": "Rye", "FALLOW": "Fallow"}

#: MAPPING has been written with either heading for each column.
CODE_COLUMNS = ("epic_code", "crop_code", "cdl_code")
NAME_COLUMNS = ("template_code", "name")


class TemplateError(ValueError):
    pass


def label_for(template_code):
    """A readable crop name for a template code."""
    return LABELS.get(str(template_code).upper(), str(template_code))


def _pick(row, names):
    for name in names:
        if name in row and str(row[name]).strip():
            return str(row[name]).strip()
    return ""


def read_mapping(folder=None):
    """EPIC crop code -> template code, in the order MAPPING declares them.

    Accepts either column spelling for both fields. Rows with an unreadable
    crop code are skipped rather than failing the whole folder: MAPPING is
    hand-edited, and one bad line should not hide the other eight crops.
    """
    path = Path(folder or TEMPLATE_DIR) / "MAPPING"
    if not path.is_file():
        raise TemplateError("No MAPPING file in {}. A template folder must declare "
                            "which crop code each template serves.".format(path.parent))
    mapping = {}
    with open(str(path), "r", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise TemplateError("{} is empty.".format(path))
        headings = [name.strip().lower() for name in reader.fieldnames]
        if not any(name in headings for name in CODE_COLUMNS):
            raise TemplateError(
                "{} has no crop code column. Expected one of: {}.".format(
                    path, ", ".join(CODE_COLUMNS)))
        for raw in reader:
            row = {(key or "").strip().lower(): value for key, value in raw.items()}
            code, name = _pick(row, CODE_COLUMNS), _pick(row, NAME_COLUMNS)
            if not name:
                continue
            try:
                mapping[int(float(code))] = name.upper()
            except (TypeError, ValueError):
                continue
    if not mapping:
        raise TemplateError("{} declares no usable crop codes.".format(path))
    return mapping


def present(folder=None):
    """The template codes that actually have a .OPC file in the folder."""
    folder = Path(folder or TEMPLATE_DIR)
    if not folder.is_dir():
        return set()
    return {path.stem.upper() for path in folder.iterdir()
            if path.is_file() and path.suffix.upper() == ".OPC"}


def path_for(template_code, folder=None):
    """Where a template lives, whether or not it is there yet."""
    return Path(folder or TEMPLATE_DIR) / "{}.OPC".format(str(template_code).upper())


def catalogue(folder=None):
    """Every declared crop, with whether its template file exists.

    Returns a list of dicts ordered as MAPPING declares them:
    ``epic_code``, ``template_code``, ``label``, ``available``, ``path``.
    The fallback crop is included like any other - it is a legitimate choice.
    """
    mapping = read_mapping(folder)
    have = present(folder)
    entries = []
    for epic_code, template_code in mapping.items():
        entries.append({"epic_code": epic_code,
                        "template_code": template_code,
                        "label": label_for(template_code),
                        "available": template_code in have,
                        "path": path_for(template_code, folder)})
    return entries


def missing(folder=None):
    """Declared crops whose template file is not there, as (code, label)."""
    return [(entry["template_code"], entry["label"])
            for entry in catalogue(folder) if not entry["available"]]


def resolve(epic_code, folder=None, mapping=None):
    """The template a crop code will actually be simulated with.

    Returns ``(template_code, fell_back)``. ``fell_back`` is True when the crop
    is unmapped or its template is absent, meaning the year will be simulated
    as fallow - the caller should say so rather than let it pass.
    """
    mapping = read_mapping(folder) if mapping is None else mapping
    have = present(folder)
    try:
        wanted = mapping.get(int(float(epic_code)), FALLBACK)
    except (TypeError, ValueError):
        wanted = FALLBACK
    if wanted in have:
        return wanted, wanted == FALLBACK and str(epic_code) != "9"
    return FALLBACK, True


def validate(folder=None):
    """Check a folder can drive generate_opc. Returns (ok, message)."""
    folder = Path(folder or TEMPLATE_DIR)
    try:
        entries = catalogue(folder)
    except TemplateError as error:
        return False, str(error)
    if not path_for(FALLBACK, folder).is_file():
        return False, ("{}.OPC is missing from {}. It is the schedule used for any "
                       "year whose crop has no template.".format(FALLBACK, folder))
    absent = [entry["label"] for entry in entries if not entry["available"]]
    if absent:
        return True, ("{} of {} declared templates present. No template for: {} - "
                      "those crops would be simulated as fallow.".format(
                          len(entries) - len(absent), len(entries), ", ".join(absent)))
    return True, "All {} declared crop templates are present.".format(len(entries))
