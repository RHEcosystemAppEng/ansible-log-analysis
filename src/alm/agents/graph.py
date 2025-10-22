from src.alm.llm import get_llm
from src.alm.models import GrafanaAlert
from src.alm.agents.node import (
    summarize_log,
    classify_log,
    suggest_step_by_step_solution,
    router_step_by_step_solution,
    infer_cluster_log,
)
from src.alm.agents.loki_agent_node import (
    identify_missing_log_data_node,
    loki_execute_query_node,
)
from src.alm.agents.loki_output_schemas import LogToolOutput
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

# from src.alm.agents.get_more_context_agent.graph import get_graph as get_more_context_agent_graph
from typing import Literal


# from langchain.globals import set_debug

# set_debug(True)  # Enables LangChain debug mode globally

llm = get_llm()


# Nodes
async def cluster_logs_node(
    state: GrafanaAlert,
) -> Command[Literal["summarize_log_node"]]:
    logs = state.logMessage
    log_cluster = infer_cluster_log(logs)
    return Command(goto="summarize_log_node", update={"logCluster": log_cluster})


async def summarize_log_node(
    state: GrafanaAlert,
) -> Command[Literal["classify_log_node"]]:
    log_summary = await summarize_log(state.logMessage, llm)
    return Command(goto="classify_log_node", update={"logSummary": log_summary})


async def classify_log_node(
    state: GrafanaAlert,
) -> Command[Literal["router_step_by_step_solution_node"]]:
    log_summary = state.logSummary
    log_category = await classify_log(log_summary, llm)
    return Command(
        goto="router_step_by_step_solution_node",
        update={"expertClassification": log_category},
    )


async def suggest_step_by_step_solution_node(
    state: GrafanaAlert,
) -> Command[Literal[END]]:
    log_summary = state.logSummary
    log = state.logMessage
    step_by_step_solution = await suggest_step_by_step_solution(log_summary, log, llm)
    return Command(goto=END, update={"stepByStepSolution": step_by_step_solution})


async def router_step_by_step_solution_node(
    state: GrafanaAlert,
) -> Command[
    Literal[
        "suggest_step_by_step_solution_node",
        "identify_missing_log_data_node",
    ]
]:
    log_summary = state.logSummary
    classification = await router_step_by_step_solution(log_summary, llm)
    return Command(
        goto="suggest_step_by_step_solution_node"
        if classification == "No More Context Needed"
        else "identify_missing_log_data_node",
        update={"needMoreContext": classification == "Need More Context"},
    )


async def suggest_step_by_step_solution_with_context_node(
    state: GrafanaAlert,
) -> Command[Literal[END]]:
    log_summary = state.logSummary
    log = state.logMessage
    
    # Build context from Loki agent result
    context_for_step_by_step_solution = None
    if state.additionalContextFromLoki:
        context_for_step_by_step_solution = f"Context logs from loki:\n{state.additionalContextFromLoki}"
        print(context_for_step_by_step_solution)
    else:
        print("WARNING: No Loki additional context found! continuing without context...")
    
    step_by_step_solution = await suggest_step_by_step_solution(
        log_summary,
        log,
        llm,
        context_for_step_by_step_solution,
    )
    return Command(goto=END, update={"stepByStepSolution": step_by_step_solution})


def build_graph():
    """call ainvoke to the graph to invoke it asynchronously"""
    builder = StateGraph(GrafanaAlert)
    builder.add_edge(START, "cluster_logs_node")
    builder.add_node("cluster_logs_node", cluster_logs_node)
    builder.add_node(summarize_log_node)
    builder.add_node(classify_log_node)
    builder.add_node(suggest_step_by_step_solution_node)
    builder.add_node(router_step_by_step_solution_node)
    builder.add_node(suggest_step_by_step_solution_with_context_node)

    # Add Loki query nodes
    builder.add_node(identify_missing_log_data_node)
    builder.add_node(loki_execute_query_node)

    return builder.compile()


_compiled_graph = build_graph()


def get_graph():
    return _compiled_graph
