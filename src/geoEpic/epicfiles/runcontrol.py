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
