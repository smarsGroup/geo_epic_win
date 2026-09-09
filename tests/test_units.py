import os
import sys
import subprocess
import pandas as pd
import pytest

from geoEpic.utils import filter_dataframe, WorkerPool
from geoEpic.core import Site


def test_filter_dataframe_and_union():
    df = pd.DataFrame({'SiteID': [1, 2, 3, 4], 'x': [1, 2, 3, 4]})
    assert filter_dataframe(df, 'x > 1; x < 3').SiteID.tolist() == [2]
    assert sorted(filter_dataframe(df, 'x < 2 + x > 3').SiteID.tolist()) == [1, 4]
    assert len(filter_dataframe(df, 'Range(0, 0.5)')) == 2


def test_workerpool_in_process(tmp_path):
    pool = WorkerPool('t_pool', root_dir=str(tmp_path)).open(2)
    a = pool.acquire()
    b = pool.acquire()
    assert pool.acquire(block=False) is None
    assert pool.queue_len() == 0
    pool.release(a)
    assert pool.queue_len() == 1
    assert pool.acquire(timeout=1) == a
    pool.close()
    assert pool.queue_len() == 2


def test_workerpool_cross_process(tmp_path):
    root = str(tmp_path)
    holder = subprocess.Popen([sys.executable, '-c', f"""
import time
from geoEpic.utils import WorkerPool
p = WorkerPool('x_pool', root_dir={root!r}).open(1)
p.acquire(); print('held', flush=True); time.sleep(3)
"""], stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == 'held'
    pool = WorkerPool('x_pool', root_dir=root).open(1)
    assert pool.acquire(block=False) is None, "slot held by another process must not be acquirable"
    holder.wait(timeout=30)
    assert pool.acquire(timeout=5) is not None
    pool.close()


def test_site_case_insensitive_lookup(workspace):
    ws, _ = workspace
    os.rename(ws / 'soil' / 'umstead.SOL', ws / 'soil' / 'umstead.sol')
    from geoEpic.io import ConfigParser
    cfg = ConfigParser('config.yml')
    site = Site.from_config(cfg, SiteID='umstead', soil='umstead', dly='NCRDU', opc='umstead', sit='umstead')
    # On case-insensitive filesystems (Windows) the original name resolves directly;
    # on Linux the fallback must find the renamed lower-case file.
    assert os.path.exists(site.sol_path)


def test_cli_prints_usage():
    out = subprocess.run([sys.executable, '-m', 'geoEpic.dispatcher'], capture_output=True, text=True)
    assert out.returncode == 0 and 'usage: geo_epic' in out.stdout
