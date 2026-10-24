import numpy as np
from data.rates import RATES
from model.forward import forward_rate
from pipeline import evaluate_options
from uagents import Context

from agents.config import address, make_agent
from agents.messages import Job, extend

agent = make_agent("pricing")


@agent.on_message(Job)
async def handle(ctx: Context, sender: str, job: Job):
    fwd = forward_rate(job.spot, job.days, RATES.get(job.currency), RATES["INR"])
    options = evaluate_options(job.amount, job.cost_inr, np.array(job.rates), fwd)
    ctx.logger.info(f"[{job.session[:8]}] pricing: fwd={fwd}, {len(options)} options")
    await ctx.send(address("recommender"), extend(job, fwd=fwd, options=options, rates=None))


if __name__ == "__main__":
    agent.run()
