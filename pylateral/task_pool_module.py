import concurrent.futures
import contextlib
import logging
import os
import time

import pylateral.exceptions
import pylateral.util


class TaskPoolAlreadyAllocated(pylateral.exceptions.PylateralError):
    pass


class TaskPool:
    """
    Process-global

    TODO: fill in
    """

    _current_task_pool = None

    @classmethod
    def get_task_pool(cls):
        return cls._current_task_pool

    @classmethod
    def unset_current_task_pool(cls):
        cls._current_task_pool = None

    @classmethod
    def create_task_pool(cls, max_workers, timeout, block_when_saturated):
        if cls._current_task_pool:
            raise TaskPoolAlreadyAllocated()

        cls._current_task_pool = cls(
            max_workers=max_workers,
            timeout=timeout,
            block_when_saturated=block_when_saturated,
        )

        return cls._current_task_pool

    @classmethod
    def join(cls):
        """
        Blocks execution until all work on the current task pool is
        complete.

        If there is no task pool, then nothing happens!
        """
        if cls._current_task_pool:
            cls._current_task_pool._join()

    def __init__(self, max_workers, timeout, block_when_saturated):
        """
        Do not use directly!

        TODO: fill-in

        :param max_workers:
        :param timeout:
        :param block_when_saturated:
        """
        self._max_workers = pylateral.util.first(
            max_workers,
            pylateral.util.safe_int(os.environ.get('PYLATERAL_WORKERS')),
            # Formula from concurrent.futures.ThreadPoolExecutor constructor
            (os.cpu_count() or 1) * 5,
        )

        if self._max_workers <= 0:
            raise ValueError("Max workers must be greater than 0")

        self._timeout = pylateral.util.first(
            timeout,
            pylateral.util.safe_int(os.environ.get('PYLATERAL_TIMEOUT'))
        )

        self._block_when_saturated = pylateral.util.first(
            block_when_saturated,
            pylateral.util.safe_bool(os.environ.get('PYLATERAL_BLOCK_WHEN_SATURATED')),
            False,
        )

        logging.info("Creating ThreadPoolExecutor with %s max_workers", self._max_workers)

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix='pylateral-',
        )

        self._futures = []
        self._results = []

    def _join(self):
        pylateral.util.wait_for_futures(self._futures, timeout=self._timeout)

    @property
    def _active_futures(self):
        return len([
            future
            for future in self._futures
            if future.running()
        ])

    @property
    def is_fully_saturated(self):
        return self._active_futures >= self._max_workers

    def submit(self, function, *args, **kwargs):
        future = self._executor.submit(function, *args, **kwargs)
        self._futures.append(future)

        if self._block_when_saturated:
            first = True

            while self.is_fully_saturated:
                if first:
                    logging.info("Thread pool is fully saturated, pausing main thread "
                                 "execution")
                    first = False
                time.sleep(1)

            logging.info("Continuing threadpool")

        return future

    def add_result(self, result):
        self._results.append(result)

    @property
    def results(self):
        """
        A list of return values of the embarrassingly parallel
        functions ran within the join context.

        The list is unsorted and has no reference to the function
        parameters; it's meant to be used like a "reduce" step in
        map-reduce.
        """
        return self._results


@contextlib.contextmanager
def task_pool(max_workers=None, timeout=None, block_when_saturated=False):
    """
    Use this context manager to allocate a thread pool that all calls
    to functions marked as @threadable will be sent to for execution.
    These will be done in parallel with no guarantees to timing and
    whose return values cannot be used.

    Do not enter more than one thread pool, just use the one that's
    allocated!

    :param max_workers: number of maximum threads / workers that can
    run in parallel
    :param timeout: the number of seconds to wait before canceling
    all threads
    :param block_when_saturated: When true, the threadpool blocks the
    main execution thread while the number of tasks reaches the number
    of max_workers.
    """
    if not pylateral.util.safe_bool(os.environ.get('PYLATERAL_ENABLED', True)):
        logging.info("pylateral task pool turned off, running everything in main thread")
        yield
        return

    current_thread_pool = TaskPool.create_task_pool(
        max_workers=max_workers,
        timeout=timeout,
        block_when_saturated=block_when_saturated,
    )

    try:
        yield current_thread_pool
        current_thread_pool.join()
    finally:
        TaskPool.unset_current_task_pool()


def join() -> None:
    TaskPool.join()


def get_current_task_pool() -> TaskPool:
    return TaskPool.get_task_pool()
