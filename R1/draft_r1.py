"""
IMC Prosperity 4 — Round 1 Strategy v2

Trial 1 results (2098 total):
  ASH: 988 from 65 trades. Good spread capture but low volume.
  PEPPER: 1110 from 9 trades. Maxed long immediately due to wrong trend_start,
          then sat idle. All profit from holding through the trend.

v2 fixes:
  1. PEPPER: Don't hardcode trend_start. Use first observed price as anchor.
     Apply known slope (+0.001/tick) to project fair value forward.
     Actively market-make around the trending fair value instead of buy-and-hold.
  2. ASH: Tighten make_spread (1 instead of 2), increase make_size (40),
     reduce take_width to 0 for more aggressive taking.
  3. Both: Place multiple quote levels to increase fill rate and capital usage.
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
        "take_width": 0,           # v1 was 1; with 16-wide spread we never took
        "make_spread": 1,           # v1 was 2; tighter = more fills
        "make_size": 40,            # v1 was 25; use more capital
        "position_skew": 1.5,
        "imbalance_weight": 1.0,
    },
    "INTARIAN_PEPPER_ROOT": {
        "trend_slope": 0.001,       # +1 per 1000 timestamps = +1000 over 1M
        "take_width": 0,            # v1 was 1
        "make_spread": 2,           # v1 was 3; tighter since we have better FV now
        "make_size": 35,            # v1 was 20
        "position_skew": 1.5,       # v1 was 2.0
        "ema_alpha": 0.3,
        "trend_weight": 0.5,        # Blend EMA with trend projection
        "trend_position_bias": 0.3, # Fraction of limit to bias long for trend
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
        PEPPER ROOT: Anchor on first observed price + linear trend projection,
        blended with EMA of actual prices.

        v1 bug: hardcoded trend_start=13000 but actual start was ~12000.
        v2 fix: use first observed mid as anchor, project forward with slope.
        """
        params = PARAMS["INTARIAN_PEPPER_ROOT"]

        # Get current mid
        mid = self._get_mid_price(order_depth)

        # Anchor: record the first observed price and timestamp
        if "PEPPER_anchor_price" not in trader_data and mid is not None:
            trader_data["PEPPER_anchor_price"] = mid
            trader_data["PEPPER_anchor_ts"] = timestamp

        anchor_price = trader_data.get("PEPPER_anchor_price", mid if mid else 12000)
        anchor_ts = trader_data.get("PEPPER_anchor_ts", 0)

        # Linear trend estimate from anchor
        elapsed = timestamp - anchor_ts
        trend_estimate = anchor_price + params["trend_slope"] * elapsed

        if mid is None:
            return trader_data.get("PEPPER_ema", trend_estimate)

        # EMA of actual mid price
        alpha = params["ema_alpha"]
        prev_ema = trader_data.get("PEPPER_ema", mid)
        ema = alpha * mid + (1 - alpha) * prev_ema
        trader_data["PEPPER_ema"] = ema

        # Blend trend model with EMA
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

        # Buy cheap asks (below fair value)
        if order_depth.sell_orders:
            for ask_price, ask_vol in sorted(order_depth.sell_orders.items()):
                if ask_price <= fair_value - take_width:
                    qty = min(-ask_vol, limit - position)
                    if qty > 0:
                        orders.append(Order(product, ask_price, qty))
                        position += qty

        # Sell expensive bids (above fair value)
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

        # For trending products, bias position toward long
        trend_bias = params.get("trend_position_bias", 0)
        # Shift the "neutral" position: 0 → trend_bias * limit
        # So position_ratio = 0 when position = bias_target
        bias_target = trend_bias * limit
        position_ratio = (position - bias_target) / limit

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
