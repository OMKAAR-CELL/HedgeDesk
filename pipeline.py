import re

import numpy as np

from data.rates import RATES
from model.forward import forward_rate
from model.montecarlo import get_market_data, simulate

EXAMPLE = "Invoice 60000 EUR due in 90 days, my cost is 5000000 INR"
HEDGE_RATIOS = [0.0, 0.5, 1.0]
NUM = r"\d[\d,]*(?:\.\d+)?"


def parse_invoice(text):
    """Return a dict with amount, currency, days, cost_inr. A field is None if not found."""
    amount_m = re.search(rf"invoice\s+(?:of\s+)?({NUM})\s*([A-Za-z]{{3}})\b", text, re.I)
    days_m = re.search(r"(?:due\s+)?in\s+(\d+)\s*(days?|months?)\b", text, re.I)
    cost_m = re.search(rf"cost(?:\s+is)?\s+(?:rs\.?\s*|₹\s*)?({NUM})\s*(?:INR)?", text, re.I)

    amount = float(amount_m.group(1).replace(",", "")) if amount_m else None
    currency = amount_m.group(2).upper() if amount_m else None

    days = None
    if days_m:
        n = int(days_m.group(1))
        days = n * 30 if days_m.group(2).lower().startswith("month") else n

    cost_inr = float(cost_m.group(1).replace(",", "")) if cost_m else None
    return {"amount": amount, "currency": currency, "days": days, "cost_inr": cost_inr}


def validate_invoice(p):
    """Return an error message for the user, or None if the parsed invoice is usable."""
    missing = [k for k, v in p.items() if v is None]
    if missing:
        return f"I couldn't find: {', '.join(missing)}.\nPlease send it like this: {EXAMPLE}"
    if p["amount"] <= 0 or p["days"] <= 0 or p["cost_inr"] <= 0:
        return f"Amount, days and cost must all be positive.\nExample: {EXAMPLE}"
    return None


def fmt_inr(x):
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1e5:
        return f"{sign}₹{x / 1e5:.2f} lakh"
    return f"{sign}₹{x:,.0f}"


def evaluate_options(amount, cost_inr, rates, fwd):
    """Profit stats for each hedge ratio. The hedged part is locked at fwd, the rest follows the simulated rate."""
    options = []
    for h in HEDGE_RATIOS:
        if h > 0 and fwd is None:
            continue
        locked = h * amount * fwd if h > 0 else 0.0
        profit = locked + (1 - h) * amount * rates - cost_inr
        options.append({
            "ratio": h,
            "mean": float(profit.mean()),
            "p5": float(np.percentile(profit, 5)),
            "prob_loss": float((profit < 0).mean()),
        })
    return options


def recommend(options, fwd):
    """Simple, explainable rule based on the chance of loss with no hedge."""
    unhedged = options[0]
    if fwd is None:
        return None, "No reliable forward could be priced for this currency, so only the unhedged risk is shown. Check with your bank whether a forward is available, or consider invoicing in USD or EUR."
    full = next(o for o in options if o["ratio"] == 1.0)
    if full["mean"] < 0:
        return None, "Even a fully hedged order makes a loss at today's forward rate. Hedging would lock that loss in, so no hedge is recommended. Revisit your pricing or costs before shipping."
    if unhedged["prob_loss"] >= 0.20:
        return 1.0, "High chance of loss without a hedge. A full hedge removes the currency risk and locks in a profit."
    if unhedged["prob_loss"] >= 0.05:
        return 0.5, "Moderate chance of loss. Hedging about half protects the downside and keeps some benefit if the rupee weakens."
    return 0.0, "Low chance of loss. Hedging is optional; you could stay unhedged."


def build_report(p, spot, vol, source, fwd, options, best_ratio, reason):
    lines = [
        f"HedgeDesk analysis: {p['amount']:,.0f} {p['currency']} due in {p['days']} days",
        f"Spot {p['currency']}/INR: {spot:.2f}  |  Volatility: {vol * 100:.1f}% a year  |  Data: {source}",
    ]
    if fwd is not None:
        lines.append(f"Forward rate (estimated): {fwd:.2f}")
    lines += ["", "Hedge options (profit after your cost of " + fmt_inr(p["cost_inr"]) + "):"]
    for o in options:
        tag = "  <- recommended" if best_ratio is not None and o["ratio"] == best_ratio else ""
        lines.append(
            f"- {int(o['ratio'] * 100)}% hedged: average {fmt_inr(o['mean'])}, "
            f"worst 5% {fmt_inr(o['p5'])}, chance of loss {o['prob_loss'] * 100:.0f}%{tag}"
        )
    lines += ["", "Recommendation: " + reason]
    if source != "live":
        lines.append(f"Note: rates came from {source} data, not live market prices.")
    lines.append("Decision support, not financial advice. Real hedges are executed through an authorised dealer bank.")
    return "\n".join(lines)


def analyze(text):
    """Single-process version of the whole chain. Used for tests and the Streamlit backup page."""
    p = parse_invoice(text)
    err = validate_invoice(p)
    if err:
        return err

    market = get_market_data(p["currency"])
    if market is None:
        return f"I don't recognise the currency '{p['currency']}'. Try USD, EUR, GBP or AED."
    spot, vol, source = market

    sim = simulate(spot, p["days"], p["amount"], p["cost_inr"], vol)
    fwd = forward_rate(spot, p["days"], RATES.get(p["currency"]), RATES["INR"])
    options = evaluate_options(p["amount"], p["cost_inr"], sim["rates"], fwd)
    best_ratio, reason = recommend(options, fwd)
    return build_report(p, spot, vol, source, fwd, options, best_ratio, reason)


if __name__ == "__main__":
    for t in [
        "Invoice 60000 USD due in 90 days, my cost is 5150000 INR",
        "invoice of 60,000 eur due in 3 months, cost 5,000,000 INR",
        "Invoice 60000 USD due in 90 days, my cost is 6000000 INR",
        "Invoice 60000 XYZ due in 90 days, my cost is 5000000 INR",
        "Invoice 60000 USD, my cost is 5000000 INR",
        "hello",
    ]:
        print("INPUT:", t)
        print(analyze(t))
        print("-" * 70)
