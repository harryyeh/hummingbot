**Reference:** <a href="https://github.com/sammchardy/python-binance" target="_blank">`Binance Python Client | github.com`</a>

- Binance Python API Library

- Install the python library

```shell
pip install python-binance
```


- Trade Websocket

```python
from binance.client import Client

api_key = ""
api_secret = ""
client = Client(api_key, api_secret)

# get market depth
#depth = client.get_order_book(symbol='BTCUSDT')

# start aggregated trade websocket for BNBBTC
def process_message(msg):
    print("message type: {}".format(msg['e']))
    print(msg)
    # do something


from binance.websockets import BinanceSocketManager
bm = BinanceSocketManager(client)
bm.start_aggtrade_socket('BTCUSDT', process_message)
bm.start()

```

- Orderbook Websocket

```python
from binance.client import Client

api_key = ""
api_secret = ""
client = Client(api_key, api_secret)

# get market depth
#depth = client.get_order_book(symbol='BTCUSDT')

# start aggregated trade websocket for BNBBTC
def process_message(msg):
    print("message type: {}".format(msg['e']))
    print(msg)
    # do something


from binance.websockets import BinanceSocketManager
bm = BinanceSocketManager(client)
bm.start_depth_socket('BTCUSDT', process_message)
bm.start()

```
