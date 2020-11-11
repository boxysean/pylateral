### Using return values

*pylateral* tasks should generally avoid returning values; tasks should largely do end-to-end processing and "push forward" results where possible (e.g., store results in a database, call an API). That's because return values from *pylateral* task methods cannot be used by the main thread directly because they are not available at the method call time as one might expect.

    import pylateral

    @pylateral.task
    def favorite_animal():
        return "cats"
    
    with pylateral.task_pool():
        print(favorite_animal())  # raises UnexpectedReturnValueError()

The return values can be accessed, but only if explicitly specified in the decorator. Since accessing the return values of tasks is not as intuitive as the programmer might initially hope, this design forces programmers to be explicit with what they are asking for.

    import random
    import time
    
    import pylateral

    @pylateral.task(has_return_value=True)
    def animal_speak(animal):
        time.sleep(random.random())
        if animal == "cats":
            return "meow"
        elif animal == "dogs":
            return "woof"
    
    with pylateral.task_pool() as pool:
        animal_speak("cats")
        animal_speak("dogs")
    
    print(pool.return_values())  # either '["meow", "woof"]' or '["woof", "meow"]'

Only a list of return values is returned, in no guaranteed order, and without relation to the task method arguments. This feature is intended to be used to collect result details of the task, similar to the reduce step in [MapReduce](https://en.wikipedia.org/wiki/MapReduce).

### Working with nested tasks

*pylateral* task methods can call other task methods without blocking the task thread execution. This is useful when traversing APIs.

    import pylateral
    import requests

    @pylateral.task
    def print_post_title(post_id):
        post = requests.get(f"https://jsonplaceholder.typicode.com/posts/{post_id}").json()
        print(post['title'])
    
    @pylateral.task
    def fetch_posts_by_user(user_id):
        """This task method calls other task methods."""
        posts = requests.get(f"https://jsonplaceholder.typicode.com/posts?userId={user_id}").json()
        for post in posts:
            fetch_post(post['id'])

    with pylateral.task_pool() as pool:
        users = requests.get("https://jsonplaceholder.typicode.com/users").json()
        for user in users:
            fetch_posts_by_user(user['id'])

### Waiting for tasks

The main thread does not wait for *pylateral* tasks to complete, but sometimes we may want the main thread to wait. 

    import random
    import time

    import pylateral

    @pylateral.task
    def parallel_print(value):
        time.sleep(random.random())
        print(value)
    
    with pylateral.task_pool():
        for i in range(10):
            parallel_print(i)  # Print the numbers...
        
        pylateral.join()  # ...then...
        
        for i in range(10):
            parallel_print(chr(ord('A') + i))  # ...print the letters.

Sometimes it's preferable for the main thread to block when the *pylateral* thread pool is fully saturated with work. In that case, use the `block_when_saturated` flag on the `task_pool`.

### Handling errors

If any exception from a threaded running tasks is uncaught, the `task_pool` will halt all currently running tasks and the main thread will re-raise the exception as soon as it can.

    import pylateral

    @pylateral.task
    def bad_task():
        raise Exception("Bad Task!")
    
    with pylateral.task_pool():
        bad_task()  # raises Exception("Bad Task!") in the main thread

To avoid one error from halting all *pylateral* execution, errors must be handled as they are raised.

### Changing the number of threads

You can hard-code the number of threads, you can use an environment variable to change the number of threads, or it will default to using the number 

The number of threads you choose to use depends on how much concurrency you want from *pylateral*. Usually this is determined by how much compute resources you have (CPU and memory), or how much concurrency any remote connection you make can handle (concurrent DB connections, API connections).

*pylateral* can be safely disabled with the flip of an environment variable switch: `PYLATERAL_ENABLED=false`. Your code will run serially and pretend like *pylateral* calls don't happen.

### Thread-local storage

It's common to re-use connections in multi-threaded code. Too many allocated connections may exhaust the OS's resources ("too many open files" is a common error here); too few connections may create [race conditions](https://en.wikipedia.org/wiki/Race_condition#Software) and present errors related to [thread safety](https://en.wikipedia.org/wiki/Thread_safety).

A good rule of thumb is one connection per thread. For example, [boto3 suggests](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html?highlight=multithreading#multithreading-multiprocessing) that you have one resource per thread and process. Similarly, [the developers of google-cloud-python think](https://github.com/googleapis/google-cloud-python/issues/3272) their library is thread-safe. (But is it?)

*pylateral* provides a method decorator to create thread-local objects. This approach ensures that each thread re-uses the same client each time it's requested, and no other thread has access to that client.

    import random
    
    import pylateral

    class MagicNumberClient:
        def __init__(self, magic_number):
            self._magic_number = magic_number
        
        def get_magic_number(self):
            return self._magic_number

    @pylateral.cache_result(scope=pylateral.CacheScopes.THREAD)
    def get_magic_number_client():
        return MagicNumberClient(random.random())
    
    @pylateral.task
    def print_magic_number():
        client = get_magic_number_client()
        print(client.get_magic_number())
    
    with pylateral.task_pool(max_workers=2):
        for _ in range(10):
            print_magic_number()  # This will print at most 2 different numbers

Another way is to use [`threading.local()`](https://docs.python.org/3/library/threading.html#thread-local-data), which is compatible with *pylateral*.
