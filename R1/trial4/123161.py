"""
IMC Prosperity 4 — Round 1 Strategy v4

Trial 3 results (3232 total, up from 2682):
  ASH: 1226 (up from 904). Reverting make_spread to 2 worked. But net pos 23
       still too high — inventory problem persists.
  PEPPER: 2006 (up from 1778). But went SHORT to -15 in first 30K timestamps
          despite target +40. Market took our asks despite small size.
          Trend capture still far below theoretical max (5000).

New ASH analysis insights:
  - deviation_ar1_beta=1.0 → pure random walk, NOT mean-reverting to fixed level
  - cheap_edge_net=-15 → NO edge after spread costs. Profit is 100% passive MM.
  - return_autocorr=-0.5 → bid-ask bounce, good for market makers

v4 changes:
  ASH: Add hard inventory limits. When |position| > 30, only quote the
       reducing side. Pure spread collection, minimize inventory risk.
  PEPPER: When far below target, suppress sell orders entirely.
          Add trend_edge to fair value — willing to pay above mid since we
          know price is going up. Get long faster to capture the trend.
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
        "take_width": 0,
        "make_spread": 2,
        "make_size": 35,
        "position_skew": 2.5,
        "imbalance_weight": 1.0,
        "hard_limit": 30,           # NEW: suppress one side when exceeded
    },
    "INTARIAN_PEPPER_ROOT": {
        "trend_slope": 0.001,
        "take_width": 0,
        "make_spread": 2,
        "make_size": 35,
        "position_skew": 2.0,
        "ema_alpha": 0.3,
        "trend_weight": 0.5,
        "trend_target_start": 40,
        "trend_target_end": 0,
        "max_timestamp": 999900,
        "trend_edge": 4,            # NEW: shift FV up to pay for trend
        "position_gap_threshold": 15,  # NEW: suppress wrong side when this far from target
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
            if product == "ASH_COATED_OSMIUM":
                make_orders = self._make_orders_ash(
                    product, fair_value, position, limit, params
                )
            elif product == "INTARIAN_PEPPER_ROOT":
                make_orders = self._make_orders_trending(
                    product, fair_value, position, limit, params, state.timestamp
                )
            else:
                make_orders = self._make_orders_ash(
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
        """ASH: EMA of mid price + book imbalance. Pure random walk — no
        directional edge, profit only from passive spread collection."""
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
        """PEPPER: Anchor + trend projection blended with EMA, plus a trend_edge
        that makes us willing to pay above mid (since price is going up)."""
        params = PARAMS["INTARIAN_PEPPER_ROOT"]

        mid = self._get_mid_price(order_depth)

        if "PEPPER_anchor_price" not in trader_data and mid is not None:
            trader_data["PEPPER_anchor_price"] = mid
            trader_data["PEPPER_anchor_ts"] = timestamp

        anchor_price = trader_data.get("PEPPER_anchor_price", mid if mid else 12000)
        anchor_ts = trader_data.get("PEPPER_anchor_ts", 0)

        elapsed = timestamp - anchor_ts
        trend_estimate = anchor_price + params["trend_slope"] * elapsed

        if mid is None:
            return trader_data.get("PEPPER_ema", trend_estimate)

        alpha = params["ema_alpha"]
        prev_ema = trader_data.get("PEPPER_ema", mid)
        ema = alpha * mid + (1 - alpha) * prev_ema
        trader_data["PEPPER_ema"] = ema

        w = params["trend_weight"]
        base_fv = w * trend_estimate + (1 - w) * ema

        # Add trend edge: we know price goes up, so fair value is higher
        # than current mid. Scale down as we approach end of day.
        max_ts = params["max_timestamp"]
        remaining = max(0, 1 - timestamp / max_ts) if max_ts > 0 else 0
        edge = params.get("trend_edge", 0) * remaining

        return base_fv + edge

    # ── Order generation ───────────────────────────────────────────────

    def _make_orders_ash(
        self,
        product: str,
        fair_value: float,
        position: int,
        limit: int,
        params: dict,
    ) -> List[Order]:
        """ASH: Pure spread collection with hard inventory limits.
        When |position| exceeds hard_limit, only quote the reducing side."""
        orders: List[Order] = []
        half_spread = params["make_spread"]
        base_size = params["make_size"]
        skew_factor = params.get("position_skew", 1.0)
        hard_limit = params.get("hard_limit", limit)

        position_ratio = position / limit
        price_adjustment = -position_ratio * skew_factor
        adjusted_fair = fair_value + price_adjustment

        bid_price = math.floor(adjusted_fair - half_spread)
        ask_price = math.ceil(adjusted_fair + half_spread)

        buy_size = int(base_size * (1 - position_ratio))
        buy_size = max(1, min(buy_size, limit - position))

        sell_size = int(base_size * (1 + position_ratio))
        sell_size = max(1, min(sell_size, limit + position))

        # Hard inventory control: suppress the accumulating side
        suppress_buy = position >= hard_limit
        suppress_sell = position <= -hard_limit

        if buy_size > 0 and not suppress_buy:
            orders.append(Order(product, bid_price, buy_size))
        if sell_size > 0 and not suppress_sell:
            orders.append(Order(product, ask_price, -sell_size))

        return orders

    def _make_orders_trending(
        self,
        product: str,
        fair_value: float,
        position: int,
        limit: int,
        params: dict,
        timestamp: int,
    ) -> List[Order]:
        """
        PEPPER: Trend-aware market making with position gating.

        Time-varying target (long early, flat late) + suppress the wrong side
        when position is far from target. This prevents the market from
        pushing us short when we need to be long.
        """
        orders: List[Order] = []
        half_spread = params["make_spread"]
        base_size = params["make_size"]
        skew_factor = params["position_skew"]

        # Time-varying target position
        target_start = params["trend_target_start"]
        target_end = params["trend_target_end"]
        max_ts = params["max_timestamp"]
        progress = min(timestamp / max_ts, 1.0) if max_ts > 0 else 0
        target_position = target_start + (target_end - target_start) * progress

        # Position ratio relative to target
        deviation = position - target_position
        position_ratio = deviation / limit

        price_adjustment = -position_ratio * skew_factor
        adjusted_fair = fair_value + price_adjustment

        bid_price = math.floor(adjusted_fair - half_spread)
        ask_price = math.ceil(adjusted_fair + half_spread)

        buy_size = int(base_size * (1 - position_ratio))
        buy_size = max(1, min(buy_size, limit - position))

        sell_size = int(base_size * (1 + position_ratio))
        sell_size = max(1, min(sell_size, limit + position))

        # Position gating: suppress wrong side when far from target
        gap_threshold = params.get("position_gap_threshold", 15)
        suppress_sell = deviation < -gap_threshold  # Too short of target → no sells
        suppress_buy = deviation > gap_threshold    # Too long of target → no buys

        if buy_size > 0 and not suppress_buy:
            orders.append(Order(product, bid_price, buy_size))
        if sell_size > 0 and not suppress_sell:
            orders.append(Order(product, ask_price, -sell_size))

        return orders

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