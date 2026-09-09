import os
import platform
import pytest

from geoEpic.core import Workspace, EPICModel
from geoEpic.io import ACY

IS_WINDOWS = platform.system() == 'Windows'


def test_parallel_run_produces_outputs(workspace):
    ws, n = workspace
    w = Workspace('config.yml')
    assert w.num_of_workers == 3, "num_of_workers must come from config.yml"
    w.run(progress_bar=False)
    w.close()

    out = ws / 'output'
    for i in range(n):
        for ext in ('ACY', 'DGN'):
            f = out / f'site{i}.{ext}'
            assert f.exists() and f.stat().st_size > 0, f"missing or empty {f}"
    assert not list((ws / 'log').glob('*.log')), "no site should have failed"


@pytest.mark.skipif(not IS_WINDOWS, reason="real EPIC1102.exe only ships for Windows")
def test_real_epic_outputs_parse(workspace):
    ws, n = workspace
    w = Workspace('config.yml')
    w.run(progress_bar=False)
    w.close()
    acy = ACY(str(ws / 'output' / 'site0.ACY'))
    assert 'YLDG' in acy.data.columns
    assert len(acy.data) >= w.model.duration  # one row per year (per crop)


def test_epicmodel_reads_control_files(workspace):
    ws, _ = workspace
    m = EPICModel.from_config('config.yml')
    try:
        assert m.duration == 6
        assert str(m.start_date) == '2000-01-01'
        assert 'FSITE' in m.file_names
        assert {'ACY', 'DGN'} <= set(m.output_types)
        m.duration = 3
        m.start_date = '2001-01-01'
    finally:
        m.close()
    # Re-read EPICCONT.DAT directly (from_config would re-apply config.yml values)
    m2 = EPICModel(os.path.join('model', os.path.basename(m.executable)))
    try:
        assert m2.duration == 3, "duration must persist in EPICCONT.DAT after in-place edit"
        assert str(m2.start_date) == '2001-01-01'
    finally:
        m2.close()
