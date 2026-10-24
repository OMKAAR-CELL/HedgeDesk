"""Shared wiring: seeds, ports, and agent addresses derived from the seeds."""
import os

from dotenv import load_dotenv
from uagents import Agent
from uagents.crypto import Identity

load_dotenv()

PORTS = {"coordinator": 8000, "exposure": 8001, "forecast": 8002,
         "pricing": 8003, "recommender": 8004}


def _seed(name: str) -> str:
    return os.environ[f"{name.upper()}_SEED"]


def address(name: str) -> str:
    """Address of another agent, computed from its seed (no hard-coding)."""
    return Identity.from_seed(_seed(name), 0).address


def make_agent(name: str, mailbox: bool = False) -> Agent:
    port = PORTS[name]
    if mailbox:  # only the coordinator talks to ASI:One
        port = int(os.environ.get("PORT", port))
        return Agent(name=f"hedgedesk-{name}", seed=_seed(name), port=port, mailbox=True)
    return Agent(name=f"hedgedesk-{name}", seed=_seed(name), port=port,
                 endpoint=[f"http://127.0.0.1:{port}/submit"])
