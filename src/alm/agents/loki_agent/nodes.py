"""
LangGraph node functions for Loki MCP integration.
"""

from typing import Dict, Any
from langchain_openai import ChatOpenAI

from alm.agents.loki_agent.constants import IDENTIFY_MISSING_DATA_PROMPT_PATH
from alm.agents.loki_agent.schemas import IdentifyMissingDataSchema
from alm.models import LogLabels


async def identify_missing_data(
    log_summary: str,
    log_labels: LogLabels | Dict[str, Any],
    log_timestamp: str,
    llm: ChatOpenAI,
):
    """
    Identify what critical data is missing to fully understand and resolve the issue.

    Args:
        log_summary: Summary of the log to analyze
        log_labels: Log labels of the log (can be LogLabels object or dict)
        log_timestamp: Timestamp of the log
        llm: ChatOpenAI instance to use for generation

    Returns:
        str: Natural language description of missing data needed for investigation
    """
    with open(IDENTIFY_MISSING_DATA_PROMPT_PATH, "r") as f:
        generate_loki_query_request_user_message = f.read()

    # Convert log_labels to LogLabels object if it's a dict to exclude none values
    if isinstance(log_labels, dict):
        log_labels_obj = LogLabels.model_validate(log_labels)
    else:
        log_labels_obj = log_labels
    log_labels_json = log_labels_obj.model_dump_json(indent=2, exclude_none=True)

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
                )
                .replace(
                    "{log_labels}",
                    log_labels_json,
                )
                .replace(
                    "{log_timestamp}",
                    log_timestamp,
                ),
            },
        ]
    )
    return missing_data_result.missing_data_request
