"""
Parallel helpers.

Q: "Why do serial when you can do parallel?"
Possible A: "Because of unintended consequences!"
"""


from .cache import cache_result, CacheScopes
from .task_module import task
from .task_group_module import task_group
from .task_pool_module import join, task_pool, TaskPoolAlreadyAllocated
