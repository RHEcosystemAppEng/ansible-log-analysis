"""
LangChain ToolCallingAgent integration with LangGraph for perfect log query function matching.
"""

import json
from typing import Dict, Any, Optional, Literal

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from alm.agents.loki_output_schemas import IdentifyMissingDataSchema, LogStream, LogToolOutput, LokiAgentOutput, ToolStatus

from ..llm import get_llm
from ..models import GrafanaAlert
from .loki_tools import LOKI_TOOLS


class LokiQueryAgent:
    """
    LangChain ToolCallingAgent wrapper for perfect function matching in log queries.
    """

    def __init__(self):
        self.llm = get_llm()
        self.tools = LOKI_TOOLS
        self.agent = None
        self.agent_executor : AgentExecutor = None
        self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the LangChain ToolCallingAgent"""
        # Create the prompt template for the agent
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a specialized log querying assistant. Your job is to select the RIGHT TOOL for the user's request.

## Available Tools:

1. **get_logs_by_file_name** - Get logs from a specific file (optionally within a specific time range)
   Use when: Request mentions a specific file name (nginx.log, app.log, etc.), possibly in some time range
   Examples: "logs from nginx.log", "show me app.log", "apache.log in the last hour", "logs from app.log between 2006-01-02T15:04:05 and 2006-01-02T16:04:05"

2. **search_logs_by_text** - Search for specific text in logs
   Use when: Simple text search across all logs or in a specific file
   Examples: "find 'timeout'", "search for error", "logs containing 'failed'"

3. **get_log_lines_above** - Get context lines before a specific log entry
   Use when: Need to see what happened before a specific log line
   Examples: "lines above this error", "context before failure"

   CRITICAL INSTRUCTIONS FOR THIS TOOL:
   - The "Log Message" field may contain complex JSON with special characters - DO NOT let this confuse you
   - ALWAYS provide BOTH required parameters: log_message AND file_name, and the lines_above parameter if needed
   - If the log message is very long or contains JSON/special chars, focus on extracting file_name from Log Stream first
   - The file_name is ALWAYS in the Log Stream dictionary under the 'filename' key - NEVER skip it

   Parameter mapping:
   - log_message: Extract the FIRST LINE from "Log Message" field (NOT from Log Summary)
   - file_name: Extract the 'filename' value from the "Log Stream" dictionary (REQUIRED - always provide this)
   - lines_above: Number of lines to retrieve

   EXAMPLE - How to extract parameters correctly:
   Input context:
     Log Message: fatal: [host.example.com]: FAILED! => {{"msg": "Request failed"}}
     Log Summary: Request failed
     Log Stream: {{'detected_level': 'error', 'filename': '/path/to/app.log', 'job': 'example_job', 'service_name': 'example_service'}}

   CORRECT tool call (BOTH required parameters provided):
     log_message: "fatal: [host.example.com]: FAILED! => {{"msg": "Request failed"}}"  (from Log Message field)
     file_name: "/path/to/app.log"  (from Log Stream 'filename' key - REQUIRED!)
     lines_above: 10 (default)

## Understanding Context Fields:
When context is provided in the input, use it to help choose the right tool and extract parameters:
- **Log Summary**: High-level summary to help you understand what the logs are about and choose the appropriate tool (do NOT use this for log_message parameter)
- **Log Message**: The actual log text - for get_log_lines_above, extract the first line from this field
- **Log Stream**: Metadata dictionary with keys like 'filename', 'detected_level', 'job', etc. - extract the filename value when needed
- **Expert Classification**: Category classification to help understand the log type

## Your Process:
1. Analyze the user's request
2. Choose the MOST SPECIFIC tool that fits
3. Extract exact parameters from the request AND from the "Additional Context" section
4. Call ONLY ONE tool with the correct parameters
5. Check the "status" field in the response
6. If "success" → return "success" immediately as your final answer
7. If "error" → return "error" immediately as your final answer

## Important:
- All tools return the same format - treat them equally
- Extract exact parameters from the user's request AND context fields
- DO NOT call multiple tools - select the single best tool
- You have to select one tool and call it with the correct parameters
- DO NOT confuse "Log Message" with "Log Summary" - they are different!"""),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}")
        ])

        # Create the tool calling agent
        self.agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=1,  # Force single tool execution
            early_stopping_method="force",
            handle_parsing_errors=True,
            return_intermediate_steps=True,
            trim_intermediate_steps=1
        )

    async def query_logs(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> LokiAgentOutput:
        """
        Execute log query using the ToolCallingAgent.

        The agent automatically selects the most appropriate tool based on the request.
        All tools return the same format (LogToolOutput)

        Args:
            user_request: Natural language log query request
            context: Additional context from the graph state (log summary, classification, etc.)

        Returns:
            LokiAgentOutput containing the query results and metadata
        """
        result = None
        try:
            # Enhance the user request with context if available
            enhanced_request = user_request
            if context:
                context_parts = []

                # Add logMessage first with clear label to avoid confusion with summary
                if 'logMessage' in context and context['logMessage']:
                    value_str = str(context['logMessage'])
                    if len(value_str) > 500:
                        value_str = value_str[:500] + "..."
                    context_parts.append(f"Log Message: {value_str}")

                # Add all other fields generically
                for key, value in context.items():
                    if key != 'logMessage' and value:  # Skip logMessage (already added) and empty values
                        # Convert camelCase to Title Case with spaces
                        formatted_key = ''.join([' ' + c if c.isupper() else c for c in key]).strip().title()

                        context_parts.append(f"{formatted_key}: {str(value)}")

                if context_parts:
                    enhanced_request = f"{user_request}\n\nAdditional Context:\n" + "\n".join(context_parts)

            print(f"\n\n📊 Enhanced Request:\n{enhanced_request}\n\n")

            # Execute the agent
            result = await self.agent_executor.ainvoke({
                "input": enhanced_request
            })

            # Parse the result
            # Get the last tool call and its result from intermediate steps
            if result.get("intermediate_steps"):
                print(f"\n\n📊 Result: {result}\n\n")
                
                # Each step is a tuple of (ToolAgentAction, result_string)
                last_step = result["intermediate_steps"][-1]
                tool_result = last_step[1]  # Get the second element which is the actual tool response
                
                try:
                    # Parse the tool result should be JSON representation of LogToolOutput
                    log_tool_output_object = LogToolOutput.model_validate_json(tool_result)   
                    
                    print(f"\n\n📊 LogToolOutput object:\n{log_tool_output_object}\n\n")
                    
                    return LokiAgentOutput(
                        status=ToolStatus.SUCCESS,
                        user_request=user_request,
                        agent_result=log_tool_output_object,
                        raw_output=tool_result,
                        intermediate_steps=result.get("intermediate_steps", [])
                    )
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in query_logs: {e}")
                    # If not JSON, return as text
                    return LokiAgentOutput(
                        status=ToolStatus.SUCCESS,
                        user_request=user_request,
                        agent_result=LogToolOutput(status=ToolStatus.ERROR, message=tool_result, logs=[], number_of_logs=0),
                        raw_output=tool_result,
                        intermediate_steps=result.get("intermediate_steps", [])
                    )
            
            else:
                return LokiAgentOutput(
                    status=ToolStatus.ERROR,
                    user_request=user_request,
                    agent_result=LogToolOutput(status=ToolStatus.ERROR, message=f"No intermediate steps received from Loki Agent. Loki Agent result: {result}", logs=[], number_of_logs=0),
                    raw_output=result,
                    intermediate_steps=result.get("intermediate_steps", [])
                )

        except Exception as e:
            print(f"Exception in query_logs: {e}")
            return LokiAgentOutput(
                status=ToolStatus.ERROR,
                user_request=user_request,
                agent_result=LogToolOutput(status=ToolStatus.ERROR, message=f"Loki Agent execution failed: {str(e)}", logs=[], number_of_logs=0),
                raw_output=str(e),
                intermediate_steps=result.get("intermediate_steps", []) if result else []
            )


# Global agent instance
_loki_agent = None


def get_loki_agent() -> LokiQueryAgent:
    """Get or create the global LokiQueryAgent instance"""
    global _loki_agent
    if _loki_agent is None:
        _loki_agent = LokiQueryAgent()
    return _loki_agent


# LangGraph Node Functions for Loki MCP

async def identify_missing_log_data_node(
    state: GrafanaAlert,
) -> Command[Literal["loki_execute_query_node"]]:
    """
    Node that processes a request for additional log context using Loki.
    This node uses an LLM to intelligently identify what data is missing and
    generate a natural language request for additional logs.
    """
    # Get the current state
    log_summary = state.logSummary
    log_stream = state.logStream

    # Get LLM instance
    llm = get_llm()

    # Use LLM to identify what data is missing and generate a smart request
    user_request = await identify_missing_data(
        log_summary=log_summary,
        log_stream=log_stream,
        llm=llm
    )

    return Command(
        goto="loki_execute_query_node",
        update={"lokiUserRequest": user_request}
    )


async def loki_execute_query_node(
    state: GrafanaAlert,
) -> Command[Literal["suggest_step_by_step_solution_with_context_node"]]:
    """
    Node that executes the Loki query using the ToolCallingAgent.

    TODO: Add query validation and retry logic
    """
    try:
        user_request = state.lokiUserRequest
        if not user_request:
            raise ValueError("No user request found in state.lokiUserRequest. \
                Please use the loki_user_query_node to set the user request.")
        agent = get_loki_agent()

        # Prepare context from the current state
        context = {
            "logSummary": state.logSummary,
            "expertClassification": state.expertClassification,
            "logMessage": state.logMessage,
            "logStream": state.logStream
        }

        # Execute the query
        result = await agent.query_logs(user_request, context)

        # Build context from Loki query result
        old_loki_context = state.additionalContextFromLoki
        if result.agent_result and isinstance(result.agent_result, LogToolOutput):
            additional_context = result.agent_result.build_context()
        else:
            print(f"WARNING: No logs returned from Loki query.")
            additional_context = ""
        if old_loki_context and additional_context:
            additional_context = old_loki_context + "\n\n" + additional_context

        return Command(
            goto="suggest_step_by_step_solution_with_context_node",
            update={
                "lokiQueryResult": result.model_dump(),
                "additionalContextFromLoki": additional_context
            }
        )

    except Exception as e:
        print(f"Exception in loki_execute_query_node: {e}")
        print(f"WARNING: Continuing to solution without Loki context due to error.")
        return Command(
            goto="suggest_step_by_step_solution_with_context_node",
            update={
                "lokiQueryResult": LokiAgentOutput(
                    status=ToolStatus.ERROR,
                    user_request=user_request if user_request else "No user request found",
                    agent_result=LogToolOutput(status=ToolStatus.ERROR, message=f"Failed to execute Loki query: {str(e)}", logs=[], number_of_logs=0),
                    raw_output=str(e),
                    intermediate_steps=[]
                ).model_dump()
            }
        )

async def identify_missing_data(
    log_summary: str, log_stream: LogStream | Dict[str, Any], llm: ChatOpenAI
):
    """
    Identify what critical data is missing to fully understand and resolve the issue.

    Args:
        log_summary: Summary of the log to analyze
        log_stream: Log stream of the log (can be LogStream object or dict)
        llm: ChatOpenAI instance to use for generation

    Returns:
        str: Natural language description of missing data needed for investigation
    """
    with open("src/alm/agents/prompts/generate_loki_query_request.md", "r") as f:
        generate_loki_query_request_user_message = f.read()

    # Convert log_stream to LogStream object if it's a dict
    if isinstance(log_stream, dict):
        log_stream_obj = LogStream.model_validate(log_stream)
    else:
        log_stream_obj = log_stream

    llm_identify_missing_data = llm.with_structured_output(IdentifyMissingDataSchema)
    missing_data_result = await llm_identify_missing_data.ainvoke(
        [
            {
                "role": "system",
                "content": "You are an Ansible expert and helpful assistant specializing in log analysis",
            },
            {
                "role": "user",
                "content": generate_loki_query_request_user_message.replace(
                    "{log_summary}", log_summary
                ).replace("{log_stream}", log_stream_obj.model_dump_json(indent=2, exclude_none=True)),
            },
        ]
    )
    return missing_data_result.missing_data_request

