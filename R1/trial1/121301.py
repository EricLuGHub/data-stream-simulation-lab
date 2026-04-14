"""
IMC Prosperity 4 — Round 1 Draft Strategy

Two products, two strategies:

1. ASH_COATED_OSMIUM — Mean Reversion
   - Tight range around ~10000, std ~5, strong mean reversion
   - cheap_edge ~+1.1–1.3, expensive_edge ~-1.1–1.4
   - Strategy: EMA fair value + book imbalance, market make around it

2. INTARIAN_PEPPER_ROOT — Trend Following
   - Linear intraday trend: +1000 per day over 1M timestamps
   - Day -2: 9998→11001, Day -1: 10998→11998, Day 0: 11998→13000
   - Day 1 estimate: 13000 → 14000 (slope ≈ +0.001 per timestamp)
   - Strategy: linear fair value estimate, bias position long early / short late
"""

from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import json
import math

POSITION_LIMITS = {
    "ASH_COATED_OSMIUM": 50,
    "INTARIAN_PEPPER_ROOT": 50,
}

PARAMS = {
    "ASH_COATED_OSMIUM": {
        "ema_alpha": 0.4,
        "take_width": 1,
        "make_spread": 2,
        "make_size": 25,
        "position_skew": 1.5,
        "imbalance_weight": 1.0,
    },
    "INTARIAN_PEPPER_ROOT": {
        # Trend parameters derived from data:
        # Each day starts ~1000 above previous day start, trends +1000 intraday
        # Day 1 extrapolation: start ~13000, end ~14000
        "trend_start": 13000,
        "trend_slope": 0.001,       # +1 per 1000 timestamps = +1000 over 1M
        "take_width": 1,
        "make_spread": 3,
        "make_size": 20,
        "position_skew": 2.0,
        "ema_alpha": 0.3,           # Blend EMA with trend estimate
        "trend_weight": 0.5,        # How much to trust linear model vs EMA
    },
}


class Trader:

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
            limit = POSITION_LIMITS.get(product, 50)
            orders: List[Order] = []

            # --- Compute fair value ---
            if product == "ASH_COATED_OSMIUM":
                fair_value = self._ash_fair_value(order_depth, trader_data)
            elif product == "INTARIAN_PEPPER_ROOT":
                fair_value = self._pepper_fair_value(
                    order_depth, trader_data, state.timestamp
                )
            else:
                mid = self._get_mid_price(order_depth)
                if mid is None:
                    result[product] = []
                    continue
                fair_value = mid

            params = PARAMS.get(product, PARAMS["ASH_COATED_OSMIUM"])

            # --- Phase 1: Aggressive takes ---
            position, take_orders = self._take_orders(
                product, order_depth, fair_value, position, limit, params
            )
            orders.extend(take_orders)

            # --- Phase 2: Passive market making ---
            make_orders = self._make_orders(
                product, fair_value, position, limit, params
            )
            orders.extend(make_orders)

            # --- Safety: clamp to position limits ---
            cur_position = state.position.get(product, 0)
            orders = self._clamp_orders(orders, cur_position, limit)

            result[product] = orders

        trader_data_str = json.dumps(trader_data)
        conversions = 0
        return result, conversions, trader_data_str

    # ── Fair value models ──────────────────────────────────────────────

    def _ash_fair_value(self, order_depth: OrderDepth, trader_data: dict) -> float:
        """ASH: EMA of mid price + book imbalance adjustment (mean reversion)."""
        mid = self._get_mid_price(order_depth)
        if mid is None:
            return trader_data.get("ASH_ema", 10000)

        alpha = PARAMS["ASH_COATED_OSMIUM"]["ema_alpha"]
        prev_ema = trader_data.get("ASH_ema", mid)
        ema = alpha * mid + (1 - alpha) * prev_ema
        trader_data["ASH_ema"] = ema

        imbalance = self._get_book_imbalance(order_depth)
        imb_weight = PARAMS["ASH_COATED_OSMIUM"]["imbalance_weight"]

        return ema + imbalance * imb_weight

    def _pepper_fair_value(
        self, order_depth: OrderDepth, trader_data: dict, timestamp: int
    ) -> float:
        """
        PEPPER ROOT: Blend a linear trend model with EMA.

        Linear model: price = trend_start + trend_slope * timestamp
        EMA: adaptive to actual prices
        Final: weighted blend of both
        """
        params = PARAMS["INTARIAN_PEPPER_ROOT"]

        # Linear trend estimate
        trend_estimate = params["trend_start"] + params["trend_slope"] * timestamp

        # EMA of actual mid price
        mid = self._get_mid_price(order_depth)
        if mid is None:
            return trader_data.get("PEPPER_ema", trend_estimate)

        alpha = params["ema_alpha"]
        prev_ema = trader_data.get("PEPPER_ema", mid)
        ema = alpha * mid + (1 - alpha) * prev_ema
        trader_data["PEPPER_ema"] = ema

        # Blend: trust trend model partially, EMA partially
        w = params["trend_weight"]
        fair_value = w * trend_estimate + (1 - w) * ema

        return fair_value

    # ── Helpers ─────────────────────────────────────────────────────────

    def _get_mid_price(self, order_depth: OrderDepth) -> float | None:
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def _get_book_imbalance(self, order_depth: OrderDepth) -> float:
        total_bid = sum(order_depth.buy_orders.values())
        total_ask = sum(-v for v in order_depth.sell_orders.values())
        if total_bid + total_ask == 0:
            return 0
        return (total_bid - total_ask) / (total_bid + total_ask)

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
            for bid_price, bid_vol in sorted(
                order_depth.buy_orders.items(), reverse=True
            ):
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