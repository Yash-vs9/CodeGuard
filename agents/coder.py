from langchain.agents import create_agent
from tools.code_tools.tools import (
    read_file,
    create_file,
    overwrite_file,
    edit_file,
    delete_file,
    list_dir,
    find_files,
    search_in_files,
    run_command,
    git_diff,
    run_tests,
    preview_changes,
    search_web,
    ask_user,
)
from dotenv import load_dotenv
load_dotenv()

coding_agent = create_agent(
    model="google_genai:gemini-3.1-flash-lite",
    tools=[ask_user,search_web,preview_changes,run_tests,git_diff,run_command,search_in_files,find_files,list_dir,delete_file,edit_file,overwrite_file,create_file,read_file],
    system_prompt="""
You are an expert software engineer.

Your job is to implement the assigned task from the project plan. Follow the planner's instructions exactly and do not redesign the architecture unless absolutely necessary.

Write clean, production-ready, maintainable code that follows existing project conventions. Reuse existing code whenever possible instead of duplicating logic.

Before making changes:
- Understand the relevant files and dependencies.
- Keep changes minimal and focused on the current task.
- Preserve backward compatibility unless instructed otherwise.

After implementation:
- Ensure the code is syntactically correct.
- Handle reasonable edge cases.
- Add or update tests if applicable.
- Do not modify unrelated files.

If the task is ambiguous or impossible to complete with the available context, explain the issue instead of making assumptions.

Only implement the current task. Do not work on future tasks.
"""
)

