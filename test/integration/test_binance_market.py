#!/usr/bin/env python
from os.path import join, realpath
import sys; sys.path.insert(0, realpath(join(__file__, "../../../")))

import asyncio
import conf
import contextlib
from decimal import Decimal
import logging
import time
from typing import (
    List,
    Dict
)
import unittest
from unittest.mock import patch

from hummingbot.core.event.events import (
    OrderType,
    TradeType
)
from hummingbot.market.binance.binance_market import (
    BinanceMarket,
    BinanceTime
)
from hummingbot.core.clock import (
    Clock,
    ClockMode
)
from hummingbot.core.event.events import (
    MarketEvent,
    BuyOrderCompletedEvent,
    SellOrderCompletedEvent,
    MarketReceivedAssetEvent,
    MarketWithdrawAssetEvent,
    OrderFilledEvent,
    BuyOrderCreatedEvent,
    SellOrderCreatedEvent,
    TradeFee
)
from hummingbot.wallet.ethereum.mock_wallet import MockWallet
from hummingbot.core.event.event_logger import EventLogger
from hummingbot.core.data_type.order_book_tracker import OrderBookTrackerDataSourceType
from hummingbot.logger.struct_logger import METRICS_LOG_LEVEL
from hummingbot.core.data_type.user_stream_tracker import UserStreamTrackerDataSourceType

MAINNET_RPC_URL = "http://mainnet-rpc.mainnet:8545"
logging.basicConfig(level=METRICS_LOG_LEVEL)


class BinanceMarketUnitTest(unittest.TestCase):
    events: List[MarketEvent] = [
        MarketEvent.ReceivedAsset,
        MarketEvent.BuyOrderCompleted,
        MarketEvent.SellOrderCompleted,
        MarketEvent.WithdrawAsset,
        MarketEvent.OrderFilled,
        MarketEvent.TransactionFailure,
        MarketEvent.BuyOrderCreated,
        MarketEvent.SellOrderCreated,
    ]

    market: BinanceMarket
    market_logger: EventLogger

    @classmethod
    def setUpClass(cls):
        global MAINNET_RPC_URL

        cls.clock: Clock = Clock(ClockMode.REALTIME)
        cls.market: BinanceMarket = BinanceMarket(
            MAINNET_RPC_URL, conf.binance_api_key, conf.binance_api_secret,
            order_book_tracker_data_source_type=OrderBookTrackerDataSourceType.EXCHANGE_API,
            user_stream_tracker_data_source_type=UserStreamTrackerDataSourceType.EXCHANGE_API,
            symbols=["ZRXETH", "LOOMETH", "IOSTETH"]
        )
        print("Initializing Binance market... this will take about a minute.")
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        cls.clock.add_iterator(cls.market)
        stack = contextlib.ExitStack()
        cls._clock = stack.enter_context(cls.clock)
        cls.ev_loop.run_until_complete(cls.wait_til_ready())
        print("Ready.")

    @classmethod
    async def wait_til_ready(cls):
        while True:
            now = time.time()
            next_iteration = now // 1.0 + 1
            if cls.market.ready:
                break
            else:
                await cls._clock.run_til(next_iteration)
            await asyncio.sleep(1.0)

    def setUp(self):
        self.market_logger = EventLogger()
        for event_tag in self.events:
            self.market.add_listener(event_tag, self.market_logger)

    def tearDown(self):
        for event_tag in self.events:
            self.market.remove_listener(event_tag, self.market_logger)
        self.market_logger = None

    async def run_parallel_async(self, *tasks):
        future: asyncio.Future = asyncio.ensure_future(asyncio.gather(*tasks))
        while not future.done():
            now = time.time()
            next_iteration = now // 1.0 + 1
            await self._clock.run_til(next_iteration)
            await asyncio.sleep(1.0)
        return future.result()

    def run_parallel(self, *tasks):
        return self.ev_loop.run_until_complete(self.run_parallel_async(*tasks))

    def test_get_fee(self):
        maker_buy_trade_fee: TradeFee = self.market.get_fee("BTC", "USDT", OrderType.LIMIT, TradeType.BUY, 1, 4000)
        self.assertGreater(maker_buy_trade_fee.percent, 0)
        self.assertEqual(len(maker_buy_trade_fee.flat_fees), 0)
        taker_buy_trade_fee: TradeFee = self.market.get_fee("BTC", "USDT", OrderType.MARKET, TradeType.BUY, 1)
        self.assertGreater(taker_buy_trade_fee.percent, 0)
        self.assertEqual(len(taker_buy_trade_fee.flat_fees), 0)
        sell_trade_fee: TradeFee = self.market.get_fee("BTC", "USDT", OrderType.LIMIT, TradeType.SELL, 1, 4000)
        self.assertGreater(sell_trade_fee.percent, 0)
        self.assertEqual(len(sell_trade_fee.flat_fees), 0)

    def test_buy_and_sell(self):
        self.assertGreater(self.market.get_balance("ETH"), 0.1)

        # Try to buy 0.02 ETH worth of ZRX from the exchange, and watch for completion event.
        current_price: float = self.market.get_price("ZRXETH", True)
        amount: float = 0.02 / current_price
        quantized_amount: Decimal = self.market.quantize_order_amount("ZRXETH", amount)
        order_id = self.market.buy("ZRXETH", amount)
        [order_completed_event] = self.run_parallel(self.market_logger.wait_for(BuyOrderCompletedEvent))
        order_completed_event: BuyOrderCompletedEvent = order_completed_event
        trade_events: List[OrderFilledEvent] = [t for t in self.market_logger.event_log
                                                if isinstance(t, OrderFilledEvent)]
        base_amount_traded: float = sum(t.amount for t in trade_events)
        quote_amount_traded: float = sum(t.amount * t.price for t in trade_events)

        self.assertTrue([evt.order_type == OrderType.MARKET for evt in trade_events])
        self.assertEqual(order_id, order_completed_event.order_id)
        self.assertEqual(quantized_amount, order_completed_event.base_asset_amount)
        self.assertEqual("ZRX", order_completed_event.base_asset)
        self.assertEqual("ETH", order_completed_event.quote_asset)
        self.assertAlmostEqual(base_amount_traded, float(order_completed_event.base_asset_amount))
        self.assertAlmostEqual(quote_amount_traded, float(order_completed_event.quote_asset_amount))
        self.assertGreater(order_completed_event.fee_amount, Decimal(0))
        self.assertTrue(any([isinstance(event, BuyOrderCreatedEvent) and event.order_id == order_id
                             for event in self.market_logger.event_log]))

        # Reset the logs
        self.market_logger.clear()

        # Try to sell back the same amount of ZRX to the exchange, and watch for completion event.
        amount = float(order_completed_event.base_asset_amount)
        quantized_amount = order_completed_event.base_asset_amount
        order_id = self.market.sell("ZRXETH", amount)
        [order_completed_event] = self.run_parallel(self.market_logger.wait_for(SellOrderCompletedEvent))
        order_completed_event: SellOrderCompletedEvent = order_completed_event
        trade_events = [t for t in self.market_logger.event_log
                        if isinstance(t, OrderFilledEvent)]
        base_amount_traded = sum(t.amount for t in trade_events)
        quote_amount_traded = sum(t.amount * t.price for t in trade_events)

        self.assertTrue([evt.order_type == OrderType.MARKET for evt in trade_events])
        self.assertEqual(order_id, order_completed_event.order_id)
        self.assertEqual(quantized_amount, order_completed_event.base_asset_amount)
        self.assertEqual("ZRX", order_completed_event.base_asset)
        self.assertEqual("ETH", order_completed_event.quote_asset)
        self.assertAlmostEqual(base_amount_traded, float(order_completed_event.base_asset_amount))
        self.assertAlmostEqual(quote_amount_traded, float(order_completed_event.quote_asset_amount))
        self.assertGreater(order_completed_event.fee_amount, Decimal(0))
        self.assertTrue(any([isinstance(event, SellOrderCreatedEvent) and event.order_id == order_id
                             for event in self.market_logger.event_log]))

    def test_limit_buy_and_sell(self):
        self.assertGreater(self.market.get_balance("ETH"), 0.1)

        # Try to put limit buy order for 0.02 ETH worth of ZRX, and watch for completion event.
        current_bid_price: float = self.market.get_price("ZRXETH", True)
        bid_price: float = current_bid_price + 0.05 * current_bid_price
        quantize_bid_price: Decimal = self.market.quantize_order_price("ZRXETH", bid_price)

        amount: float = 0.02 / bid_price
        quantized_amount: Decimal = self.market.quantize_order_amount("ZRXETH", amount)

        order_id = self.market.buy("ZRXETH", quantized_amount, OrderType.LIMIT, quantize_bid_price)
        [order_completed_event] = self.run_parallel(self.market_logger.wait_for(BuyOrderCompletedEvent))
        order_completed_event: BuyOrderCompletedEvent = order_completed_event
        trade_events: List[OrderFilledEvent] = [t for t in self.market_logger.event_log
                                                if isinstance(t, OrderFilledEvent)]
        base_amount_traded: float = sum(t.amount for t in trade_events)
        quote_amount_traded: float = sum(t.amount * t.price for t in trade_events)

        self.assertTrue([evt.order_type == OrderType.LIMIT for evt in trade_events])
        self.assertEqual(order_id, order_completed_event.order_id)
        self.assertEqual(quantized_amount, order_completed_event.base_asset_amount)
        self.assertEqual("ZRX", order_completed_event.base_asset)
        self.assertEqual("ETH", order_completed_event.quote_asset)
        self.assertAlmostEqual(base_amount_traded, float(order_completed_event.base_asset_amount))
        self.assertAlmostEqual(quote_amount_traded, float(order_completed_event.quote_asset_amount))
        self.assertGreater(order_completed_event.fee_amount, Decimal(0))
        self.assertTrue(any([isinstance(event, BuyOrderCreatedEvent) and event.order_id == order_id
                             for event in self.market_logger.event_log]))

        # Reset the logs
        self.market_logger.clear()

        # Try to put limit sell order for 0.02 ETH worth of ZRX, and watch for completion event.
        current_ask_price: float = self.market.get_price("ZRXETH", False)
        ask_price: float = current_ask_price - 0.05 * current_ask_price
        quantize_ask_price: Decimal = self.market.quantize_order_price("ZRXETH", ask_price)

        amount = float(order_completed_event.base_asset_amount)
        quantized_amount = order_completed_event.base_asset_amount

        order_id = self.market.sell("ZRXETH", amount, OrderType.LIMIT, quantize_ask_price)
        [order_completed_event] = self.run_parallel(self.market_logger.wait_for(SellOrderCompletedEvent))
        order_completed_event: SellOrderCompletedEvent = order_completed_event
        trade_events = [t for t in self.market_logger.event_log
                        if isinstance(t, OrderFilledEvent)]
        base_amount_traded = sum(t.amount for t in trade_events)
        quote_amount_traded = sum(t.amount * t.price for t in trade_events)

        self.assertTrue([evt.order_type == OrderType.LIMIT for evt in trade_events])
        self.assertEqual(order_id, order_completed_event.order_id)
        self.assertEqual(quantized_amount, order_completed_event.base_asset_amount)
        self.assertEqual("ZRX", order_completed_event.base_asset)
        self.assertEqual("ETH", order_completed_event.quote_asset)
        self.assertAlmostEqual(base_amount_traded, float(order_completed_event.base_asset_amount))
        self.assertAlmostEqual(quote_amount_traded, float(order_completed_event.quote_asset_amount))
        self.assertGreater(order_completed_event.fee_amount, Decimal(0))
        self.assertTrue(any([isinstance(event, SellOrderCreatedEvent) and event.order_id == order_id
                             for event in self.market_logger.event_log]))

    @unittest.skipUnless(any("test_deposit_eth" in arg for arg in sys.argv), "Deposit test requires manual action.")
    def test_deposit_eth(self):
        with open(realpath(join(__file__, "../../../data/ZRXABI.json"))) as fd:
            zrx_abi: str = fd.read()
        local_wallet: MockWallet = MockWallet(conf.web3_test_private_key_a,
                                              MAINNET_RPC_URL,
                                              {"0xE41d2489571d322189246DaFA5ebDe1F4699F498": zrx_abi},
                                              chain_id=1)

        # Ensure the local wallet has enough balance for deposit testing.
        self.assertGreaterEqual(local_wallet.get_balance("ETH"), 0.02)

        # Deposit ETH to Binance, and wait.
        tracking_id: str = self.market.deposit(local_wallet, "ETH", 0.01)
        [received_asset_event] = self.run_parallel(
            self.market_logger.wait_for(MarketReceivedAssetEvent, timeout_seconds=1800)
        )
        received_asset_event: MarketReceivedAssetEvent = received_asset_event
        self.assertEqual("ETH", received_asset_event.asset_name)
        self.assertEqual(tracking_id, received_asset_event.tx_hash)
        self.assertEqual(local_wallet.address, received_asset_event.from_address)
        self.assertAlmostEqual(0.01, received_asset_event.amount_received)

    @unittest.skipUnless(any("test_deposit_zrx" in arg for arg in sys.argv), "Deposit test requires manual action.")
    def test_deposit_zrx(self):
        with open(realpath(join(__file__, "../../../data/ZRXABI.json"))) as fd:
            zrx_abi: str = fd.read()
        local_wallet: MockWallet = MockWallet(conf.web3_test_private_key_a,
                                              MAINNET_RPC_URL,
                                              {"0xE41d2489571d322189246DaFA5ebDe1F4699F498": zrx_abi},
                                              chain_id=1)

        # Ensure the local wallet has enough balance for deposit testing.
        self.assertGreaterEqual(local_wallet.get_balance("ZRX"), 1)

        # Deposit ZRX to Binance, and wait.
        tracking_id: str = self.market.deposit(local_wallet, "ZRX", 1)
        [received_asset_event] = self.run_parallel(
            self.market_logger.wait_for(MarketReceivedAssetEvent, timeout_seconds=1800)
        )
        received_asset_event: MarketReceivedAssetEvent = received_asset_event
        self.assertEqual("ZRX", received_asset_event.asset_name)
        self.assertEqual(tracking_id, received_asset_event.tx_hash)
        self.assertEqual(local_wallet.address, received_asset_event.from_address)
        self.assertEqual(1, received_asset_event.amount_received)

    @unittest.skipUnless(any("test_withdraw" in arg for arg in sys.argv), "Withdraw test requires manual action.")
    def test_withdraw(self):
        with open(realpath(join(__file__, "../../../data/ZRXABI.json"))) as fd:
            zrx_abi: str = fd.read()
        local_wallet: MockWallet = MockWallet(conf.web3_test_private_key_a,
                                              MAINNET_RPC_URL,
                                              {"0xE41d2489571d322189246DaFA5ebDe1F4699F498": zrx_abi},
                                              chain_id=1)

        # Ensure the market account has enough balance for withdraw testing.
        self.assertGreaterEqual(self.market.get_balance("ZRX"), 10)

        # Withdraw ZRX from Binance to test wallet.
        self.market.withdraw(local_wallet.address, "ZRX", 10)
        [withdraw_asset_event] = self.run_parallel(
            self.market_logger.wait_for(MarketWithdrawAssetEvent)
        )
        withdraw_asset_event: MarketWithdrawAssetEvent = withdraw_asset_event
        print(withdraw_asset_event)
        self.assertEqual(local_wallet.address, withdraw_asset_event.to_address)
        self.assertEqual("ZRX", withdraw_asset_event.asset_name)
        self.assertEqual(10, withdraw_asset_event.amount)
        self.assertGreater(withdraw_asset_event.fee_amount, 0)

    def test_cancel_all(self):
        symbol = "LOOMETH"
        bid_price: float = self.market.get_price(symbol, True)
        ask_price: float = self.market.get_price(symbol, False)
        amount: float = 0.02 / bid_price
        quantized_amount: Decimal = self.market.quantize_order_amount(symbol, amount)

        # Intentionally setting invalid price to prevent getting filled
        quantize_bid_price: Decimal = self.market.quantize_order_price(symbol, bid_price * 0.7)
        quantize_ask_price: Decimal = self.market.quantize_order_price(symbol, ask_price * 1.5)

        self.market.buy(symbol, quantized_amount, OrderType.LIMIT, quantize_bid_price)
        self.market.sell(symbol, quantized_amount, OrderType.LIMIT, quantize_ask_price)

        self.run_parallel(asyncio.sleep(1))
        [cancellation_results] = self.run_parallel(self.market.cancel_all(5))
        for cr in cancellation_results:
            self.assertEqual(cr.success, True)

    def test_order_price_precision(self):
        # As of the day this test was written, the min order size (base) is 1 IOST, the min order size (quote) is
        # 0.01 ETH, and order step size is 1 IOST.
        symbol = "IOSTETH"
        bid_price: float = self.market.get_price(symbol, True)
        ask_price: float = self.market.get_price(symbol, False)
        mid_price: float = (bid_price + ask_price) / 2
        amount: float = 0.02 / mid_price
        binance_client = self.market.binance_client

        # Make sure there's enough balance to make the limit orders.
        self.assertGreater(self.market.get_balance("ETH"), 0.1)
        self.assertGreater(self.market.get_balance("IOST"), amount * 2)

        # Intentionally set some prices with too many decimal places s.t. they
        # need to be quantized. Also, place them far away from the mid-price s.t. they won't
        # get filled during the test.
        bid_price: float = mid_price * 0.3333192292111341
        ask_price: float = mid_price * 3.4392431474884933

        # This is needed to get around the min quote amount limit.
        bid_amount: float = 0.02 / bid_price

        # Test bid order
        bid_order_id: str = self.market.buy(
            symbol,
            bid_amount,
            OrderType.LIMIT,
            bid_price
        )

        # Wait for the order created event and examine the order made
        [order_created_event] = self.run_parallel(
            self.market_logger.wait_for(BuyOrderCreatedEvent, timeout_seconds=10)
        )
        order_data: Dict[str, any] = binance_client.get_order(
            symbol=symbol,
            origClientOrderId=bid_order_id
        )
        quantized_bid_price: Decimal = self.market.quantize_order_price(symbol, bid_price)
        bid_size_quantum: Decimal = self.market.get_order_size_quantum(symbol, bid_amount)
        self.assertEqual(quantized_bid_price, Decimal(order_data["price"]))
        self.assertTrue(Decimal(order_data["origQty"]) % bid_size_quantum == 0)

        # Test ask order
        ask_order_id: str = self.market.sell(
            symbol,
            amount,
            OrderType.LIMIT,
            ask_price
        )

        # Wait for the order created event and examine and order made
        [order_created_event] = self.run_parallel(
            self.market_logger.wait_for(SellOrderCreatedEvent, timeout_seconds=10)
        )
        order_data = binance_client.get_order(
            symbol=symbol,
            origClientOrderId=ask_order_id
        )
        quantized_ask_price: Decimal = self.market.quantize_order_price(symbol, ask_price)
        quantized_ask_size: Decimal = self.market.quantize_order_amount(symbol, amount)
        self.assertEqual(quantized_ask_price, Decimal(order_data["price"]))
        self.assertEqual(quantized_ask_size, Decimal(order_data["origQty"]))

        # Cancel all the orders
        [cancellation_results] = self.run_parallel(self.market.cancel_all(5))
        for cr in cancellation_results:
            self.assertEqual(cr.success, True)

    def test_server_time_offset(self):
        BinanceTime.get_instance().SERVER_TIME_OFFSET_CHECK_INTERVAL = 3.0
        self.run_parallel(asyncio.sleep(60))
        with patch("hummingbot.market.binance.binance_market.time") as market_time:
            def delayed_time():
                return time.time() - 30.0
            market_time.time = delayed_time
            self.run_parallel(asyncio.sleep(5.0))
            time_offset = BinanceTime.get_instance().time_offset_ms
            print("offest", time_offset)
            # check if it is less than 5% off
            self.assertTrue(time_offset > 0)
            self.assertTrue(abs(time_offset - 30.0 * 1e3) < 1.5 * 1e3)


if __name__ == "__main__":
    logging.getLogger("hummingbot.core.event.event_reporter").setLevel(logging.WARNING)
    unittest.main()
