import pytest

import pylateral
import pylateral.task_module


def test_task_unexpected_result():
    @pylateral.task
    def my_func():
        return "something"

    with pytest.raises(pylateral.task_module.UnexpectedReturnValue):
        my_func()


def test_task_has_return_value():
    @pylateral.task(has_return_value=True)
    def my_func():
        return "something"

    result = my_func()

    assert result is None
