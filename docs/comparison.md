Comparison with other python libraries
======================================

There's lots of way to skin the threading cat! 

### When to use *pylateral*

- Your workload is network-bound and/or IO-bound (e.g., API calls, database queries, read/write to FTP, read/write to files).

- Your workload can be run [embarrassingly parallel](https://en.wikipedia.org/wiki/Embarrassingly_parallel).

- You are writing a script or prototype that isn't very large nor complex.

### When not to use *pylateral*

- Your workload is CPU-bound and blocked by the [Global Interpreter Lock](https://en.wikipedia.org/wiki/CPython#Design). *python* threading will not help speed up your workload, consider using [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) or [concurrent.futures.ProcessPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor) instead.

- The complexity of your program would benefit from thinking about it in terms of [futures and promises](https://en.wikipedia.org/wiki/Futures_and_promises). Consider using [asyncio](https://docs.python.org/3/library/asyncio.html) or [concurrent.futures.ThreadPoolExecutors](https://docs.python.org/3/library/concurrent.futures.html) instead.

- When you want to have tighter controls around the lifecycle of your thread. Consider using [threading](https://docs.python.org/3/library/threading.html) instead.

- For larger workloads, consider using [dask.distributed](https://distributed.dask.org/en/latest/#), [Airflow](https://airflow.apache.org/), [Dagster](https://github.com/dagster-io/dagster/) or [Prefect](https://www.prefect.io/) to perform work across many nodes.

- You would benefit from a web UI for viewing and interacting with your tasks. For that, consider using [Airflow](https://airflow.apache.org/) or [Prefect](https://www.prefect.io/).

Feature comparison
------------------

| Feature                            | pylateral | [asyncio](https://docs.python.org/3/library/asyncio.html) | [concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)       | [multiprocessing](https://docs.python.org/3/library/multiprocessing.html) | [threading](https://docs.python.org/3/library/threading.html) |
| ---------------------------------- | --------- | ------- | ------------------------ | --------------- | --------- |
| Easy to adapt single-threaded code | ✅         | ❌      | ❌                       | ❌              | ❌        |
| [Simple nested tasks](usage.md#working-with-nested-tasks)                | ✅         | ✅      | ❌                       | ❌              | ❌        |
| Concurrent IO-bound workloads      | ✅         | ✅      | ✅                       | ✅              | ✅        |
| Concurrent CPU-bound workloads     | ❌         | ❌      | ✅ (Process Pool)        | ✅              | ❌        |
| Flexibility in using return values | ❌         | ✅      | ✅                       | ❌              | ❌        |

Code comparison
----------

[PEP-3148 -- futures - execute computations asynchronously](https://www.python.org/dev/peps/pep-3148/#id13) introduces `concurrent.futures` and illustrates it by example. Here I show that example in *pylateral*, stacked up against the main threading libraries offered in python.

### `asyncio`

```python
import aiohttp
import asyncio
import sqlite3

URLS = [
    'http://www.foxnews.com/',
    'http://www.cnn.com/',
    'http://europe.wsj.com/',
    'http://www.bbc.co.uk/',
    'http://some-made-up-domain.com/',
]

async def extract_and_load(url, timeout=30):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as response:
                web_result = await response.text()
                print(f"{url} is {len(web_result)} bytes")

                with sqlite3.connect('example.db') as conn, conn as cursor:
                    cursor.execute('CREATE TABLE IF NOT EXISTS web_results (url text, length int);')
                    cursor.execute('INSERT INTO web_results VALUES (?, ?)', (url, len(web_result)))
    except Exception as e:
        print(f"{url} generated an exception: {e}")
        return False
    else:
        return True

async def main():
    succeeded = await asyncio.gather(*[
        extract_and_load(url)
        for url in URLS
    ])

    print(f"Successfully completed {sum(1 for result in succeeded if result)}")

asyncio.run(main())
```

### `concurrent.futures.ThreadPoolExecutor`

```python
import concurrent.futures
import requests
import sqlite3

URLS = [
    'http://www.foxnews.com/',
    'http://www.cnn.com/',
    'http://europe.wsj.com/',
    'http://www.bbc.co.uk/',
    'http://some-made-up-domain.com/',
]

def extract_and_load(url, timeout=30):
    try:
        web_result = requests.get(url, timeout=timeout).text
        print(f"{url} is {len(web_result)} bytes")

        with sqlite3.connect('example.db') as conn, conn as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS web_results (url text, length int);')
            cursor.execute('INSERT INTO web_results VALUES (?, ?)', (url, len(web_result)))
    except Exception as e:
        print(f"{url} generated an exception: {e}")
        return False
    else:
        return True

succeeded = []

with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_url = dict(
        (executor.submit(extract_and_load, url), url)
        for url in URLS
    )

    for future in concurrent.futures.as_completed(future_to_url):
        succeeded.append(future.result())

print(f"Successfully completed {sum(1 for result in succeeded if result)}")
```

### `pylateral`

```python
import requests
import sqlite3

import pylateral

URLS = [
    'http://www.foxnews.com/',
    'http://www.cnn.com/',
    'http://europe.wsj.com/',
    'http://www.bbc.co.uk/',
    'http://some-made-up-domain.com/',
]

@pylateral.task(has_return_value=True)
def extract_and_load(url, timeout=30):
    try:
        web_result = requests.get(url, timeout=timeout).text
        print(f"{url} is {len(web_result)} bytes")

        with sqlite3.connect('example.db') as conn, conn as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS web_results (url text, length int);')
            cursor.execute('INSERT INTO web_results VALUES (?, ?)', (url, len(web_result)))
    except Exception as e:
        print(f"{url} generated an exception: {e}")
        return False
    else:
        return True

with pylateral.task_pool() as pool:
    for url in URLS:
        extract_and_load(url)

succeeded = pool.results

print(f"Successfully completed {sum(1 for result in succeeded if result)}")
```

### Unthreaded

```python
import requests
import sqlite3

URLS = [
    'http://www.foxnews.com/',
    'http://www.cnn.com/',
    'http://europe.wsj.com/',
    'http://www.bbc.co.uk/',
    'http://some-made-up-domain.com/',
]

def extract_and_load(url, timeout=30):
    try:
        web_result = requests.get(url, timeout=timeout).text
        print(f"{url} is {len(web_result)} bytes")

        with sqlite3.connect('example.db') as conn, conn as cursor:
            cursor.execute('CREATE TABLE IF NOT EXISTS web_results (url text, length int);')
            cursor.execute('INSERT INTO web_results VALUES (?, ?)', (url, len(web_result)))
    except Exception as e:
        print(f"{url} generated an exception: {e}")
        return False
    else:
        return True

succeeded = [
    extract_and_load(url)
    for url in URLs
]

print(f"Successfully completed {sum(1 for result in succeeded if result)}")
```
