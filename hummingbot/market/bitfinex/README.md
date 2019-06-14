

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