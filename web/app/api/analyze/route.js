export const maxDuration = 60;
import { NextResponse } from "next/server";

const AGENT_API_URL = process.env.AGENT_API_URL || "http://127.0.0.1:8000";

function bad(message, status = 400) {
  return NextResponse.json({ ok: false, error: message }, { status });
}

export async function POST(request) {
  let body;
  try {
    body = await request.json();
  } catch {
    return bad("Invalid request.");
  }

  const amount = Number(body.amount);
  const days = Math.round(Number(body.days));
  const cost = Number(body.cost);
  const currency = String(body.currency || "").trim().toUpperCase();

  if (!/^[A-Z]{3}$/.test(currency)) return bad("Currency must be a 3-letter code, like USD.");
  if (!(amount > 0 && amount < 1e15)) return bad("Invoice amount must be a positive number.");
  if (!(days > 0 && days <= 1095)) return bad("Days must be between 1 and 1095.");
  if (!(cost > 0 && cost < 1e15)) return bad("Cost must be a positive number.");

  // The agents read a plain-English invoice, same as the ASI:One chat.
  const text = `Invoice ${amount} ${currency} due in ${days} days, my cost is ${cost} INR`;

  try {
    const res = await fetch(`${AGENT_API_URL}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
      cache: "no-store",
      signal: AbortSignal.timeout(60000),
    });
    if (!res.ok) return bad(`The agents returned an error (${res.status}).`, 502);

    const data = await res.json();
    let result = null;
    if (data.result_json) {
      try {
        result = JSON.parse(data.result_json);
      } catch {
        return bad("Could not read the agents' answer.", 502);
      }
    }
    // ok:false here means the agents answered with a message for the user
    // (bad invoice, unknown currency, timeout), not a server failure.
    return NextResponse.json({ ok: Boolean(data.ok && result), reply: data.reply, result });
  }  catch (e) {
    console.error("analyze failed:", e);
    return bad(`Can't reach the HedgeDesk agents (${e?.cause?.code || e?.name || e?.message}).`, 502);
  }
}
