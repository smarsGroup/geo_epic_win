from .parallel import parallel_executor, run_with_timeout
from .raster_utils import *
from .misc import *
from .workerpool import WorkerPool


def __getattr__(name):
    # Lazy optional: the Redis-backed pool is kept for users who already run redis.
    if name == 'RedisWorkerPool':
        from .redis_utils import WorkerPool as RedisWorkerPool
        return RedisWorkerPool
    raise AttributeError(f"module 'geoEpic.utils' has no attribute '{name}'")
