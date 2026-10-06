"""The run path imports without the heavy optional packages.

QGIS's own Python (3.12 + numpy 2 on Windows) has no rasterio, pyproj,
scikit-learn, redis, lmdb or pygmo; Q-EPIC runs geoEpic on it. Importing what a
run needs must therefore not pull any of them in.
"""
import json
import os
import subprocess
import sys

HEAVY = ("rasterio", "pyproj", "sklearn", "geopandas", "redis", "lmdb", "pygmo", "xarray")


def test_running_epic_needs_none_of_the_optional_packages():
    code = ("import json, sys\n"
            "from geoEpic.core import Workspace, EPICModel, Site\n"
            "from geoEpic.io import Parm, CropCom, DataLogger\n"
            "print(json.dumps(sorted(m for m in %r if m in sys.modules)))" % (HEAVY,))
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env=env, check=True).stdout
    assert json.loads(out.strip().splitlines()[-1]) == []


def test_raster_helpers_still_load_on_first_use():
    import geoEpic.utils as utils
    assert "find_nearest" in utils.RASTER_NAMES
    assert callable(utils.__getattr__)
