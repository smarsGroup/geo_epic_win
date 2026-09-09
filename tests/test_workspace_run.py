import os
import glob
import platform
import subprocess
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
            assert f.exists() and f.stat().st_size > 0, f"missing or empty {f}\n{_log_tails(ws)}"
    assert not list((ws / 'log').glob('*.log')), "no site should have failed\n" + _log_tails(ws)


def _log_tails(ws, n=40):
    """Collect the tails of every EPIC log so CI failures are self-explanatory."""
    parts = []
    for f in sorted(glob.glob(str(ws / 'log' / '*.log'))):
        with open(f, errors='replace') as fh:
            lines = fh.readlines()
        parts.append(f"--- {os.path.basename(f)} (last {n} lines) ---\n" + ''.join(lines[-n:]))
    return '\n'.join(parts) or '(no log files)'


@pytest.mark.skipif(not IS_WINDOWS, reason="real EPIC1102.exe only ships for Windows")
def test_real_epic_runs_directly(workspace):
    """Diagnostic: prepare one site exactly as EPICModel.run() does, keep the run
    folder, execute EPIC1102.exe by hand and show its exit code and full output."""
    from geoEpic.core import Site
    from geoEpic.io import ConfigParser
    ws, _ = workspace
    cfg = ConfigParser('config.yml')
    m = EPICModel.from_config('config.yml')
    m.delete_after_run = False
    site = Site.from_config(cfg, SiteID='umstead', soil='umstead', dly='NCRDU', opc='umstead', sit='umstead')
    try:
        try:
            m.run(site)
            print("EPICModel.run succeeded")
        except Exception as e:
            print(f"EPICModel.run raised: {e}")
        run_dir = os.path.join(m.cache_path, 'EPICRUNS', 'umstead')
        assert os.path.isdir(run_dir), f"run dir missing: {run_dir}"
    finally:
        m.close()
    exe = glob.glob(os.path.join(run_dir, 'EPIC1102_*.exe'))[0]
    for f in ('umstead.ACY', 'umstead.DGN'):
        if os.path.exists(os.path.join(run_dir, f)):
            os.remove(os.path.join(run_dir, f))
    print("EPICCONT.DAT line 1:", open(os.path.join(run_dir, 'EPICCONT.DAT'), errors='replace').readline().rstrip())
    r = subprocess.run([exe], cwd=run_dir, input=b'\r\n' * 40, capture_output=True, timeout=300)
    out = (r.stdout + r.stderr).decode(errors='replace')
    lines = [l for l in out.splitlines() if l.strip() and 'Unknown' not in l and 'Fortran Pause' not in l]
    produced = {f: os.path.getsize(os.path.join(run_dir, f)) for f in os.listdir(run_dir) if f.startswith('umstead.')}
    print(f"returncode={r.returncode & 0xFFFFFFFF:#x} produced={produced}\n--- output ---\n" + "\n".join(lines[:60]))
    assert r.returncode == 0 and produced.get('umstead.ACY', 0) > 0, "see captured output"
