from .parallel import parallel_executor, run_with_timeout
from .raster_utils import *
from .misc import *


def __getattr__(name):
    # Lazy: redis (and a redis-server) are only needed for the GEE worker pool.
    if name == 'WorkerPool':
        from .redis_utils import WorkerPool
        return WorkerPool
    raise AttributeError(f"module 'geoEpic.utils' has no attribute '{name}'")
