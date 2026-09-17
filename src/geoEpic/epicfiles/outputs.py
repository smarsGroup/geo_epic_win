"""Reading EPIC's output tables, without pandas.

Every EPIC output file is the same shape: a short preamble naming the run and
its inputs, one header line of column names, then whitespace-separated rows.
What differs is the time column - ``YR`` alone for an annual file, ``Y M`` for
a monthly one, ``Y M D`` for a daily one - and that is what decides how a file
can be aggregated.

The header is found by content rather than by line number, because the
preamble's length varies with how many input paths the run recorded.

Rows whose column count does not match the header are skipped and counted
rather than zipped short. Measured across 128,104 rows of real ACY and DGN
output there were none, but a row that did not line up would otherwise put
every later value under the wrong column - the same silent misalignment that
parallel arrays cause elsewhere in this codebase.
"""
import math
from pathlib import Path

ENCODING = "ISO-8859-1"

#: Time columns, longest match first: a daily file also has Y and M.
TIME_COLUMNS = (("daily", ("Y", "M", "D")),
                ("monthly", ("Y", "M")),
                ("annual", ("YR",)),
                ("annual", ("Y",)))

#: Columns that identify the row rather than measure anything.
LABEL_COLUMNS = {"YR", "Y", "M", "D", "RT#", "CPNM", "CPNM1", "CROP", "ROT"}


class OutputError(ValueError):
    pass


def _is_number(token):
    try:
        float(token)
        return True
    except ValueError:
        return False


def find_header(lines):
    """Index of the header line: names, followed by a row of the same width."""
    for index, line in enumerate(lines):
        names = line.split()
        if len(names) < 2 or any(_is_number(name) for name in names):
            continue
        for following in lines[index + 1:]:
            values = following.split()
            if not values:
                continue
            numeric = sum(1 for value in values if _is_number(value))
            if len(values) == len(names) and numeric >= len(values) - 2:
                return index
            break
    raise OutputError("No column header found; this does not look like an EPIC "
                      "output table.")


class Table:
    """One EPIC output file: its columns, its rows, and its time resolution."""

    def __init__(self, columns, rows, skipped=0, path=None):
        self.columns = list(columns)
        self.rows = rows
        self.skipped = skipped
        self.path = path
        self.index = {name: position for position, name in enumerate(self.columns)}

    @property
    def resolution(self):
        """"daily", "monthly", "annual", or None when no time column is found."""
        for name, needed in TIME_COLUMNS:
            if all(column in self.index for column in needed):
                return name
        return None

    @property
    def value_columns(self):
        """Columns that measure something, rather than label the row."""
        return [name for name in self.columns if name.upper() not in LABEL_COLUMNS]

    def column(self, name):
        """Every value of one column, in file order, as floats where possible."""
        if name not in self.index:
            raise OutputError("{} has no column {}. It has: {}".format(
                self.path or "This table", name, ", ".join(self.columns)))
        position = self.index[name]
        return [row[position] for row in self.rows]

    def period_of(self, row):
        """The row's time key: (year,), (year, month) or (year, month, day)."""
        resolution = self.resolution
        if resolution == "daily":
            return (int(row[self.index["Y"]]), int(row[self.index["M"]]),
                    int(row[self.index["D"]]))
        if resolution == "monthly":
            return (int(row[self.index["Y"]]), int(row[self.index["M"]]))
        if resolution == "annual":
            key = "YR" if "YR" in self.index else "Y"
            return (int(row[self.index[key]]),)
        return ()

    def series(self, name):
        """[(period, value)] for one column, skipping values that are not numbers."""
        position = self.index.get(name)
        if position is None:
            raise OutputError("{} has no column {}.".format(self.path or "This table", name))
        found = []
        for row in self.rows:
            value = row[position]
            if isinstance(value, float) and value == value:
                found.append((self.period_of(row), value))
        return found


def read(path):
    """Parse an EPIC output file into a :class:`Table`."""
    path = Path(path)
    if not path.is_file():
        raise OutputError("No output file at {}".format(path))
    with open(str(path), "r", encoding=ENCODING, errors="replace") as handle:
        lines = handle.readlines()
    header = find_header(lines)
    columns = lines[header].split()
    rows, skipped = [], 0
    for line in lines[header + 1:]:
        values = line.split()
        if not values:
            continue
        if len(values) != len(columns):
            # Never zipped short: a row that does not line up would put every
            # later value under the wrong column.
            skipped += 1
            continue
        rows.append([float(value) if _is_number(value) else value for value in values])
    return Table(columns, rows, skipped, str(path))


# ------------------------------------------------------------------ statistics

def _mean(values):
    return sum(values) / len(values)


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def _std(values):
    """Sample standard deviation; zero for a single value rather than undefined."""
    if len(values) < 2:
        return 0.0
    average = _mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / (len(values) - 1))


#: How a set of periods is reduced to the one number a map cell shows.
AGGREGATIONS = {"mean": _mean, "sum": sum, "min": min, "max": max,
                "median": _median, "std": _std}

#: Offered in this order; mean first because it is what is usually wanted.
AGGREGATION_NAMES = ["mean", "sum", "min", "max", "median", "std"]


def aggregate(values, how="mean"):
    """Reduce many periods to one number. Returns None when there is nothing."""
    numbers = [value for value in values
               if isinstance(value, (int, float)) and value == value]
    if not numbers:
        return None
    function = AGGREGATIONS.get(str(how).lower())
    if function is None:
        raise OutputError("Unknown aggregation {!r}. Use one of: {}.".format(
            how, ", ".join(AGGREGATION_NAMES)))
    return float(function(numbers))
