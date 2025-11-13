"""
LangChain ToolCallingAgent integration with LangGraph for perfect log query function matching.
"""

import json
from typing import Dict, Any, Optional

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage

from alm.agents.loki_agent.constants import (
    CONTEXT_TRUNCATE_LENGTH,
    CONTEXT_TRUNCATE_SUFFIX,
    LOKI_AGENT_SYSTEM_PROMPT_PATH,
)
from alm.agents.loki_agent.schemas import LogToolOutput, LokiAgentOutput, ToolStatus
from alm.llm import get_llm


class LokiQueryAgent:
    """
    LangChain Agent wrapper for perfect function matching in log queries.
    """

    def __init__(self):
        # Import LOKI_TOOLS here to avoid circular dependency
        from alm.tools import LOKI_TOOLS

        self.llm = get_llm()
        self.tools = LOKI_TOOLS
        self.agent = self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the LangChain Agent using create_agent()"""
        # Load system prompt from file
        with open(LOKI_AGENT_SYSTEM_PROMPT_PATH, "r") as f:
            system_prompt = f.read()

        # Create the agent with system prompt
        return create_agent(
            model=self.llm,
            tools=self.tools,
            debug=True,  # uncomment this to enable debugging
            system_prompt=system_prompt,
        )

    async def query_logs(
        self, user_request: str, context: Optional[Dict[str, Any]] = None
    ) -> LokiAgentOutput:
        """
        Execute log query using the LangChain Agent.

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
                if "logMessage" in context and context["logMessage"]:
                    value_str = str(context["logMessage"])
                    if len(value_str) > CONTEXT_TRUNCATE_LENGTH:
                        value_str = (
                            value_str[:CONTEXT_TRUNCATE_LENGTH]
                            + CONTEXT_TRUNCATE_SUFFIX
                        )
                    context_parts.append(f"Log Message: {value_str}")

                # Add all other fields generically
                for key, value in context.items():
                    if (
                        key != "logMessage" and value
                    ):  # Skip logMessage (already added) and empty values
                        # Convert camelCase to Title Case with spaces
                        formatted_key = (
                            "".join([" " + c if c.isupper() else c for c in key])
                            .strip()
                            .title()
                        )

                        context_parts.append(f"{formatted_key}: {str(value)}")

                if context_parts:
                    enhanced_request = (
                        f"{user_request}\n\nAdditional Context:\n"
                        + "\n".join(context_parts)
                    )

            print(f"\n\n📊 Enhanced Request:\n{enhanced_request}\n\n")

            # Execute the agent
            result = await self.agent.ainvoke(
                {"messages": [{"role": "user", "content": enhanced_request}]}
            )

            print(f"\n\n📊 Result: {result}\n\n")

            # Extract tool results from ToolMessages
            messages = result.get("messages", [])
            tool_messages = [msg for msg in messages if isinstance(msg, ToolMessage)]

            if tool_messages:
                # Get the last tool result
                last_tool_message = tool_messages[-1]
                tool_result = last_tool_message.content

                try:
                    # Parse the tool result should be JSON representation of LogToolOutput
                    log_tool_output_object = LogToolOutput.model_validate_json(
                        tool_result
                    )

                    print(f"\n\n📊 LogToolOutput object:\n{log_tool_output_object}\n\n")

                    return LokiAgentOutput(
                        status=ToolStatus.SUCCESS,
                        user_request=user_request,
                        agent_result=log_tool_output_object,
                        raw_output=tool_result,
                        tool_messages=tool_messages,
                    )
                except json.JSONDecodeError as e:
                    print(f"JSON decode error in query_logs: {e}")
                    # If not JSON, return as text
                    return LokiAgentOutput(
                        status=ToolStatus.SUCCESS,
                        user_request=user_request,
                        agent_result=LogToolOutput(
                            status=ToolStatus.ERROR,
                            message=tool_result,
                            logs=[],
                            number_of_logs=0,
                        ),
                        raw_output=tool_result,
                        tool_messages=tool_messages,
                    )

            else:
                return LokiAgentOutput(
                    status=ToolStatus.ERROR,
                    user_request=user_request,
                    agent_result=LogToolOutput(
                        status=ToolStatus.ERROR,
                        message=f"No tool messages received from Loki Agent. Loki Agent result: {result}",
                        logs=[],
                        number_of_logs=0,
                    ),
                    raw_output=str(result),
                    tool_messages=[],
                )

        except Exception as e:
            print(f"Exception in query_logs: {e}")
            import traceback

            traceback.print_exc()

            return LokiAgentOutput(
                status=ToolStatus.ERROR,
                user_request=user_request,
                agent_result=LogToolOutput(
                    status=ToolStatus.ERROR,
                    message=f"Loki Agent execution failed: {str(e)}",
                    logs=[],
                    number_of_logs=0,
                ),
                raw_output=str(e),
                tool_messages=[],
            )


# Global agent instance
_loki_agent = None


def get_loki_agent() -> LokiQueryAgent:
    """Get or create the global LokiQueryAgent instance"""
    global _loki_agent
    if _loki_agent is None:
        _loki_agent = LokiQueryAgent()
    return _loki_agent
