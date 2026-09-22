"""The control files EPIC reads to run one site, written without pandas.

EPIC is not told about a site through arguments. It reads a fixed set of list
files from its working directory, each naming the inputs for run number 1, plus
EPICRUN.DAT which says which runs to perform. Running one site therefore means
building a directory that looks like a one-site experiment:

    EPICRUN.DAT      the run line: site id and the list indices to use
    ieSite.DAT       -> the .SIT
    ieSllist.DAT     -> the .SOL
    ieOplist.DAT     -> the .OPC
    ieWedlst.DAT     -> 1.DLY
    ieWealst.DAT     -> 1.WP1, with latitude, longitude and elevation
    ieWndlst.DAT     -> 1.WND, likewise

The names on the left are not fixed either: EPICFILE.DAT maps a role (FSITE,
FSOIL, FOPSC...) to the file name that model folder happens to use, so they are
read from there rather than assumed.

Weather is always presented as ``1.DLY`` / ``1.WP1`` / ``1.WND`` regardless of
what the files are called in the workspace, because the list files above refer
to it by that name. The caller copies them in under those names.

Dependency-light, like the rest of ``epicfiles``: the QGIS plugin and the CLI
build identical run directories.
"""
import os
from pathlib import Path

#: EPIC's .DAT files are Latin-1; a stray byte must not abort a run.
ENCODING = "ISO-8859-1"

#: Role -> the default file name, used when EPICFILE.DAT does not list it.
DEFAULT_FILES = {"FSITE": "ieSite.DAT", "FSOIL": "ieSllist.DAT",
                 "FOPSC": "ieOplist.DAT", "FWLST": "ieWedlst.DAT",
                 "FWPM1": "ieWealst.DAT", "FWIND": "ieWndlst.DAT"}

#: The names the weather files must have inside a run directory.
WEATHER_STEM = "1"


class RunControlError(ValueError):
    pass


def read_file_names(model_dir):
    """Role -> file name, from a model folder's EPICFILE.DAT."""
    path = Path(model_dir) / "EPICFILE.DAT"
    if not path.is_file():
        raise RunControlError(
            "No EPICFILE.DAT in {}. That file maps EPIC's internal roles to the "
            "list files this model folder uses, so a run cannot be set up "
            "without it.".format(model_dir))
    names = dict(DEFAULT_FILES)
    with open(str(path), "r", encoding=ENCODING) as handle:
        for line in handle:
            parts = line.split()
            # Later duplicates lose: EPICFILE.DAT lists FPEST twice in stock
            # model folders, and EPIC uses the first.
            if len(parts) == 2 and parts[0] not in names:
                names[parts[0]] = parts[1]
            elif len(parts) == 2 and parts[0] in DEFAULT_FILES:
                names[parts[0]] = parts[1]
    return names


def run_line(site_id):
    """The single line of EPICRUN.DAT: which site, and which list entries."""
    return "{} 1  0  0  0  1  1  1/".format(site_id)


def _listing(target):
    return '1    "./{}"\n'.format(os.path.basename(str(target)))


def _weather_listing(suffix, latitude, longitude, elevation):
    return "1    {}.{}   {:.2f}   {:.2f}    {:.2f}\n".format(
        WEATHER_STEM, suffix, float(latitude), float(longitude), float(elevation))


def write(directory, site_id, sit_name, sol_name, opc_name,
          latitude, longitude, elevation, file_names=None):
    """Write every control file one run needs into ``directory``.

    The .SIT, .SOL and .OPC are referred to by name only - EPIC resolves them
    relative to its working directory - so the caller must place them there
    under exactly these names.

    Returns the paths written, so a caller can check or log them.
    """
    directory = Path(directory)
    names = file_names or read_file_names(directory)
    written = []

    def put(name, text):
        path = directory / name
        with open(str(path), "w", encoding=ENCODING, newline="\n") as handle:
            handle.write(text)
        written.append(path)

    put("EPICRUN.DAT", run_line(site_id))
    put(names["FSITE"], _listing(sit_name))
    put(names["FSOIL"], _listing(sol_name))
    put(names["FOPSC"], _listing(opc_name))
    put(names["FWLST"], "1    {}.DLY\n".format(WEATHER_STEM))
    put(names["FWPM1"], _weather_listing("WP1", latitude, longitude, elevation))
    put(names["FWIND"], _weather_listing("WND", latitude, longitude, elevation))
    return written


def expected_outputs(site_id, output_types):
    """The files a finished run should have produced, by name."""
    types = list(output_types)
    if "ACY" not in types:
        # EPIC always writes ACY; the runner checks it to tell a silent failure
        # from a run that simply produced no rows for the chosen outputs.
        types.append("ACY")
    return ["{}.{}".format(site_id, kind) for kind in types]


# ---------------------------------------------------------------- run period

#: The first line of EPICCONT.DAT begins NBYR IYR0 IMO0 IDA0: how many years to
#: simulate, then the start year, month and day.
PERIOD_FIELDS = 4
FIELD_WIDTH = 4


def _plausible(years, year, month, day):
    return years >= 1 and 1800 <= year <= 2200 and 1 <= month <= 12 and 1 <= day <= 31


def period_style(line):
    """How EPICCONT's first line is laid out: "fixed" or "free".

    The model folder shipped in this repo writes free format - every value
    separated by spaces - and a whitespace split reads it exactly right. Other
    EPIC builds write Fortran I4 fields, where a duration of 20 and a start
    year of 2001 run together as "  202001" and that same split reads one
    number. Detecting the layout costs little and lets one writer serve a model
    folder the user points at, whichever build produced it. Whichever
    interpretation yields a plausible date is the one the file uses.
    """
    fields = [line[i:i + FIELD_WIDTH] for i in range(0, FIELD_WIDTH * PERIOD_FIELDS, FIELD_WIDTH)]
    try:
        values = [int(field) for field in fields]
        if _plausible(*values):
            return "fixed"
    except ValueError:
        pass
    tokens = line.split()
    try:
        if len(tokens) >= PERIOD_FIELDS and _plausible(*[int(tokens[i]) for i in range(PERIOD_FIELDS)]):
            return "free"
    except ValueError:
        pass
    raise RunControlError("The first line of EPICCONT.DAT does not start with a readable "
                          "duration and start date: {!r}".format(line.rstrip()[:40]))


def read_period(text):
    """``(years, start year, month, day)`` from EPICCONT.DAT's text."""
    line = text.splitlines()[0] if text else ""
    if period_style(line) == "fixed":
        return tuple(int(line[i:i + FIELD_WIDTH])
                     for i in range(0, FIELD_WIDTH * PERIOD_FIELDS, FIELD_WIDTH))
    return tuple(int(token) for token in line.split()[:PERIOD_FIELDS])


def _replace_free(line, values):
    """Rewrite the first tokens of a space-separated line, keeping its columns.

    Each value takes the width of its original token plus the spaces before it,
    right-aligned, so the columns after it stay where they were - "   5" becomes
    "  20" rather than pushing everything one place right.
    """
    import re
    matches = list(re.finditer(r"\S+", line))
    out, last = [], 0
    for index, match in enumerate(matches[:len(values)]):
        field = line[last:match.end()]
        text = str(int(values[index]))
        # Keep one separating space unless the field is the start of the line.
        room = len(field) - (1 if last and not field[:1].isspace() else 0)
        out.append(text.rjust(max(room, len(text) + (1 if last else 0))))
        last = match.end()
    return "".join(out) + line[last:]


def with_period(text, start_year, years, month=1, day=1):
    """EPICCONT.DAT's text with a new run period, in the file's own style.

    Line endings are kept as they were: the Windows model folder uses CRLF, and
    rewriting it with LF is an edit nobody asked for.
    """
    if not _plausible(int(years), int(start_year), int(month), int(day)):
        raise RunControlError("Not a usable run period: {} years from {}-{:02d}-{:02d}.".format(
            years, start_year, int(month), int(day)))
    lines = text.splitlines(True)
    if not lines:
        raise RunControlError("EPICCONT.DAT is empty.")
    first = lines[0]
    body = first.rstrip("\r\n")
    ending = first[len(body):]
    values = (int(years), int(start_year), int(month), int(day))
    if period_style(body) == "fixed":
        width = FIELD_WIDTH * PERIOD_FIELDS
        body = "".join("{:4d}".format(value) for value in values) + body[width:]
    else:
        body = _replace_free(body, values)
    lines[0] = body + ending
    return "".join(lines)


def read_text(path):
    """A control file's text with its line endings exactly as stored."""
    with open(str(path), "r", encoding=ENCODING, newline="") as handle:
        return handle.read()


def write_text(path, text):
    """Write control text back without translating its line endings."""
    with open(str(path), "w", encoding=ENCODING, newline="") as handle:
        handle.write(text)
