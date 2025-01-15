from tqdm import tqdm
from pebble import ProcessPool, ThreadPool
from concurrent.futures import TimeoutError

def parallel_executor(func, args, method='Process', max_workers=10, return_value=False, bar=True, timeout=None, verbose_errors=False):
    """
    Executes a function across multiple processes and collects the results.

    Args:
        func: The function to execute.
        method: string as Process or Thread.
        args: An iterable of arguments to pass to the function.
        max_workers: The maximum number of processes to use.
        return_value: A boolean indicating whether the function returns a value.
        timeout: Number of seconds to wait for a process to complete
        verbose_errors: A boolean indicating whether to print full error traceback or just the exception

    Returns:
        results: If return_value is True, a list of results from the function executions sorted according to 
                If return_value is False, an empty list is returned.
        failed_indices: A list of indices of arguments for which the function execution failed.
    """
    failed_indices = []
    results = [None] * len(args) if return_value else []
    Pool = ProcessPool if method == 'Process' else ThreadPool

    with Pool(max_workers=max_workers) as pool:
        if bar:
            if isinstance(bar, int):
                pbar = tqdm(total=len(args) + bar)
                pbar.update(bar)
            else:
                pbar = tqdm(total=len(args))

        futures = {}
        for i, arg in enumerate(args):
            if method == 'Process':
                future = pool.schedule(func, args=(arg,), timeout=timeout)
            else:
                future = pool.schedule(func, args=(arg,))
            futures[future] = i
        
        try:
            import traceback

            for future in futures:
                ind = futures[future]
                try:
                    if return_value:
                        results[ind] = future.result()
                except TimeoutError:
                    print(f'\nExecution timed out for args:\n {args[ind]}')
                    failed_indices.append(ind)
                except Exception as exc:
                    print(f'\nExecution failed for args:\n {args[ind]}')
                    if verbose_errors:
                        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                        print(f'Error details:\n{tb}\n')
                    else:
                        print(f'Exception: {exc}\n')
                    failed_indices.append(ind)
                if bar:
                    pbar.update(1)

        except KeyboardInterrupt:
            print("\nKeyboardInterrupt caught, canceling remaining operations...")
            pool.stop()
            pool.join()
        finally:
            if bar:
                pbar.close()
    
    return results, failed_indices

# import random

# def delayed_square(x):
#     """Test function that squares a number after a delay"""
#     time.sleep(random.uniform(0.05, 0.08))  # Simulate random work duration
#     return x * x

# if __name__ == "__main__":
#     # Test data
#     test_numbers = list(range(10))
    
#     print("\nTesting with ThreadPool:")
#     results, failed = parallel_executor(delayed_square, test_numbers, method='Thread', return_value=True, timeout = 0.1)
#     print(f"Thread results: {results}")
#     print(f"Thread failed indices: {failed}")
    
    
#     print("Testing with ProcessPool:")
#     results, failed = parallel_executor(delayed_square, test_numbers, method='Process', return_value=True, timeout = 0.1)
#     print(f"Process results: {results}")
#     print(f"Process failed indices: {failed}")