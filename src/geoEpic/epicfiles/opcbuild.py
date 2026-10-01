"""Building one cell's .OPC from crop templates, year by year, without pandas.

``generate_opc`` (the CLI, pandas-based) stitches a schedule from one template
per simulated year. This is the same stitching in the standard library, so the
QGIS plugin can write schedules and both surfaces produce the same bytes:

  * each year's crop picks a template through :func:`opc.resolve_schedule`,
    so an unmapped crop or a missing template runs as FALLOW, and an irrigated
    cell uses ``<CROP>_IRR.OPC`` where there is one - each reported, not hidden;
  * templates are appended as ``geoEpic.io.OPC.append`` does: the next
    template's first year follows the last year written so far;
  * dates are the templates' own. Nothing here moves an operation.

Nitrogen can be set per crop. A row is a nitrogen application when its
operation is a fertilizer applicator - operation type (IHC) 9 in the model's
TILLCOM - and its fertilizer carries nitrogen in the model's FERT table. The
rate is the nitrogen delivered, not the product: urea solution is 20 % N, so
180 kg N/ha is written as 900 kg/ha of it. A season split into several
applications keeps its proportions and sums to the rate.
"""
from pathlib import Path

from . import opc

#: Column widths of an operation row, as geoEpic.io.OPC reads them.
WIDTHS = (3, 3, 3, 5, 5, 5, 5, 8, 8, 8, 8, 8, 8, 8, 8)

#: How an operation row is written, as geoEpic.io.OPC.save writes it.
ROW_FORMAT = "%3d%3d%3d%5d%5d%5d%5d%8.3f%8.2f%8.2f%8.3f%8.2f%8.2f%8.2f%8.2f"

#: Field positions in a row.
YEAR, MONTH, DAY, OPERATION, TRACTOR, CROP, MATERIAL, AMOUNT = range(8)

#: TILLCOM operation type (IHC) of a fertilizer applicator.
FERTILIZE = 9


class BuildError(ValueError):
    pass


# --------------------------------------------------------------------- reading

def _split(line):
    """One operation row as 15 numbers, or None for a line that is not one."""
    fields, start = [], 0
    for width in WIDTHS:
        text = line[start:start + width].strip()
        start += width
        if not text:
            fields.append(0.0)
            continue
        try:
            fields.append(float(text))
        except ValueError:
            return None
    if not line[:9].strip() or fields[YEAR] < 1:
        return None
    return fields


def read_template(path):
    """``(title, land_use_line, rows)`` from a template .OPC."""
    path = Path(path)
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError as error:
        raise BuildError("Cannot read the template {}: {}".format(path, error))
    if len(lines) < 2:
        raise BuildError("{} is not an operation schedule.".format(path))
    rows = [row for row in (_split(line) for line in lines[2:]) if row is not None]
    return lines[0].split(":")[0].strip(), lines[1].rstrip(), rows


def read_operation_types(path):
    """``{operation code: IHC}`` from a model's TILLCOM file."""
    lines = Path(path).read_text(errors="replace").splitlines()
    header = next((index for index, line in enumerate(lines[:5]) if " IHC" in line), None)
    if header is None:
        raise BuildError("{} has no IHC column; it is not a TILLCOM file.".format(path))
    column = lines[header].index(" IHC")
    types = {}
    for line in lines[header + 1:]:
        parts = line.split()
        if not parts or not parts[0].isdigit():
            continue
        text = line[column - 2:column + 6].strip()
        try:
            types[int(parts[0])] = int(float(text))
        except ValueError:
            continue
    return types


def read_nitrogen(path):
    """``{fertilizer id: N fraction}`` - mineral plus organic - from a FERT file.

    Rows are ``id name minN minP minK orgN orgP ...``; the name is one token.
    """
    fractions = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 6 or not parts[0].isdigit():
            continue
        try:
            values = [float(value) for value in parts[2:6]]
        except ValueError:
            continue
        fractions[int(parts[0])] = values[0] + values[3]
    return fractions


# -------------------------------------------------------------------- nitrogen

def set_nitrogen(rows, rates, operation_types, nitrogen):
    """Rewrite nitrogen applications so each crop's season gets ``rates[crop]``.

    ``rates`` maps an EPIC crop code to kg N/ha; crops not in it keep the
    template's amounts. Changes ``rows`` in place; returns how many changed.
    """
    seasons = {}
    for row in rows:
        crop = int(row[CROP])
        if crop not in rates:
            continue
        if operation_types.get(int(row[OPERATION])) != FERTILIZE:
            continue
        fraction = nitrogen.get(int(row[MATERIAL]), 0.0)
        if fraction <= 0:
            continue                       # phosphate, potash: not nitrogen
        seasons.setdefault((int(row[YEAR]), crop), []).append((row, fraction))
    changed = 0
    for (_, crop), applications in seasons.items():
        delivered = [row[AMOUNT] * fraction for row, fraction in applications]
        total = sum(delivered)
        for (row, fraction), share in zip(applications, delivered):
            # Split seasons keep their proportions; one with no amount yet
            # shares the rate equally.
            part = share / total if total > 0 else 1.0 / len(applications)
            row[AMOUNT] = float(rates[crop]) * part / fraction
            changed += 1
    return changed


# -------------------------------------------------------------------- building

def stitch(templates):
    """Append templates' rows one after another, as OPC.append does."""
    combined = []
    for rows in templates:
        rows = [list(row) for row in rows]
        if not rows:
            continue
        if combined:
            first = min(row[YEAR] for row in rows)
            last = max(row[YEAR] for row in combined)
            for row in rows:
                row[YEAR] = row[YEAR] - (first - 1) + last
        combined.extend(rows)
    return combined


def render(title, start_year, land_use, rows):
    """The text of a .OPC file."""
    lines = ["{} : {}".format(title, start_year), land_use]
    lines.extend(ROW_FORMAT % tuple(row) for row in rows)
    return "\n".join(lines) + "\n"


def build(name, start_year, schedule, folder=None, rates=None, model=None):
    """One cell's schedule: ``(text, report)``.

    ``schedule`` is ``[(epic_code or None, irrigated)]``, one entry per year from
    ``start_year``; None means the year has no crop and runs as fallow.
    ``rates`` is ``{epic_code: kg N/ha}``, applied with the FERT and TILLCOM
    files of ``model`` (a model folder; required when rates are given).
    ``report`` counts what the caller should tell the user about.
    """
    folder = folder or opc.TEMPLATE_DIR
    mapping = opc.read_mapping(folder)
    report = {"fallow": 0, "fell_back": [], "irrigated": 0, "irrigation_dropped": [],
              "nitrogen_rows": 0, "years": len(schedule)}
    templates, title, land_use = [], name, None
    for epic_code, irrigated in schedule:
        if epic_code is None:
            chosen = {"template_code": opc.FALLBACK, "fell_back": False,
                      "irrigated_applied": False, "irrigation_dropped": False}
            report["fallow"] += 1
        else:
            chosen = opc.resolve_schedule(epic_code, folder, mapping, bool(irrigated))
            if chosen["fell_back"]:
                report["fell_back"].append(int(epic_code))
            if chosen["irrigated_applied"]:
                report["irrigated"] += 1
            if chosen["irrigation_dropped"]:
                report["irrigation_dropped"].append(chosen["template_code"])
        _, header, rows = read_template(opc.path_for(chosen["template_code"], folder))
        if land_use is None:
            land_use = header
        templates.append(rows)
    rows = stitch(templates)
    if rates:
        if model is None:
            raise BuildError("Setting a nitrogen rate needs the model folder, for its "
                             "fertilizer and equipment tables.")
        tables = model_tables(model)
        report["nitrogen_rows"] = set_nitrogen(rows, rates, *tables)
    return render(title, start_year, land_use or "   3  0", rows), report


def model_tables(model):
    """``(operation types, nitrogen fractions)`` from a model folder's files."""
    from . import runcontrol
    model = Path(model)
    names = runcontrol.read_file_names(model)
    till, fert = model / names.get("FTILL", "TILLCOM.DAT"), model / names.get("FFERT", "FERT2012.DAT")
    for path in (till, fert):
        if not path.is_file():
            raise BuildError("{} is missing from the model folder {}.".format(path.name, model))
    return read_operation_types(till), read_nitrogen(fert)
