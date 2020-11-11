pylateral
=========

**Simple multi-threaded task processing in python**

Example
-------

    import urllib.request

    import pylateral
    
    @pylateral.task
    def request_and_print(url):
        response = urllib.request.urlopen(url)
        print(response.read())
        
    URLS = [
        "https://www.nytimes.com/",
        "https://www.cnn.com/",
        "https://europe.wsj.com/",
        "https://www.bbc.co.uk/",
        "https://some-made-up-domain.com/",
    ]

    with pylateral.task_pool():
        for url in URLS:
            request_and_print(url)

    print("Complete!")

### What's going on here

-  `def request_and_print(url)` is a *pylateral* task that, when called, is run on a task pool thread rather than on the main thread.

- `with pylateral.task_pool()` allocates threads and a task pool. The context manager may exit only when there are no remaining tasks.

- Each call to `request_and_print(url)` adds that task to the task pool. Meanwhile, the main thread continues execution.

- The `Complete!` statement is printed after all the `request_and_print()` task invocations are complete by the pool threads.

To learn more about the features of *pylateral*, check out the [usage](usage.md) section.

Background
----------

A couple of years ago, I inherited my company's codebase to get data into our data warehouse using an ELT approach (extract-and-loads done in python, transforms done in [dbt](https://www.getdbt.com/)/SQL). The codebase has dozens of python scripts to integrate first-party and third-party data from databases, FTPs, and APIs, which are run on a scheduler (typically daily or hourly). The scripts I inherited were single-threaded procedural scripts, looking like glue code, and spending most of their time in network I/O. This got my company pretty far!

As my team and I added more and more integrations with more and more data, we wanted to have faster and faster scripts to reduce our dev cycles and reduce our multi-hour nightly jobs to minutes. Because our scripts were network-bound, multi-threading was a good way to accomplish this, and so I looked into `concurrent.futures` and `asyncio`, but I decided against these options because:

1. It wasn't immediately apparently how to adapt my codebase to use these libraries without either some fundamental changes to our execution platform and/or reworking of our scripts from the ground up and/or adding significant lines of multi-threading code to each script.

2. I believe the procedural style glue code we have is quite easy to comprehend, which I think has a positive impact on the scale of supporting a wide-variety of programs.

And so, I designed *pylateral*, a simple interface to `concurrent.futures.ThreadPoolExecutor` for extract-and-load workloads. The design considerations of this interface include:

- The usage is minimally-invasive to the original un-threaded approach of my company's codebase. (And so, teaching the library has been fairly straightforward despite the multi-threaded paradigm shift.)

- The `@pylateral.task` decorator should be used to encapsulate a homogeneous method accepting different parameters. The contents of the method should be primarily I/O to achieve the concurrency gains of python multi-threading.

- If no `pylateral.pool` context manager has been entered, or if it has been disabled by an environment variable, the `@pylateral.task` decorator does nothing (and the code runs serially).

- While it's possible to return a value from a `@pylateral.task` method, I encourage my team to use the decorator to start-and-complete work; think of writing "embarrassingly parallel" methods that can be "mapped".

### Why not other libraries?

I think that *pylateral* meets an unmet need in python's concurrency eco-system: a simple way to gain the benefits of multi-threading without radically transforming either mindset or codebase.

That said, I don't think *pylateral* is a [silver bullet](https://en.wikipedia.org/wiki/No_Silver_Bullet). See my [comparison](comparison.md) of *pylateral* against other concurrency offerings.
