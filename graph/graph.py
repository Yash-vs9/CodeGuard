from agents.planner_agent import planner_agent
from agents.code_quality_agent import code_quality_agent
from agents.logic_agent import logic_agent
from agents.project_scanner_agent import project_scanner_agent
from agents.security_agent import security_agent
from agents.chat_agent import chat_agent
from langgraph.graph import StateGraph, START, END
from typing import TypedDict,List
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI

class Agents(BaseModel):
    security_agent: bool
    logic_agent: bool
    code_quality_agent: bool


class AgentState(TypedDict):
    user_query: str
    project_path: str
    agents_required: Agents

    project_map: str
    plan: str

    security_report: str
    logic_report: str
    quality_report: str

    final_report: str

def chat(state: AgentState) -> AgentState:
    response = chat_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"Summarize the following user request/conversation into a concise, actionable goal for a code scanning and quality analysis tool:\n\n{state['user_query']}"
                }
            ]
        }
    )
    return {
        "user_query": get_last_message(response)
    }

def get_last_message(result):
    content = result["messages"][-1].content
    if isinstance(content, list):
        # Extract text from list of content blocks (e.g. Gemini/Anthropic format)
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return content


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
    
    plan_text = get_last_message(result)
    
    # Use structured output to decide which agents to run
    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")
    structured_llm = llm.with_structured_output(Agents)
    agents_required = structured_llm.invoke(f"Based on this plan, which agents should be executed? Return true for the needed agents.\n\nPlan:\n{plan_text}")

    return {
        "plan": plan_text,
        "agents_required": agents_required
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
graph.add_node("chat", chat)

graph.add_node("planner", planner_node)

graph.add_node("security", security_node)
graph.add_node("logic", logic_node)
graph.add_node("code_quality", code_quality_node)

graph.add_node("report", report_node)

graph.add_edge(START, "chat")
graph.add_edge("chat", "scanner")

graph.add_edge("scanner", "planner")

def route_to_agents(state: AgentState):
    destinations = []
    if "agents_required" in state:
        reqs = state["agents_required"]
        if getattr(reqs, "security_agent", False):
            destinations.append("security")
        if getattr(reqs, "logic_agent", False):
            destinations.append("logic")
        if getattr(reqs, "code_quality_agent", False):
            destinations.append("code_quality")
            
    if not destinations:
        return ["report"]
    return destinations

graph.add_conditional_edges(
    "planner", 
    route_to_agents, 
    ["security", "logic", "code_quality", "report"]
)


graph.add_edge(["security", "logic", "code_quality"], "report")

graph.add_edge("report", END)

app_graph = graph.compile()

# for event in app.stream(
#     {
#         "user_query": "Find bugs in this project",
#         "project_path": "/Users/yash/Desktop/NERVE"
#     }
# ):
#     node_name = list(event.keys())[0]
#     node_output = event[node_name]

#     print("\n" + "=" * 60)
#     print(f"NODE: {node_name.upper()}")
#     print("=" * 60)

#     for key, value in node_output.items():
#         if isinstance(value, list):
#             for item in value:
#                 if isinstance(item, dict) and "text" in item:
#                     print(item["text"])
#                 else:
#                     print(item)
#         else:
#             print(value)

#     print()