import concurrent.futures

import pylateral.exceptions


class PoolTimeoutError(pylateral.exceptions.PylateralError, TimeoutError):
    pass


def wait_for_futures(futures, timeout=None):
    done, not_done = concurrent.futures.wait(
        futures,
        timeout=timeout,
        return_when=concurrent.futures.FIRST_EXCEPTION,
    )

    for future in done:
        if not future.cancelled() and future.exception() is not None:
            if not_done:
                # If there are some calls that haven't finished, cancel and recreate
                # the thread pool. Otherwise we may have a thread running forever
                # blocking parallel calls.
                for nd in not_done:
                    nd.cancel()
            raise future.exception()

    if not_done:
        for future in not_done:
            future.cancel()
        raise PoolTimeoutError()

    results = []

    for future in concurrent.futures.as_completed(futures):
        results.append(future.result())

    return results


def first(*args):
    for arg in args:
        if arg:
            return arg
    return None


def safe_int(x):
    if x:
        return int(x)
    else:
        return x


def safe_bool(x):
    if isinstance(x, str):  # Remember that bool('False') is truthy
        return x.lower() != 'false'
    elif x is not None:
        return bool(x)
    else:
        return x
