"""
LangChain tools for Loki log querying with perfect function matching.
Each tool represents a common log querying pattern with rich descriptions.
"""

import os
import json
from typing import Literal, Optional

from langchain_core.tools import tool

from alm.mcp import MCPClient
from alm.agents.loki_agent.constants import (
    DEFAULT_DIRECTION,
    DEFAULT_END_TIME,
    DEFAULT_START_TIME,
    LOGQL_FILE_NAME_QUERY_TEMPLATE,
    LOGQL_JOB_WILDCARD_QUERY,
    LOGQL_LEVEL_FILTER_TEMPLATE,
    LOGQL_TEXT_SEARCH_TEMPLATE,
    MAX_LOGS_PER_QUERY,
)
from alm.agents.loki_agent.schemas import (
    DEFAULT_LINE_ABOVE,
    DEFAULT_LIMIT,
    FileLogSchema,
    LogLevel,
    SearchTextSchema,
    LogLinesAboveSchema,
    LogEntry,
    LogLabels,
    LogToolOutput,
    ToolStatus,
)
from alm.tools.loki_helpers import escape_logql_string, validate_timestamp


# MCP Server URL configuration
_mcp_server_url = os.getenv("LOKI_MCP_SERVER_URL")


async def create_mcp_client() -> MCPClient:
    """Create and initialize a new MCP client instance"""
    client = MCPClient(_mcp_server_url)
    await client.__aenter__()
    init_result = await client.initialize()
    if not init_result:
        raise Exception("Failed to initialize MCP session")
    return client


async def execute_loki_query(
    query: str,
    start: str | int = DEFAULT_START_TIME,
    end: str | int = DEFAULT_END_TIME,
    limit: int = DEFAULT_LIMIT,
    reference_timestamp: Optional[str] = None,
    direction: str = DEFAULT_DIRECTION,
) -> str:
    """Execute a LogQL query via MCP client"""
    # Import here to avoid circular dependency
    from alm.tools.loki_helpers import parse_time_input, merge_loki_streams

    client = None
    if limit > MAX_LOGS_PER_QUERY:
        print(
            f"Warning: Limit is greater than {MAX_LOGS_PER_QUERY}, setting to {MAX_LOGS_PER_QUERY}"
        )
        limit = MAX_LOGS_PER_QUERY

    try:
        # Create a new MCP client for each query (proper async context management)
        client = await create_mcp_client()

        # Prepare arguments for loki_query tool
        # If it not str its already a timestamp, so we don't need to parse it
        start_parsed = (
            parse_time_input(start, reference_timestamp)
            if isinstance(start, str)
            else start
        )
        end_parsed = (
            parse_time_input(end, reference_timestamp) if isinstance(end, str) else end
        )

        arguments = {
            "query": query,
            "start": start_parsed,
            "end": end_parsed,
            "limit": limit,
            "direction": direction,
            "format": "json",
        }

        print(f"🔍 Executing MCP query with args: {arguments}")

        # Call the MCP loki_query tool
        result = await client.call_tool("loki_query", arguments)

        # Parse the result, format should be json as default
        if isinstance(result, str) and result.strip().startswith("{"):
            try:
                parsed_result = json.loads(result)
                # print(f"📊 Parsed MCP result: {parsed_result}")
                logs = []

                # Parse Loki response format and merge streams efficiently
                if "data" in parsed_result and "result" in parsed_result["data"]:
                    # Use heapq.merge to efficiently merge pre-sorted streams
                    # Groups by file (excluding log level) and sorts chronologically
                    logs = merge_loki_streams(
                        parsed_result["data"]["result"], direction=direction
                    )

                # Add helpful message when no logs are found and no message is provided by the tools
                message = parsed_result.get("message", None)
                if len(logs) == 0 and not message:
                    message = "No logs found matching the query. Try using a different search term, simpler keywords, or expanding the time range."

                return LogToolOutput(
                    status=ToolStatus.SUCCESS,
                    message=message,
                    logs=logs,
                    number_of_logs=len(logs),
                    query=query,
                    execution_time_ms=parsed_result.get("stats", {})
                    .get("summary", {})
                    .get("execTime", 0),
                ).model_dump_json(indent=2)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                # If not JSON, treat as plain text result
                return LogToolOutput(
                    status=ToolStatus.SUCCESS,
                    logs=[LogEntry(log_labels=LogLabels(), message=result)],
                    number_of_logs=1,
                    query=query,
                ).model_dump_json(indent=2)
        else:
            # Handle non-JSON or error responses
            print(f"Non-JSON result: {result}")
            return LogToolOutput(
                status=ToolStatus.SUCCESS,
                logs=[LogEntry(log_labels=LogLabels(), message=str(result))],
                number_of_logs=1,
                query=query,
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
            except Exception:
                pass


@tool(args_schema=FileLogSchema)
async def get_logs_by_file_name(
    file_name: str,
    log_timestamp: Optional[str] = None,
    start_time: str | int = DEFAULT_START_TIME,
    end_time: str = DEFAULT_END_TIME,
    level: LogLevel | None = None,
    limit: int = DEFAULT_LIMIT,
    direction: Literal["backward", "forward"] = DEFAULT_DIRECTION,
) -> str:
    """
    Get logs for a specific file with time ranges relative to a reference timestamp,
    optionally filtered by log level.

    Perfect for queries like:
    - "show me logs from nginx.log 5 minutes before this error"
    - "get error logs from api.log between 1 hour before and 10 minutes before this timestamp"
    """
    try:
        # Build LogQL query for file name
        query_parts = [LOGQL_FILE_NAME_QUERY_TEMPLATE.format(file_name=file_name)]

        if level:
            query_parts.append(LOGQL_LEVEL_FILTER_TEMPLATE.format(level=level.value))

        query = "".join(query_parts)

        result = await execute_loki_query(
            query, start_time, end_time, limit, log_timestamp, direction
        )
        return result

    except Exception as e:
        print(f"Error in get_logs_by_file_name: {e}")
        output = LogToolOutput(
            status=ToolStatus.ERROR, message=str(e), number_of_logs=0, logs=[]
        )
        return output.model_dump_json(indent=2)


@tool(args_schema=SearchTextSchema)
async def search_logs_by_text(
    text: str,
    log_timestamp: Optional[str] = None,
    start_time: str | int = DEFAULT_START_TIME,
    end_time: str | int = DEFAULT_END_TIME,
    file_name: Optional[str] = None,
    limit: int = DEFAULT_LIMIT,
) -> str:
    """
    Search for logs containing specific text with time ranges relative to a reference timestamp,
    across all logs or in a specific file.


    Perfect for queries like:
    - "find logs containing 'timeout' 5 minutes before this error"
    - "search for 'user login' between 1 hour before and 30 minutes before this timestamp"
    - "show logs with 'database connection' around this time"

    Note: This is a case-sensitive text search using LogQL's |= operator.
    """
    try:
        # Escape special characters in search text for LogQL
        escaped_text = escape_logql_string(text)

        # Build LogQL query for text search
        if file_name:
            # Search within a specific file
            query = (
                LOGQL_FILE_NAME_QUERY_TEMPLATE.format(file_name=file_name)
                + " "
                + LOGQL_TEXT_SEARCH_TEMPLATE.format(text=escaped_text)
            )
        else:
            # Search across all logs
            # Use job=~".+" to match any job with non-empty value (Loki requirement)
            query = (
                LOGQL_JOB_WILDCARD_QUERY
                + " "
                + LOGQL_TEXT_SEARCH_TEMPLATE.format(text=escaped_text)
            )

        result = await execute_loki_query(
            query, start_time, end_time, limit, log_timestamp
        )
        return result

    except Exception as e:
        print(f"Error in search_logs_by_text: {e}")
        output = LogToolOutput(
            status=ToolStatus.ERROR, message=str(e), number_of_logs=0, logs=[]
        )
        return output.model_dump_json(indent=2)


def create_log_lines_above_tool(
    file_name: str,
    log_message: str,
    log_timestamp: str,
):
    """
    Factory function to create get_log_lines_above tool with bound context values.

    This uses Python closures to capture file_name, log_message, and log_timestamp,
    avoiding the need for LLM JSON serialization of these constant values.
    Especially useful for passing complex log messages to the tool, avoiding JSON serialization issues.

    Args:
        file_name: The log file name to search in
        log_message: The target log message to find context for
        log_timestamp: The timestamp of the target log

    Returns:
        A LangChain tool with the context values bound via closure
    """

    @tool(args_schema=LogLinesAboveSchema)
    async def get_log_lines_above(lines_above: int = DEFAULT_LINE_ABOVE) -> str:
        """
        Get log lines that occurred before/above a specific log line in a file.

        This tool has log context (file_name, log_message, log_timestamp) bound
        via closure at creation time. The LLM only needs to specify how many lines
        to retrieve.

        This tool uses a time window approach to retrieve context lines:
        1. Uses the bound timestamp, or finds the target log line to get its timestamp
        2. Queries a wide time window (target - 25 days to target + 2 minutes)
        3. Fetches up to 5000 logs to ensure we have enough context
        4. Filters client-side to extract N lines before the target

        The +10 minute buffer handles cases where Loki ignores fractional seconds
        and multiple logs have the same timestamp.

        Args:
            lines_above: Number of lines to retrieve before the target log (default: 10)

        Perfect for queries like:
        - "get 10 lines above this error"
        - "show me 5 lines before this failure"
        - "get context lines above this specific log entry"
        """
        try:
            # Import helper functions
            from alm.tools.log_lines_context_helpers import (
                calculate_time_window,
                query_logs_in_time_window,
                extract_context_lines_above,
            )
            from alm.agents.loki_agent.constants import CONTEXT_TRUNCATE_SUFFIX

            # Use closure-captured values
            print("🔍 get_log_lines_above invoked with closure-bound context:")
            print(f"  - file_name: {file_name}")
            print(
                f"  - log_message: {log_message[:100]}..."
                if log_message and len(log_message) > 100
                else f"  - log_message: {log_message}"
            )
            print(f"  - log_timestamp: {log_timestamp}")
            print(f"  - lines_above: {lines_above}")

            # Process the log message
            processed_log_message = log_message
            # Truncate the log message at the end only if it ends with the truncate suffix
            if processed_log_message and processed_log_message.endswith(
                CONTEXT_TRUNCATE_SUFFIX
            ):
                processed_log_message = processed_log_message[
                    : -len(CONTEXT_TRUNCATE_SUFFIX)
                ].rstrip()

            # Step 1: Validate and convert the timestamp to a datetime object
            print("🔍 [Step 1] Validating and converting timestamp to datetime object")
            target_datetime, is_valid = validate_timestamp(log_timestamp)
            if not is_valid or not target_datetime:
                return LogToolOutput(
                    status=ToolStatus.ERROR,
                    message=f"Invalid timestamp: {log_timestamp}, please provide a valid timestamp",
                    number_of_logs=0,
                    logs=[],
                ).model_dump_json(indent=2)

            # Step 2: Calculate time window
            print("🔍 [Step 2] Calculating time window around timestamp")
            start_time_rfc3339, end_time_rfc3339 = calculate_time_window(
                target_datetime
            )

            # Step 3: Query logs in the time window
            print("🔍 [Step 3] Querying large context window (limit=5000)")
            context_data, error = await query_logs_in_time_window(
                file_name, start_time_rfc3339, end_time_rfc3339
            )
            if error or not isinstance(context_data, LogToolOutput):
                return LogToolOutput(
                    status=ToolStatus.ERROR,
                    message=f"Failed to query logs in time window. Error: {error}, Context data: {context_data}",
                    number_of_logs=0,
                    logs=[],
                ).model_dump_json(indent=2)

            # Step 4: Extract N lines before the target
            print(f"🔍 [Step 4] Extracting {lines_above} lines before target")

            context_logs, error = extract_context_lines_above(
                context_data.logs, processed_log_message, lines_above
            )

            if error:
                return LogToolOutput(
                    status=ToolStatus.ERROR,
                    message=error,
                    query=context_data.query,
                    number_of_logs=0,
                    logs=[],
                ).model_dump_json(indent=2)

            print(
                f"✅ Successfully extracted {len(context_logs)} logs (including target)"
            )
            print(
                f"   Requested: {lines_above} lines above, Got: {len(context_logs) - 1} lines above + target"
            )

            # Step 5: Return the context logs
            return LogToolOutput(
                status=ToolStatus.SUCCESS,
                message=f"Retrieved {len(context_logs) - 1} lines above the target log (total {len(context_logs)} logs including target)",
                query=context_data.query,
                number_of_logs=len(context_logs),
                logs=context_logs,
                execution_time_ms=context_data.execution_time_ms,
            ).model_dump_json(indent=2)

        except Exception as e:
            print(f"❌ Error in get_log_lines_above: {e}")
            import traceback

            traceback.print_exc()

            return LogToolOutput(
                status=ToolStatus.ERROR, message=str(e), number_of_logs=0, logs=[]
            ).model_dump_json(indent=2)

    return get_log_lines_above


# List of static tools (tools that don't need closure-bound context)
# get_log_lines_above is created dynamically via create_log_lines_above_tool()
# TODO: Add fallback_query tool
LOKI_STATIC_TOOLS = [
    get_logs_by_file_name,
    search_logs_by_text,
]
