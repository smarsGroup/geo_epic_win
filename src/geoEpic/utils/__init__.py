from .parallel import parallel_executor, run_with_timeout
from .misc import *
from .workerpool import WorkerPool

#: Raster helpers, loaded on first use: they need rasterio, pyproj, geopandas
#: and scikit-learn, which running EPIC does not - so a Python without them
#: (QGIS's own, for one) can still import geoEpic.utils.
RASTER_NAMES = {'find_nearest', 'raster_to_dataframe', 'sample_raster_aggregated',
                'sample_raster_nearest', 'reproject_crop_raster', 'GeoInterface'}


def __getattr__(name):
    if name in RASTER_NAMES:
        from . import raster_utils
        return getattr(raster_utils, name)
    # Lazy optional: the Redis-backed pool is kept for users who already run redis.
    if name == 'RedisWorkerPool':
        from .redis_utils import WorkerPool as RedisWorkerPool
        return RedisWorkerPool
    raise AttributeError(f"module 'geoEpic.utils' has no attribute '{name}'")
