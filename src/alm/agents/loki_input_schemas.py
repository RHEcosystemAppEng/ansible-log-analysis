"""
Pydantic schemas for Loki query tools.
These schemas define the input parameters for each tool using args_schema.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from enum import Enum

DEFAULT_START_TIME = "-24h"
DEFAULT_END_TIME = "now"
DEFAULT_LIMIT = 100
DEFAULT_DIRECTION = "backward"
DEFAULT_LINE_ABOVE = 10


class LogLevel(str, Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"
    DEBUG = "debug"
    UNKNOWN = "unknown"


class FileLogSchema(BaseModel):
    """Schema for get_file_log_by_name tool"""
    file_name: str = Field(description="File name to search for (e.g., 'nginx.log', 'api.log', 'database.log')")
    start_time: str|int = Field(default=DEFAULT_START_TIME, description="Start time, e.g. '-1h', ISO datetime, or unix nanoseconds")
    end_time: str|int = Field(default=DEFAULT_END_TIME, description="End time, e.g. 'now', '-1h', ISO datetime, or unix nanoseconds")
    level: LogLevel | None = Field(default=None, description="Log level filter: error, warn, info, debug, unknown")
    limit: int = Field(default=DEFAULT_LIMIT, description="Maximum number of log entries to return")
    direction: Literal["backward", "forward"] = Field(default=DEFAULT_DIRECTION, description="Direction of the query: 'backward' or 'forward'")


class SearchTextSchema(BaseModel):
    """Schema for search_logs_by_text tool"""
    text: str = Field(description="Text to search for in log messages (case-sensitive, e.g., 'ERROR', 'timeout', 'user login')")
    start_time: str|int = Field(default=DEFAULT_START_TIME, description="Start time, e.g. '-1h', ISO datetime, or unix nanoseconds")
    end_time: str|int = Field(default=DEFAULT_END_TIME, description="End time, e.g. 'now', '-1h', ISO datetime, or unix nanoseconds")
    file_name: Optional[str] = Field(default=None, description="Optional: File name to search within (e.g., 'nginx.log'). If not specified, searches across all files.")
    limit: int = Field(default=DEFAULT_LIMIT, description="Maximum number of matching log entries to return")


class LogLinesAboveSchema(BaseModel):
    """Schema for get_log_lines_above tool"""
    file_name: str = Field(description="File name to search for the log line (e.g., 'nginx.log', 'api.log')")
    log_message: str = Field(description="The first line of the log message")
    lines_above: int = Field(default=DEFAULT_LINE_ABOVE, description="Number of lines to retrieve that occurred before/above the target log line")
