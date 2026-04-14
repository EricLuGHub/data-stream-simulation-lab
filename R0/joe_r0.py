"""
IMC Prosperity 4 — Tutorial Round 1 Trading Algorithm (v5)

Base: v1 (proven 1,240 profit on real exchange)

Two targeted improvements backed by real trade data analysis:

1. TOMATOES EMA CONVERGENCE GUARD:
   v1 lost 212 profit buying 22 units at 5000-5003 in the first 15000ms
   because the EMA started at 5006 and hadn't settled. We now require
   N ticks of history before aggressive taking, avoiding early adverse selection.

2. TOMATOES BOOK IMBALANCE SIGNAL:
   When bid_volume >> ask_volume, next-tick price moves +3.2 on average.
   When ask_volume >> bid_volume, price moves -3.1.
   We shift fair value by imbalance * weight to lean into predicted moves.
   This improves the average entry/exit price on our trades.

EMERALDS: Kept exactly as v1 (proven optimal for this market structure).
"""

from datamodel import OrderDepth, TradingState, Order, Trade
from typing import List, Dict
import json
import math

POSITION_LIMITS = {
    "EMERALDS": 50,
    "TOMATOES": 50,
}

PARAMS = {
    "EMERALDS": {
        "fair_value": 10_000,
        "take_width": 0,
        "make_spread": 2,
        "make_size": 30,
        "position_skew": 1.5,
    },
    "TOMATOES": {
        "ema_alpha": 0.4,
        "take_width": 0,
        "make_spread": 2,
        "make_size": 25,
        "position_skew": 1.5,
        "warmup_ticks": 50,       # Don't aggressively take until EMA settles
        "imbalance_weight": 1.0,  # Shift fair value by imbalance * weight
    },
}


class Trader:

    def bid(self):
        return 15

    def run(self, state: TradingState):
        trader_data = {}
        if state.traderData and state.traderData != "":
            try:
                trader_data = json.loads(state.traderData)
            except (json.JSONDecodeError, TypeError):
                trader_data = {}

        result: Dict[str, List[Order]] = {}

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            position = state.position.get(product, 0)
            limit = POSITION_LIMITS.get(product, 20)
            orders: List[Order] = []

            # --- Compute fair value ---
            if product == "EMERALDS":
                fair_value = PARAMS["EMERALDS"]["fair_value"]
            elif product == "TOMATOES":
                fair_value = self._compute_tomatoes_fair_value(
                    order_depth, trader_data
                )
            else:
                fair_value = self._get_mid_price(order_depth)
                if fair_value is None:
                    result[product] = []
                    continue

            params = PARAMS.get(product, PARAMS["TOMATOES"])

            # --- Phase 1: Aggressive takes ---
            # For TOMATOES: skip takes during warmup (EMA hasn't settled)
            skip_takes = False
            if product == "TOMATOES":
                tick_count = trader_data.get("TOMATOES_ticks", 0)
                warmup = params.get("warmup_ticks", 0)
                if tick_count < warmup:
                    skip_takes = True

            if not skip_takes:
                position, take_orders = self._take_orders(
                    product, order_depth, fair_value, position, limit, params
                )
                orders.extend(take_orders)

            # --- Phase 2: Passive quotes (always active, even during warmup) ---
            make_orders = self._make_orders(
                product, fair_value, position, limit, params
            )
            orders.extend(make_orders)

            # --- Safety: clamp to position limits ---
            cur_position = state.position.get(product, 0)
            orders = self._clamp_orders(orders, cur_position, limit)

            result[product] = orders

        # Track tick count for warmup
        trader_data["TOMATOES_ticks"] = trader_data.get("TOMATOES_ticks", 0) + 1

        trader_data_str = json.dumps(trader_data)
        conversions = 0
        return result, conversions, trader_data_str

    def _compute_tomatoes_fair_value(
        self, order_depth: OrderDepth, trader_data: dict
    ) -> float:
        """
        TOMATOES fair value = EMA of mid price + book imbalance adjustment.

        Book imbalance: when bids >> asks, price tends to go up (+3 avg).
        We shift fair value to lean into the predicted direction.
        """
        mid = self._get_mid_price(order_depth)
        if mid is None:
            return trader_data.get("TOMATOES_ema", 5000)

        # EMA
        alpha = PARAMS["TOMATOES"]["ema_alpha"]
        prev_ema = trader_data.get("TOMATOES_ema", mid)
        ema = alpha * mid + (1 - alpha) * prev_ema
        trader_data["TOMATOES_ema"] = ema

        # Book imbalance signal
        imbalance = self._get_book_imbalance(order_depth)
        imb_weight = PARAMS["TOMATOES"].get("imbalance_weight", 0)

        return ema + imbalance * imb_weight

    def _get_book_imbalance(self, order_depth: OrderDepth) -> float:
        """
        Calculate order book imbalance: (bid_vol - ask_vol) / (bid_vol + ask_vol).
        Returns value in [-1, 1]. Positive = more buying pressure.
        """
        total_bid = sum(order_depth.buy_orders.values())
        total_ask = sum(-v for v in order_depth.sell_orders.values())

        if total_bid + total_ask == 0:
            return 0
        return (total_bid - total_ask) / (total_bid + total_ask)

    def _get_mid_price(self, order_depth: OrderDepth) -> float | None:
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def _take_orders(
        self,
        product: str,
        order_depth: OrderDepth,
        fair_value: float,
        position: int,
        limit: int,
        params: dict,
    ) -> tuple[int, List[Order]]:
        orders: List[Order] = []
        take_width = params["take_width"]

        if order_depth.sell_orders:
            for ask_price, ask_vol in sorted(order_depth.sell_orders.items()):
                if ask_price <= fair_value - take_width:
                    qty = min(-ask_vol, limit - position)
                    if qty > 0:
                        orders.append(Order(product, ask_price, qty))
                        position += qty

        if order_depth.buy_orders:
            for bid_price, bid_vol in sorted(order_depth.buy_orders.items(), reverse=True):
                if bid_price >= fair_value + take_width:
                    qty = min(bid_vol, limit + position)
                    if qty > 0:
                        orders.append(Order(product, bid_price, -qty))
                        position -= qty

        return position, orders

    def _make_orders(
        self,
        product: str,
        fair_value: float,
        position: int,
        limit: int,
        params: dict,
    ) -> List[Order]:
        orders: List[Order] = []
        half_spread = params["make_spread"]
        base_size = params["make_size"]
        skew_factor = params.get("position_skew", 1.0)

        position_ratio = position / limit

        price_adjustment = -position_ratio * skew_factor
        adjusted_fair = fair_value + price_adjustment

        bid_price = math.floor(adjusted_fair - half_spread)
        ask_price = math.ceil(adjusted_fair + half_spread)

        buy_size = int(base_size * (1 - position_ratio))
        buy_size = max(1, min(buy_size, limit - position))

        sell_size = int(base_size * (1 + position_ratio))
        sell_size = max(1, min(sell_size, limit + position))

        if buy_size > 0:
            orders.append(Order(product, bid_price, buy_size))
        if sell_size > 0:
            orders.append(Order(product, ask_price, -sell_size))

        return orders

    def _clamp_orders(
        self, orders: List[Order], cur_position: int, limit: int
    ) -> List[Order]:
        total_buy = sum(o.quantity for o in orders if o.quantity > 0)
        total_sell = sum(-o.quantity for o in orders if o.quantity < 0)

        if cur_position + total_buy > limit:
            max_buy = max(0, limit - cur_position)
            if total_buy > 0:
                scale = max_buy / total_buy
                for o in orders:
                    if o.quantity > 0:
                        o.quantity = max(0, int(o.quantity * scale))

        if cur_position - total_sell < -limit:
            max_sell = max(0, limit + cur_position)
            if total_sell > 0:
                scale = max_sell / total_sell
                for o in orders:
                    if o.quantity < 0:
                        o.quantity = min(0, -int(-o.quantity * scale))

        return [o for o in orders if o.quantity != 0]