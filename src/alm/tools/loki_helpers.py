"""
Helper functions for Loki log querying tools.
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from dateutil import parser as date_parser


def timestamp_to_utc_datetime(timestamp: str) -> datetime:
    """
    Convert timestamp (any format) to UTC-aware datetime.

    Supports:
    - Nanoseconds (19+ digits)
    - Milliseconds (13+ digits)
    - Seconds (10 digits or less)
    - ISO format strings

    Args:
        timestamp: Timestamp string in any supported format

    Returns:
        UTC-aware datetime object

    Raises:
        ValueError: If timestamp format is invalid
    """
    if timestamp.isdigit():
        ts_int = int(timestamp)

        # Detect format based on number of digits
        if ts_int > 1_000_000_000_000_000_000:  # 19+ digits = nanoseconds
            ts_seconds = ts_int / 1_000_000_000
        elif ts_int > 1_000_000_000_000:  # 13+ digits = milliseconds
            ts_seconds = ts_int / 1_000
        else:  # 10 digits or less = seconds
            ts_seconds = float(ts_int)

        # Create UTC-aware datetime
        return datetime.fromtimestamp(ts_seconds, tz=timezone.utc)
    else:
        # ISO format or other parseable format
        dt = date_parser.parse(timestamp)

        # Ensure it's UTC-aware
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            dt = dt.astimezone(timezone.utc)

        return dt


def format_rfc3339_utc(dt: datetime) -> str:
    """
    Format UTC datetime as RFC3339 with Z suffix.

    Output format: YYYY-MM-DDTHH:MM:SS.ffffffZ
    Note: Python datetime only supports microsecond precision (6 digits),
    not nanosecond precision (9 digits).

    Args:
        dt: UTC-aware datetime object

    Returns:
        RFC3339 formatted string with Z suffix
    """
    # Format with microseconds and Z suffix
    # isoformat() gives us YYYY-MM-DDTHH:MM:SS.ffffff+00:00
    # We want YYYY-MM-DDTHH:MM:SS.ffffffZ
    iso_str = dt.isoformat()

    # Replace timezone offset with Z
    if iso_str.endswith("+00:00"):
        return iso_str[:-6] + "Z"
    elif iso_str.endswith("Z"):
        return iso_str
    else:
        # Should not happen if dt is UTC, but handle it
        return dt.astimezone(timezone.utc).isoformat()[:-6] + "Z"


def parse_relative_offset(time_str: str) -> timedelta:
    """
    Parse relative time string like '-5m', '2h', '-1d' into timedelta.

    Args:
        time_str: Relative time string (e.g., "-5m", "2h", "-1d")

    Returns:
        timedelta object representing the offset

    Raises:
        ValueError: If the time string format is invalid
    """
    match = re.match(r"(-?)(\d+)([smhd])", time_str.strip())
    if not match:
        raise ValueError(f"Invalid relative time format: {time_str}")

    sign, value, unit = match.groups()
    value = int(value)
    if sign == "-":
        value = -value

    unit_map = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
    return timedelta(**{unit_map[unit]: value})


def parse_time_relative_to_timestamp(time_str: str, reference_timestamp: str) -> str:
    """
    Parse relative time string based on a reference timestamp.

    Args:
        time_str: Relative time string (e.g., "-5m", "2h")
        reference_timestamp: Reference timestamp (milliseconds, nanoseconds, or ISO format)

    Returns:
        RFC3339 UTC formatted string with Z suffix

    Raises:
        ValueError: If timestamp or time format is invalid
    """
    # Convert reference timestamp to UTC datetime
    ref_datetime = timestamp_to_utc_datetime(reference_timestamp)

    # Parse the relative offset and calculate result
    offset = parse_relative_offset(time_str)
    result_datetime = ref_datetime + offset

    # Format as RFC3339 with Z
    return format_rfc3339_utc(result_datetime)


def parse_time_absolute(time_str: str) -> str:
    """
    Parse absolute time string into RFC3339 UTC format.

    Args:
        time_str: Absolute time string (ISO format, human-readable, etc.)

    Returns:
        RFC3339 UTC formatted string with Z suffix, or original string if parsing fails
    """
    try:
        dt = date_parser.parse(time_str)

        # Ensure it's UTC-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        return format_rfc3339_utc(dt)
    except Exception:
        # Return as-is and let Loki handle it
        return time_str


def parse_time_input(time_str: str, reference_timestamp: Optional[str] = None) -> str:
    """
    Parse various time input formats into Loki-compatible format.

    When reference_timestamp is provided, all relative times are calculated from it
    and returned as RFC3339 UTC format with Z suffix.
    When reference_timestamp is None, relative times are returned as-is for Loki.

    Args:
        time_str: Time string to parse (relative like "-5m" or absolute like ISO format)
        reference_timestamp: Optional reference timestamp for relative calculations.
                           If None, relative times are passed as-is to Loki.

    Returns:
        Loki-compatible time string (RFC3339 UTC with Z or relative format like "-5m")

    Examples:
        parse_time_input("-5m", "1762414393000000000") → "2025-05-01T14:33:13.000000Z"
        parse_time_input("-5m", None) → "-5m"
        parse_time_input("now", "1762414393000000000") → "2025-05-01T14:38:13.000000Z"
        parse_time_input("now", None) → "now"
        parse_time_input("2024-01-01T10:00:00", ...) → "2024-01-01T10:00:00.000000Z"
    """
    # Validate reference_timestamp if provided
    ref_datetime, is_valid_timestamp = validate_timestamp(reference_timestamp)
    if reference_timestamp and not is_valid_timestamp:
        print(
            f"⚠️  Warning: Invalid reference timestamp '{reference_timestamp}'. Treating relative times as relative to 'now' instead."
        )
        reference_timestamp = None

    # Handle "now"
    if not time_str or time_str.lower() == "now":
        if ref_datetime:
            # "now" relative to reference timestamp = the reference timestamp itself
            return format_rfc3339_utc(ref_datetime)
        else:
            # No reference timestamp: pass "now" to Loki
            return "now"

    # Handle relative times like "2h ago", "30m ago", "1d ago"
    if "ago" in time_str.lower():
        time_str = f"-{time_str.replace('ago', '').strip()}"

    # Handle direct relative times like "2h", "30m", "1d", "-5m"
    if any(unit in time_str for unit in ["h", "m", "s", "d"]):
        if reference_timestamp:
            # Calculate relative to reference timestamp
            try:
                return parse_time_relative_to_timestamp(time_str, reference_timestamp)
            except Exception as e:
                print(
                    f"⚠️  Warning: Failed to parse relative time '{time_str}' with reference timestamp: {e}"
                )
                # Fallback: return as-is for Loki
                return time_str
        else:
            # No reference timestamp: return as-is for Loki (relative to "now")
            return time_str

    # Try to parse as absolute datetime
    return parse_time_absolute(time_str)


async def find_log_timestamp(
    file_name: str, log_message: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find the timestamp of a target log message by searching for it.

    This is a fallback function used when timestamp is not provided or invalid.

    Args:
        file_name: The log file to search in
        log_message: The log message to find

    Returns:
        Tuple of (timestamp, error_message)
        - timestamp: The timestamp string in nanoseconds if found, None otherwise
        - error_message: Error description if not found, None otherwise
    """
    from alm.agents.loki_agent.schemas import LogToolOutput
    from alm.tools import search_logs_by_text

    print(f"\n🔍 [find_log_timestamp] Searching for target log message in {file_name}")

    # Use current time for the search (past 30 days)
    current_time = datetime.now(timezone.utc)
    start_time = current_time - timedelta(
        days=30
    )  # 30 days which is the max time range allowed by Loki

    target_result = await search_logs_by_text.ainvoke(
        {
            "text": log_message,
            "file_name": file_name,
            "log_timestamp": str(
                int(current_time.timestamp() * 1_000_000_000)
            ),  # Current time in nanoseconds
            "start_time": format_rfc3339_utc(start_time),  # RFC3339 UTC format
            "end_time": format_rfc3339_utc(current_time),  # RFC3339 UTC format
            "limit": 1,
        }
    )
    target_result = LogToolOutput.model_validate_json(target_result)

    if not target_result.logs:
        error_msg = f"Log message '{log_message}' not found in file '{file_name}'"
        return None, error_msg

    # Get the timestamp of the target log line
    target_log = target_result.logs[0]
    target_timestamp_raw = target_log.timestamp

    print(f"✅ Target log found with timestamp: {target_timestamp_raw}")
    return target_timestamp_raw, None


def validate_timestamp(timestamp: Optional[str]) -> Tuple[Optional[datetime], bool]:
    """
    Validate if a timestamp string is valid (milliseconds, nanoseconds, or ISO format).

    Args:
        timestamp: Timestamp string to validate

    Returns:
        Tuple of (UTC-aware datetime object if valid, None otherwise, True if valid, False otherwise)
    """
    if not timestamp:
        return None, False

    try:
        # Try to convert to datetime - if it works, it's valid
        dt = timestamp_to_utc_datetime(timestamp)
        # Check if the timestamp is in a reasonable range (year 2000 to 2100)
        if (
            datetime(2000, 1, 1, tzinfo=timezone.utc)
            < dt
            < datetime(2100, 1, 1, tzinfo=timezone.utc)
        ):
            return dt, True
        else:
            return None, False
    except Exception:
        return None, False
