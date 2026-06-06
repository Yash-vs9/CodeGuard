from agents.planner_agent import planner_agent
from agents.code_quality_agent import code_quality_agent
from agents.logic_agent import logic_agent
from agents.project_scanner_agent import project_scanner_agent
from agents.security_agent import security_agent

from langgraph.graph import StateGraph, START, END
from typing import TypedDict


class AgentState(TypedDict):
    user_query: str
    project_path: str

    project_map: str
    plan: str

    security_report: str
    logic_report: str
    quality_report: str

    final_report: str


def get_last_message(result):
    return result["messages"][-1].content


def project_scanner_node(state: AgentState):

    result = project_scanner_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
User Request:
{state["user_query"]}

Project Path:
{state["project_path"]}
"""
                }
            ]
        }
    )

    return {
        "project_map": get_last_message(result)
    }


def planner_node(state: AgentState):

    result = planner_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
User Request:
{state["user_query"]}

Project Scan:
{state["project_map"]}
"""
                }
            ]
        }
    )

    return {
        "plan": get_last_message(result)
    }


def security_node(state: AgentState):

    result = security_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Project Scan:
{state["project_map"]}

Plan:
{state["plan"]}
"""
                }
            ]
        }
    )

    return {
        "security_report": get_last_message(result)
    }


def logic_node(state: AgentState):

    result = logic_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Project Scan:
{state["project_map"]}

Plan:
{state["plan"]}
"""
                }
            ]
        }
    )

    return {
        "logic_report": get_last_message(result)
    }


def code_quality_node(state: AgentState):

    result = code_quality_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
Project Scan:
{state["project_map"]}

Plan:
{state["plan"]}
"""
                }
            ]
        }
    )

    return {
        "quality_report": get_last_message(result)
    }


def report_node(state: AgentState):

    report = f"""
================ SECURITY ================

{state.get("security_report", "")}

================ LOGIC ===================

{state.get("logic_report", "")}

============= CODE QUALITY ===============

{state.get("quality_report", "")}
"""

    return {
        "final_report": report
    }


graph = StateGraph(AgentState)

graph.add_node("scanner", project_scanner_node)
graph.add_node("planner", planner_node)

graph.add_node("security", security_node)
graph.add_node("logic", logic_node)
graph.add_node("code_quality", code_quality_node)

graph.add_node("report", report_node)

graph.add_edge(START, "scanner")
graph.add_edge("scanner", "planner")

graph.add_edge("planner", "security")
graph.add_edge("planner", "logic")
graph.add_edge("planner", "code_quality")

# Depending on LangGraph version this may need adjustment
graph.add_edge(["security", "logic", "code_quality"], "report")

graph.add_edge("report", END)

app = graph.compile()

for event in app.stream(
    {
        "user_query": "Find bugs in this project",
        "project_path": "/Users/yash/Desktop/NERVE"
    }
):
    node_name = list(event.keys())[0]
    node_output = event[node_name]

    print("\n" + "=" * 60)
    print(f"NODE: {node_name.upper()}")
    print("=" * 60)

    for key, value in node_output.items():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "text" in item:
                    print(item["text"])
                else:
                    print(item)
        else:
            print(value)

    print()