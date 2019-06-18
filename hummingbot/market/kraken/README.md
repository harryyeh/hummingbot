

**Reference:** <a href="https://github.com/krakenfx/kraken-wsclient-py" target="_blank">`Kraken Websocket Client | github.com`</a>

**Reference:** <a href="https://www.kraken.com/features/websocket-api" target="_blank">`Kraken Websocket Client API Documentation | github.com`</a>

- Kraken Python API Library

Install the python library

```shell
pip install kraken-wsclient-py
```

```python

from kraken_wsclient_py import kraken_wsclient_py as client

def my_handler(message):
    # Here you can do stuff with the messages
    print(message)

my_client = client.WssClient()
my_client.subscribe_public(
    subscription={
        'name': 'trade'
    },
    pair=['XBT/USD', 'XRP/USD'],
    callback=my_handler
)

my_client.start()
```