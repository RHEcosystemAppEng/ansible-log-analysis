"""
Simple example to test the get_log_lines_above tool directly.

This example demonstrates calling the get_log_lines_above tool
without using the agent, to retrieve context lines before a specific log message.
"""

import asyncio
import json

from alm.agents.loki_agent.schemas import LogToolOutput
from alm.tools.loki_tools import get_log_lines_above


async def test_log_lines_above():
    """
    Run a direct test of the get_log_lines_above tool.
    """
    print("=" * 80)
    print("🧪 Testing get_log_lines_above Tool")
    print("=" * 80)

    # Test parameters
    file_name = "/var/log/ansible_logs/failed/job_1461865.txt"
    log_message = 'fatal: [bastion.6jxd6.internal]: FAILED! => {"changed": false, "dest": "/usr/bin/argocd", "elapsed": 0, "msg": "Request failed", "response": "HTTP Error 307: The HTTP server returned a redirect error that would lead to an infinite loop.\\\\nThe last 30x error message was:\\\\nTemporary Redirect", "status_code": 307, "url": "https://openshift-gitops-server-openshift-gitops.apps.cluster-6jxd6.6jxd6.sandbox2747.opentlc.com/download/argocd-linux-amd64"}'
    log_timestamp = "1762427889459"
    lines_above = 20

    print("\n📝 Test Parameters:")
    print(f"  File Name: {file_name}")
    print(f"  Log Message: {log_message}")
    print(f"  Log Timestamp: {log_timestamp}")
    print(f"  Lines Above: {lines_above}")

    print("\n🚀 Calling get_log_lines_above tool...")
    print("-" * 80)

    try:
        # Call the tool directly
        result = await get_log_lines_above.ainvoke(
            {
                "file_name": file_name,
                "log_message": log_message,
                "log_timestamp": log_timestamp,
                "lines_above": lines_above,
            }
        )

        print("\n" + "=" * 80)
        print("✨ Tool Execution Complete!")
        print("=" * 80)

        # Parse the JSON result
        result_json = json.loads(result)

        print("\n📊 Result Summary:")
        print(f"  Status: {result_json['status']}")
        print(f"  Message: {result_json.get('message', 'N/A')}")
        print(f"  Number of Logs: {result_json['number_of_logs']}")
        print(f"  Execution Time: {result_json.get('execution_time_ms', 'N/A')} ms")

        # Display the retrieved logs
        if result_json["logs"]:
            print(f"\n📄 Retrieved {len(result_json['logs'])} Log Entries:")
            print("-" * 80)
            for i, log in enumerate(result_json["logs"], 1):
                timestamp = log.get("timestamp", "N/A")
                message = log.get("message", "")
                # Truncate long messages for display
                if len(message) > 150:
                    message_display = message[:150] + "..."
                else:
                    message_display = message
                print(f"\n  [{i}] Timestamp: {timestamp}")
                print(f"      Message: {message_display}")
        else:
            print("\n  ❌ No logs retrieved")

        # Print full raw result for debugging
        log_tool_output = LogToolOutput.model_validate_json(result)
        print(f"Context is: \n{log_tool_output.build_context()}")

        return result_json

    except Exception as e:
        print(f"\n❌ Error during tool execution: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_log_lines_above())

    print("\n" + "=" * 80)
    print("🎉 Test Complete!")
    print("=" * 80)
