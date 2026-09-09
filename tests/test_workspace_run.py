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
    folder, then execute EPIC1102.exe under several WORKSPACE/EPICFILE variants
    and report which one makes the executable find its list files."""
    import shutil
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
        except Exception as e:
            print(f"EPICModel.run raised: {e}")
        run_dir = os.path.join(m.cache_path, 'EPICRUNS', 'umstead')
        assert os.path.isdir(run_dir), f"run dir missing: {run_dir}"
    finally:
        m.close()

    exe_name = [f for f in os.listdir(run_dir) if f.startswith('EPIC1102_')][0]
    list_files = ['SITECOM.DAT', 'SOILCOM.DAT', 'OPSCCOM.DAT', 'WPM1USEL.DAT', 'WPM5US.DAT',
                  'WINDUSEL.DAT', 'WIDXCOM.DAT', 'WDLSTCOM.DAT']

    def v_baseline(d):
        pass

    def v_ws_n1_exe(d):
        with open(os.path.join(d, 'WORKSPACE.DAT'), 'w') as f:
            f.write(f"   1\n{os.path.join(d, exe_name)}   umstead 1 0 0 0 1 1 1\n")

    def v_ws_n1_dir(d):
        with open(os.path.join(d, 'WORKSPACE.DAT'), 'w') as f:
            f.write(f"   1\n{d}\\\n")

    def v_ws_n0_dir4(d):
        with open(os.path.join(d, 'WORKSPACE.DAT'), 'w') as f:
            f.write("   0\n" + "".join(f"{d}\\\n" for _ in range(4)))

    def v_epicfile_abs(d):
        p = os.path.join(d, 'EPICFILE.DAT')
        with open(p) as f:
            lines = f.read().splitlines()
        out = []
        for ln in lines:
            parts = ln.split()
            if len(parts) == 2 and parts[1] in list_files:
                out.append(f" {parts[0]:8s} {os.path.join(d, parts[1])}")
            else:
                out.append(ln)
        with open(p, 'w') as f:
            f.write("\n".join(out) + "\n")

    def v_c_dirs(d):
        for sub in ('WEATDATA', 'SITE', 'SOIL', 'OPSC'):
            os.makedirs(f"C:\\{sub}", exist_ok=True)
            for lf in list_files:
                shutil.copy(os.path.join(d, lf), f"C:\\{sub}\\{lf}")
            for extra in os.listdir(d):
                if extra.upper().endswith(('.SIT', '.SOL', '.OPC', '.DLY', '.WP1', '.WND')):
                    shutil.copy(os.path.join(d, extra), f"C:\\{sub}\\{extra}")

    results = {}
    for name, fn in [('baseline', v_baseline), ('ws_n1_exe', v_ws_n1_exe), ('ws_n1_dir', v_ws_n1_dir),
                     ('ws_n0_dir4', v_ws_n0_dir4), ('epicfile_abs', v_epicfile_abs), ('c_dirs', v_c_dirs)]:
        d = run_dir + '_' + name
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(run_dir, d)
        for f in glob.glob(os.path.join(d, 'umstead.ACY')) + glob.glob(os.path.join(d, 'umstead.DGN')):
            os.remove(f)
        fn(d)
        r = subprocess.run([os.path.join(d, exe_name)], cwd=d, input=b'\r\n' * 20, capture_output=True, timeout=120)
        out = (r.stdout + r.stderr).decode(errors='replace')
        acy = os.path.join(d, 'umstead.ACY')
        size = os.path.getsize(acy) if os.path.exists(acy) else 0
        missing = sorted(set(l.strip() for l in out.splitlines() if 'IS MISSING' in l))
        results[name] = (r.returncode & 0xFFFFFFFF, size, missing[:3], out.strip().splitlines()[-2:])
        print(f"\n=== VARIANT {name}: rc={results[name][0]:#x} ACY={size} bytes\n  missing={missing[:4]}\n  tail={results[name][3]}")
    assert any(v[1] > 0 for v in results.values()), f"no variant produced an ACY: {results}"
