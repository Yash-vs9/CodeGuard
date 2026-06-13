import argparse
import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from graph.graph import app_graph
from graph.code import graph as code_graph

console = Console()

CODEGUARD_ART = r"""
[bold green]  ██████╗ ██████╗ ██████╗ ███████╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗ [/bold green]
[bold green] ██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗[/bold green]
[bold green] ██║     ██║   ██║██║  ██║█████╗  ██║  ███╗██║   ██║███████║██████╔╝██║  ██║[/bold green]
[bold green]██║     ██║   ██║██║  ██║██╔══╝  ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║[/bold green]
[bold green]╚██████╗╚██████╔╝██████╔╝███████╗╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝[/bold green]
[bold green] ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝[/bold green]
"""


def print_banner():
    console.print(Panel.fit(
        CODEGUARD_ART.strip('\n'),
        title="[bold cyan][/bold cyan]",
        subtitle="[bold magenta]AI Security & Quality Scanner[/bold magenta]",
        border_style="bold blue"
    ))

from agents.chat_agent import chat_agent

def main():
    parser = argparse.ArgumentParser(description="Dragon CLI - LangGraph Project Scanner")
    parser.add_argument("-q", "--query", type=str, help="The user query to run")
    parser.add_argument("-p", "--path", type=str, help="The path to the project directory (scan mode) or working directory (code mode)")
    parser.add_argument("-m", "--mode", type=str, choices=["scan", "code"], default="scan", help="Mode: 'scan' (vulnerability/quality scanner) or 'code' (coding agent)")
    args = parser.parse_args()

    print_banner()

    if args.mode == "code":
        run_code_graph(args)
    else:
        run_scan_graph(args)


def run_code_graph(args):
    """Run the coding agent graph (graph/code.py)."""
    query = args.query
    if not query:
        console.print("[bold green]Coding Agent ready. Describe what you want to build or fix:[/bold green]")
        query = Prompt.ask("[bold cyan]Query[/bold cyan]")

    working_dir = args.path
    if not working_dir:
        working_dir = Prompt.ask("[bold cyan]Enter the working directory for the project[/bold cyan]")

    os.environ["AGENT_WORKING_DIR"] = working_dir
    console.print(f"\n[bold yellow]Starting coding agent for:[/bold yellow] {working_dir}\n")

    input_data = {
        "user_query": query,
        "plan": "",
        "memory": [],
        "working_dir": working_dir,
        "tasks": [],
        "current_task": 0,
        "feedback_on_current_task_ifany": "",
    }

    with Progress(
        SpinnerColumn("dots12", style="bold cyan"),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("Initializing coding agent...", total=None)

        try:
            for event in code_graph.stream(input_data, stream_mode="updates"):
                node_name = list(event.keys())[0]
                node_output = event[node_name]

                if node_name == "planner":
                    tasks = node_output.get("tasks", [])
                    plan_text = node_output.get("plan", "")
                    progress.update(task_id, description="[bold green]Planner[/bold green] finished building the task list...")
                    if plan_text:
                        progress.console.print(Panel(Markdown(plan_text), title="[bold green]📋 Coding Plan[/bold green]", border_style="bold green"))
                    if tasks:
                        task_lines = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(tasks))
                        progress.console.print(Panel(task_lines, title="[bold cyan]🗂️  Task List[/bold cyan]", border_style="bold cyan"))

                elif node_name == "coding":
                    current = node_output.get("current_task")
                    feedback = node_output.get("feedback_on_current_task_ifany", "")

                    if feedback:
                        progress.update(task_id, description="[bold red]Reviewer[/bold red] sent feedback — retrying task...")
                        progress.console.print(Panel(
                            Markdown(feedback),
                            title="[bold red]🔍 Review Feedback[/bold red]",
                            border_style="bold red",
                        ))
                    elif current is not None:
                        progress.update(task_id, description=f"[bold cyan]Coding[/bold cyan] task {current} done — moving to next...")

                else:
                    progress.update(task_id, description=f"Processing: [bold]{node_name}[/bold]...")

                time.sleep(0.1)

        except Exception as e:
            progress.stop()
            console.print(f"[bold red]An error occurred: {e}[/bold red]")
            sys.exit(1)

    console.print("\n[bold green]✅ Coding Agent Finished![/bold green]")


def run_scan_graph(args):
    """Run the original vulnerability/quality scanner graph (graph/graph.py)."""
    query = args.query
    if not query:
        console.print("[bold green]Chat Agent is ready. Describe your problem (type 'done', 'scan', or 'exit' to finish):[/bold green]")
        chat_memory = []
        while True:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            if user_input.lower() in ["done", "scan", "exit", "quit"]:
                break

            chat_memory.append({"role": "user", "content": user_input})

            with console.status("[bold magenta]Agent is typing...[/bold magenta]"):
                response = chat_agent.invoke({"messages": chat_memory})

            ai_msg = response["messages"][-1].content[0]['text']
            console.print(f"[bold magenta]Agent:[/bold magenta] {ai_msg}")
            chat_memory.append({"role": "assistant", "content": ai_msg})

        query = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_memory])

    project_path = args.path
    if not project_path:
        project_path = Prompt.ask("\n[bold cyan]Enter the project path to analyze[/bold cyan]")

    console.print(f"\n[bold yellow]Starting analysis for:[/bold yellow] {project_path}\n")

    input_data = {
        "user_query": query,
        "project_path": project_path
    }

    final_report = ""

    # Setup the progress bar with a nice spinner
    with Progress(
        SpinnerColumn("dots12", style="bold magenta"),
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        console=console,
        transient=True
    ) as progress:
        task_id = progress.add_task("Initializing...", total=None)

        try:
            for event in app_graph.stream(input_data):
                node_name = list(event.keys())[0]

                if node_name == "chat":
                    progress.update(task_id, description="[bold cyan]Chat[/bold cyan] processed memory...")
                elif node_name == "scanner":
                    progress.update(task_id, description="[bold cyan]Scanner[/bold cyan] is mapping the project structure...")
                elif node_name == "planner":
                    progress.update(task_id, description="[bold green]Planner[/bold green] finished building the approach...")
                    plan_text = event[node_name].get("plan", "")
                    if plan_text:
                        progress.console.print(Panel(Markdown(plan_text), title="[bold green]📋 Investigation Plan[/bold green]", border_style="bold green"))
                elif node_name == "security":
                    progress.update(task_id, description="[bold red]Security Agent[/bold red] finished!")
                    report = event[node_name].get("security_report", "")
                    if report:
                        progress.console.print(Panel(Markdown(report), title="[bold red]🛡️ Security Report[/bold red]", border_style="bold red"))
                elif node_name == "logic":
                    progress.update(task_id, description="[bold yellow]Logic Agent[/bold yellow] finished!")
                    report = event[node_name].get("logic_report", "")
                    if report:
                        progress.console.print(Panel(Markdown(report), title="[bold yellow]🧠 Logic Report[/bold yellow]", border_style="bold yellow"))
                elif node_name == "code_quality":
                    progress.update(task_id, description="[bold magenta]Quality Agent[/bold magenta] finished!")
                    report = event[node_name].get("quality_report", "")
                    if report:
                        progress.console.print(Panel(Markdown(report), title="[bold magenta]✨ Code Quality Report[/bold magenta]", border_style="bold magenta"))
                elif node_name == "report":
                    progress.update(task_id, description="[bold white]Finishing up...[/bold white]")
                    final_report = event[node_name].get("final_report", "")
                else:
                    progress.update(task_id, description=f"Processing node: [bold]{node_name}[/bold]...")

                # Small delay to make it feel smooth visually
                time.sleep(0.1)

        except Exception as e:
            progress.stop()
            console.print(f"[bold red]An error occurred during execution: {e}[/bold red]")
            sys.exit(1)

    # After completion
    if final_report:
        console.print("\n[bold green]✅ Analysis Complete![/bold green]")
    else:
        console.print("\n[bold red]No final report was generated![/bold red]")

if __name__ == "__main__":
    main()
