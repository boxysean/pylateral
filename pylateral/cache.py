"""
Scoped caching of function call results for pylateral.

Implements thread-scoped caching to support caching of resource factory
functions we see throughout the codebase.

Consider using other caching helpers such as `functools.lru_cache`
built for other use-cases, such as fixed-size memory caching.
"""

import collections
import enum
import functools
import threading
import typing


class CacheScopes(int, enum.Enum):
    THREAD = 1
    PROCESS = 2


class FunctionCacheStore:
    """
    Storage for results of function calls.
    """
    def __init__(self):
        self._store = collections.defaultdict(lambda: collections.defaultdict(dict))

    @staticmethod
    def _make_store_key(args: tuple, kwargs: dict) -> tuple:
        return args, tuple(sorted(kwargs.items()))

    @property
    def scope(self) -> typing.Any:
        """
        The scope of storage, which is part of the underlying storage
        dictionary key. Collisions of the scope means that the storage
        space is shared.

        By default, the scope is the CacheStore object itself; so it
        acts like a basic dictionary. Override this in subclasses to
        have more complex collision logic.

        :returns: A hashable object that can be tested for equality.
        """
        return self

    def has(self, function: typing.Callable, args: tuple, kwargs: dict) -> bool:
        return self._make_store_key(args, kwargs) in self._store[self.scope][function]

    def get(self, function: typing.Callable, args: tuple, kwargs: dict) -> typing.Any:
        return self._store[self.scope][function][self._make_store_key(args, kwargs)]

    def store(self, function: typing.Callable, args: tuple, kwargs: dict,
              resource: typing.Any) -> None:
        self._store[self.scope][function][self._make_store_key(args, kwargs)] = resource

    def clear_if_exists(self, function: typing.Callable) -> None:
        if function in self._store[self.scope]:
            del self._store[self.scope][function]


class ThreadScopedFunctionCacheStore(FunctionCacheStore):
    """
    Thread-scoped storage for results of function calls.
    """
    @property
    def scope(self):
        return threading.current_thread()


class ProcessScopedFunctionCacheStore(FunctionCacheStore):
    """
    Thread-scoped storage for results of function calls.
    """
    @property
    def scope(self):
        """This cache key will be hit by all."""
        return 'process-wide'


_THREAD_SCOPED_FUNCTION_CACHE = ThreadScopedFunctionCacheStore()
_PROCESS_SCOPED_FUNCTION_CACHE = ProcessScopedFunctionCacheStore()


def cache_result(scope: CacheScopes):
    """
    A decorator for indefinitely caching the outputs of a function, per
    arguments provided and per thread.

    This works particularly well on factory methods that return
    resources that can be re-used by the same thread.

    For example, suppose we wanted to fetch our implementation of the
    pets.com API using the method `my_api_factory` in two threads:

    Thread A:

        first_pets_api = my_api_factory("http://pets.com")
        ...
        # Do stuff, go to another function...
        ...
        second_pets_api = my_api_factory("http://pets.com")

    Thread B:

        third_pets_api = my_api_factory("http://pets.com")

    Here are facts about these objects:

    - The `first_pets_api` and `second_pets_api` objects are the same.
    - The `first_pets_api` object is different from `third_pets_api`.

    When not to use:

    - When the underlying function can return differing values with the
      same arguments.
    - When you want to limit the cache size. (Consider using
      `functools.lru_cache` instead.)
    """
    def wrap(func):
        if scope == CacheScopes.THREAD:
            store = _THREAD_SCOPED_FUNCTION_CACHE
        elif scope == CacheScopes.PROCESS:
            store = _PROCESS_SCOPED_FUNCTION_CACHE
        else:
            raise ValueError(f'Unexpected cache scope "{scope}" provided')

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not store.has(func, args, kwargs):
                resource = func(*args, **kwargs)
                store.store(func, args, kwargs, resource)
                return resource
            else:
                return store.get(func, args, kwargs)

        # Attach a `clear_cache` function.
        wrapper.clear_cache = lambda: store.clear_if_exists(func)
        return wrapper

    return wrap
