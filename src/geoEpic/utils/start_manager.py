import os
from multiprocessing.managers import BaseManager
import queue

shared_queues = {}

def get_pool_queue(name):
    if name not in shared_queues:
        shared_queues[name] = queue.Queue()
    return shared_queues[name]

def is_new_queue(name):
    return name not in shared_queues

if __name__ == '__main__':
    BaseManager.register('get_pool_queue', get_pool_queue)
    BaseManager.register('is_new_queue', is_new_queue)
    
    manager = BaseManager(address=('', 50001), authkey=b'abc123')
    server = manager.get_server()
    print(f"Server started at PID {os.getpid()}...")
    server.serve_forever()
