from pydantic import BaseModel, Field
from typing import Optional

from alm.agents.get_more_context_agent.node import LokiRouterSchema
from alm.models import LogEntry


class ContextAgentState(BaseModel):
    log_entry: LogEntry = Field(description="The log entry that triggered the alert")
    log_summary: str = Field(description="The summary of Ansible error log")
    cheat_sheet_context: Optional[str] = Field(
        description="The context from the cheat sheet that will help understand the log error.",
        default=None,
    )
    expert_classification: Optional[str] = Field(
        default=None, description="Classification of the log message"
    )
    loki_router_result: Optional[LokiRouterSchema] = Field(
        description="The result from the loki router that will help understand the log error.",
        default=None,
    )
    loki_context: Optional[str] = Field(
        description="The context from the loki db that will help understand the log error.",
        default=None,
    )
