"""
Simple example to test Loki agent nodes as a separate graph.

This example demonstrates running the Loki agent flow in isolation:
1. Starts with identify_missing_log_data_node
2. Executes the query via loki_execute_query_node
3. Routes to suggest_step_by_step_solution_with_context_node (terminal node)

The graph terminates at suggest_step_by_step_solution_with_context_node and does nothing
after that point, as requested.
"""

import asyncio
import sys
import os

# Add src to path to handle imports correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from langgraph.graph import StateGraph, START, END
from typing import Literal
from langgraph.types import Command

from alm.agents.loki_input_schemas import LogLevel
from alm.agents.loki_output_schemas import LogToolOutput, LogStream
from alm.models import GrafanaAlert
from alm.agents.loki_agent_node import (
    identify_missing_log_data_node,
    loki_execute_query_node,
)


# Terminal node that does nothing (as requested)
async def suggest_step_by_step_solution_with_context_node(
    state: GrafanaAlert,
) -> Command[Literal[END]]:
    """
    Terminal node that does nothing - just ends the graph.
    This simulates the final destination without any processing.
    """
    print("\n✅ Reached suggest_step_by_step_solution_with_context_node")
    print("📊 Loki Additional Context:", state.additionalContextFromLoki)
    print("🎯 Doing nothing as requested - graph ends here.")
    return Command(goto=END)


def build_loki_test_graph():
    """
    Build a simple graph containing only the Loki agent nodes for testing.

    Graph flow:
    START → identify_missing_log_data_node → loki_execute_query_node →
    suggest_step_by_step_solution_with_context_node → END
    """
    builder = StateGraph(GrafanaAlert)

    # Start with the query request node
    builder.add_edge(START, "identify_missing_log_data_node")

    # Add all Loki agent nodes
    builder.add_node(identify_missing_log_data_node)
    builder.add_node(loki_execute_query_node)

    # Add terminal node (does nothing)
    builder.add_node(suggest_step_by_step_solution_with_context_node)

    return builder.compile()


async def test_loki_graph():
    """
    Run a simple test of the Loki agent graph.
    """
    print("=" * 80)
    print("🧪 Testing Loki Agent Graph in Isolation")
    print("=" * 80)

    # Create a test state with sample data
    test_state = GrafanaAlert(
        logMessage="fatal: [bastion.6jxd6.internal]: FAILED! => {\"changed\": false, \"dest\": \"/usr/bin/argocd\", \"elapsed\": 0, \"msg\": \"Request failed\", \"response\": \"HTTP Error 307: The HTTP server returned a redirect error that would lead to an infinite loop.\\nThe last 30x error message was:\\nTemporary Redirect\", \"status_code\": 307, \"url\": \"https://openshift-gitops-server-openshift-gitops.apps.cluster-6jxd6.6jxd6.sandbox2747.opentlc.com/download/argocd-linux-amd64\"}",
        logSummary="Request failed",
        expertClassification="performance",
        logStream=LogStream(
            detected_level=LogLevel.ERROR,
            filename="/var/log/ansible_logs/failed/job_1461865.txt",
            job="failed_logs",
            service_name="failed_logs"
        ).model_dump()
    )


    print("\n📝 Initial State:")
    print(f"  Log Message: {test_state.logMessage}")
    print(f"  Log Summary: {test_state.logSummary}")
    print(f"  Classification: {test_state.expertClassification}")

    # Build and run the graph
    graph = build_loki_test_graph()

    print("\n🚀 Running Loki Agent Graph...")
    print("-" * 80)

    try:
        # Execute the graph (returns a dict)
        result_dict = await graph.ainvoke(test_state)
        # Convert dict back to GrafanaAlert object
        result = GrafanaAlert.model_validate(result_dict)

        print("\n" + "=" * 80)
        print("✨ Graph Execution Complete!")
        print("=" * 80)

        print("\n📊 Final State Summary:")
        print(f"  Loki User Request: {result.lokiUserRequest}")
        print(f"  Has Loki Query Result: {result.lokiQueryResult is not None}")
        print(f"  Has Additional Context: {result.additionalContextFromLoki is not None}")

        if result.lokiQueryResult:
            print(f"\n  Loki Query Result:")
            print(f"    Status: {result.lokiQueryResult.get('status')}")
            print(f"    User Request: {result.lokiQueryResult.get('user_request')}")

            agent_result = result.lokiQueryResult.get('agent_result')
            if agent_result:
                print(f"    Number of Logs: {agent_result.get('number_of_logs')}")
                print(f"    Query: {agent_result.get('query')}")
                print(f"    Message: {agent_result.get('message')}")

        if result.additionalContextFromLoki:
            print(f"\n  Additional Context from Loki:")
            # Truncate if too long for display
            context = result.additionalContextFromLoki
            if len(context) > 500:
                print(f"    {context[:500]}...")
                print(f"    (truncated, total length: {len(context)} chars)")
            else:
                print(f"    {context}")

        return result

    except Exception as e:
        print(f"\n❌ Error during graph execution: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_loki_graph())

    print("\n" + "=" * 80)
    print("🎉 Test Complete!")
    print("=" * 80)
