import contextlib
import os
import threading
import typing

import pylateral.exceptions

from .util import wait_for_futures


class TaskGroupAlreadyExists(pylateral.exceptions.PylateralError):
    """
    Attempted to use a nested join() context manager in the
    same thread.
    """


class TaskGroup:
    _active_task_groups = {}

    @classmethod
    def get_current_task_group(cls):
        return cls._active_task_groups.get(threading.current_thread())

    @classmethod
    def unset_current_task_group(cls):
        del cls._active_task_groups[threading.current_thread()]

    @classmethod
    def create_task_group(cls):
        if cls.get_current_task_group():
            raise TaskGroupAlreadyExists(
                "Attempted to nest task_group() context managers in the same thread"
            )

        cls._active_task_groups[threading.current_thread()] = TaskGroup()
        return cls._active_task_groups[threading.current_thread()]

    def __init__(self):
        self._futures = []
        self._results = []

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

    def add_result(self, result):
        self._results.append(result)

    def add_future(self, future):
        self._futures.append(future)

    def join(self):
        wait_for_futures(self._futures)


@contextlib.contextmanager
def task_group():
    """
    Waits for task methods within the context manager to complete
    before continuing.
    """
    if not pylateral.util.safe_bool(os.environ.get('PYLATERAL_ENABLED', True)):
        yield
        return

    current_task_group = TaskGroup.create_task_group()

    try:
        yield current_task_group
        current_task_group.join()
    finally:
        TaskGroup.unset_current_task_group()


def get_current_task_group() -> typing.Optional[task_group]:
    return TaskGroup.get_current_task_group()
