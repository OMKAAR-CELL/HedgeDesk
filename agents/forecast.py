import asyncio

from model.montecarlo import get_market_data, simulate
from uagents import Context

from agents.config import address, make_agent
from agents.messages import Job, extend

agent = make_agent("forecast")


@agent.on_message(Job)
async def handle(ctx: Context, sender: str, job: Job):
    market = await asyncio.to_thread(get_market_data, job.currency)  # network call
    if market is None:
        msg = f"I don't recognise the currency '{job.currency}'. Try USD, EUR, GBP or AED."
        await ctx.send(address("coordinator"), extend(job, reply=msg))
        return
    spot, vol, source = market
    sim = simulate(spot, job.days, job.amount, job.cost_inr, vol)
    ctx.logger.info(f"[{job.session[:8]}] forecast: spot={spot:.2f} vol={vol:.3f} ({source})")
    await ctx.send(address("pricing"), extend(
        job, spot=spot, vol=vol, source=source,
        rates=[round(float(r), 4) for r in sim["rates"]]))


if __name__ == "__main__":
    agent.run()
