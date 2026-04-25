from __future__ import annotations

import itertools
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRIALS_DIR = ROOT / "R3" / "trials"


PACK_TEMPLATE = '''from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
import json
import math


PRODUCT = "HYDROGEL_PACK"
LIMIT = 200
EMA_ALPHA = {ema_alpha}
SIGNAL_WEIGHT = {signal_weight}
TAKE_EDGE = {take_edge}
MAKE_EDGE = {make_edge}
INVENTORY_SKEW = {inventory_skew}
SIGNAL_GATE = {signal_gate}
MAX_TAKE = {max_take}
QUOTE_SIZE = {quote_size}


class Trader:
    def run(self, state: TradingState):
        data = self._load(state.traderData)
        od = state.order_depths.get(PRODUCT)
        if od is None or not od.buy_orders or not od.sell_orders:
            return {{}}, 0, json.dumps(data)

        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        mid = 0.5 * (best_bid + best_ask)
        spread = best_ask - best_bid
        imbalance = self._imbalance(od)

        ema = float(data.get("ema", mid))
        ema = (1.0 - EMA_ALPHA) * ema + EMA_ALPHA * mid
        fair = ema + SIGNAL_WEIGHT * imbalance * max(1.0, spread)

        pos = state.position.get(PRODUCT, 0)
        orders: List[Order] = []

        if imbalance > SIGNAL_GATE and best_ask < fair - TAKE_EDGE:
            qty = min(-od.sell_orders[best_ask], LIMIT - pos, MAX_TAKE)
            if qty > 0:
                orders.append(Order(PRODUCT, best_ask, qty))
                pos += qty

        if imbalance < -SIGNAL_GATE and best_bid > fair + TAKE_EDGE:
            qty = min(od.buy_orders[best_bid], LIMIT + pos, MAX_TAKE)
            if qty > 0:
                orders.append(Order(PRODUCT, best_bid, -qty))
                pos -= qty

        inv = pos / LIMIT
        bid_px = math.floor(fair - MAKE_EDGE - INVENTORY_SKEW * inv)
        ask_px = math.ceil(fair + MAKE_EDGE - INVENTORY_SKEW * inv)

        if bid_px >= ask_px:
            bid_px = ask_px - 1

        if best_bid < bid_px < best_ask and pos < LIMIT:
            orders.append(Order(PRODUCT, bid_px, min(QUOTE_SIZE, LIMIT - pos)))
        if best_bid < ask_px < best_ask and pos > -LIMIT:
            orders.append(Order(PRODUCT, ask_px, -min(QUOTE_SIZE, LIMIT + pos)))

        result: Dict[str, List[Order]] = {{}}
        if orders:
            result[PRODUCT] = orders

        data["ema"] = ema
        return result, 0, json.dumps(data)

    def _imbalance(self, od: OrderDepth) -> float:
        bid_vol = float(od.buy_orders[max(od.buy_orders)])
        ask_vol = float(-od.sell_orders[min(od.sell_orders)])
        den = bid_vol + ask_vol
        if den <= 0.0:
            return 0.0
        return (bid_vol - ask_vol) / den

    def _load(self, raw: str):
        if not raw:
            return {{}}
        try:
            return json.loads(raw)
        except Exception:
            return {{}}
'''


VOUCHER_TEMPLATE = '''from datamodel import Order, OrderDepth, TradingState
from typing import Dict, List
import json
import math


UNDERLYING = "VELVETFRUIT_EXTRACT"
VOUCHERS_BASE = {{
    "VEV_4000": (4000.0, 0.495),
    "VEV_4500": (4500.0, 0.285),
    "VEV_5000": (5000.0, 0.225),
    "VEV_5100": (5100.0, 0.225),
    "VEV_5200": (5200.0, 0.225),
    "VEV_5300": (5300.0, 0.225),
    "VEV_5400": (5400.0, 0.210),
    "VEV_5500": (5500.0, 0.240),
    "VEV_6000": (6000.0, 0.345),
    "VEV_6500": (6500.0, 0.520),
}}
LIMIT_VEV = {{k: 300 for k in VOUCHERS_BASE}}
LIMIT_UNDERLYING = 200
TAU_SCALE = {tau_scale}
SIGMA_SCALE = {sigma_scale}
EDGE_MULT = {edge_mult}
JOIN_SIZE = {join_size}
VELV_ENABLE = {velv_enable}
VELV_EMA_ALPHA = {velv_ema_alpha}
VELV_SIGNAL_WEIGHT = {velv_signal_weight}
VELV_TAKE_EDGE = {velv_take_edge}
VELV_MAKE_EDGE = {velv_make_edge}
VELV_SIGNAL_GATE = {velv_signal_gate}
MAX_TAKE_WING = {max_take_wing}
MAX_TAKE_MID = {max_take_mid}
TRADED = {traded_list}


class Trader:
    def run(self, state: TradingState):
        data = self._load(state.traderData)
        result: Dict[str, List[Order]] = {{}}

        spot_od = state.order_depths.get(UNDERLYING)
        if spot_od is None or not spot_od.buy_orders or not spot_od.sell_orders:
            return result, 0, json.dumps(data)

        day = self._infer_day(data, state.timestamp)
        tau = max((7.0 - day) / TAU_SCALE, 1e-5)
        spot_bid = max(spot_od.buy_orders)
        spot_ask = min(spot_od.sell_orders)
        spot = 0.5 * (spot_bid + spot_ask)

        if VELV_ENABLE:
            velv_orders = self._trade_underlying(state, data, spot_od, spot)
            if velv_orders:
                result[UNDERLYING] = velv_orders

        for product in TRADED:
            cfg = VOUCHERS_BASE[product]
            strike = cfg[0]
            sigma = cfg[1] * SIGMA_SCALE
            od = state.order_depths.get(product)
            if od is None or not od.buy_orders or not od.sell_orders:
                continue

            fair = self._call_price(spot, strike, tau, sigma)
            best_bid = max(od.buy_orders)
            best_ask = min(od.sell_orders)
            spread = max(1, best_ask - best_bid)
            edge = self._edge(product, spread)
            pos = state.position.get(product, 0)
            take_cap = MAX_TAKE_MID
            if product in ("VEV_4000", "VEV_4500", "VEV_6000", "VEV_6500"):
                take_cap = MAX_TAKE_WING
            orders: List[Order] = []

            if best_ask < fair - edge:
                qty = min(-od.sell_orders[best_ask], LIMIT_VEV[product] - pos, take_cap)
                if qty > 0:
                    orders.append(Order(product, best_ask, qty))
                    pos += qty

            if best_bid > fair + edge:
                qty = min(od.buy_orders[best_bid], LIMIT_VEV[product] + pos, take_cap)
                if qty > 0:
                    orders.append(Order(product, best_bid, -qty))
                    pos -= qty

            inv = pos / LIMIT_VEV[product]
            bid_px = math.floor(fair - edge * 0.55 - 1.2 * inv)
            ask_px = math.ceil(fair + edge * 0.55 - 1.2 * inv)
            if bid_px >= ask_px:
                bid_px = ask_px - 1

            if best_bid < bid_px < best_ask and pos < LIMIT_VEV[product]:
                orders.append(Order(product, bid_px, min(JOIN_SIZE, LIMIT_VEV[product] - pos)))
            if best_bid < ask_px < best_ask and pos > -LIMIT_VEV[product]:
                orders.append(Order(product, ask_px, -min(JOIN_SIZE, LIMIT_VEV[product] + pos)))

            if orders:
                result[product] = orders

        data["last_ts"] = state.timestamp
        data["day"] = day
        return result, 0, json.dumps(data)

    def _trade_underlying(self, state: TradingState, data, od: OrderDepth, mid: float) -> List[Order]:
        best_bid = max(od.buy_orders)
        best_ask = min(od.sell_orders)
        spread = max(1, best_ask - best_bid)
        imb = self._imbalance(od)

        ema = float(data.get("velv_ema", mid))
        ema = (1.0 - VELV_EMA_ALPHA) * ema + VELV_EMA_ALPHA * mid
        fair = ema + VELV_SIGNAL_WEIGHT * imb * spread
        data["velv_ema"] = ema

        pos = state.position.get(UNDERLYING, 0)
        orders: List[Order] = []

        if imb > VELV_SIGNAL_GATE and best_ask < fair - VELV_TAKE_EDGE:
            qty = min(-od.sell_orders[best_ask], LIMIT_UNDERLYING - pos, 20)
            if qty > 0:
                orders.append(Order(UNDERLYING, best_ask, qty))
                pos += qty

        if imb < -VELV_SIGNAL_GATE and best_bid > fair + VELV_TAKE_EDGE:
            qty = min(od.buy_orders[best_bid], LIMIT_UNDERLYING + pos, 20)
            if qty > 0:
                orders.append(Order(UNDERLYING, best_bid, -qty))
                pos -= qty

        inv = pos / LIMIT_UNDERLYING
        bid_px = math.floor(fair - VELV_MAKE_EDGE - 1.0 * inv)
        ask_px = math.ceil(fair + VELV_MAKE_EDGE - 1.0 * inv)
        if best_bid < bid_px < best_ask and pos < LIMIT_UNDERLYING:
            orders.append(Order(UNDERLYING, bid_px, min(12, LIMIT_UNDERLYING - pos)))
        if best_bid < ask_px < best_ask and pos > -LIMIT_UNDERLYING:
            orders.append(Order(UNDERLYING, ask_px, -min(12, LIMIT_UNDERLYING + pos)))
        return orders

    def _infer_day(self, data, timestamp: int) -> int:
        if timestamp >= 1_000_000:
            return int(timestamp // 1_000_000)
        day = int(data.get("day", 0))
        last = data.get("last_ts")
        if last is not None and timestamp < int(last):
            day += 1
        return max(0, min(6, day))

    def _edge(self, product: str, spread: int) -> float:
        if product in ("VEV_4000", "VEV_4500", "VEV_5500"):
            return EDGE_MULT * max(0.8, 0.18 * spread)
        if product in ("VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400"):
            return EDGE_MULT * max(1.0, 0.22 * spread)
        return EDGE_MULT * max(0.7, 0.16 * spread)

    def _imbalance(self, od: OrderDepth) -> float:
        bid_vol = float(od.buy_orders[max(od.buy_orders)])
        ask_vol = float(-od.sell_orders[min(od.sell_orders)])
        den = bid_vol + ask_vol
        if den <= 0.0:
            return 0.0
        return (bid_vol - ask_vol) / den

    def _call_price(self, s: float, k: float, tau: float, sigma: float) -> float:
        vol_t = sigma * math.sqrt(tau)
        d1 = (math.log(s / k) + 0.5 * sigma * sigma * tau) / vol_t
        d2 = d1 - vol_t
        return s * self._norm_cdf(d1) - k * self._norm_cdf(d2)

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def _load(self, raw: str):
        if not raw:
            return {{}}
        try:
            return json.loads(raw)
        except Exception:
            return {{}}
'''


def write_trial(trial_num: int, trader_code: str, metadata: dict[str, Any]) -> None:
    trial_dir = TRIALS_DIR / f"trial{trial_num}"
    trial_dir.mkdir(parents=True, exist_ok=True)
    (trial_dir / "trader.py").write_text(trader_code)
    (trial_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True))


def generate_pack_trials(start_num: int = 1) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    profile_bank = [
        {"make_edge": 1.6, "inventory_skew": 1.2, "max_take": 14, "quote_size": 16, "signal_gate": 0.02, "family": "pack_balanced"},
        {"make_edge": 1.9, "inventory_skew": 1.8, "max_take": 12, "quote_size": 14, "signal_gate": 0.03, "family": "pack_conservative"},
        {"make_edge": 1.3, "inventory_skew": 0.9, "max_take": 18, "quote_size": 20, "signal_gate": 0.01, "family": "pack_aggressive"},
        {"make_edge": 2.2, "inventory_skew": 2.2, "max_take": 10, "quote_size": 12, "signal_gate": 0.05, "family": "pack_lowrisk"},
        {"make_edge": 1.5, "inventory_skew": 1.5, "max_take": 16, "quote_size": 18, "signal_gate": 0.00, "family": "pack_unconventional"},
    ]

    idx = start_num
    for ema_alpha, signal_weight, take_edge, profile in itertools.product(
        [0.05, 0.12],
        [0.8, 1.6],
        [0.8, 1.4],
        profile_bank,
    ):
        params = {
            "ema_alpha": ema_alpha,
            "signal_weight": signal_weight,
            "take_edge": take_edge,
            "make_edge": profile["make_edge"],
            "inventory_skew": profile["inventory_skew"],
            "signal_gate": profile["signal_gate"],
            "max_take": profile["max_take"],
            "quote_size": profile["quote_size"],
        }
        code = PACK_TEMPLATE.format(**params)
        metadata = {
            "trial": idx,
            "set": "PACK_ONLY",
            "family": profile["family"],
            "params": params,
        }
        write_trial(idx, code, metadata)
        manifests.append(metadata)
        idx += 1

    return manifests


def generate_velv_vev_trials(start_num: int = 41) -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    profiles = [
        {
            "join_size": 14,
            "velv_enable": "True",
            "velv_ema_alpha": 0.08,
            "velv_signal_weight": 1.4,
            "velv_take_edge": 1.3,
            "velv_make_edge": 1.8,
            "velv_signal_gate": 0.02,
            "max_take_wing": 10,
            "max_take_mid": 16,
            "traded_list": repr(["VEV_4000", "VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_6000", "VEV_6500"]),
            "family": "smile_hybrid",
        },
        {
            "join_size": 12,
            "velv_enable": "False",
            "velv_ema_alpha": 0.06,
            "velv_signal_weight": 1.0,
            "velv_take_edge": 1.2,
            "velv_make_edge": 1.9,
            "velv_signal_gate": 0.03,
            "max_take_wing": 8,
            "max_take_mid": 14,
            "traded_list": repr(["VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_6000"]),
            "family": "smile_voucher_only",
        },
        {
            "join_size": 18,
            "velv_enable": "True",
            "velv_ema_alpha": 0.11,
            "velv_signal_weight": 1.8,
            "velv_take_edge": 1.0,
            "velv_make_edge": 1.5,
            "velv_signal_gate": 0.01,
            "max_take_wing": 12,
            "max_take_mid": 20,
            "traded_list": repr(["VEV_4000", "VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"]),
            "family": "smile_highrisk",
        },
        {
            "join_size": 10,
            "velv_enable": "True",
            "velv_ema_alpha": 0.07,
            "velv_signal_weight": 1.1,
            "velv_take_edge": 1.6,
            "velv_make_edge": 2.2,
            "velv_signal_gate": 0.04,
            "max_take_wing": 8,
            "max_take_mid": 12,
            "traded_list": repr(["VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500", "VEV_6000"]),
            "family": "smile_lowrisk",
        },
        {
            "join_size": 16,
            "velv_enable": "True",
            "velv_ema_alpha": 0.10,
            "velv_signal_weight": 1.6,
            "velv_take_edge": 1.1,
            "velv_make_edge": 1.6,
            "velv_signal_gate": 0.02,
            "max_take_wing": 10,
            "max_take_mid": 18,
            "traded_list": repr(["VEV_4000", "VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"]),
            "family": "smile_regime_mix",
        },
    ]

    idx = start_num
    for tau_scale, sigma_scale, edge_mult, profile in itertools.product(
        [250.0, 320.0],
        [0.90, 1.05],
        [0.85, 1.10],
        profiles,
    ):
        params = {
            "tau_scale": tau_scale,
            "sigma_scale": sigma_scale,
            "edge_mult": edge_mult,
            "join_size": profile["join_size"],
            "velv_enable": profile["velv_enable"],
            "velv_ema_alpha": profile["velv_ema_alpha"],
            "velv_signal_weight": profile["velv_signal_weight"],
            "velv_take_edge": profile["velv_take_edge"],
            "velv_make_edge": profile["velv_make_edge"],
            "velv_signal_gate": profile["velv_signal_gate"],
            "max_take_wing": profile["max_take_wing"],
            "max_take_mid": profile["max_take_mid"],
            "traded_list": profile["traded_list"],
        }
        code = VOUCHER_TEMPLATE.format(**params)
        metadata = {
            "trial": idx,
            "set": "VELV_VEV_TARGET",
            "family": profile["family"],
            "params": {
                **{k: v for k, v in params.items() if k != "traded_list"},
                "traded_list": json.loads(profile["traded_list"].replace("'", '"')),
            },
        }
        write_trial(idx, code, metadata)
        manifests.append(metadata)
        idx += 1

    return manifests


def main() -> None:
    TRIALS_DIR.mkdir(parents=True, exist_ok=True)
    pack = generate_pack_trials(1)
    vv = generate_velv_vev_trials(41)
    manifest = sorted(pack + vv, key=lambda x: x["trial"])

    out = ROOT / "R3" / "experiments" / "trial_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    print(f"Generated {len(pack)} PACK trials and {len(vv)} VELV/VEV trials.")
    print(f"Manifest written to {out}")


if __name__ == "__main__":
    main()
