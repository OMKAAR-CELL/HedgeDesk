import asyncio
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from uagents import Context, Model, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, TextContent, chat_protocol_spec)

from agents.config import address, make_agent
from agents.messages import Job

REST_TIMEOUT = 45  # seconds to wait for the chain when called from the website

agent = make_agent("coordinator", mailbox=True)
protocol = Protocol(spec=chat_protocol_spec)

# session id -> who is waiting: a str (ASI:One sender address) or a Future (website request)
pending: dict = {}


class AnalyzeRequest(Model):
    text: str


class AnalyzeResponse(Model):
    ok: bool
    reply: str
    result_json: Optional[str] = None


def _now():
    return datetime.now(timezone.utc)


# ---------- Website door: POST /analyze ----------
@agent.on_rest_post("/analyze", AnalyzeRequest, AnalyzeResponse)
async def analyze_rest(ctx: Context, req: AnalyzeRequest) -> AnalyzeResponse:
    session = uuid4().hex
    fut = asyncio.get_running_loop().create_future()
    pending[session] = fut
    ctx.logger.info(f"[{session[:8]}] new request from website")
    await ctx.send(address("exposure"), Job(session=session, text=(req.text or "").strip()))
    try:
        job = await asyncio.wait_for(fut, timeout=REST_TIMEOUT)
    except asyncio.TimeoutError:
        pending.pop(session, None)
        return AnalyzeResponse(ok=False, reply="The agents took too long to answer. Please try again.")
    return AnalyzeResponse(
        ok=job.result_json is not None,
        reply=job.reply or "Sorry, something went wrong analysing that invoice.",
        result_json=job.result_json)


# ---------- ASI:One door: chat protocol ----------
@protocol.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(
        timestamp=_now(), acknowledged_msg_id=msg.msg_id))

    text = " ".join(c.text for c in msg.content if isinstance(c, TextContent)).strip()
    session = uuid4().hex
    pending[session] = sender
    ctx.logger.info(f"[{session[:8]}] new request from {sender[:12]}...")
    await ctx.send(address("exposure"), Job(session=session, text=text))


@protocol.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"Ack from {sender} for {msg.acknowledged_msg_id}")


# ---------- Result coming back from the chain (both doors) ----------
@agent.on_message(Job)
async def on_result(ctx: Context, sender: str, job: Job):
    target = pending.pop(job.session, None)
    if target is None:
        ctx.logger.warning(f"[{job.session[:8]}] result for unknown session")
        return
    if isinstance(target, asyncio.Future):
        if not target.done():
            target.set_result(job)
        return
    reply = job.reply or "Sorry, something went wrong analysing that invoice. Please try again."
    await ctx.send(target, ChatMessage(
        timestamp=_now(), msg_id=uuid4(),
        content=[TextContent(type="text", text=reply)]))


agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
