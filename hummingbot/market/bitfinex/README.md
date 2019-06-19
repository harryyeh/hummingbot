

**Reference:** <a href="https://github.com/bitfinexcom/bitfinex-api-py" target="_blank">`Bitfinex API Python | github.com`</a>

- Bitfinex Python API Library

```python

from bfxapi import Client

bfx = Client(
  API_KEY=API_KEY,
  API_SECRET=API_SECRET,
  logLevel='DEBUG'
)

@bfx.ws.on('new_trade')
def log_trade(trade):
  print ("New trade: {}".format(trade))

@bfx.ws.on('connected')
def start():
  bfx.ws.subscribe('trades', 'tBTCUSD')

bfx.ws.run()
```

- requirements.txt

```shell
eventemitter==0.2.0
asyncio==3.4.3
websockets==7.0
pylint==2.3.0
pytest-asyncio==0.9.0
six==1.12.0
pyee==5.0.0
aiohttp==3.4.4
```