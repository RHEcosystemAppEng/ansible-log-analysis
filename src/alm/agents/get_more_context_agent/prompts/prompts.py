with open("src/alm/agents/get_more_context_agent/prompts/loki_router.md", "r") as f:
    loki_router_system_message = f.read()

loki_router_user_message = """**Log Summary:**
{log_summary}

**Cheat Sheet Context:**
{cheat_sheet_context}"""
