from pebble import ProcessPool, ThreadPool
from concurrent.futures import TimeoutError as CFTimeoutError, as_completed
from tqdm import tqdm
import sys, traceback
import inspect

def run_with_timeout(func, args=(), kwargs={}, timeout=None):
    """
    Run a function with a timeout using pebble.ThreadPool.
    """
    with ThreadPool(max_workers=1) as pool:
        future = pool.schedule(func, args=args, kwargs=kwargs)
        return future.result(timeout=timeout)

def parallel_executor(func, args, method='Process', max_workers=10, return_value=False,
                      bar=True, timeout=None, verbose=True):
    """
    Pebble-only parallel executor.
    - method: 'Process' or 'Thread'
    - args: iterable of items; each item can be a single arg or a tuple for *args
    - timeout: per-task timeout (sec). For ProcessPool it is enforced at schedule(),
               for ThreadPool it's enforced at result().
    Returns: (results, failed_indices)
    """
    def _is_importable_callable(f):
        mod = getattr(f, "__module__", None)
        qn  = getattr(f, "__qualname__", "")
        # Importable means: defined in a real module, not a cell/local
        return bool(mod and mod not in ("__main__", "builtins") and "<locals>" not in qn)

    args_list = list(args)
    n = len(args_list)
    results = [None] * n if return_value else []
    failed_indices = []

    # Pick pool type
    use_process = method.lower().startswith('p')
    is_windows = sys.platform.startswith('win')

    if use_process and is_windows and not _is_importable_callable(func):
        if verbose:
            raise RuntimeError(
                "parallel_executor: For method='Process' the worker must be importable "
                "(module-level function or @staticmethod in a real module). "
                "In notebooks, either move the function to a .py or use method='Thread'."
            )

    Pool = ProcessPool if use_process else ThreadPool

    # Progress bar
    pbar = None
    if bar:
        if isinstance(bar, int):
            pbar = tqdm(total=n + bar); pbar.update(bar)
        else:
            pbar = tqdm(total=n)

    def _record_failure(ind, exc, arg):
        failed_indices.append(ind)
        print(f'\nExecution failed for args:\n {arg}')
        if verbose:
            tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            print(f'Error details:\n{tb}\n')
        else:
            print(f'Exception: {exc}\n')

    futures = {}
    try:
        with Pool(max_workers=max_workers) as pool:
            # Submit
            for i, arg in enumerate(args_list):
                try:
                    call_args = arg if isinstance(arg, (tuple, list)) else (arg,)
                    if use_process:
                        fut = pool.schedule(func, args=call_args, timeout=timeout)
                    else:
                        fut = pool.schedule(func, args=call_args)  # enforce timeout at .result()
                    futures[fut] = i
                except Exception as exc:
                    _record_failure(i, exc, arg)
                    if pbar: pbar.update(1)

            # Collect as they finish
            for fut in as_completed(list(futures.keys())):
                ind = futures[fut]
                try:
                    if use_process or timeout is None:
                        val = fut.result()
                    else:
                        val = fut.result(timeout=timeout)  # ThreadPool per-task timeout
                    if return_value:
                        results[ind] = val
                except CFTimeoutError:
                    print(f'\nExecution timed out for args:\n {args_list[ind]}')
                    failed_indices.append(ind)
                except Exception as exc:
                    _record_failure(ind, exc, args_list[ind])
                finally:
                    if pbar: pbar.update(1)

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt caught, canceling remaining operations...")
        # Exiting the 'with Pool' context will shut down workers.

    finally:
        if pbar:
            pbar.close()

    return results, failed_indices

# from test import *

# import random
# import time

# def delayed_square(x):
#     """Test function that squares a number after a delay"""
#     time.sleep(random.uniform(0.5, 0.8))  # Simulate random work duration
#     return x * x

# if __name__ == "__main__":
#     # Test data
#     test_numbers = list(range(10))
    
#     print("\nTesting with ThreadPool:")
#     results, failed = parallel_executor(delayed_square, test_numbers, method='Thread', return_value=True, timeout = 0.1)
#     print(f"Thread results: {results}")
#     print(f"Thread failed indices: {failed}")
    
    
#     print("Testing with ProcessPool:")
#     results, failed = parallel_executor(delayed_square, test_numbers, method='Process', return_value=True, timeout = 0.7)
#     print(f"Process results: {results}")
#     print(f"Process failed indices: {failed}")