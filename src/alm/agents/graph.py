from alm.agents.get_more_context_agent.state import ContextAgentState
from alm.agents.loki_agent.schemas import LogEntry, LogLabels
from alm.llm import get_llm
from alm.models import GrafanaAlert
from alm.agents.node import (
    summarize_log,
    classify_log,
    suggest_step_by_step_solution,
    router_step_by_step_solution,
    infer_cluster_log,
)
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from alm.agents.get_more_context_agent.graph import more_context_agent_graph


llm = get_llm()


# Nodes
async def cluster_logs_node(
    state: GrafanaAlert,
) -> Command:
    logs = state.logMessage
    log_cluster = infer_cluster_log(logs)
    return Command(goto="summarize_log_node", update={"logCluster": log_cluster})


async def summarize_log_node(
    state: GrafanaAlert,
) -> Command:
    log_summary = await summarize_log(state.logMessage, llm)
    return Command(goto="classify_log_node", update={"logSummary": log_summary})


async def classify_log_node(
    state: GrafanaAlert,
) -> Command:
    log_summary = state.logSummary
    log_category = await classify_log(log_summary, llm)
    return Command(
        goto="router_step_by_step_solution_node",
        update={"expertClassification": log_category},
    )


async def suggest_step_by_step_solution_node(
    state: GrafanaAlert,
) -> Command:
    log_summary = state.logSummary
    log = state.logMessage
    context = state.contextForStepByStepSolution
    step_by_step_solution = await suggest_step_by_step_solution(
        log_summary, log, llm, context
    )
    return Command(goto=END, update={"stepByStepSolution": step_by_step_solution})


async def router_step_by_step_solution_node(
    state: GrafanaAlert,
) -> Command:
    log_summary = state.logSummary
    classification = await router_step_by_step_solution(log_summary, llm)
    return Command(
        goto="suggest_step_by_step_solution_node"
        if classification == "No More Context Needed"
        else "get_more_context_node",
        update={"needMoreContext": classification == "Need More Context"},
    )


async def get_more_context_node(
    state: GrafanaAlert,
) -> Command:
    log_summary = state.logSummary
    log_labels = LogLabels.model_validate(state.log_labels)
    log_entry = LogEntry(
        message=state.logMessage,
        log_labels=log_labels,
        timestamp="Unknown timestamp"
        if state.logTimestamp is None
        else state.logTimestamp.isoformat(),
    )
    subgraph_state = await more_context_agent_graph.ainvoke(
        ContextAgentState(
            log_summary=log_summary,
            log_entry=log_entry,
            expert_classification=state.expertClassification,
        )
    )
    context_agent_state = ContextAgentState.model_validate(subgraph_state)
    loki_context = context_agent_state.loki_context
    cheat_sheet_context = (
        f"Context from cheat sheet:\n{context_agent_state.cheat_sheet_context}"
    )
    context = (
        f"Context logs from loki:\n{loki_context}\n\n{cheat_sheet_context}"
        if loki_context
        else cheat_sheet_context
    )
    return Command(
        goto="suggest_step_by_step_solution_node",
        update={"contextForStepByStepSolution": context},
    )


def build_graph():
    """call ainvoke to the graph to invoke it asynchronously"""
    builder = StateGraph(GrafanaAlert)
    builder.add_edge(START, "cluster_logs_node")
    builder.add_node("cluster_logs_node", cluster_logs_node)
    builder.add_node(summarize_log_node)
    builder.add_node(classify_log_node)
    builder.add_node(suggest_step_by_step_solution_node)
    builder.add_node(router_step_by_step_solution_node)
    builder.add_node(get_more_context_node)

    return builder.compile()


_compiled_graph = build_graph()


def get_graph():
    return _compiled_graph
