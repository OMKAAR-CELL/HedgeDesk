import json
import os
import numpy as np

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rate_cache.json")

FALLBACK_SPOT = {"USD": 88.0, "EUR": 100.0, "GBP": 115.0, "AED": 24.0, "JPY": 0.58, "SGD": 68.0}
FALLBACK_VOL = 0.065


def _load_cache():
    try:
        with open(CACHE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _history(currency):
    """Daily closes for <currency>/INR from yfinance, or None if unavailable."""
    try:
        import yfinance as yf
        px = yf.Ticker(f"{currency}INR=X").history(period="1y")["Close"].dropna()
        return px if len(px) > 30 else None
    except Exception:
        return None


def get_market_data(currency):
    """Return (spot, annual_vol, source) for <currency>/INR.
    source is 'live', 'cache' or 'fallback'. Returns None if the currency is unsupported."""
    currency = currency.upper().strip()
    cache = _load_cache()

    px = _history(currency)
    if px is not None:
        spot = float(px.iloc[-1])
        vol = float(np.log(px / px.shift(1)).dropna().std() * np.sqrt(252))
        cache[currency] = {"spot": spot, "vol": vol}
        _save_cache(cache)
        return spot, vol, "live"

    if currency in cache:
        return cache[currency]["spot"], cache[currency]["vol"], "cache"

    if currency in FALLBACK_SPOT:
        return FALLBACK_SPOT[currency], FALLBACK_VOL, "fallback"

    return None  # unsupported: let the Exposure agent reject it


def simulate(spot, days, amount_foreign, cost_inr, vol, n=10000, drift=0.0, seed=7):
    """Monte Carlo of <currency>/INR at the due date (lognormal).
    drift is an annual expected change in the rate; 0 means no view on the trend."""
    rng = np.random.default_rng(seed)
    t = days / 365.0
    z = rng.standard_normal(n)
    rate = spot * np.exp((drift - 0.5 * vol**2) * t + vol * np.sqrt(t) * z)
    profit = amount_foreign * rate - cost_inr
    return {
        "p5_rate": float(np.percentile(rate, 5)),
        "mean_rate": float(rate.mean()),
        "p95_rate": float(np.percentile(rate, 95)),
        "mean_profit": float(profit.mean()),
        "p5_profit": float(np.percentile(profit, 5)),
        "prob_loss": float((profit < 0).mean()),
        "rates": rate,  # full array, for the before/after chart
    }