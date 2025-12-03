"""
Helper functions specifically for the get_log_lines_above tool.

These functions implement the step-by-step logic for retrieving context lines
before a specific log entry using a time window approach.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple

from alm.agents.loki_agent.constants import (
    CONTEXT_WINDOW_DAYS_BEFORE,
    CONTEXT_WINDOW_MINUTES_AFTER,
    DIRECTION_BACKWARD,
    MAX_LOGS_PER_QUERY,
)
from alm.agents.loki_agent.schemas import LogToolOutput


def calculate_time_window(
    target_datetime: datetime,
) -> Tuple[str, str]:
    """
    Calculate the time window for querying around the target datetime.

    Args:
        target_datetime: The target datetime (UTC-aware datetime object)

    Returns:
        Tuple of (start_time_rfc3339, end_time_rfc3339)
        - start_time_rfc3339: Start time in RFC3339 UTC format (25 days before target)
        - end_time_rfc3339: End time in RFC3339 UTC format (2 minutes after target)
    """
    from alm.tools.loki_helpers import format_rfc3339_utc

    # Calculate time window: N days before to M minutes after target
    # This ensures we capture the file start and handle fractional second issues
    start_datetime = target_datetime - timedelta(days=CONTEXT_WINDOW_DAYS_BEFORE)
    end_datetime = target_datetime + timedelta(minutes=CONTEXT_WINDOW_MINUTES_AFTER)

    # Format as RFC3339 with Z
    start_time_rfc3339 = format_rfc3339_utc(start_datetime)
    end_time_rfc3339 = format_rfc3339_utc(end_datetime)

    print(f"📅 Time window: {start_time_rfc3339} to {end_time_rfc3339}")

    return start_time_rfc3339, end_time_rfc3339


async def query_logs_in_time_window(
    file_name: str, start_time_rfc3339: str, end_time_rfc3339: str
) -> Tuple[Optional[LogToolOutput], Optional[str]]:
    """
    Query logs within the specified time window.

    Args:
        file_name: File name to query
        start_time_rfc3339: Start time in RFC3339 UTC format
        end_time_rfc3339: End time in RFC3339 UTC format

    Returns:
        Tuple of (log_output, error_message)
        - log_output: LogToolOutput with the fetched logs if successful
        - error_message: Error description if query fails or returns no logs, None otherwise
    """
    from alm.agents.loki_agent.schemas import LogToolOutput, ToolStatus
    from alm.tools.loki_tools import get_logs_by_file_name

    context_query = {
        "file_name": file_name,
        "start_time": start_time_rfc3339,
        "end_time": end_time_rfc3339,
        "limit": MAX_LOGS_PER_QUERY,  # Max allowed by Loki
        "direction": DIRECTION_BACKWARD,  # Get most recent logs in the window
    }

    context_result = await get_logs_by_file_name.ainvoke(context_query)
    context_data = LogToolOutput.model_validate_json(context_result)

    if context_data.status != ToolStatus.SUCCESS.value or not context_data.logs:
        error_msg = f"Failed to retrieve context logs, Status: {context_data.status}, Logs: {context_data.logs}"
        return None, error_msg

    print(f"📊 Fetched {len(context_data.logs)} logs from Loki")
    return context_data, None


def extract_context_lines_above(
    all_logs: list, target_message: str, lines_above: int
) -> Tuple[list, Optional[str]]:
    """
    Extract N lines before the target message from a list of logs.

    Args:
        all_logs: List of LogEntry objects (should be sorted chronologically)
        target_message: The log message to find
        lines_above: Number of lines to return before the target

    Returns:
        Tuple of (context_logs, error_message)
        - context_logs: List containing N lines before target + target itself
        - error_message: Error description if target not found, None otherwise
    """
    # Find the target log in the list
    target_idx = None
    for i, log in enumerate(all_logs):
        if target_message in log.message:
            target_idx = i
            break
    print(f"Target log message found at index: {target_idx}")

    if target_idx is None:
        return [], f"Target log message not found in the {len(all_logs)} fetched logs"

    # Calculate the range of logs to return
    # We want N lines BEFORE the target, plus the target itself
    start_idx = max(0, target_idx - lines_above)
    end_idx = target_idx + 1  # +1 to include the target line

    print(f"Start index: {start_idx}, End index: {end_idx}")

    context_logs = all_logs[start_idx:end_idx]

    print(f"Context logs length: {len(context_logs)}")

    return context_logs, None
