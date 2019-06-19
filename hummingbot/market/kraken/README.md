

**Reference:** <a href="https://github.com/krakenfx/kraken-wsclient-py" target="_blank">`Kraken Websocket Client | github.com`</a>

**Reference:** <a href="https://www.kraken.com/features/websocket-api" target="_blank">`Kraken Websocket Client API Documentation | github.com`</a>

**Reference:** <a href="https://pypi.org/project/krakenex/" target="_blank">`Kraken REST API Client | github.com`</a>

**Reference:** <a href="https://www.kraken.com/features/api" target="_blank">`Kraken REST API Reference | github.com`</a>

- Kraken Python API Library

- Notes
    + Websockets are for public information only
    + Need to use REST API Client


- Install the python library

```shell
pip install kraken-wsclient-py
```

- Trade Websocket

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
    pair=['XBT/USD'],
    callback=my_handler
)

my_client.start()
```

- Orderbook Websocket

```python
from kraken_wsclient_py import kraken_wsclient_py as client
import logging
import sys


# Logging Functions
def get_console_handler():
    FORMATTER = logging.Formatter("%(asctime)s — %(name)s — %(levelname)s — %(message)s")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler

def set_log_level(level):
    log_level = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'notset': logging.NOTSET
    }
    return(log_level[level.lower()])

def get_logger(logger_name):
    global config, logger
    logger = logging.getLogger(logger_name)
    level = set_log_level('info')
    logger.setLevel(level) # better to have too much log than not enough
    logger.addHandler(get_console_handler())
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger

def my_handler(message):
    # Here you can do stuff with the messages
    #print(type(message))
    # Check type
    # if dict
    if type(message) == dict:
        # Connection Information, Channel and Heartbeat
        logger.debug(message)
    # if list
    if type(message) == list:
        logger.debug(message)

        #1st message is snapshot of bid and ask
        if "as" in message[1]:
            logger.info("ask snapshot:")
            logger.info(message[1]['as'])
            logger.info("bid snapshot:")
            logger.info(message[1]['bs'])
            logger.info("timestamp")
            logger.info(message[1]['as'][0][2])
        # a = asks
        elif "a" in message[1]:
            logger.info("ask:")
            logger.info(message[1]['a'])
        elif "b" in message[1]:
            logger.info("bid:")
            logger.info(message[1]['b'])
        logger.info("symbol: " + message[3])
        # b = bids
        #logger.info(message[1]["as"])
        #logger.info(type(message[1]))

logger = None
logger = get_logger("kraken")



my_client = client.WssClient()
my_client.subscribe_public(
    subscription={
        'name': 'book'
    },
    pair=['XBT/USD'],
    callback=my_handler
)

my_client.start()
```

* To Do

- Place Order
- Cancel Order
- Get Balances
- Get Trading Pairs
- OrderBook
- Trade History
- Python Testing
