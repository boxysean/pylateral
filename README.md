pylateral
=========

Intuitive multi-threaded task processing in python.

## Example

    import urllib.request
    
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

