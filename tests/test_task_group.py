import time

import pylateral


def test_task_group():
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
        with pylateral.task_group():
            set_true()
        assert val


def test_task_group_results():
    @pylateral.task(has_return_value=True)
    def fn(x):
        return x+1

    vals = list(range(10))

    with pylateral.task_pool():
        with pylateral.task_group() as task_group:
            for i in vals:
                fn(i)

        assert sorted(task_group.results) == [x+1 for x in vals]


def test_task_group_results_are_independent():
    @pylateral.task(has_return_value=True)
    def fn(x):
        return x+1

    with pylateral.task_pool():
        with pylateral.task_group() as task_group_1:
            fn(1)

        with pylateral.task_group() as task_group_2:
            fn(2)

        assert task_group_1.results == [2]
        assert task_group_2.results == [3]


def test_task_group_works_without_task_pool():
    @pylateral.task(has_return_value=True)
    def fn(x):
        return x+1

    with pylateral.task_group() as task_group:
        fn(1)

    assert task_group.results == [2]
