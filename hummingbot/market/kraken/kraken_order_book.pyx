#!/usr/bin/env python
import logging
from typing import (
    Dict,
    Optional
)
import ujson

from hummingbot.logger import HummingbotLogger
from hummingbot.core.event.events import TradeType
from hummingbot.core.data_type.order_book cimport OrderBook
from hummingbot.core.data_type.order_book_message import (
    OrderBookMessage,
    OrderBookMessageType
)

_bob_logger = None


cdef class KrakenOrderBook(OrderBook):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global _kob_logger
        if _kob_logger is None:
            _kob_logger = logging.getLogger(__name__)
        return _kob_logger

