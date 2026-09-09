import os
import csv
import shutil
import stat
import platform
import pytest

import geoEpic

ASSETS = os.path.join(os.path.dirname(geoEpic.__file__), 'assets', 'workspace_win')
IS_WINDOWS = platform.system() == 'Windows'

# On non-Windows platforms the package ships no EPIC binary, so the run pipeline
# is exercised with a stub that behaves like EPIC from the outside: it reads the
# site id from EPICRUN.DAT and writes non-empty <id>.ACY / <id>.DGN files.
STUB_EXE = """#!/bin/sh
id=$(awk '{print $1}' EPICRUN.DAT | head -1)
printf 'stub ACY for %s\\n' "$id" > "$id.ACY"
printf 'stub DGN for %s\\n' "$id" > "$id.DGN"
echo "TOTAL RUN TIME: 0"
"""


@pytest.fixture
def workspace(tmp_path):
    """A copy of the template workspace with N sites and a platform-appropriate executable."""
    ws = tmp_path / 'ws'
    shutil.copytree(ASSETS, ws)

    n_sites = 6
    with open(ws / 'info.csv', newline='') as f:
        base = next(csv.DictReader(f))
    # every synthetic site reuses the template site's SIT/SOL/OPC/DLY files
    base['sit'] = base['SiteID']
    with open(ws / 'info.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(base.keys()))
        w.writeheader()
        for i in range(n_sites):
            row = dict(base)
            row['SiteID'] = f'site{i}'
            w.writerow(row)

    cfg = (ws / 'config.yml').read_text()
    if not IS_WINDOWS:
        stub = ws / 'model' / 'EPIC1102'
        stub.write_text(STUB_EXE)
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        cfg = cfg.replace('./model/EPIC1102.exe', './model/EPIC1102')
    cfg += '\nnum_of_workers: 3\n'
    (ws / 'config.yml').write_text(cfg)
    (ws / 'output').mkdir(exist_ok=True)
    (ws / 'log').mkdir(exist_ok=True)

    old = os.getcwd()
    os.chdir(ws)
    try:
        yield ws, n_sites
    finally:
        os.chdir(old)
