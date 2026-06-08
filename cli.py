import argparse
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from graph.graph import app_graph

console = Console()

DRAGON_ART = r"""
[bold green]                                                 /===-_---~~~~~~~~~------____[/bold green]
[bold green]                                                |===-~___                _,-'[/bold green]
[bold green]                 -==\\                         `//~\\   ~~~~`---.___.-~~[/bold green]
[bold green]             ______-==|                         | |  \\           _-~`[/bold green]
[bold green]       __--~~~  ,-/-==\\                        | |   `\\        ,'[/bold green]
[bold green]    _-~       /'    |  \\                      / /      \\      /[/bold green]
[bold green]  .'        /       |   \\                   /' /        \\   /'[/bold green]
[bold green] /  ____  /         |    \\`\\.__/-~~ ~ \\ _ _/'  /          \\/'[/bold green]
[bold green]/-'~    ~~~~~---__  |     ~-/~         ( )   /'        _--~`[/bold green]
[bold green]                  \\_|      /        _)   ;  ),   __--~~[/bold green]
[bold green]                    '~~--_/      _-~/-  / \\   '-~ \\[/bold green]
[bold green]                   {\\__--_/}    / \\\\_>- )<__\\      \\[/bold green]
[bold green]                   /'   (_/  _-~  | |__>--<__|      |[/bold green]
[bold green]                  |[/bold green][bold red]O  O[/bold red][bold green] _/) )-~     | |__>--<__|     |[/bold green]
[bold green]                  / /~ ,_/       / /__>---<__/      |[/bold green]
[bold green]                 o o _//        /-~_>---<__-~      /[/bold green]
[bold green]                 (^(~          /~_>---<__-      _-~[/bold green]
[bold green]                ,/|           /__>--<__/     _-~[/bold green]
[bold green]             ,//('(          |__>--<__|     /                  .----_[/bold green]
[bold green]            ( ( '))          |__>--<__|    |                 /' _---_[/bold green]
[bold green]         `-)) )) (           |__>--<__|    |               /'  /     ~\\`\\[/bold green]
[bold green]        ,/,'//( (             \\__>--<__\\    \\            /'  //        ||[/bold green]
[bold green]      ,( ( ((, ))              ~-__>--<_~-_  ~--____---~' _/'/        /'[/bold green]
[bold green]    `~/  )` ) ,/|                 ~-_~>--<_/-__       __-~ _/[/bold green]
[bold green]  ._-~//( )/ )) `                    ~~-'_/_/ /~~~~~~~__--~[/bold green]
[bold green]   ;'( ')/ ,)(                              ~~~~~~~~~~[/bold green]
[bold green]  ' ') '( (/[/bold green]
[bold green]    '   '  `[/bold green]
"""


def print_banner():
    console.print(Panel.fit(
        DRAGON_ART.strip('\n'),
        title="[bold cyan][/bold cyan]",
        subtitle="[bold magenta]AI Security & Quality Scanner[/bold magenta]",
        border_style="bold blue"
    ))

from agents.chat_agent import chat_agent

def main():
    parser = argparse.ArgumentParser(description="Dragon CLI - LangGraph Project Scanner")
    parser.add_argument("-q", "--query", type=str, help="The user query to run")
    parser.add_argument("-p", "--path", type=str, help="The path to the project directory")
    args = parser.parse_args()

    print_banner()

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
                    progress.update(task_id, description="[bold green]Planner[/bold green] is building the approach...")
                elif node_name == "security":
                    progress.update(task_id, description="[bold red]Security Agent[/bold red] is hunting for vulnerabilities...")
                elif node_name == "logic":
                    progress.update(task_id, description="[bold yellow]Logic Agent[/bold yellow] is evaluating code logic...")
                elif node_name == "code_quality":
                    progress.update(task_id, description="[bold magenta]Quality Agent[/bold magenta] is reviewing standards...")
                elif node_name == "report":
                    progress.update(task_id, description="[bold white]Generating Final Report...[/bold white]")
                    final_report = event[node_name].get("final_report", "")
                else:
                    progress.update(task_id, description=f"Processing node: [bold]{node_name}[/bold]...")

                # Small delay to make it feel smooth visually
                time.sleep(0.1)
                
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]An error occurred during execution: {e}[/bold red]")
            sys.exit(1)

    # After completion, display the final report beautifully
    if final_report:
        # Pre-process the final report text to make headers render well in markdown
        report_text = final_report.replace("================ SECURITY ================", "# 🛡️ SECURITY")
        report_text = report_text.replace("================ LOGIC ===================", "# 🧠 LOGIC")
        report_text = report_text.replace("============= CODE QUALITY ===============", "# ✨ CODE QUALITY")
        
        console.print(Panel(
            Markdown(report_text),
            title="[bold green]Analysis Complete[/bold green]",
            border_style="bold green",
            expand=True
        ))
    else:
        console.print("[bold red]No final report was generated![/bold red]")

if __name__ == "__main__":
    main()
