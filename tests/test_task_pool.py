import datetime
import time

import pytest

import pylateral
import pylateral.util


def test_task_pool_is_parallel():
    """This test will time-out if it's not truly parallel!"""
    call_counter = 0

    @pylateral.task
    def call_it():
        nonlocal call_counter
        time.sleep(0.2)
        call_counter += 1

    with pylateral.task_pool(max_workers=10, timeout=1):
        for _ in range(10):
            call_it()

    assert call_counter == 10


def test_task_pool_timeout_error():
    @pylateral.task
    def call_it():
        time.sleep(2)

    with pytest.raises(pylateral.util.PoolTimeoutError):
        with pylateral.task_pool(max_workers=1, timeout=1):
            call_it()

    # Clean up worked properly
    assert not pylateral.task_pool_module.get_current_task_pool()


def test_task_pool_block_when_saturated():
    @pylateral.task()
    def call_it():
        time.sleep(1)

    with pylateral.task_pool(max_workers=1, block_when_saturated=True):
        t1 = datetime.datetime.now().replace(microsecond=0)
        call_it()
        t2 = datetime.datetime.now().replace(microsecond=0)
        call_it()

    # t1 and t2 occur in different seconds
    assert t1 != t2


def test_task_pool_multiple_pools_raises_error():
    with pytest.raises(pylateral.TaskPoolAlreadyAllocated):
        with pylateral.task_pool():
            with pylateral.task_pool():
                pass


def test_join_function():
    """
    This test confirms that the assertion of val
    doesn't occur until set_true has finished.
    """
    val = False

    @pylateral.task
    def set_true():
        nonlocal val

        time.sleep(1)
        val = True

    with pylateral.task_pool():
        set_true()
        pylateral.join()
        assert val
