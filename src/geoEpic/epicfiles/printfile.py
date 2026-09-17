"""Which output files EPIC will write, read from the model folder's print file.

EPIC's output is not chosen on the command line. The print file (named by FPRNT
in EPICFILE.DAT - PRNT1102.DAT in the Windows build shipped here) carries two
lines listing every output extension the build supports, and two matching lines
of 0/1 toggles saying which are switched on. Turning DGN on means writing a 1
into the right column of the toggle lines.

The layout, from the file's own footnote ("These are the extensions of the
output files to turn on/off in lines 15-16"):

    line 15, 16 (1-based)   the toggles, 0 or 1 per extension
    last two non-blank      the extensions themselves

"Last two non-blank" rather than simply the last two lines: the Windows print
file ends with the extension lines, but other builds end with a blank or
space-filled line, and counting back from the end then reads the wrong lines.
Against a real Linux PRNT0810.DAT that mistake reports RTC and SGI enabled for
a model that in fact writes ACY and DGN.

Some builds mark selected extensions with an asterisk (``*acy``). The asterisk
is documentation, not state - the toggles decide - so it is stripped.
"""
from pathlib import Path

ENCODING = "ISO-8859-1"

#: 0-based indices of the toggle lines, as the print file's own note describes.
TOGGLE_LINES = (14, 15)

#: Extensions that are listed but are not output files, per the file's footnote.
NOT_FILES = {"erx", "run", "rtc", "rts", "sgi", "gis"}


class PrintFileError(ValueError):
    pass


def _read(path):
    path = Path(path)
    if not path.is_file():
        raise PrintFileError("No print file at {}. It lists the output files this "
                             "EPIC build can write.".format(path))
    with open(str(path), "r", encoding=ENCODING) as handle:
        return handle.readlines()


def _extension_lines(lines):
    """Indices of the two lines carrying extensions: the last two with content."""
    filled = [index for index, line in enumerate(lines)
              if line.replace("*", " ").split()]
    if len(filled) < 2:
        raise PrintFileError("The print file lists no output extensions.")
    return filled[-2], filled[-1]


def extensions(path):
    """Every output extension this build supports, lower-case, in file order."""
    lines = _read(path)
    first, second = _extension_lines(lines)
    found = []
    for index in (first, second):
        found.extend(token.lower() for token in lines[index].replace("*", " ").split())
    return found


def supported(path, include_non_files=False):
    """The extensions that name real output files, upper-case."""
    return [name.upper() for name in extensions(path)
            if include_non_files or name not in NOT_FILES]


def _toggles(lines):
    values = []
    for index in TOGGLE_LINES:
        if index < len(lines):
            values.extend(lines[index].split())
    return values


def enabled(path):
    """The output types currently switched on, upper-case."""
    lines = _read(path)
    names = extensions(path)
    flags = _toggles(lines)
    if len(flags) < len(names):
        raise PrintFileError(
            "The print file lists {} extensions but only {} toggles; they cannot be "
            "matched, so no output selection can be read.".format(len(names), len(flags)))
    return [name.upper() for name, flag in zip(names, flags) if flag == "1"]


def set_enabled(path, wanted):
    """Switch on exactly ``wanted`` and nothing else. Returns what was written."""
    lines = _read(path)
    names = extensions(path)
    flags = _toggles(lines)
    if len(flags) < len(names):
        raise PrintFileError("The print file's toggles do not match its extensions.")
    chosen = {str(name).strip().lower() for name in wanted}
    unknown = chosen - set(names)
    if unknown:
        raise PrintFileError(
            "This EPIC build cannot write: {}. It supports: {}.".format(
                ", ".join(sorted(name.upper() for name in unknown)),
                ", ".join(supported(path))))
    updated = ["1" if name in chosen else "0" for name in names]
    # The toggle lines keep their original split: the first holds as many
    # values as it did before, the rest go on the second.
    first_count = len(lines[TOGGLE_LINES[0]].split())
    for line_index, values in ((TOGGLE_LINES[0], updated[:first_count]),
                               (TOGGLE_LINES[1], updated[first_count:])):
        lines[line_index] = "".join("{:>4}".format(value) for value in values) + "\n"
    with open(str(path), "w", encoding=ENCODING, newline="\n") as handle:
        handle.writelines(lines)
    return [name.upper() for name in names if name in chosen]
