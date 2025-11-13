with open("src/alm/agents/prompts/summarize_error_log.md", "r") as f:
    log_summary_system_message = f.read()
log_summary_user_message = """ansible_log_error:
```
{error_log}
```

log_summary:"""

with open("src/alm/agents/prompts/classifiy_log.md", "r") as f:
    log_category_system_message = f.read()
log_category_user_message = """**Now classify the following Ansible log entry:**

```
{log_summary}
```

**Category:**"""


with open("src/alm/agents/prompts/create_step_by_step_sol.md", "r") as f:
    suggest_step_by_step_solution_system_message = f.read()
suggest_step_by_step_solution_user_message = """**Log Summary:**
```
{log_summary}
```
**Error Log:**
```
{log}
```"""
suggest_step_by_step_solution_with_context_user_message = """**Log Summary:**
```
{log_summary}
```
**Additional Context:**
```
{context}
```
**Error Log:**
```
{log}
```"""

with open("src/alm/agents/prompts/router_step_by_step_solution.md", "r") as f:
    router_step_by_step_solution_system_message = f.read()
router_step_by_step_solution_user_message = """**Error Log Summary:**
```
{log_summary}
```

**Classification:**"""
