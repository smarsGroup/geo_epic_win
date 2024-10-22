import signal
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

def _run_with_timeout(func, timeout, *args, **kwargs):
    """
    Executes a function with a timeout using signals (not recommended).

    Args:
      func: The function to execute.
      timeout: The maximum execution time in seconds.
      *args: Arguments to pass to the function.
      **kwargs: Keyword arguments to pass to the function.

    Returns:
      The result of the function if it finishes within the timeout.

    Raises:
      TimeoutError: If the function execution exceeds the timeout.
    """
    def handler(signum, frame):
        raise TimeoutError("Execution timed out")

    original_signal = signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)

    try:
        result = func(*args, **kwargs)
    finally:
        signal.signal(signal.SIGALRM, original_signal)
        signal.alarm(0)  # Cancel any pending alarms

    return result
    
    
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
    PoolExecutor = {'Process': ProcessPoolExecutor, 'Thread': ThreadPoolExecutor}[method]
    
    with PoolExecutor(max_workers=max_workers) as executor:
        if bar: 
            if isinstance(bar, int):
                pbar = tqdm(total=len(args) + bar)
                pbar.update(bar)
            else:
                pbar = tqdm(total=len(args))

        if method == 'Process' and timeout is not None:
            futures = {executor.submit(_run_with_timeout, func, timeout, arg): i for i, arg in enumerate(args)}
        else:
            futures = {executor.submit(func, arg): i for i, arg in enumerate(args)}
        
        try:
            import traceback

            for future in as_completed(futures):
                ind = futures[future]
                exc = future.exception()
                if exc is not None:
                    print(f'\nExecution failed for args:\n {args[ind]}')
                    if verbose_errors:
                        tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
                        print(f'Error details:\n{tb}\n')
                    else:
                        print(f'Exception: {exc}\n')
                    failed_indices.append(ind)
                elif return_value:
                    results[ind] = future.result()
                if bar: pbar.update(1)
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt caught, canceling remaining operations...")
            for future in futures.keys():
                future.cancel()
        finally:
            if bar: pbar.close()
    
    return results, failed_indices
