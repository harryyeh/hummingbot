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

SNAPSHOT_REST_URL = "https://api.binance.com/api/v1/depth"
DIFF_STREAM_URL = "wss://stream.binance.com:9443/ws"
TICKER_PRICE_CHANGE_URL = "https://api.binance.com/api/v1/ticker/24hr"
EXCHANGE_INFO_URL = "https://api.binance.com/api/v1/exchangeInfo"
