from langgraph.graph import StateGraph, START, END
from typing import TypedDict,List,Literal
from agents.code_planner import planner_agent
from agents.coder import coding_agent
from agents.reviewer_agent import review_agent
import os
from models.review import Review
from langchain_groq import ChatGroq
from models.task_list import TaskList


def _extract_content(message_content) -> str:
    """Safely extract a plain string from a message's content field.
    Handles both plain strings and list-of-block formats (Gemini/Anthropic)."""
    if isinstance(message_content, str):
        return message_content
    if isinstance(message_content, list):
        parts = []
        for item in message_content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(message_content)


class AgentState(TypedDict):
    user_query: str
    plan: str
    memory: str
    working_dir: str
    tasks: List[str]
    current_task:int
    feedback_on_current_task_ifany:str



def plan(state:AgentState)->AgentState:
    response=planner_agent.invoke(
        {
            "messages":[
                {
                "role":"user",
                "content":f"This is user query : {state['user_query']}"
                }

            ]
        }
    )
    llm= ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.2,
    
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
)
    get_tasks=llm.with_structured_output(TaskList)
    plan_text = _extract_content(response["messages"][-1].content)
    result=get_tasks.invoke(f"""Read this plan and give all the tasks in the order in which they need to be executed first
                     to build a project, Like you can's do the task implement JWT without initialising backend
                     This is the plan {plan_text} """)
    return {
            "tasks": result.tasks,
        "plan": plan_text,
        "current_task":0
    }

def coding(state:AgentState)->AgentState:
    tasks=state['tasks']
    task=tasks[state['current_task']]

    # Ensure all tools resolve paths relative to the user's project directory
    os.environ["AGENT_WORKING_DIR"] = state["working_dir"]

    response= coding_agent.invoke({
        "messages":[
            {
                "role":"user",
                "content":f"""This is the plan {state['plan']}
                This is the first task you need to perform {task}
                This is the working directory: {state['working_dir']}
                This is the review if any : {state['feedback_on_current_task_ifany']}
                return what files you have created or added
"""
            }
        ]
    
    })
    review_result = review_agent.invoke({
    "messages": [
        {
            "role": "user",
            "content": f"""
This is the plan:
{state['plan']}

Task:
{task}

Working directory:
{state['working_dir']}

Coder response:
{_extract_content(response["messages"][-1].content)}
"""
        }
    ]
})
    llm= ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.2,
    
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
)
    review_result_structured=llm.with_structured_output(Review)
    review=review_result_structured.invoke(f"""
    This is the message , Return if the code is passed or not and the feedback
                                           {_extract_content(review_result["messages"][-1].content)}
""")
    if(review.passed==False):
        return { 
                "feedback_on_current_task_ifany": review.feedback

        }
    return {
        "current_task":state['current_task']+1
    }
    
    

from langgraph.graph import StateGraph, START, END

# -----------------------------------
# Conditional Edge
# -----------------------------------

def should_continue(state: AgentState):
    # All tasks completed
    if state["current_task"] >= len(state["tasks"]):
        return END

    # Still have tasks remaining
    return "coding"


# -----------------------------------
# Build Graph
# -----------------------------------

builder = StateGraph(AgentState)

builder.add_node("planner", plan)
builder.add_node("coding", coding)

builder.add_edge(START, "planner")
builder.add_edge("planner", "coding")

builder.add_conditional_edges(
    "coding",
    should_continue,
)

graph = builder.compile()


# -----------------------------------
# Test
# -----------------------------------
if __name__ == "__main__":
    os.environ["AGENT_WORKING_DIR"] = "/Users/yash/Desktop/test_project"

    for event in graph.stream(
        {
            "user_query": "My tic tac toe app is not working, i cant click buttons and the grid is vertical not matrix like, fix the code",
            "plan": "",
            "memory": "",
            "working_dir": "/Users/yash/Desktop/test_project",
            "tasks": [],
            "current_task": 0,
            "feedback_on_current_task_ifany": "",
        },
        stream_mode="updates",
    ):
        print(event)

