import threading
import time

import pylateral


def test_thread_cache_with_task_pool():
    resource_list = []
    thread_list = []

    @pylateral.task
    def append_resource():
        time.sleep(0.5)
        resource_list.append(resource_factory())
        thread_list.append(threading.current_thread())

    @pylateral.cache_result(scope=pylateral.CacheScopes.THREAD)
    def resource_factory():
        return object()

    with pylateral.task_pool(max_workers=2):
        for _ in range(2):
            append_resource()

    assert len(thread_list) == 2
    assert thread_list[0] != thread_list[1]  # They are different!
    assert len(resource_list) == 2
    assert resource_list[0] != resource_list[1]  # They are different!


def test_thread_cache_without_threadpool():
    @pylateral.cache_result(scope=pylateral.CacheScopes.THREAD)
    def resource_factory(_):
        return object()

    # They are the same since they are stored at the main thread level
    assert resource_factory('spot') == resource_factory('spot')


def test_cache_clear():
    @pylateral.cache_result(scope=pylateral.CacheScopes.THREAD)
    def resource_factory(*, pet_breed):
        return object()

    first_object = resource_factory(pet_breed='cat')
    second_object = resource_factory(pet_breed='cat')
    resource_factory.clear_cache()
    third_object = resource_factory(pet_breed='cat')

    assert first_object == second_object
    assert first_object != third_object
