import os
import shutil
import redis
import shortuuid
import time
import subprocess
import platform

def connect_to_redis(host='localhost', port=56379, db=0):
    """
    Establish connection to Redis, attempting to start the Redis server if needed.
    
    Args:
        host (str): Redis server hostname.
        port (int): Redis server port.
        db (int): Redis database number.

    Returns:
        redis.Redis: A connected Redis client instance.
    """
    client = redis.Redis(host=host, port=port, db=db)

    try:
        # Check if the connection is alive by pinging the server
        client.ping()
    except redis.ConnectionError:
        # If the connection fails, try to start the Redis server
        print("Redis server not running. Attempting to start...")
        try:
            if platform.system() == 'Windows':  # Windows
                metadata_dir = os.path.join(os.path.expanduser("~"), 'GeoEPIC')
                redis_server = os.path.join(metadata_dir, 'redis-server.exe')
                redis_conf = os.path.join(metadata_dir, 'redis.conf')
                subprocess.Popen([redis_server, redis_conf])
            else:  # Unix-like systems
                subprocess.Popen(['redis-server', '--port', '56379'])  # Start Redis in the background
            # Wait briefly for the Redis server to start up
            time.sleep(1)
            # Re-check the connection after starting the server
            client.ping()
            print("Redis server started.")
        except Exception as e:
            raise Exception(f"Failed to start Redis server: {str(e)}\n Please try: \"geo_epic init\" in command line.")

    return client


class WorkerPool:
    def __init__(self, pool_key=None, base_dir=None, host='localhost', port=56379, db=0):
        self.redis = connect_to_redis(host=host, port=port, db=db)
        self.pool_key = pool_key or f"worker_pool_{shortuuid.uuid()}"

        existing_base_dir = self.redis.get(f"{self.pool_key}_base_dir")
        
        if base_dir:
            self.base_dir = base_dir
            self.redis.set(f"{self.pool_key}_base_dir", self.base_dir)
        elif existing_base_dir:
            self.base_dir = existing_base_dir.decode('utf-8')  # Decode bytes to string
        else:
            self.base_dir = None
            self.redis.set(f"{self.pool_key}_base_dir", "None")

    def open(self, max_resources):
        """Initialize resources and add them to the Redis queue."""
        self.redis.delete(self.pool_key)
        if self.base_dir:
            os.makedirs(self.base_dir, exist_ok=True)

        # Loop to create each resource and push to Redis
        for i in range(max_resources):
            if self.base_dir:
                resource = os.path.join(self.base_dir, str(i))
                os.makedirs(resource, exist_ok=True)
            else: resource = str(i)
            
            # Push the resource to the Redis queue
            self.redis.rpush(self.pool_key, resource)

    def acquire(self):
        """Acquire a resource by blocking until one is available."""
        _, resource = self.redis.blpop(self.pool_key)
        return resource.decode('utf-8')

    def release(self, resource):
        """Release a resource back to the pool."""
        self.redis.rpush(self.pool_key, resource)

    def close(self):
        """Remove all resources from the pool, deleting directories if applicable."""
        while not self.redis.llen(self.pool_key) == 0:
            resource = self.redis.lpop(self.pool_key).decode('utf-8')
            if self.base_dir and os.path.exists(resource):
                shutil.rmtree(resource, ignore_errors=True)
        self.redis.delete(f"{self.pool_key}_base_dir")
    
    def queue_len(self):
        if self.redis.exists(self.pool_key):
            return self.redis.llen(self.pool_key)
        else: return None
    
