import functools
import logging
import typing

import pylateral.exceptions
import pylateral.task_pool_module
import pylateral.task_group_module


class UnexpectedReturnValue(pylateral.exceptions.PylateralError):
    """
    Embarrassingly parallel functions should not return values unless
    explicitly specified with `@pylateral.task(has_return_value=True)`.
    """


def _record_result_wrapper(
        func: typing.Callable,
        has_return_value: bool,
        task_pool: pylateral.task_pool_module.TaskPool,
        task_group: pylateral.task_group_module.task_group,
        *args,
        **kwargs,
) -> None:
    """
    Records the function's result on the active join_context.

    If no join_context is present and a value is returned, raises an
    UnexpectedReturnValue exception.
    """
    result = func(*args, **kwargs)

    if has_return_value:
        if task_group:
            task_group.add_result(result)
        elif task_pool:
            task_pool.add_result(result)
    elif result is not None:
        raise UnexpectedReturnValue(
            f"Function {func.__name__} returned value where None should be returned."
        )


def _submit_to_pool(
        func: typing.Callable,
        has_return_value: bool,
        *args,
        **kwargs
) -> None:
    """
    Puts the function call onto the parallel pool.

    If there is no parallel pool (either by design or because the pool
    has been disabled), then run the function call in serial.
    """
    task_pool = pylateral.task_pool_module.get_current_task_pool()
    task_group = pylateral.task_group_module.get_current_task_group()

    # Wrap the provided function in the _record_result function to
    # handle the result appropriately.
    func = functools.partial(_record_result_wrapper, func, has_return_value, task_pool, task_group)

    if task_pool:
        # There's a pool, throw the function on the pool
        logging.debug({
            'msg': 'Submitting to pool',
            'func': func,
            'args': args,
            'kwargs': kwargs,
        })

        future = task_pool.submit(func, *args, **kwargs)

        if task_group:
            task_group.add_future(future)
    else:
        # No pool, run the function in serial
        func(*args, **kwargs)


def task(*dargs, **dkwargs):
    """
    Marks a function as an embarrassingly parallel function. All such
    functions can be run by the provided `context.threadpool`, if one
    exists.

    **Important** A function is embarrassingly parallel if the return
    value is not needed by the outer code. To prevent any mis-use,
    any return values in single-threaded mode throws an exception.

    It's best to decorate functions that are I/O bound (e.g., API call
    followed by a DB insert).
    """
    # Support both @pylateral.task and @pylateral.task()
    if len(dargs) == 1 and callable(dargs[0]):  # Decorator without params
        def wrap_simple(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                _submit_to_pool(func, False, *args, **kwargs)
            return wrapper
        return wrap_simple(dargs[0])
    else:
        def wrap(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                _submit_to_pool(func, dkwargs.get('has_return_value'), *args, **kwargs)
            return wrapper
        return wrap
