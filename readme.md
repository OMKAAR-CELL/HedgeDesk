# HedgeDesk

A multi-agent forex hedging desk for Indian MSME exporters, built for **Fetch-A-Thon 3.0** on [uAgents](https://uagents.fetch.ai), Agentverse and ASI:One.

An exporter ships goods and gets paid in foreign currency about three months later. The rupee keeps moving in between, and one bad move can wipe out the profit on an order. HedgeDesk takes a plain-English invoice and answers three questions: how risky is this order, what would a forward lock in, and should I hedge?

**Team:** Omkaar (team leader), Aditi Sharma, Manasvi Kaushik

## Try it

Send this to the agent on ASI:One:

```
Invoice 60000 USD due in 90 days, my cost is 5150000 INR
```

You get back the spot rate, volatility, an estimated forward rate, and three hedge options (0%, 50%, 100%) with the average profit, the worst 5% case and the chance of loss, plus a recommendation.

A tighter-margin order shows a different answer:

```
Invoice 60000 USD due in 90 days, my cost is 5600000 INR
```

**Input format:** amount and currency after `invoice`, the due date as `in N days` or `in N months`, and the cost after `cost`.

**Currencies:** any currency that has a Yahoo Finance pair against INR (for example USD, EUR, GBP, AED, SGD, JPY, AUD, CAD, CHF) gets live spot, volatility and Monte Carlo risk. Forward and hedge options are priced for currencies with an interest rate in `data/rates.py` (currently INR, USD, EUR, GBP, AED, SGD). For any other currency the report shows the unhedged risk only and says no forward could be priced. To enable hedging for another currency, add its interest rate to `data/rates.py`.

## How it works

Five agents, each owning one job and passing a single `Job` message down the chain:

| # | Agent | Job |
|---|-------|-----|
| 1 | **Coordinator** | Talks to the user over the ASI:One chat protocol (Agentverse mailbox) and returns the final answer |
| 2 | **Exposure** | Parses and validates the invoice |
| 3 | **Forecast** | Fetches currency/INR history and runs a 10,000-path Monte Carlo simulation |
| 4 | **Pricing** | Prices the forward with interest-rate parity and computes profit for each hedge ratio |
| 5 | **Recommender** | Applies a simple, explainable rule on the chance of loss and writes the report |

```
User -> ASI:One -> Coordinator -> Exposure -> Forecast -> Pricing -> Recommender -> Coordinator -> User
```

Numbers come from code, not from an LLM. If any stage fails (bad input, unknown currency), the error goes straight back to the user.

**Recommendation rule** (chance of loss with no hedge): 20% or more recommends a full hedge, 5% to 20% a 50% hedge, below 5% hedging is optional. If even a full hedge loses money at the forward rate, no hedge is recommended.

**Data sources:** each reply is labelled `live` (fetched from Yahoo Finance via yfinance), `cache` (last saved live rate) or `fallback` (built-in approximate rates, used only if both fail).

## Project layout

```
agents/
  coordinator.py   chat protocol + mailbox, session handling
  exposure.py      invoice parsing
  forecast.py      market data + Monte Carlo
  pricing.py       forward pricing + hedge options
  recommender.py   recommendation + report
  messages.py      the shared Job message
  config.py        seeds, ports, agent addresses
model/
  forward.py       interest-rate parity forward
  montecarlo.py    market data (yfinance, cache, fallback) + simulation
data/
  rates.py         assumed interest rates per currency
pipeline.py        shared logic; analyze() runs the whole chain in one process
run_all.py         starts all five agents
```

## Setup

Requires Python 3.10+.

```bash
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (see `.env.example`). Each agent needs its own seed phrase:

```
COORDINATOR_SEED=
EXPOSURE_SEED=
FORECAST_SEED=
PRICING_SEED=
RECOMMENDER_SEED=
```

Use a different long, random phrase for each. **Never commit `.env`**: anyone with a seed controls that agent.

## Run

```bash
python run_all.py
```

To make the Coordinator reachable from ASI:One:

1. Open the Coordinator's **Agent inspector** link from the terminal.
2. Click **Connect**, then **Mailbox**.
3. In Agentverse, open the agent and use **Chat with Agent**.

Only the Coordinator needs the mailbox. The other four agents talk to each other locally, so keep `run_all.py` running while you use it.

## Test

Logic only, no agents:

```bash
python pipeline.py
```

## Limitations

- Forward rates are estimated from **assumed** interest rates in `data/rates.py`, not live bank quotes.
- The simulation assumes lognormal currency moves with zero drift, using one year of historical volatility.
- Handles one invoice per message. Option strategies and monthly exposure totals are not built yet.
- The agents run on your machine, so the demo works only while `run_all.py` is running.

## Roadmap

Upload invoices as PDFs, total exposure by month, add option strategies, show live bank forward quotes, and a web frontend.

---

*Decision support, not financial advice. Real hedges are executed through authorised dealer banks.*