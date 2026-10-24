from pipeline import parse_invoice, validate_invoice
from uagents import Context

from agents.config import address, make_agent
from agents.messages import Job, extend

agent = make_agent("exposure")


@agent.on_message(Job)
async def handle(ctx: Context, sender: str, job: Job):
    p = parse_invoice(job.text)
    err = validate_invoice(p)
    if err:
        await ctx.send(address("coordinator"), extend(job, reply=err))
        return
    ctx.logger.info(f"[{job.session[:8]}] exposure: {p}")
    await ctx.send(address("forecast"), extend(job, **p))


if __name__ == "__main__":
    agent.run()
