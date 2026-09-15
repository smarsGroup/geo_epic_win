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


# --------------------------------------------------------------- monthly stats

#: Row order of a .WP1 file, and where each comes from.
WP1_ROWS = ("OBMX", "OBMN", "SDTMX", "SDTMN", "RMO", "RST2", "RST3",
            "PRW1", "PRW2", "DAYP", "WI", "OBSL", "RH", "UAVO")

#: Days per month EPIC assumes for the monthly totals, leap years included.
NOMINAL_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

#: A day counts as wet above this many millimetres.
WET_MM = 0.5


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _sample_std(values):
    """Standard deviation with ddof=1, as pandas Series.std() uses."""
    count = len(values)
    if count < 2:
        return float("nan")
    average = _mean(values)
    return (sum((value - average) ** 2 for value in values) / (count - 1)) ** 0.5


def _median(values):
    ordered = sorted(values)
    count = len(ordered)
    if not count:
        return float("nan")
    middle = count // 2
    return ordered[middle] if count % 2 else (ordered[middle - 1] + ordered[middle]) / 2.0


def monthly_statistics(rows):
    """The fourteen EPIC monthly statistics, one value per month present.

    Mirrors ``geoEpic.io.inputs.dly.DLY.to_monthly``: means of the daily series,
    precipitation scaled to a nominal month, sample standard deviations, wet-day
    counts and the two wet/dry transition probabilities.
    """
    by_month = {}
    for values in deduplicate(rows):
        row = dict(zip(COLUMNS, values))
        by_month.setdefault(int(row["month"]), []).append(row)
    if not by_month:
        raise DlyError("No rows to summarise.")

    months = sorted(by_month)
    stats = {name: [] for name in WP1_ROWS}
    scaled_precipitation = []
    for month in months:
        days = by_month[month]
        count = len(days)
        nominal = NOMINAL_DAYS[month - 1]
        precipitation = [day["prcp"] for day in days]
        wet = [value > WET_MM for value in precipitation]

        stats["OBMX"].append(_mean([day["tmax"] for day in days]))
        stats["OBMN"].append(_mean([day["tmin"] for day in days]))
        stats["OBSL"].append(_mean([day["srad"] for day in days]))
        stats["RH"].append(_mean([day["rh"] for day in days]))
        stats["UAVO"].append(_mean([day["ws"] for day in days]))
        stats["SDTMX"].append(_sample_std([day["tmax"] for day in days]))
        stats["SDTMN"].append(_sample_std([day["tmin"] for day in days]))
        # The deviation is of the daily series, before the monthly scaling.
        stats["RST2"].append(_sample_std(precipitation))
        scaled_precipitation.append(_mean(precipitation) * nominal)
        stats["DAYP"].append(sum(wet) / count * nominal)
        # PRW1 is always zero, and that is bug-for-bug deliberate.
        #
        # to_monthly computes it as
        #     np.sum(np.diff(x['prcp'] > 0.5) == -1) / len(x)
        # but np.diff on a *boolean* array yields booleans (the XOR of
        # neighbours), never -1, so the comparison is never true. The intent was
        # plainly the wet-to-dry transition rate,
        #     sum(1 for a, b in zip(wet, wet[1:]) if a and not b) / count
        # which for this fixture gives 0.03 in January rather than 0.00.
        #
        # PRW1 feeds EPIC's precipitation occurrence model, so correcting it
        # here would silently change model results and break the byte-for-byte
        # contract with the files GeoEPIC has always written. Left as it is,
        # pinned by a test, and raised for a decision instead.
        stats["PRW1"].append(0.0)
        # Wet days preceded by a wet day; this one works as intended.
        stats["PRW2"].append(sum(1 for a, b in zip([False] + wet[:-1], wet) if a and b) / count)
        stats["WI"].append(0.0)

    stats["RMO"] = scaled_precipitation
    middle = _median(scaled_precipitation)
    stats["RST3"] = [3 * abs(value - middle) / deviation if deviation else float("nan")
                     for value, deviation in zip(scaled_precipitation, stats["RST2"])]
    return months, stats


def dumps_monthly(rows, name):
    """Render a .WP1 file as text."""
    months, stats = monthly_statistics(rows)
    lines = ["Monthly Weather Statistics : {}".format(name), "     .00     .00"]
    for label in WP1_ROWS:
        lines.append(("%10.2f" * len(months) + "%8s") % tuple(stats[label] + [label]))
    # The pandas writer joined without a trailing newline; EPIC reads it either
    # way, but the bytes are pinned by tests/fixtures/weather_2016.WP1.
    return "\n".join(lines)


def dumps_wind(rows, name):
    """Render a .WND file: the monthly mean wind, then sixteen rows of zeros."""
    months, stats = monthly_statistics(rows)
    lines = ["Monthly Wind Statistics : {}".format(name), "     .00     .00",
             "".join("{:10.2f}".format(value) for value in stats["UAVO"])]
    zeros = "".join("{:10.1f}".format(0.0) for _ in range(12))
    lines.extend([zeros] * 16)
    return "\n".join(lines) + "\n"


def write_monthly(path, rows, name=None):
    """Write the .WP1 and .WND companions beside a .DLY, returning both paths."""
    path = str(path)
    for suffix in (".DLY", ".WP1", ".WND"):
        if path.upper().endswith(suffix):
            path = path[:-4]
            break
    name = name or os.path.basename(path)
    written = []
    for suffix, text in ((".WP1", dumps_monthly(rows, name)),
                         (".WND", dumps_wind(rows, name))):
        temporary = path + suffix + ".partial"
        with open(temporary, "w", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path + suffix)
        written.append(path + suffix)
    return written


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
