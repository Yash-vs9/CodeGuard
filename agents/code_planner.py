from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
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
import os
from dotenv import load_dotenv
load_dotenv()

GOOGLE_API_KEY_1=os.getenv("GOOGLE_API_KEY_1")
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY_1,
)
planner_agent = create_agent(
    model=model,
    tools=[ask_user,search_web,preview_changes,run_tests,git_diff,run_command,search_in_files,find_files,list_dir,delete_file,edit_file,overwrite_file,create_file,read_file],
    system_prompt="""
You are an expert software architect and planner.

Your job is to analyze the user's request and create a clear, beautiful implementation plan. Do NOT write code.

# Formatting Rules
You MUST format your output in rich Markdown so it is easy to read in a terminal:
- Use `#` and `##` for section headers.
- Use bullet points (`*` or `-`) for lists.
- Use **bold text** to highlight important terms, file names, or module names.
- Use `inline code formatting` for any variable names, paths, or shell commands.

# Task Breakdown
Break the project into small, ordered tasks that can be implemented one at a time. For each task, create a clean subsection specifying:
* **Objective:** What this task achieves.
* **Files Affected:** Files/modules likely to be created or modified.
* **Dependencies:** What must be done before this.
* **Implementation Notes:** Brief, high-level guidelines.

Keep tasks independent and concise so a coding agent can execute them sequentially. Focus on architecture, data flow, APIs, edge cases, and project structure.

# Modern Web Development & Research
The frontend ecosystem (Tailwind CSS, Next.js, Vite, React) evolves extremely fast. Do NOT rely purely on your internal knowledge for modern libraries, as you may hallucinate outdated configurations (e.g., confusing Tailwind v3 vs v4).
**If a task involves configuring or debugging modern web tools, YOU MUST use the `search_web` tool or explicitly instruct the Coder Agent to research the official documentation first.**

Output ONLY the beautifully formatted Markdown plan.
"""
)

