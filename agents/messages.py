from typing import Dict, List, Optional

from uagents import Model


class Job(Model):
    """One envelope passed down the chain. Each agent fills in its own fields.
    If `reply` is set, the job is finished (result or error) and goes back to the user."""
    session: str
    text: str = ""
    # Exposure
    amount: Optional[float] = None
    currency: Optional[str] = None
    days: Optional[int] = None
    cost_inr: Optional[float] = None
    # Forecast
    spot: Optional[float] = None
    vol: Optional[float] = None
    source: Optional[str] = None
    rates: Optional[List[float]] = None
    # Pricing
    fwd: Optional[float] = None
    options: Optional[List[Dict[str, float]]] = None
    # Final text for the user (also used for early errors)
    reply: Optional[str] = None


def extend(job: Job, **fields) -> Job:
    data = job.dict()
    data.update(fields)
    return Job(**data)
