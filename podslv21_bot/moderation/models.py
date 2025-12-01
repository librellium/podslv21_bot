from typing import Any, Literal

from pydantic import BaseModel


class ModerationEvent(BaseModel):
    type: str
    result: Any

class ModerationDecision(BaseModel):
    status: Literal["PASS", "REJECT"]
    explanation: str