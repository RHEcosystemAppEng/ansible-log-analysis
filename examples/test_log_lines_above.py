"""
Example to test the get_log_lines_above tool with closure-bound context.

This example demonstrates calling the get_log_lines_above tool
through the Loki agent, which has log context (file_name, log_message,
log_timestamp) bound via Python closures.

Note: The agent is created per-alert with context values bound at creation time.
"""

import asyncio
from datetime import datetime
from alm.agents.loki_agent.agent import create_loki_agent
from alm.agents.loki_agent.schemas import LogToolOutput


async def test_log_lines_above():
    """
    Run a test of the get_log_lines_above tool directly.
    This test creates an agent with closure-bound context and then
    extracts the tool to call it directly with ainvoke.
    """
    print("=" * 80)
    print("🧪 Testing get_log_lines_above Tool (Direct Tool Call)")
    print("=" * 80)

    # Test parameters - these will be bound via closure
    file_name = "/var/log/ansible_logs/failed/job_1461865.txt"
    log_message = r'fatal: [bastion.6jxd6.internal]: FAILED! => {"changed": false, "dest": "/usr/bin/argocd", "elapsed": 0, "msg": "Request failed", "response": "HTTP Error 307: The HTTP server returned a redirect error that would lead to an infinite loop.\\nThe last 30x error message was:\\nTemporary Redirect", "status_code": 307, "url": "https://openshift-gitops-server-openshift-gitops.apps.cluster-6jxd6.6jxd6.sandbox2747.opentlc.com/download/argocd-linux-amd64"}'
    log_timestamp = (
        datetime.now().isoformat()
    )  # Usually close enough to the target log message
    lines_above = 20

    print("\n📝 Test Parameters (to be bound via closure):")
    print(f"  File Name: {file_name}")
    print(
        f"  Log Message: {log_message[:100]}..."
        if len(log_message) > 100
        else f"  Log Message: {log_message}"
    )
    print(f"  Log Timestamp: {log_timestamp}")
    print(f"  Lines Above: {lines_above}")

    print("\n🚀 Creating Loki agent with closure-bound context...")
    print("-" * 80)

    try:
        # Create the Loki agent with context bound via closure
        agent = create_loki_agent(file_name, log_message, log_timestamp)

        # Extract the get_log_lines_above tool from the agent's tools list
        get_log_lines_above = None
        for tool in agent.tools:
            if tool.name == "get_log_lines_above":
                get_log_lines_above = tool
                break

        if not get_log_lines_above:
            raise Exception("get_log_lines_above tool not found in agent.tools")

        print(f"✅ Found tool: {get_log_lines_above.name}")
        print("\n🔧 Calling tool directly with ainvoke...")
        print("-" * 80)

        # Call the tool directly with ainvoke
        tool_result = await get_log_lines_above.ainvoke({"lines_above": lines_above})

        print("\n" + "=" * 80)
        print("✨ Tool Execution Complete!")
        print("=" * 80)

        # Parse the tool result (it's a JSON string)
        tool_output = LogToolOutput.model_validate_json(tool_result)

        print("\n📊 Tool Output:")
        print(f"  Status: {tool_output.status}")
        print(f"  Message: {tool_output.message}")
        print(f"  Number of Logs: {tool_output.number_of_logs}")
        print(f"  Execution Time: {tool_output.execution_time_ms} ms")

        # Display the retrieved logs
        if tool_output.logs:
            print(f"\n📄 Retrieved {len(tool_output.logs)} Log Entries:")
            print("-" * 80)
            for i, log in enumerate(tool_output.logs, 1):
                timestamp = log.timestamp
                message = log.message
                # Truncate long messages for display
                if len(message) > 150:
                    message_display = message[:150] + "..."
                else:
                    message_display = message
                print(f"\n  [{i}] Timestamp: {timestamp}")
                print(f"      Message: {message_display}")

            # Print context
            print("\n📝 Context Output:")
            print("-" * 80)
            print(tool_output.build_context())
        else:
            print("\n  ❌ No logs retrieved")

        return tool_output

    except Exception as e:
        print(f"\n❌ Error during tool execution: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_log_lines_above())

    print("\n" + "=" * 80)
    print("🎉 Direct Tool Test Complete!")
    print("=" * 80)
