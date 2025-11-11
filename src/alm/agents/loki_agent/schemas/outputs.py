"""
Pydantic schemas for Loki tool outputs.
These schemas define the output structure for each tool to ensure consistency.
"""

from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
from collections import defaultdict
from langchain_core.messages import ToolMessage

from alm.agents.loki_agent.constants import (
    LOG_CONTEXT_SEPARATOR_WIDTH,
    NANOSECONDS_PER_SECOND,
)
from .inputs import LogLevel


class ToolStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


class LogLabels(BaseModel):
    """Metadata labels for a single log entry from Loki"""

    detected_level: Optional[LogLevel] = Field(
        default=None, description="Detected level of the log"
    )
    filename: Optional[str] = Field(default=None, description="Filename of the log")
    job: Optional[str] = Field(default=None, description="Job of the log")
    service_name: Optional[str] = Field(
        default=None, description="Service name of the log"
    )


class LogEntry(BaseModel):
    """Represents a single log entry from Loki"""

    timestamp: str = Field(
        default="Unknown timestamp", description="Timestamp of the log"
    )
    log_labels: LogLabels = Field(description="Log labels of the log")
    message: str = Field(description="Message of the log")


class LogToolOutput(BaseModel):
    """Output schema for tools that retrieve logs"""

    status: ToolStatus = Field(description="Status of the operation")
    message: Optional[str] = Field(
        default=None, description="Human-readable message, especially for errors"
    )
    query: Optional[str] = Field(
        default=None, description="The LogQL query that was executed"
    )
    execution_time_ms: Optional[int] = Field(
        default=None, description="Query execution time in milliseconds"
    )
    logs: List[LogEntry] = Field(
        default_factory=list, description="List of log entries retrieved"
    )
    number_of_logs: int = Field(
        default=0, description="Total number of log entries returned"
    )

    def build_context(self) -> str:
        """
        Build a context for the step by step solution from the log entries.
        Groups logs by stream and sorts them by timestamp.
        """
        return build_log_context(self.logs)


class LokiAgentOutput(BaseModel):
    """Output schema for the Loki agent"""

    user_request: str = Field(description="User request that was processed")
    status: ToolStatus = Field(description="Status of the operation")
    message: Optional[str] = Field(
        default=None, description="Human-readable message, especially for errors"
    )
    agent_result: LogToolOutput = Field(description="Result of the agent")
    raw_output: str | Any = Field(description="Raw output of the agent")
    tool_messages: List[ToolMessage] = Field(
        default_factory=list, description="Tool messages from the agent execution"
    )


class IdentifyMissingDataSchema(BaseModel):
    missing_data_request: str = Field(
        description="Natural language description of what data/context is missing to fully understand and resolve the issue"
    )


# Helper functions for log context building


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime object for sorting"""
    try:
        # Try nanosecond timestamp (common in Loki)
        if timestamp_str.isdigit():
            # Convert nanoseconds to seconds
            timestamp_seconds = int(timestamp_str) / NANOSECONDS_PER_SECOND
            return datetime.fromtimestamp(timestamp_seconds)

        # Try ISO format
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        # Return epoch if parsing fails
        return datetime.fromtimestamp(0)


def format_timestamp(timestamp_str: str) -> str:
    """Convert timestamp to readable format"""
    dt = parse_timestamp(timestamp_str)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def build_log_context(logs: List["LogEntry"]) -> str:
    """
    Build a context for the step by step solution from the log entries.
    Groups logs by labels and sorts them by timestamp.
    """
    if not logs:
        print("WARNING: No logs found to build context from.")
        return ""

    # Group logs by labels
    logs_by_labels = defaultdict(list)
    for log in logs:
        # Convert labels dict to a string key for grouping
        labels_key = ", ".join(
            [
                f"{k}={v}"
                for k, v in sorted(log.log_labels.model_dump(exclude_none=True).items())
            ]
        )
        logs_by_labels[labels_key].append(log)

    # Build context with grouped and sorted logs
    context_parts = []

    for labels_key, label_logs in sorted(logs_by_labels.items()):
        # Sort logs within each label group by timestamp
        sorted_logs = sorted(label_logs, key=lambda x: parse_timestamp(x.timestamp))

        # Add labels header
        context_parts.append(f"\n{'=' * LOG_CONTEXT_SEPARATOR_WIDTH}")
        context_parts.append(f"Labels: {labels_key}")
        context_parts.append(f"{'=' * LOG_CONTEXT_SEPARATOR_WIDTH}")

        # Add logs for this label group
        for log in sorted_logs:
            readable_timestamp = format_timestamp(log.timestamp)
            context_parts.append(f"{readable_timestamp} - {log.message}")

    return "\n".join(context_parts)
