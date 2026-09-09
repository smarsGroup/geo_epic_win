"""
Cross-platform, cross-process worker pool built on OS file locks.

Replaces the Redis-based pool (Linux) and the Win32 semaphore pool (Windows).
Works anywhere Python's ``fcntl`` (POSIX) or ``msvcrt`` (Windows) exists, needs
no server and no extra dependency.

API (same as the previous pools):
    pool = WorkerPool(pool_key=None, base_dir=None)
    pool.open(max_resources)          # idempotent; reuses an existing pool with the same key
    slot = pool.acquire(block=True, timeout=None)   # -> str index or path, None on timeout
    pool.release(slot)
    pool.queue_len()                  # free slots, or None if the pool was never opened
    pool.close(cleanup_dirs=False)

Each slot is a small file ``<pool_dir>/slot_<i>.lock``. A process holds a slot
by holding an exclusive, non-blocking lock on that file; the lock is released
automatically by the OS if the process dies, so a crashed worker never leaks a
slot.
"""
import os
import time
import tempfile
import shutil
import platform

import shortuuid

IS_WINDOWS = platform.system() == 'Windows'
if IS_WINDOWS:
    import msvcrt
else:
    import fcntl


def _try_lock(fh):
    """Try to take an exclusive non-blocking lock on an open file. True on success."""
    try:
        if IS_WINDOWS:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError):
        return False


def _unlock(fh):
    try:
        if IS_WINDOWS:
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fh, fcntl.LOCK_UN)
    except (IOError, OSError):
        pass


class WorkerPool:
    _POLL = 0.05  # seconds between acquire attempts

    def __init__(self, pool_key=None, base_dir=None, root_dir=None):
        self.pool_key = pool_key or f"worker_pool_{shortuuid.uuid()}"
        self.base_dir = base_dir
        root = root_dir or os.path.join(tempfile.gettempdir(), 'geo_epic_pools')
        self.pool_dir = os.path.join(root, self.pool_key)
        self._handles = {}   # slot index -> open file handle we currently hold
        self.capacity = None

    # ------------------------------------------------------------------ setup
    def open(self, max_resources):
        os.makedirs(self.pool_dir, exist_ok=True)
        cap_file = os.path.join(self.pool_dir, 'capacity')
        if os.path.exists(cap_file):
            # reuse an existing pool with the same key (another process opened it)
            with open(cap_file) as f:
                existing = int(f.read().strip() or 0)
            if existing:
                max_resources = existing
        else:
            with open(cap_file, 'w') as f:
                f.write(str(int(max_resources)))
        self.capacity = int(max_resources)
        for i in range(self.capacity):
            p = self._slot_path(i)
            if not os.path.exists(p):
                open(p, 'a').close()
            if self.base_dir:
                os.makedirs(os.path.join(self.base_dir, str(i)), exist_ok=True)
        return self

    def _slot_path(self, i):
        return os.path.join(self.pool_dir, f'slot_{i}.lock')

    def _resource(self, i):
        return os.path.join(self.base_dir, str(i)) if self.base_dir else str(i)

    def _index(self, resource):
        return int(os.path.basename(str(resource)))

    # --------------------------------------------------------------- acquire
    def acquire(self, block=True, timeout=None):
        if self.capacity is None:
            raise RuntimeError("Pool not open: call open(max_resources) first.")
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            for i in range(self.capacity):
                if i in self._handles:
                    continue
                fh = open(self._slot_path(i), 'a+')
                if _try_lock(fh):
                    self._handles[i] = fh
                    return self._resource(i)
                fh.close()
            if not block:
                return None
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(self._POLL)

    def release(self, resource):
        i = self._index(resource)
        fh = self._handles.pop(i, None)
        if fh is None:
            return
        _unlock(fh)
        fh.close()

    def queue_len(self):
        """Number of currently free slots (probe), or None if the pool does not exist."""
        if self.capacity is None:
            cap_file = os.path.join(self.pool_dir, 'capacity')
            if not os.path.exists(cap_file):
                return None
            with open(cap_file) as f:
                self.capacity = int(f.read().strip() or 0)
        free = 0
        for i in range(self.capacity):
            if i in self._handles:
                continue
            try:
                fh = open(self._slot_path(i), 'a+')
            except OSError:
                continue
            if _try_lock(fh):
                free += 1
                _unlock(fh)
            fh.close()
        return free

    def close(self, cleanup_dirs=False):
        for i in list(self._handles):
            self.release(self._resource(i))
        if cleanup_dirs and self.base_dir:
            shutil.rmtree(self.base_dir, ignore_errors=True)

    # context manager sugar
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
