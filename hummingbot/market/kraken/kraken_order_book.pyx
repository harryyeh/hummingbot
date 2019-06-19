#!/usr/bin/env python

from aiokafka import ConsumerRecord
import bz2
import logging
from sqlalchemy.engine import RowProxy
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

_kob_logger = None


cdef class KrakenOrderBook(OrderBook):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global _kob_logger
        if _kob_logger is None:
            _kob_logger = logging.getLogger(__name__)
        return _kob_logger


    @classmethod
    def snapshot_message_from_exchange(cls,
                                       msg: Dict[str, any],
                                       timestamp: float,
                                       metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "symbol": msg[1][3],
            "update_id": message[1]['as'][0][2],
            "bids": message[1]['as'],
            "asks": message[1]['bs']
        }, timestamp=timestamp)

    @classmethod
    def diff_message_from_exchange(cls,
                                   msg: Dict[str, any],
                                   timestamp: Optional[float] = None,
                                   metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "symbol": msg[1][3],
            "update_id": msg["u"],
            "bids": msg["b"],
            "asks": msg["a"]
        }, timestamp=timestamp)

    @classmethod
    def snapshot_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None) -> OrderBookMessage:
        msg = record["json"] if type(record["json"])==dict else ujson.loads(record["json"])
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "symbol": msg["symbol"],
            "update_id": msg["lastUpdateId"],
            "bids": msg["bids"],
            "asks": msg["asks"]
        }, timestamp=record["timestamp"] * 1e-3)

    @classmethod
    def diff_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None) -> OrderBookMessage:
        msg = ujson.loads(record["json"]) # Binance json in DB is TEXT
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "symbol": msg["s"],
            "update_id": msg["u"],
            "bids": msg["b"],
            "asks": msg["a"]
        }, timestamp=record["timestamp"] * 1e-3)

    @classmethod
    def snapshot_message_from_kafka(cls, record: ConsumerRecord, metadata: Optional[Dict] = None) -> OrderBookMessage:
        msg = ujson.loads(record.value.decode("utf-8"))
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "symbol": msg["symbol"],
            "update_id": msg["lastUpdateId"],
            "bids": msg["bids"],
            "asks": msg["asks"]
        }, timestamp=record.timestamp * 1e-3)

    @classmethod
    def diff_message_from_kafka(cls, record: ConsumerRecord, metadata: Optional[Dict] = None) -> OrderBookMessage:
        msg = ujson.loads(record.value.decode("utf-8"))
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "symbol": msg["s"],
            "update_id": msg["u"],
            "bids": msg["b"],
            "asks": msg["a"],

        }, timestamp=record.timestamp * 1e-3)

    @classmethod
    def trade_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None):
        msg = record["json"]
        if metadata:
            msg.update(metadata)
        ts = record.timestamp
        return OrderBookMessage(OrderBookMessageType.TRADE, {
            "symbol": msg["s"],
            "trade_type": float(TradeType.SELL.value) if msg["m"] else float(TradeType.BUY.value),
            "trade_id": msg["t"],
            "update_id": ts,
            "price": msg["p"],
            "amount": msg["q"]
        }, timestamp=ts * 1e-3)

    @classmethod
    def from_snapshot(cls, msg: OrderBookMessage) -> "OrderBook":
        retval = BinanceOrderBook()
        retval.apply_snapshot(msg.bids, msg.asks, msg.update_id)
        return retval
