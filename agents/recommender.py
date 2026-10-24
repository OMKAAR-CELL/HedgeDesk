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
    ctx.logger.info(f"[{job.session[:8]}] recommender: ratio={best_ratio}")
    await ctx.send(address("coordinator"), extend(job, reply=report, options=None))


if __name__ == "__main__":
    agent.run()
