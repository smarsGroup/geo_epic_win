"""EPIC daily weather files (.DLY), without pandas.

Dependency-light so the QGIS plugin and the CLI share one implementation; see
``design/q-epic-integration.md``. The heavy ``geoEpic.io.inputs.dly.DLY`` keeps
its DataFrame API but delegates formatting here, so the two cannot drift.

Byte-for-byte compatibility with the previous ``numpy.savetxt`` output is a hard
requirement and is pinned by ``tests/fixtures/weather_2016.DLY``. That includes
three behaviours worth knowing about before changing anything:

* ``%6.2f`` is *not* clamped. A value like -100.0 needs seven characters and
  simply runs into its neighbour, exactly as it did before. EPIC's Fortran reads
  these columns positionally, so silently "fixing" the overflow would change
  which values the model sees.
* Ties round half-to-even, because that is what C's printf does: 9.995 formats
  as ``9.99`` and -0.005 as ``-0.01``.
* Negative zero survives as ``-0.00``.
"""
import os

#: Column order EPIC expects in a .DLY file.
COLUMNS = ("year", "month", "day", "srad", "tmax", "tmin", "prcp", "rh", "ws")

#: Fixed-width layout. Integers first, then six two-decimal fields.
ROW_FORMAT = "%6d%4d%4d%6.2f%6.2f%6.2f%6.2f%6.2f%6.2f"

#: Character widths, for reading the file back.
WIDTHS = (6, 4, 4, 6, 6, 6, 6, 6, 6)

DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


class DlyError(ValueError):
    pass


def _as_tuple(row):
    """Accept a mapping or an ordered sequence for one day."""
    if hasattr(row, "get"):
        try:
            values = [row[name] for name in COLUMNS]
        except KeyError as error:
            raise DlyError("Row is missing column {}.".format(error))
    else:
        values = list(row)
        if len(values) != len(COLUMNS):
            raise DlyError("Expected {} values per row, got {}.".format(
                len(COLUMNS), len(values)))
    try:
        return (int(values[0]), int(values[1]), int(values[2])) + tuple(
            float(value) for value in values[3:])
    except (TypeError, ValueError) as error:
        raise DlyError("Row {!r} is not numeric: {}".format(row, error))


def format_row(row):
    """One fixed-width .DLY line, without its terminator."""
    return ROW_FORMAT % _as_tuple(row)


def deduplicate(rows):
    """Drop repeated calendar dates, keeping the first, as the writer always has."""
    seen, kept = set(), []
    for row in rows:
        values = _as_tuple(row)
        key = values[:3]
        if key in seen:
            continue
        seen.add(key)
        kept.append(values)
    return kept


def dumps(rows):
    """Render rows as the complete text of a .DLY file."""
    lines = [ROW_FORMAT % values for values in deduplicate(rows)]
    # numpy.savetxt terminates every row, including the last.
    return "".join(line + "\n" for line in lines)


def write(path, rows):
    """Write a .DLY file, adding the extension if it is missing."""
    path = str(path)
    if not path.upper().endswith(".DLY"):
        path += ".DLY"
    text = dumps(rows)
    # Write through a temporary file so a cancelled fetch cannot leave a
    # half-written input that later looks cached.
    temporary = path + ".partial"
    with open(temporary, "w", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)
    return path


def read(path):
    """Parse a .DLY file back into a list of dicts."""
    path = str(path)
    if not path.upper().endswith(".DLY"):
        path += ".DLY"
    rows = []
    with open(path, "r") as handle:
        for number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            values, position = [], 0
            for width in WIDTHS:
                values.append(line[position:position + width])
                position += width
            try:
                row = dict(zip(COLUMNS, [int(values[0]), int(values[1]), int(values[2])]
                               + [float(v) for v in values[3:]]))
            except ValueError as error:
                raise DlyError("{} line {}: {}".format(path, number, error))
            rows.append(row)
    return rows


#: Calendar quirks a source may declare, and how a continuous series is built.
#: Daymet's GEE collection carries 365 days even in a leap year, dropping 31
#: December (verified live for 2020; the ORNL CSV drops 29 February instead,
#: which geoEpic.weather.daymet repairs by averaging its neighbours).
CALENDARS = ("drops-dec-31-in-leap-years",)


def repair_calendar(rows, first_year, last_year, calendar):
    """Fill a source's known calendar gap so the series is continuous.

    EPIC reads a .DLY as one unbroken run of days, so a hole is not an option.
    Returns ``(rows, filled)`` where ``filled`` lists the dates synthesised, for
    the caller to report - a fabricated day must never pass silently.
    """
    if not calendar:
        return list(rows), []
    if calendar not in CALENDARS:
        raise DlyError("Unknown calendar policy {!r}.".format(calendar))

    by_date = {(int(r["year"]), int(r["month"]), int(r["day"])): r for r in rows}
    filled = []
    for year in range(int(first_year), int(last_year) + 1):
        if not is_leap(year) or (year, 12, 31) in by_date:
            continue
        previous = by_date.get((year, 12, 30))
        if previous is None:
            continue        # nothing to carry forward; leave the gap visible
        # No following day exists inside the year to average with, so the last
        # observed day is carried forward.
        synthetic = dict(previous)
        synthetic["day"] = 31
        by_date[(year, 12, 31)] = synthetic
        filled.append((year, 12, 31))
    ordered = [by_date[key] for key in sorted(by_date)]
    return ordered, filled


def missing_dates(rows, start_year, end_year):
    """Calendar dates in the range that the rows do not cover.

    Used for the incremental rule: only absent years are ever requested.
    """
    present = {(int(r["year"]), int(r["month"]), int(r["day"])) for r in rows}
    absent = []
    for year in range(int(start_year), int(end_year) + 1):
        for month in range(1, 13):
            for day in range(1, days_in(year, month) + 1):
                if (year, month, day) not in present:
                    absent.append((year, month, day))
    return absent


def covered_years(rows):
    """Years for which every calendar day is present."""
    by_year = {}
    for row in rows:
        by_year.setdefault(int(row["year"]), set()).add((int(row["month"]), int(row["day"])))
    complete = []
    for year, days in by_year.items():
        expected = sum(days_in(year, month) for month in range(1, 13))
        if len(days) == expected:
            complete.append(year)
    return sorted(complete)


def days_in(year, month):
    if month == 2 and is_leap(year):
        return 29
    return DAYS_IN_MONTH[month - 1]


def is_leap(year):
    year = int(year)
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
