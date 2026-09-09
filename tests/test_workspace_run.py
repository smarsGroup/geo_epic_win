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

    def ws_n1(d, trailing='\\'):
        with open(os.path.join(d, 'WORKSPACE.DAT'), 'w') as f:
            f.write(f"   1\n{d}{trailing}\n")

    def bare_pointers(d):
        # rewrite the pointer files the way the shipped template writes them: no quotes, no ./
        for lf, ext in (('SITECOM.DAT', '.SIT'), ('SOILCOM.DAT', '.SOL'), ('OPSCCOM.DAT', '.OPC')):
            name = [f for f in os.listdir(d) if f.upper().endswith(ext)][0]
            with open(os.path.join(d, lf), 'w') as f:
                f.write(f"    1 {name}\n")

    def v_quoted(d):
        ws_n1(d)

    def v_bare(d):
        ws_n1(d); bare_pointers(d)

    def v_bare_noslash(d):
        ws_n1(d, trailing=''); bare_pointers(d)

    def v_bare_fwd(d):
        ws_n1(d.replace('\\', '/'), trailing='/'); bare_pointers(d)

    def run_and_report(name, d, exe, site_prefix):
        r = subprocess.run([exe], cwd=d, input=b'\r\n' * 20, capture_output=True, timeout=120)
        out = (r.stdout + r.stderr).decode(errors='replace')
        produced = {f: os.path.getsize(os.path.join(d, f)) for f in os.listdir(d) if f.lower().startswith(site_prefix.lower() + '.')}
        lines = [l for l in out.splitlines() if l.strip() and 'Unknown' not in l and 'Fortran Pause' not in l]
        print(f"\n=== VARIANT {name}: rc={r.returncode & 0xFFFFFFFF:#x} produced={produced}\n  out ({len(lines)} lines):\n    " + "\n    ".join(lines[:80]))
        return produced

    results = {}
    # 1. our generated run folder, bare pointers, full output
    d = run_dir + '_bare'; shutil.rmtree(d, ignore_errors=True); shutil.copytree(run_dir, d)
    for f in glob.glob(os.path.join(d, 'umstead.ACY')) + glob.glob(os.path.join(d, 'umstead.DGN')) + glob.glob(os.path.join(d, 'umstead.out')): os.remove(f)
    v_bare(d)
    for lf in ('EPICRUN.DAT', 'SITECOM.DAT', 'SOILCOM.DAT', 'OPSCCOM.DAT', 'WDLSTCOM.DAT', 'WPM1USEL.DAT', 'WINDUSEL.DAT', 'WORKSPACE.DAT'):
        p_ = os.path.join(d, lf)
        if os.path.exists(p_):
            print(f"  -- {lf}: {open(p_, errors='replace').read()[:200]!r}")
    results['bare'] = run_and_report('bare', d, os.path.join(d, exe_name), 'umstead')

    # 2. the template model folder exactly as shipped (its own pointer files & EPICRUN.DAT),
    #    with the site/soil/opc/weather files copied next to the exe
    for name, touch_ws in (('as_shipped_ws', True), ('as_shipped_raw', False)):
        d = run_dir + '_' + name; shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(str(ws / 'model'), d)
        for src in ('sites/umstead.SIT', 'soil/umstead.SOL', 'opc/umstead.OPC', 'weather/NCRDU.DLY'):
            shutil.copy(str(ws / src), d)
        if touch_ws:
            ws_n1(d)
        print(f"  -- EPICRUN.DAT: {open(os.path.join(d, 'EPICRUN.DAT'), errors='replace').read()[:120]!r}")
        results[name] = run_and_report(name, d, os.path.join(d, 'EPIC1102.exe'), 'umstead_0')
    print("\n=== workspace run log head ===\n" + "".join(open(glob.glob(str(ws / 'log' / '*.log'))[0], errors='replace').readlines()[:12]) if glob.glob(str(ws / 'log' / '*.log')) else "(no log)")
    assert any(any(k.upper().endswith(".ACY") and v > 0 for k, v in p.items()) for p in results.values()), f"no variant produced an ACY: {results}"
