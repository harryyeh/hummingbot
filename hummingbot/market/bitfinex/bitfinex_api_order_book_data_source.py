#!/usr/bin/env python

import asyncio
import aiohttp
import logging
import pandas as pd
from typing import (
    AsyncIterable,
    Dict,
    List,
    Optional,
)
import re
import time
import ujson
import websockets
from websockets.exceptions import ConnectionClosed

from hummingbot.market.bitfinex.bitfinex_order_book import BitfinexOrderBook
from hummingbot.core.utils import async_ttl_cache
from hummingbot.logger import HummingbotLogger
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.order_book_tracker_entry import OrderBookTrackerEntry
from hummingbot.core.data_type.order_book_message import OrderBookMessage

TRADING_PAIR_FILTER = re.compile(r"(BTC|ETH|USDT)$")

BITFINEX_PUB_WS_URL = "wss://api-pub.bitfinex.com"
BITFINEX_AUTH_WS_URL = "wss://api.bitfinex.com"

class BitfinexAPIOrderBookDataSource(OrderBookTrackerDataSource):

    MESSAGE_TIMEOUT = 30.0
    PING_TIMEOUT = 10.0

    _raobds_logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._raobds_logger is None:
            cls._raobds_logger = logging.getLogger(__name__)
        return cls._raobds_logger

    @classmethod
    @async_ttl_cache(ttl=60 * 30, maxsize=1)
    async def get_active_exchange_markets(cls) -> pd.DataFrame:
        """
        Returned data frame should have symbol as index and include usd volume, baseAsset and quoteAsset
        """
        async with aiohttp.ClientSession() as client:

            # market_response, exchange_response = await asyncio.gather(
            #     client.get(TICKER_PRICE_CHANGE_URL),
            #     client.get(EXCHANGE_INFO_URL)
            # )
            # market_response: aiohttp.ClientResponse = market_response
            # exchange_response: aiohttp.ClientResponse = exchange_response

            # if market_response.status != 200:
            #     raise IOError(f"Error fetching Binance markets information. "
            #                   f"HTTP status is {market_response.status}.")
            # if exchange_response.status != 200:
            #     raise IOError(f"Error fetching Binance exchange information. "
            #                   f"HTTP status is {exchange_response.status}.")

            # market_data = await market_response.json()
            # exchange_data = await exchange_response.json()

            # trading_pairs: Dict[str, any] = {item["symbol"]: {k: item[k] for k in ["baseAsset", "quoteAsset"]}
            #                                  for item in exchange_data["symbols"]
            #                                  if item["status"] == "TRADING"}

            # market_data: List[Dict[str, any]] = [{**item, **trading_pairs[item["symbol"]]}
            #                                      for item in market_data
            #                                      if item["symbol"] in trading_pairs]

            # # Build the data frame.
            # all_markets: pd.DataFrame = pd.DataFrame.from_records(data=market_data, index="symbol")
            # btc_price: float = float(all_markets.loc["BTCUSDT"].lastPrice)
            # eth_price: float = float(all_markets.loc["ETHUSDT"].lastPrice)
            # usd_volume: float = [
            #     (
            #         quoteVolume * btc_price if symbol.endswith("BTC") else
            #         quoteVolume * eth_price if symbol.endswith("ETH") else
            #         quoteVolume
            #     )
            #     for symbol, quoteVolume in zip(all_markets.index,
            #                                    all_markets.quoteVolume.astype("float"))]
            # all_markets.loc[:, "USDVolume"] = usd_volume
            # all_markets.loc[:, "volume"] = all_markets.quoteVolume

            # return all_markets.sort_values("USDVolume", ascending=False)