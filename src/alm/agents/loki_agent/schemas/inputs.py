"""
Pydantic schemas for Loki query tools.
These schemas define the input parameters for each tool using args_schema.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field

from alm.agents.loki_agent.constants import (
    DEFAULT_DIRECTION,
    DEFAULT_END_TIME,
    DEFAULT_LIMIT,
    DEFAULT_LINE_ABOVE,
    DEFAULT_START_TIME,
)
from alm.models import LogLevel


class FileLogSchema(BaseModel):
    """Schema for get_file_log_by_name tool"""

    file_name: str = Field(
        description="File name to search for (e.g., 'nginx.log', 'api.log', 'database.log')"
    )
    log_timestamp: Optional[str] = Field(
        default=None,
        description="Reference timestamp for relative time calculations (Unix timestamp, or datetime string). REQUIRED when using relative times like '-5m'. Not needed when using absolute datetime strings.",
    )
    start_time: str | int = Field(
        default=DEFAULT_START_TIME,
        description="Relative offset from log_timestamp (e.g., '-1h'), Unix timestamp, absolute datetime string, or 'now'. Offsets require log_timestamp.",
    )
    end_time: str | int = Field(
        default=DEFAULT_END_TIME,
        description="Relative offset from log_timestamp (e.g., '-5m'), Unix timestamp, absolute datetime string, or 'now'. Offsets require log_timestamp.",
    )
    level: LogLevel | None = Field(
        default=None, description="Log level filter: error, warn, info, debug, unknown"
    )
    limit: int = Field(
        default=DEFAULT_LIMIT, description="Maximum number of log entries to return"
    )
    direction: Literal["backward", "forward"] = Field(
        default=DEFAULT_DIRECTION,
        description="Direction of the query: 'backward' or 'forward'",
    )


class SearchTextSchema(BaseModel):
    """Schema for search_logs_by_text tool"""

    text: str = Field(
        description="Text to search for in log messages (case-sensitive, e.g., 'ERROR', 'timeout', 'user login')"
    )
    log_timestamp: Optional[str] = Field(
        default=None,
        description="Reference timestamp for relative time calculations (Unix timestamp, or datetime string). REQUIRED when using relative times like '-5m'. Not needed when using absolute datetime strings.",
    )
    start_time: str | int = Field(
        default=DEFAULT_START_TIME,
        description="Relative offset from log_timestamp (e.g., '-1h'), Unix timestamp, absolute datetime string, or 'now'. Offsets require log_timestamp.",
    )
    end_time: str | int = Field(
        default=DEFAULT_END_TIME,
        description="Relative offset from log_timestamp (e.g., '-5m'), Unix timestamp, absolute datetime string, or 'now'. Offsets require log_timestamp.",
    )
    file_name: Optional[str] = Field(
        default=None,
        description="Optional: File name to search within (e.g., 'nginx.log'). If not specified, searches across all files.",
    )
    limit: int = Field(
        default=DEFAULT_LIMIT,
        description="Maximum number of matching log entries to return",
    )


class LogLinesAboveSchema(BaseModel):
    """Schema for get_log_lines_above tool"""

    file_name: str = Field(
        description="File name to search for the log line (e.g., 'nginx.log', 'api.log')"
    )
    log_message: str = Field(description="The first line of the log message")
    log_timestamp: Optional[str] = Field(
        default=None,
        description="The timestamp of the target log entry (Unix timestamp, or datetime string)",
    )
    lines_above: int = Field(
        default=DEFAULT_LINE_ABOVE,
        description="Number of lines to retrieve that occurred before/above the target log line",
    )
