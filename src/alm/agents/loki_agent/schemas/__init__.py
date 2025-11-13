"""
Loki agent schemas for inputs and outputs.
"""

from alm.agents.loki_agent.constants import (
    DEFAULT_START_TIME,
    DEFAULT_END_TIME,
    DEFAULT_LIMIT,
    DEFAULT_DIRECTION,
    DEFAULT_LINE_ABOVE,
)
from alm.agents.loki_agent.schemas.inputs import (
    LogLevel,
    FileLogSchema,
    SearchTextSchema,
    LogLinesAboveSchema,
)
from alm.agents.loki_agent.schemas.outputs import (
    ToolStatus,
    LogLabels,
    LogEntry,
    LogToolOutput,
    LokiAgentOutput,
    IdentifyMissingDataSchema,
)

__all__ = [
    # Inputs
    "LogLevel",
    "FileLogSchema",
    "SearchTextSchema",
    "LogLinesAboveSchema",
    "DEFAULT_START_TIME",
    "DEFAULT_END_TIME",
    "DEFAULT_LIMIT",
    "DEFAULT_DIRECTION",
    "DEFAULT_LINE_ABOVE",
    # Outputs
    "ToolStatus",
    "LogLabels",
    "LogEntry",
    "LogToolOutput",
    "LokiAgentOutput",
    "IdentifyMissingDataSchema",
]
