import json

from pipeline import build_report, recommend
from uagents import Context

from agents.config import address, make_agent
from agents.messages import Job, extend

agent = make_agent("recommender")


@agent.on_message(Job)
async def handle(ctx: Context, sender: str, job: Job):
    best_ratio, reason = recommend(job.options, job.fwd)
    p = {"amount": job.amount, "currency": job.currency, "days": job.days, "cost_inr": job.cost_inr}
    report = build_report(p, job.spot, job.vol, job.source, job.fwd, job.options, best_ratio, reason)

    result = {
        "input": p,
        "market": {"spot": job.spot, "vol": job.vol, "source": job.source},
        "forward": job.fwd,
        "options": job.options,
        "histogram": {"edges": job.hist_edges, "pct": job.hist_pct},
        "recommended_ratio": best_ratio,
        "reason": reason,
        "report": report,
    }
    ctx.logger.info(f"[{job.session[:8]}] recommender: ratio={best_ratio}")
    await ctx.send(address("coordinator"), extend(
        job, reply=report, result_json=json.dumps(result),
        options=None, hist_edges=None, hist_pct=None))


if __name__ == "__main__":
    agent.run()
