"""
LangChain tools for Loki log querying with perfect function matching.
Each tool represents a common log querying pattern with rich descriptions.
"""

import os
import json
from typing import Literal, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser

from langchain_core.tools import tool

from ..mcp import MCPClient
from .loki_input_schemas import (
    DEFAULT_DIRECTION,
    DEFAULT_LINE_ABOVE,
    DEFAULT_END_TIME,
    DEFAULT_LIMIT,
    DEFAULT_START_TIME,
    FileLogSchema,
    LogLevel,
    SearchTextSchema,
    LogLinesAboveSchema,
)
from .loki_output_schemas import (
    LogEntry,
    LogStream,
    LogToolOutput,
    ToolStatus
)


# MCP Server URL configuration
_mcp_server_url = os.getenv("LOKI_MCP_SERVER_URL", "http://localhost:8080/stream")
MAX_LOGS_PER_QUERY = 5000


async def create_mcp_client() -> MCPClient:
    """Create and initialize a new MCP client instance"""
    client = MCPClient(_mcp_server_url)
    await client.__aenter__()
    init_result = await client.initialize()
    if not init_result:
        raise Exception("Failed to initialize MCP session")
    return client


def parse_time_input(time_str: str) -> str:
    """Parse various time input formats into Loki-compatible format"""
    if not time_str or time_str.lower() == "now":
        return "now"

    # Handle relative times like "2h ago", "30m ago", "1d ago"
    if "ago" in time_str.lower():
        return f"-{time_str.replace('ago', '')}"

    # Handle direct relative times like "2h", "30m", "1d"
    if any(unit in time_str for unit in ['h', 'm', 's', 'd']):
        if not '-' in time_str:
            return f"-{time_str}"
        else:
            return time_str

    # Try to parse as absolute datetime
    try:
        dt = date_parser.parse(time_str)
        return dt.isoformat()
    except:
        # Fallback: return as-is and let Loki handle it
        return time_str


async def execute_loki_query(query: str, start: str|int = "-24h",
                             end: str|int = "now", limit: int = DEFAULT_LIMIT,
                             direction: str = "backward") -> str:
    """Execute a LogQL query via MCP client"""
    client = None
    if limit > MAX_LOGS_PER_QUERY:
        print(f"Warning: Limit is greater than {MAX_LOGS_PER_QUERY}, setting to {MAX_LOGS_PER_QUERY}")
        limit = MAX_LOGS_PER_QUERY

    try:
        # Create a new MCP client for each query (proper async context management)
        client = await create_mcp_client()

        # Prepare arguments for loki_query tool (like the working test)
        arguments = {
            "query": query,
            "start": parse_time_input(start) if isinstance(start, str) else start,
            "end": parse_time_input(end) if isinstance(end, str) else end,
            "limit": limit,
            "direction": direction,
            "format": "json"
        }

        print(f"🔍 Executing MCP query with args: {arguments}")

        # Call the MCP loki_query tool
        result = await client.call_tool("loki_query", arguments)

        # Parse the result, format should be json as default
        if isinstance(result, str) and result.strip().startswith("{"):
            try:
                parsed_result = json.loads(result)
                print(f"📊 Parsed MCP result: {parsed_result}")
                logs = []

                # Parse Loki response format
                if "data" in parsed_result and "result" in parsed_result["data"]:
                    for stream in parsed_result["data"]["result"]:
                        stream_labels = stream.get("stream", {})
                        for entry in stream.get("values", []):
                            logs.append(LogEntry(
                                timestamp=entry[0],
                                stream=stream_labels,
                                message=entry[1]
                            ))

                return LogToolOutput(
                    status=ToolStatus.SUCCESS,
                    message=parsed_result.get("message", None),
                    logs=logs,
                    number_of_logs=len(logs),
                    query=query,
                    execution_time_ms=parsed_result.get("stats", {}).get("summary", {}).get("execTime", 0)
                ).model_dump_json(indent=2)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                # If not JSON, treat as plain text result
                return LogToolOutput(
                    status=ToolStatus.SUCCESS,
                    logs=[LogEntry(stream=LogStream(), message=result)],
                    number_of_logs=1,
                    query=query
                ).model_dump_json(indent=2)
        else:
            # Handle non-JSON or error responses
            print(f"Non-JSON result: {result}")
            return LogToolOutput(
                status=ToolStatus.SUCCESS,
                logs=[LogEntry(stream=LogStream(), message=str(result))],
                number_of_logs=1,
                query=query
            ).model_dump_json(indent=2)

    except Exception as e:
        print(f"MCP query execution failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Failed to execute Loki query: {str(e)}")
    finally:
        # Clean up the client
        if client:
            try:
                await client.__aexit__(None, None, None)
            except:
                pass


@tool(args_schema=FileLogSchema)
async def get_logs_by_file_name(
    file_name: str,
    start_time: str|int = "-24h",
    end_time: str = "now",
    level: LogLevel | None = None,
    limit: int = DEFAULT_LIMIT,
    direction: Literal["backward", "forward"] = "backward",
) -> str:
    """
    Get logs for a specific file in the last N hours, optionally filtered by log level.

    Perfect for queries like:
    - "show me logs of file nginx.log in last 2 hours"
    - "get error logs from file api.log between 2025-01-01T00:00:00 and 2025-01-01T01:00:00"
    - "show me logs from file nginx.log from last hour"
    """
    try:
        # Build LogQL query for file name
        query_parts = [f'{{filename=~".*{file_name}$"}}']

        if level:
            query_parts.append(f'| detected_level=`{level.value}`')

        query = "".join(query_parts)

        result = await execute_loki_query(query, start_time, end_time, limit, direction)
        return result

    except Exception as e:
        print(f"Error in get_logs_by_file_name: {e}")
        output = LogToolOutput(
            status=ToolStatus.ERROR,
            message=str(e),
            number_of_logs=0,
            logs=[]
        )
        return output.model_dump_json(indent=2)


@tool(args_schema=SearchTextSchema)
async def search_logs_by_text(
    text: str,
    start_time: str|int = "-24h",
    end_time: str|int = "now",
    file_name: Optional[str] = None,
    limit: int = DEFAULT_LIMIT
) -> str:
    """
    Search for logs containing specific text (case-sensitive) across all sources or in a specific file.

    Perfect for queries like:
    - "find all logs containing 'timeout' in the last hour"
    - "search for 'user login' in logs from last 2 hours"
    - "show me all logs with 'database connection' from last 30 minutes"
    - "search for 'error' in nginx.log from last hour"
    - "find 'connection refused' in api.log"

    Note: This is a case-sensitive text search using LogQL's |= operator.
    """
    try:
        text = text.replace('"', '\\"')
        # Build LogQL query for text search
        if file_name:
            # Search within a specific file
            query = f'{{filename=~".*{file_name}$"}} |= "{text}"'
        else:
            # Search across all logs
            # Use job=~".+" to match any job with non-empty value (Loki requirement)
            query = f'{{job=~".+"}} |= "{text}"'

        result = await execute_loki_query(query, start_time, end_time, limit)
        return result

    except Exception as e:
        print(f"Error in search_logs_by_text: {e}")
        output = LogToolOutput(
            status=ToolStatus.ERROR,
            message=str(e),
            number_of_logs=0,
            logs=[]
        )
        return output.model_dump_json(indent=2)


def _extract_context_lines_above(
    all_logs: list[LogEntry],
    target_message: str,
    lines_above: int
) -> tuple[list[LogEntry], Optional[str]]:
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

    print(f"Start index: {start_idx}")
    print(f"End index: {end_idx}")

    context_logs = all_logs[start_idx:end_idx]

    print(f"Context logs: {len(context_logs)}")

    return context_logs, None


@tool(args_schema=LogLinesAboveSchema)
async def get_log_lines_above(
    file_name: str,
    log_message: str,
    lines_above: int = DEFAULT_LINE_ABOVE
) -> str:
    """
    Get log lines that occurred before/above a specific log line in a file.

    This tool uses a time window approach to retrieve context lines:
    1. Finds the target log line to get its timestamp
    2. Queries a wide time window (target - 25 days to target + 2 minutes)
    3. Fetches up to 5000 logs to ensure we have enough context
    4. Filters client-side to extract N lines before the target

    The +2 minute buffer handles cases where Loki ignores fractional seconds
    and multiple logs have the same timestamp.

    Note: log_message is the content of the log line without timestamp.

    Perfect for queries like:
    - "get 10 lines above this error in nginx.log"
    - "show me 5 lines before this failure in api.log"
    - "get context lines above this specific log entry"
    """
    try:
        # Step 1: Find the exact log line to get its timestamp
        print(f"\n🔍 [get_log_lines_above] Step 1: Finding target log message in {file_name}")
        target_result = await search_logs_by_text.ainvoke({
            "text": log_message,
            "file_name": file_name,
            "start_time": "-720h", # 30 days ago which is the max time window for Loki
            "end_time": "now",
            "limit": 1
        })
        target_result = LogToolOutput.model_validate_json(target_result)

        if not target_result.logs:
            output = LogToolOutput(
                status=ToolStatus.ERROR,
                message=f"Log message '{log_message}' not found in file '{file_name}'",
                query=target_result.query,
                number_of_logs=0,
                logs=[]
            )
            return output.model_dump_json(indent=2)

        # Get the timestamp of the target log line
        target_log = target_result.logs[0]
        target_timestamp_raw = target_log.timestamp

        print(f"✅ Target log found with timestamp: {target_timestamp_raw}")

        # Step 2: Convert nanosecond timestamp to datetime and calculate time window
        try:
            target_timestamp_seconds = int(target_timestamp_raw) / 1_000_000_000
            target_datetime = datetime.fromtimestamp(target_timestamp_seconds)
        except (ValueError, TypeError) as e:
            return LogToolOutput(
                status=ToolStatus.ERROR,
                message=f"Failed to parse target timestamp '{target_timestamp_raw}': {str(e)}",
                number_of_logs=0,
                logs=[]
            ).model_dump_json(indent=2)

        # Calculate time window: 25 days before to 2 minutes after target
        # This ensures we capture the file start and handle fractional second issues
        start_datetime = target_datetime - timedelta(days=25)
        end_datetime = target_datetime + timedelta(minutes=10)

        start_time_iso = start_datetime.isoformat()
        end_time_iso = end_datetime.isoformat()

        print(f"📅 Time window: {start_time_iso} to {end_time_iso}")
        print(f"🔍 [get_log_lines_above] Step 2: Querying large context window (limit=5000)")

        # Step 3: Query with wide time window and large limit
        context_query = {
            "file_name": file_name,
            "start_time": start_time_iso,
            "end_time": end_time_iso,
            "limit": 5000,  # Max allowed by Loki
            "direction": "backward",  # Get most recent logs in the window
        }
        context_result = await get_logs_by_file_name.ainvoke(context_query)
        context_data = LogToolOutput.model_validate_json(context_result)

        if context_data.status != ToolStatus.SUCCESS.value:
            output = LogToolOutput(
                status=ToolStatus.ERROR,
                message=f"Failed to retrieve context logs: {context_data.message}",
                query=context_data.query,
                number_of_logs=0,
                logs=[]
            )
            return output.model_dump_json(indent=2)

        print(f"📊 Fetched {len(context_data.logs)} logs from Loki")
        print(f"🔍 [get_log_lines_above] Step 3: Extracting {lines_above} lines before target")

        # Step 4: Extract N lines before the target using client-side filtering
        # Note: context_data.logs are in reverse chronological order (backward direction)
        # We need to reverse them to get chronological order for proper indexing
        chronological_logs = list(reversed(context_data.logs))
        
        print(f"first line of chronological logs: {chronological_logs[0].message}")
        print(f"last line of chronological logs: {chronological_logs[-1].message}")

        context_logs, error = _extract_context_lines_above(
            chronological_logs,
            log_message,
            lines_above
        )

        if error:
            output = LogToolOutput(
                status=ToolStatus.ERROR,
                message=error,
                query=context_data.query,
                number_of_logs=0,
                logs=[]
            )
            return output.model_dump_json(indent=2)

        print(f"✅ Successfully extracted {len(context_logs)} logs (including target)")
        print(f"   Requested: {lines_above} lines above, Got: {len(context_logs) - 1} lines above + target")

        # Step 5: Return the context logs
        output = LogToolOutput(
            status=ToolStatus.SUCCESS,
            message=f"Retrieved {len(context_logs) - 1} lines above the target log (total {len(context_logs)} logs including target)",
            query=context_data.query,
            number_of_logs=len(context_logs),
            logs=context_logs,
            execution_time_ms=context_data.execution_time_ms
        )
        return output.model_dump_json(indent=2)

    except Exception as e:
        print(f"❌ Error in get_log_lines_above: {e}")
        import traceback
        traceback.print_exc()

        output = LogToolOutput(
            status=ToolStatus.ERROR,
            message=str(e),
            number_of_logs=0,
            logs=[]
        )
        return output.model_dump_json(indent=2)


# List of all available tools for easy import
# TODO: Add fallback_query tool
LOKI_TOOLS = [
    get_logs_by_file_name,
    search_logs_by_text,
    get_log_lines_above,
]