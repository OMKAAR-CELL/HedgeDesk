"use client";

import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const CURRENCIES = ["USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD", "CAD", "CHF"];
const AGENTS = ["Coordinator", "Exposure", "Forecast", "Pricing", "Recommender"];

const PRESETS = [
  { name: "Comfortable margin", cost: "5000000" },
  { name: "Tight margin", cost: "5600000" },
];

function fmtInr(x) {
  const sign = x < 0 ? "-" : "";
  const a = Math.abs(x);
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} lakh`;
  return `${sign}₹${Math.round(a).toLocaleString("en-IN")}`;
}

const hedgeLabel = (r) =>
  r === 0 ? "No hedge" : r === 1 ? "Full hedge" : `${Math.round(r * 100)}% hedged`;

export default function Home() {
  const [form, setForm] = useState({ amount: "60000", currency: "USD", days: "90", cost: "5600000" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [view, setView] = useState(0);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  async function analyze(e) {
    e?.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!data.ok) {
        setError(data.reply || data.error || "Something went wrong.");
      } else {
        setResult(data.result);
        setView(data.result.recommended_ratio ?? 0);
      }
    } catch {
      setError("Could not reach the server.");
    } finally {
      setLoading(false);
    }
  }

  let chartData = [];
  if (result) {
    const { edges, pct } = result.histogram;
    const idx = Math.max(0, result.options.findIndex((o) => o.ratio === view));
    chartData = edges.slice(0, -1).map((lo, i) => {
      const mid = (lo + edges[i + 1]) / 2;
      return { x: (mid / 1e5).toFixed(1), pct: pct[idx][i], loss: mid < 0 };
    });
  }

  const input = result?.input;

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-5xl px-4 py-10">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-teal-900">HedgeDesk</h1>
          <p className="mt-1 text-slate-600">
            Should you hedge this export invoice? Five agents simulate the rupee and tell you.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
            {AGENTS.map((a, i) => (
              <span key={a} className="flex items-center gap-2">
                <span className="rounded-full bg-teal-900 px-3 py-1 font-medium text-white">{a}</span>
                {i < AGENTS.length - 1 && <span className="text-slate-400">→</span>}
              </span>
            ))}
          </div>
        </header>

        <form onSubmit={analyze} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-sm font-medium">
              Invoice amount (in foreign currency)
              <input type="number" min="1" required value={form.amount} onChange={set("amount")}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </label>
            <label className="text-sm font-medium">
              Currency
              <input list="currencies" required maxLength={3} value={form.currency}
                onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 uppercase" />
              <datalist id="currencies">
                {CURRENCIES.map((c) => <option key={c} value={c} />)}
              </datalist>
            </label>
            <label className="text-sm font-medium">
              Due in (days)
              <input type="number" min="1" max="1095" required value={form.days} onChange={set("days")}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </label>
            <label className="text-sm font-medium">
              Your cost (₹)
              <input type="number" min="1" required value={form.cost} onChange={set("cost")}
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="submit" disabled={loading}
              className="rounded-lg bg-teal-900 px-5 py-2 font-semibold text-white hover:bg-teal-800 disabled:opacity-50">
              {loading ? "Agents working…" : "Analyse"}
            </button>
            <span className="text-xs text-slate-500">Quick fill:</span>
            {PRESETS.map((p) => (
              <button key={p.name} type="button" onClick={() => setForm({ ...form, cost: p.cost })}
                className="rounded-full border border-slate-300 px-3 py-1 text-xs hover:bg-slate-100">
                {p.name}
              </button>
            ))}
          </div>
        </form>

        {error && (
          <div className="mt-6 whitespace-pre-line rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        )}

        {result && (
          <section className="mt-6 space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <Stat label={`Spot ${input.currency}/INR`} value={result.market.spot.toFixed(2)} />
              <Stat label="Volatility (a year)" value={`${(result.market.vol * 100).toFixed(1)}%`} />
              <Stat label="Forward (estimated)" value={result.forward ? result.forward.toFixed(2) : "n/a"} />
              <Stat label="Data" value={result.market.source} />
              <Stat label="Invoice value today" value={fmtInr(input.amount * result.market.spot)} />
            </div>

            <div className="rounded-xl border border-teal-200 bg-teal-50 p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-teal-800">Recommendation</p>
              <p className="mt-1 text-lg font-semibold text-teal-950">
                {result.recommended_ratio !== null
                  ? hedgeLabel(result.recommended_ratio)
                  : result.forward === null
                    ? "No forward available"
                    : "No hedge recommended"}
              </p>
              <p className="mt-1 text-sm text-teal-900">{result.reason}</p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {result.options.map((o) => {
                const active = o.ratio === view;
                const best = o.ratio === result.recommended_ratio;
                return (
                  <button key={o.ratio} type="button" onClick={() => setView(o.ratio)}
                    className={`rounded-xl border p-4 text-left shadow-sm transition ${
                      active ? "border-teal-700 bg-white ring-2 ring-teal-700" : "border-slate-200 bg-white hover:border-slate-400"
                    }`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">{hedgeLabel(o.ratio)}</span>
                      {best && (
                        <span className="rounded-full bg-amber-400 px-2 py-0.5 text-xs font-bold text-amber-950">
                          Recommended
                        </span>
                      )}
                    </div>
                    <dl className="mt-3 space-y-1 text-sm">
                      <Row k="Average profit" v={fmtInr(o.mean)} />
                      <Row k="Worst 5% of cases" v={fmtInr(o.p5)} bad={o.p5 < 0} />
                      <Row k="Chance of loss" v={`${(o.prob_loss * 100).toFixed(0)}%`} bad={o.prob_loss >= 0.05} />
                    </dl>
                  </button>
                );
              })}
            </div>

            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="font-semibold">Profit across 10,000 rupee scenarios — {hedgeLabel(view)}</h2>
              <p className="text-xs text-slate-500">Red bars are scenarios where the order loses money. Click a card above to compare.</p>
              <div className="mt-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="x" minTickGap={16}
                      label={{ value: "Profit on the order (₹ lakh)", position: "insideBottom", offset: -12 }} />
                    <YAxis unit="%" />
                    <Tooltip formatter={(v) => [`${v}%`, "of scenarios"]}
                      labelFormatter={(l) => `Profit ≈ ₹${l} lakh`} />
                    <Bar dataKey="pct" radius={[3, 3, 0, 0]}>
                      {chartData.map((d, i) => (
                        <Cell key={i} fill={d.loss ? "#c0392b" : "#0b4f5c"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {result.market.source !== "live" && (
              <p className="text-sm text-amber-800">
                Note: rates came from {result.market.source} data, not live market prices.
              </p>
            )}
          </section>
        )}

        <footer className="mt-10 text-xs text-slate-500">
          Decision support, not financial advice. Real hedges are executed through an authorised dealer bank.
        </footer>
      </div>
    </main>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold">{value}</p>
    </div>
  );
}

function Row({ k, v, bad }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate-500">{k}</dt>
      <dd className={`font-medium ${bad ? "text-red-700" : ""}`}>{v}</dd>
    </div>
  );
}