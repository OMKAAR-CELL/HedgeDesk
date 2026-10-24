import os, sys
sys.path.insert(0, ".")
from uagents import Agent, Bureau, Context
from agents.config import _seed, address
from agents.messages import Job
from agents import exposure, forecast, pricing, recommender

tests = [
    "Invoice 60000 USD due in 90 days, my cost is 5000000 INR",
    "Invoice 60000 XYZ due in 90 days, my cost is 5000000 INR",
    "hello",
]
fake = Agent(name="fake-coord", seed=_seed("coordinator"))
got = []

@fake.on_event("startup")
async def go(ctx: Context):
    for i, t in enumerate(tests):
        await ctx.send(address("exposure"), Job(session=f"s{i}", text=t))

@fake.on_message(Job)
async def rec(ctx, sender, job):
    got.append(job.session)
    print(f"--- {job.session} ---\n{job.reply}\n")
    if len(got) == len(tests):
        os._exit(0)

b = Bureau(port=8010)
for a in (exposure.agent, forecast.agent, pricing.agent, recommender.agent, fake):
    b.add(a)
b.run()