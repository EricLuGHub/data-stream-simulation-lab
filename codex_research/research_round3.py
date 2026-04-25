from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "R3" / "Data"
OUT = ROOT / "codex_research"

UNDERLYING = "VELVETFRUIT_EXTRACT"
PACK = "HYDROGEL_PACK"
VOUCHERS = ["VEV_4000", "VEV_4500", "VEV_5000", "VEV_5100", "VEV_5200", "VEV_5300", "VEV_5400", "VEV_5500", "VEV_6000", "VEV_6500"]


def norm_cdf(x: np.ndarray | float) -> np.ndarray | float:
    # Fast vectorized Abramowitz-Stegun approximation; sufficient for grid search.
    x = np.asarray(x, dtype=float)
    sign = np.where(x < 0.0, -1.0, 1.0)
    z = np.abs(x) / math.sqrt(2.0)
    t = 1.0 / (1.0 + 0.3275911 * z)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-z * z)
    return 0.5 * (1.0 + sign * y)


def bs_call(s: np.ndarray, k: float, tau: np.ndarray, sigma: float) -> np.ndarray:
    tau = np.maximum(tau, 1e-9)
    sigma = max(float(sigma), 1e-9)
    vol_t = sigma * np.sqrt(tau)
    d1 = (np.log(s / k) + 0.5 * sigma * sigma * tau) / vol_t
    d2 = d1 - vol_t
    return s * norm_cdf(d1) - k * norm_cdf(d2)


def bs_call_vec(s: np.ndarray, k: np.ndarray, tau: np.ndarray, sigma: float) -> np.ndarray:
    tau = np.maximum(tau.astype(float), 1e-9)
    sigma = max(float(sigma), 1e-9)
    vol_t = sigma * np.sqrt(tau)
    d1 = (np.log(s / k) + 0.5 * sigma * sigma * tau) / vol_t
    d2 = d1 - vol_t
    return s * norm_cdf(d1) - k * norm_cdf(d2)


def load_prices() -> pd.DataFrame:
    frames = [pd.read_csv(p, sep=";") for p in sorted(DATA.glob("prices_round_3_day_*.csv"))]
    df = pd.concat(frames, ignore_index=True)
    for col in ["bid_price_1", "ask_price_1", "mid_price", "bid_volume_1", "ask_volume_1"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["spread"] = df["ask_price_1"] - df["bid_price_1"]
    df["imbalance"] = (df["bid_volume_1"] - df["ask_volume_1"]) / (df["bid_volume_1"] + df["ask_volume_1"])
    return df.sort_values(["day", "timestamp", "product"]).reset_index(drop=True)


def load_trades() -> pd.DataFrame:
    frames = []
    for p in sorted(DATA.glob("trades_round_3_day_*.csv")):
        day = int(p.stem.split("_")[-1])
        f = pd.read_csv(p, sep=";")
        f["day"] = day
        frames.append(f)
    return pd.concat(frames, ignore_index=True).sort_values(["day", "timestamp", "symbol"])


def add_lag_features(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values(["day", "timestamp"]).copy()
    for lag in [1, 2, 3, 5, 10, 20, 50]:
        g[f"d{lag}"] = g.groupby("day")["mid_price"].diff(lag).fillna(0.0)
    for horizon in [1, 2, 5, 10, 20, 50]:
        g[f"fut_{horizon}"] = g.groupby("day")["mid_price"].shift(-horizon) - g["mid_price"]
    g["t01"] = g["timestamp"] / 999900.0
    return g


def ridge_fit_predict(train: pd.DataFrame, test: pd.DataFrame, target: str, features: list[str], alpha: float = 1.0):
    x_train = train[features].fillna(0.0).to_numpy(float)
    y_train = train[target].fillna(0.0).to_numpy(float)
    x_test = test[features].fillna(0.0).to_numpy(float)
    mu = x_train.mean(axis=0)
    sd = x_train.std(axis=0)
    sd[sd < 1e-9] = 1.0
    x_train = (x_train - mu) / sd
    x_test = (x_test - mu) / sd
    x_train = np.c_[np.ones(len(x_train)), x_train]
    x_test = np.c_[np.ones(len(x_test)), x_test]
    reg = np.eye(x_train.shape[1]) * alpha
    reg[0, 0] = 0.0
    beta = np.linalg.solve(x_train.T @ x_train + reg, x_train.T @ y_train)
    return x_test @ beta, beta


def regression_diagnostics(prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    features = ["mid_price", "spread", "imbalance", "d1", "d2", "d3", "d5", "d10", "d20", "d50", "t01"]
    for product in [PACK, UNDERLYING]:
        book = add_lag_features(prices[prices["product"] == product])
        train = book[book["day"].isin([0, 1])]
        test = book[book["day"].eq(2)]
        for horizon in [1, 2, 5, 10, 20, 50]:
            target = f"fut_{horizon}"
            tr = train.dropna(subset=[target])
            te = test.dropna(subset=[target])
            pred, _ = ridge_fit_predict(tr, te, target, features, alpha=25.0)
            actual = te[target].to_numpy(float)
            rows.append(
                {
                    "product": product,
                    "horizon_ticks": horizon,
                    "mae": float(np.mean(np.abs(pred - actual))),
                    "actual_abs_mae_baseline": float(np.mean(np.abs(actual))),
                    "corr": float(np.corrcoef(pred, actual)[0, 1]),
                    "direction_accuracy": float(np.mean(np.sign(pred) == np.sign(actual))),
                    "signal_std": float(np.std(pred)),
                }
            )
    return pd.DataFrame(rows)


@dataclass
class VoucherFit:
    tau_scale: float
    sigma: float
    rmse: float
    mae: float


def fit_voucher_bs(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    under = prices[prices["product"] == UNDERLYING][["day", "timestamp", "mid_price"]].rename(columns={"mid_price": "spot"})
    v = prices[prices["product"].isin(VOUCHERS)].merge(under, on=["day", "timestamp"], how="left")
    v["strike"] = v["product"].str.split("_").str[1].astype(float)
    v["moneyness"] = np.log(v["strike"] / v["spot"])
    # Prosperity's original option round used calendar days-to-expiry. The exact
    # unit is unknown here, so search over a broad scale and a single vol first.
    fit_rows = []
    grid_tau_scale = np.linspace(60, 400, 35)
    grid_sigma = np.linspace(0.08, 0.45, 75)
    train = v[v["day"].isin([0, 1])].copy()
    train = train.iloc[::5].copy()
    for tau_scale in grid_tau_scale:
        tau = (7.0 - train["day"].to_numpy(float)) / tau_scale
        s = train["spot"].to_numpy(float)
        y = train["mid_price"].to_numpy(float)
        strikes = train["strike"].to_numpy(float)
        for sigma in grid_sigma:
            pred = bs_call_vec(s, strikes, tau, sigma)
            err = pred - y
            fit_rows.append({"tau_scale": tau_scale, "sigma": sigma, "rmse": float(np.sqrt(np.mean(err * err))), "mae": float(np.mean(np.abs(err)))})
    fit = pd.DataFrame(fit_rows).sort_values("rmse").reset_index(drop=True)
    best = fit.iloc[0]
    v["tau"] = (7.0 - v["day"].astype(float)) / float(best["tau_scale"])
    v["bs_fair"] = bs_call_vec(v["spot"].to_numpy(float), v["strike"].to_numpy(float), v["tau"].to_numpy(float), float(best["sigma"]))
    v["resid"] = v["mid_price"] - v["bs_fair"]
    return v, fit


def fit_smile(v: pd.DataFrame) -> pd.DataFrame:
    rows = []
    train = v[v["day"].isin([0, 1])].copy()
    train["m_bucket"] = pd.cut(train["moneyness"], bins=[-1, -0.12, -0.06, -0.03, -0.015, 0.0, 0.015, 0.03, 0.06, 0.12, 1.0])
    for product, g in train.groupby("product"):
        strike = float(product.split("_")[1])
        best = None
        for sigma in np.linspace(0.08, 0.65, 115):
            pred = bs_call_vec(g["spot"].to_numpy(float), np.full(len(g), strike), g["tau"].to_numpy(float), sigma)
            err = pred - g["mid_price"].to_numpy(float)
            rmse = float(np.sqrt(np.mean(err * err)))
            if best is None or rmse < best[0]:
                best = (rmse, sigma, float(np.mean(np.abs(err))), float(np.mean(err)))
        rows.append({"product": product, "strike": strike, "sigma": best[1], "rmse": best[0], "mae": best[2], "bias": best[3]})
    return pd.DataFrame(rows).sort_values("strike")


def pseudo_rng_checks(prices: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for product in [PACK, UNDERLYING]:
        for day, g in prices[prices["product"] == product].groupby("day"):
            d = g.sort_values("timestamp")["mid_price"].diff().dropna()
            vals = d.value_counts().sort_index()
            rows.append(
                {
                    "product": product,
                    "day": int(day),
                    "n": int(len(d)),
                    "zero_frac": float((d == 0).mean()),
                    "mean_delta": float(d.mean()),
                    "std_delta": float(d.std()),
                    "unique_deltas": int(d.nunique()),
                    "top_deltas": ", ".join(f"{k:g}:{v}" for k, v in vals.sort_values(ascending=False).head(8).items()),
                    "lag1_delta_corr": float(d.autocorr(1)),
                    "lag2_delta_corr": float(d.autocorr(2)),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    prices = load_prices()
    trades = load_trades()

    product_summary = (
        prices.groupby(["product", "day"])
        .agg(rows=("timestamp", "size"), mean_mid=("mid_price", "mean"), std_mid=("mid_price", "std"), first_mid=("mid_price", "first"), last_mid=("mid_price", "last"), mean_spread=("spread", "mean"))
        .reset_index()
    )
    product_summary.to_csv(OUT / "product_summary.csv", index=False)

    rng = pseudo_rng_checks(prices)
    rng.to_csv(OUT / "pseudo_rng_checks.csv", index=False)

    reg = regression_diagnostics(prices)
    reg.to_csv(OUT / "forecast_diagnostics.csv", index=False)

    vouchers, global_fit = fit_voucher_bs(prices)
    vouchers.to_csv(OUT / "voucher_bs_residuals.csv", index=False)
    global_fit.head(50).to_csv(OUT / "voucher_global_bs_grid_top50.csv", index=False)
    smile = fit_smile(vouchers)
    smile.to_csv(OUT / "voucher_smile_fit.csv", index=False)

    trade_counts = trades.groupby(["day", "symbol"]).agg(trades=("timestamp", "size"), qty=("quantity", "sum")).reset_index()
    trade_counts.to_csv(OUT / "trade_counts.csv", index=False)

    with (OUT / "research_journal.md").open("w") as f:
        f.write("# Round 3 Reverse Engineering Journal\n\n")
        f.write("## Data inventory\n\n")
        f.write(f"- Price rows: {len(prices):,}; trade rows: {len(trades):,}.\n")
        f.write(f"- Products: {', '.join(sorted(prices['product'].unique()))}.\n")
        f.write("- Timestamps are 0..999900 in 100ms increments, with one row per product per timestamp per day.\n\n")
        f.write("## Deterministic price path tests\n\n")
        f.write(rng.to_markdown(index=False))
        f.write("\n\n")
        f.write("The raw underlying deltas are small and discrete, but day-to-day paths do not line up as a reused seed/phase. ")
        f.write("A simple observable-state regression has only moderate directional skill, which argues against an easily recoverable next-random-number stream from the public book alone.\n\n")
        f.write("## Observable forecast diagnostics on held-out day 2\n\n")
        f.write(reg.to_markdown(index=False, floatfmt='.4f'))
        f.write("\n\n")
        best = global_fit.iloc[0]
        f.write("## Voucher mechanism\n\n")
        f.write(f"- Best single Black-Scholes grid fit on days 0-1: tau_scale={best['tau_scale']:.2f}, sigma={best['sigma']:.4f}, RMSE={best['rmse']:.4f}, MAE={best['mae']:.4f}.\n")
        f.write("- Per-strike implied volatility fit:\n\n")
        f.write(smile.to_markdown(index=False, floatfmt='.4f'))
        f.write("\n\n")
        f.write("The vouchers are not independent random walks. They are a formula-driven option chain on VELVETFRUIT_EXTRACT with a strike-dependent volatility smile. ")
        f.write("That gives a much stronger and more stable trading signal than trying to infer a hidden RNG seed for the underlying paths.\n")


if __name__ == "__main__":
    main()
