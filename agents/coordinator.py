from datetime import datetime, timezone
from uuid import uuid4

from uagents import Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement, ChatMessage, TextContent, chat_protocol_spec)

from agents.config import address, make_agent
from agents.messages import Job

agent = make_agent("coordinator", mailbox=True)
protocol = Protocol(spec=chat_protocol_spec)

# session id -> the ASI:One sender waiting for the answer (in memory; lost on restart)
pending: dict[str, str] = {}


def _now():
    return datetime.now(timezone.utc)


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


@agent.on_message(Job)
async def on_result(ctx: Context, sender: str, job: Job):
    user = pending.pop(job.session, None)
    if user is None:
        ctx.logger.warning(f"[{job.session[:8]}] result for unknown session")
        return
    reply = job.reply or "Sorry, something went wrong analysing that invoice. Please try again."
    await ctx.send(user, ChatMessage(
        timestamp=_now(), msg_id=uuid4(),
        content=[TextContent(type="text", text=reply)]))


agent.include(protocol, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
