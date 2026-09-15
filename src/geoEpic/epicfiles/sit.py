"""EPIC site files (.SIT), without pandas.

Dependency-light so the QGIS plugin and the CLI share one implementation; see
``design/q-epic-integration.md``. The heavy ``geoEpic.io.inputs.sit.SIT`` keeps
its API but delegates rendering here, so the two cannot drift.

Byte-for-byte compatibility with the previous writer is pinned by
``tests/fixtures/site_plain.SIT`` and ``site_edges.SIT``. As with .DLY and
.SOL, ``%8.2f`` is not clamped: an elevation like -12345.678 needs nine
characters and runs into its neighbour, and EPIC reads these columns
positionally, so widening the field would change what the model sees.

Only four numbers are ours - latitude, longitude, elevation and the two slope
fields. Everything else on the line comes from the template untouched.
"""
import os
from pathlib import Path

TEMPLATE = Path(__file__).with_name("templates") / "template.SIT"

FIELD = "{:8.2f}"

#: Where our values sit in the template's lines.
COORDINATE_LINE = 3      # latitude, longitude, elevation occupy columns 0-24
SLOPE_LINE = 4           # slope length and steepness occupy columns 48-64
SLOPE_START, SLOPE_END = 48, 64
BLANK_LINE = 6

DEFAULTS = {"ID": "Ne2", "lat": 0.0, "lon": 0.0, "elevation": 0.0,
            "slope_length": 0.0, "slope_steep": 0.0}


class SitError(ValueError):
    pass


def read_template(template=None):
    """Accept a path, an already-read list of lines, or nothing for the default."""
    if isinstance(template, (list, tuple)):
        return list(template)
    path = Path(template) if template else TEMPLATE
    if not path.is_file():
        raise SitError("Site template not found: {}".format(path))
    with open(str(path), "r") as handle:
        return handle.readlines()


def _number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise SitError("Site value {!r} is not numeric.".format(value))
    return 0.0 if number != number else number      # NaN


def dumps(site, template=None):
    """Render a complete .SIT file as text.

    ``site`` is a mapping with ID, lat, lon, elevation, slope_length and
    slope_steep; anything absent falls back to the same defaults as before.
    """
    values = dict(DEFAULTS)
    values.update(site or {})
    if not str(values.get("ID") or "").strip():
        raise SitError("Site ID is not set. Cannot write a .SIT file.")

    lines = read_template(template)
    if len(lines) <= BLANK_LINE:
        raise SitError("The site template is too short: {} lines.".format(len(lines)))

    lines[0] = "Crop Simulations\n"
    lines[1] = "Prototype\n"
    lines[2] = "ID: {}\n".format(values["ID"])
    lines[COORDINATE_LINE] = (
        (FIELD * 3).format(_number(values["lat"]), _number(values["lon"]),
                           _number(values["elevation"]))
        + lines[COORDINATE_LINE][24:])
    lines[SLOPE_LINE] = (
        lines[SLOPE_LINE][:SLOPE_START]
        + (FIELD * 2).format(_number(values["slope_length"]), _number(values["slope_steep"]))
        + lines[SLOPE_LINE][SLOPE_END:])
    # The writer has always blanked this line to a fixed width.
    lines[BLANK_LINE] = " " * 51 + "\n"
    return "".join(lines)


def write(path, site, template=None):
    """Write a .SIT file, adding the extension if it is missing."""
    path = str(path)
    if not path.upper().endswith(".SIT"):
        path += ".SIT"
    text = dumps(site, template=template)
    # Write through a temporary file so a cancelled run cannot leave a
    # half-written input that later looks complete.
    temporary = path + ".partial"
    with open(temporary, "w", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)
    return path


def read(path):
    """Parse a .SIT file back into the values this writer controls."""
    path = str(path)
    with open(path, "r") as handle:
        lines = handle.readlines()
    if len(lines) <= SLOPE_LINE:
        raise SitError("{} is too short to be a .SIT file.".format(path))
    try:
        site_id = lines[2].split(":", 1)[1].strip()
    except IndexError:
        site_id = ""
    coordinates = lines[COORDINATE_LINE]
    slope = lines[SLOPE_LINE]

    def field(text, start):
        chunk = text[start:start + 8]
        try:
            return float(chunk)
        except ValueError:
            raise SitError("{}: unreadable value {!r}. A value wider than eight "
                           "characters shifts every column after it.".format(path, chunk))

    return {"ID": site_id,
            "lat": field(coordinates, 0),
            "lon": field(coordinates, 8),
            "elevation": field(coordinates, 16),
            "slope_length": field(slope, SLOPE_START),
            "slope_steep": field(slope, SLOPE_START + 8)}
