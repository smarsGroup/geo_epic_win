import os
import shutil
import shortuuid
import time
from multiprocessing.managers import BaseManager
import queue
import subprocess
import sys

class TimeoutException(Exception):
    """Custom exception for resource acquisition timeout."""
    pass


class WorkerPool:
    """ A pool for managing workers and resources, leveraging multiprocessing
        to handle resource allocation through queues. """
    server_process = None

    @classmethod
    def start_server(cls):
        """ Start the queue server as a separate process if it's not already running. """
        if cls.server_process is None:
            # Get the current script's directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            server_script_path = os.path.join(script_dir, 'start_manager.py')
            log_path = os.path.join(script_dir, 'server_log.txt')
            # Start the server script as a subprocess
            cls.log_file = open(log_path, 'w')
            cls.server_process = subprocess.Popen([sys.executable, server_script_path],
                                                  stdout=cls.log_file,
                                                  stderr=cls.log_file,
                                                  start_new_session=True)
            print("Pool Manager Server starting. (Logging to {log_path})")
            time.sleep(1)  # Give the server a moment to start

    @classmethod
    def stop_server(cls):
        """ Stop the queue server cleanly. """
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.join()
            print("Server stopped.")
            cls.server_process = None

    def __init__(self, pool_key: str = None, base_dir: str = None):
        """ Initialize the worker pool with optional specific pool key and base directory. """
        self.pool_key = pool_key or f"worker_pool_{shortuuid.uuid()}"
        self.base_dir = base_dir
        self.opened = False

        self.ensure_server_running()
        self.connect_to_server()

        if self.base_dir:
            os.makedirs(self.base_dir, exist_ok=True)

    def ensure_server_running(self):
        """ Ensure the queue server is running, and start it if necessary. """
        try:
            self.connect_to_server()
        except ConnectionRefusedError:
            self.start_server()

    def connect_to_server(self):
        """ Connect to the queue server using the BaseManager. """
        BaseManager.register('get_pool_queue')
        BaseManager.register('is_new_queue')
        self.manager = BaseManager(address=('localhost', 50001), authkey=b'abc123')
        self.manager.connect()
        self.opened = not self.manager.is_new_queue(self.pool_key)
        self.queue = self.manager.get_pool_queue(self.pool_key)

    def open(self, max_resources: int):
        """ Open and allocate a specified number of resources. """
        for i in range(max_resources):
            resource = os.path.join(self.base_dir, str(i)) if self.base_dir else str(i)
            if self.base_dir:
                os.makedirs(resource, exist_ok=True)
            self.queue.put(resource)
        self.opened = True

    def acquire(self, timeout=120):
        """ Acquire a resource from the pool. """
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutException(f"Timed out waiting for a resource after {timeout} seconds")

    def release(self, resource: str):
        """ Release a resource back to the pool. """
        self.queue.put(resource)

    def close(self):
        """ Clean up resources and empty the pool. """
        while not self.queue.empty():
            resource = self.queue.get()
            if self.base_dir and os.path.exists(resource):
                shutil.rmtree(resource, ignore_errors=True)

    def queue_len(self) -> int:
        """ Return the current number of available resources in the pool. """
        if self.opened: return self.queue.qsize()
        else: return None

    def __del__(self):
        """ Clean up resources when the WorkerPool instance is deleted. """
        if hasattr(self, 'manager'):
            try:
                self.manager._close()
            except:
                pass

if __name__ == "__main__":
    # Test the WorkerPool class
    # try:
    # Create a WorkerPool instance
    WorkerPool.stop_server()

    pool = WorkerPool(pool_key="test_pool_2")
    print(f"Pool opened with {pool.queue_len()} resources")
    
    # Open the pool with 5 resources
    pool.open(5)
    print(f"Pool opened with {pool.queue_len()} resources")
    
    # Acquire and release resources
    resource1 = pool.acquire()
    print(f"Acquired resource: {resource1}")
    print(f"Resources left: {pool.queue_len()}")
    
    resource2 = pool.acquire()
    print(f"Acquired resource: {resource2}")
    print(f"Resources left: {pool.queue_len()}")
    
    # pool.release(resource1)
    # print(f"Released resource: {resource1}")
    # print(f"Resources available: {pool.queue_len()}")
    
    # # Try to acquire more resources than available
    # for i in range(4):
    #     try:
    #         resource = pool.acquire(timeout=2)
    #         print(f"Acquired resource: {resource}")
    #     except TimeoutException:
    #         print("Timeout occurred while trying to acquire resource")
    
    # Close the pool
    pool.close()
    print("Pool closed")
        
    # finally:
    #     # Ensure the server is stopped
    #     WorkerPool.stop_server()

