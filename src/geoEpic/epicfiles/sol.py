"""EPIC soil files (.SOL), without pandas.

Dependency-light so the QGIS plugin and the CLI share one implementation; see
``design/q-epic-integration.md``. The heavy ``geoEpic.io.inputs.sol.SOL`` keeps
its DataFrame API but delegates rendering here, so the two cannot drift.

Byte-for-byte compatibility with the previous pandas writer is a hard
requirement and is pinned by ``tests/fixtures/soil_123456.SOL``. As with .DLY,
``%8.3f`` is not clamped: a value needing more than eight characters runs into
its neighbour, and EPIC reads these columns positionally, so widening the field
would change which numbers the model sees.

A .SOL is written column-per-layer: the template's first three lines carry the
identifier, albedo and hydrologic group, and the next nineteen lines each hold
one property across all layers.
"""
import os
from pathlib import Path

TEMPLATE = Path(__file__).with_name("templates") / "template.SOL"

#: Row order of the per-layer block, lines 4 onward of the file.
LAYER_PROPERTIES = (
    "Layer_depth", "Bulk_Density", "Wilting_capacity", "Field_Capacity",
    "Sand_content", "Silt_content", "N_concen", "pH", "Sum_Bases",
    "Organic_Carbon", "Calcium_Carbonate", "Cation_exchange", "Course_Fragment",
    "cnds", "pkrz", "rsd", "Bulk_density_dry", "psp", "Saturated_conductivity",
)

FIELD = "{:8.3f}"

#: EPIC splits the profile into this many layers internally (TSLN).
LAYERS_AFTER_SPLIT = 10

#: Hydrologic soil group to the code EPIC expects; C when unknown, as before.
HYDGRP_CODES = {"A": 1, "B": 2, "C": 3, "D": 4}
DEFAULT_HYDGRP = 3

#: Lines after the property block that are blanked out, and the width of the
#: zero padding written into them.
PADDING_UNTIL = 45
MAX_PADDING_COLUMNS = 23


class SolError(ValueError):
    pass


def hydgrp_code(group):
    """Numeric code for a hydrologic group letter, tolerating '' and 'B/D'."""
    if group is None:
        return DEFAULT_HYDGRP
    text = str(group).strip()
    if not text:
        return DEFAULT_HYDGRP
    return HYDGRP_CODES.get(text[0].upper(), DEFAULT_HYDGRP)


def _number(value):
    """Coerce to float, mapping blanks and NaN to zero as the writer always has."""
    if value is None or value == "":
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise SolError("Soil property {!r} is not numeric.".format(value))
    return 0.0 if number != number else number      # NaN


def ordered_layers(layers):
    """Sort by depth and fill gaps with zero, as the pandas writer did."""
    prepared = []
    for layer in layers:
        try:
            prepared.append({name: _number(layer.get(name)) for name in LAYER_PROPERTIES})
        except AttributeError:
            raise SolError("Each layer must be a mapping of property names to values.")
    if not prepared:
        raise SolError("A .SOL file needs at least one layer.")
    return sorted(prepared, key=lambda layer: layer["Layer_depth"])


def read_template(template=None):
    """Accept a path, an already-read list of lines, or nothing for the default."""
    if isinstance(template, (list, tuple)):
        return list(template)
    path = Path(template) if template else TEMPLATE
    if not path.is_file():
        raise SolError("Soil template not found: {}".format(path))
    with open(str(path), "r") as handle:
        return handle.readlines()


def dumps(soil_id, albedo, hydgrp, layers, template=None, layers_after_split=LAYERS_AFTER_SPLIT):
    """Render a complete .SOL file as text."""
    lines = read_template(template)
    rows = ordered_layers(layers)
    count = len(rows)

    lines[0] = "ID: {}\n".format(soil_id)
    lines[1] = (FIELD * 2).format(_number(albedo), float(hydgrp_code(hydgrp))) + lines[1][16:]
    lines[2] = FIELD.format(float(layers_after_split)) + lines[2][8:]

    for index, name in enumerate(LAYER_PROPERTIES):
        lines[3 + index] = "".join(FIELD.format(row[name]) for row in rows) + "\n"

    # Everything between the property block and line 45 is zeroed to the layer
    # count; the tail of the template is left untouched.
    padding = "".join([FIELD.format(0.0)] * min(count, MAX_PADDING_COLUMNS)) + "\n"
    for index in range(len(LAYER_PROPERTIES) + 3, PADDING_UNTIL):
        lines[index] = padding
    return "".join(lines)


def write(path, soil_id, albedo, hydgrp, layers, template=None):
    """Write a .SOL file, adding the extension if it is missing."""
    path = str(path)
    if not path.upper().endswith(".SOL"):
        path += ".SOL"
    text = dumps(soil_id, albedo, hydgrp, layers, template=template)
    # Write through a temporary file so a cancelled fetch cannot leave a
    # half-written input that later looks cached.
    temporary = path + ".partial"
    with open(temporary, "w", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)
    return path


def read(path):
    """Parse a .SOL file back into its identifier, albedo, group and layers."""
    path = str(path)
    with open(path, "r") as handle:
        lines = handle.readlines()
    if len(lines) < 3 + len(LAYER_PROPERTIES):
        raise SolError("{} is too short to be a .SOL file.".format(path))
    try:
        soil_id = int(lines[0].split(":", 1)[1].strip())
    except (IndexError, ValueError):
        soil_id = None
    try:
        albedo = float(lines[1][0:8])
        code = int(float(lines[1][8:16]))
    except ValueError as error:
        raise SolError("{}: unreadable albedo or hydrologic group: {}".format(path, error))
    hydgrp = {value: key for key, value in HYDGRP_CODES.items()}.get(code, "C")

    columns = []
    for index, name in enumerate(LAYER_PROPERTIES):
        text = lines[3 + index].rstrip("\n")
        values = []
        for start in range(0, len(text.rstrip()), 8):
            chunk = text[start:start + 8]
            try:
                values.append(float(chunk))
            except ValueError:
                raise SolError("{}: unreadable {} value {!r}. A value wider than "
                               "eight characters shifts every column after it.".format(
                                   path, name, chunk))
        columns.append(values)
    count = min(len(values) for values in columns)
    layers = [{name: columns[i][layer] for i, name in enumerate(LAYER_PROPERTIES)}
              for layer in range(count)]
    return {"soil_id": soil_id, "albedo": albedo, "hydgrp": hydgrp, "layers": layers}
