**Reference:** <a href="https://github.com/ericls/huobi" target="_blank">`Huobi Python SDK | github.com`</a>

**Reference:** <a href="https://github.com/huobiapi/API_Docs_en/wiki/Huobi.pro-API" target="_blank">`Huobi Websocket Reference Docs | github.com`</a>

**Reference:** <a href="https://github.com/huobiapi/API_Docs_en/wiki/WS_General" target="_blank">`Huobi Websocket Reference General | github.com`</a>

- Huobi Python API Library



- Orderbook Websocket

from huobi import subscribe
import asyncio

```python
def btc_callback(data):
    print(data)


task = subscribe({
        'market.btcusdt.depth.step5': {
            'callback': btc_callback
        }
    })
asyncio.get_event_loop().run_until_complete(task)
```
