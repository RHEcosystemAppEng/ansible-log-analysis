from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Literal

from .rag_handler import RAGHandler

# Initialize RAG handler instance
_rag_handler = RAGHandler()


class LokiRouterSchema(BaseModel):
    reasoning: str = Field(description="the reasoning for the decision")
    classification: Literal[
        "need_more_context_from_loki_db", "no_need_more_context_from_loki_db"
    ] = Field(
        description="determines if we need to fetch more context from loki db, 'need_more_context_from_loki_db' if we need to fetch more context, 'no_need_more_context_from_loki_db' if we don't need to fetch more context"
    )


with open("src/alm/agents/get_more_context_agent/prompts/loki_router.md", "r") as f:
    loki_router_user_message = f.read()


async def get_cheat_sheet_context(log_summary: str) -> str:
    """
    Retrieve relevant context from the RAG knowledge base for solving the error.

    Args:
        log_summary: Summary of the Ansible error log

    Returns:
        Formatted string with relevant error solutions, or empty string if unavailable
    """
    return await _rag_handler.get_cheat_sheet_context(log_summary)


async def loki_router(
    log_summary: str, cheat_sheet_context: str, llm: ChatOpenAI
) -> LokiRouterSchema:
    llm_structured = llm.with_structured_output(LokiRouterSchema)
    output = await llm_structured.ainvoke(
        [
            {
                "role": "system",
                "content": "You are an Ansible expert and helpful assistant",
            },
            {
                "role": "user",
                "content": loki_router_user_message.format(
                    log_summary=log_summary, cheat_sheet_context=cheat_sheet_context
                ),
            },
        ]
    )
    return LokiRouterSchema.model_validate(output)
