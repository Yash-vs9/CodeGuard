import os
from typing import TypedDict, List, Literal
from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from agents.code_planner import planner_agent
from agents.coder import coding_agent
from agents.reviewer_agent import review_agent
from models.review import Review
from models.task_list import TaskList
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from dotenv import load_dotenv
load_dotenv()
llm = ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.2,
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
)

class AgentState(TypedDict):
    user_query: str
    plan: str
    memory: List[str]
    working_dir: str
    tasks: List[str]
    current_task: int
    feedback_on_current_task_ifany: str

@traceable
def plan(state: AgentState) -> AgentState:
    print("\n" + "="*50)
    print("--- [Planner Agent] Creating Plan ---")
    print("="*50)
    
    response = planner_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""You are an expert technical planner.
Analyze the user query and create a comprehensive, step-by-step implementation plan.
Focus on architecture, file structure, and technical requirements.

User Query: {state['user_query']}"""
                }
            ]
        }
    )
    
    plan_text = response["messages"][-1].content
    if isinstance(plan_text, list):
        plan_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in plan_text)
        
    get_tasks = llm.with_structured_output(TaskList)
    result = get_tasks.invoke(f"""Analyze the following implementation plan and extract a strictly ordered list of tasks.
Each task must be a clear, actionable step. Dependencies must be respected (e.g., initialize backend before writing API endpoints).

Implementation Plan:
{plan_text}""")
    
    return {
        "tasks": result.tasks,
        "plan": plan_text,
        "current_task": 0
    }

@traceable
def coding(state: AgentState) -> AgentState:
    tasks = state['tasks']
    task = tasks[state['current_task']]
    new_memory = state['memory']
    
    print("\n" + "="*50)
    print(f"--- [Coder Agent] Executing Task {state['current_task'] + 1}/{len(tasks)} ---")
    print("="*50)
    print(f"Task: {task}\n")
    
    if len(state["memory"]) > 10:
        memory = state['memory']
        summarised_memory = llm.invoke(
            f"Please summarize the following context of actions taken so far. Keep it concise but retain key technical details, file paths, and decisions made:\n\n{memory[:-2]}"
        )
        new_memory = [summarised_memory.content] + memory[-2:]

    feedback_text = state.get('feedback_on_current_task_ifany') or "None"
    memory_text = "\n".join(new_memory) if new_memory else "No previous actions."

    response = coding_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": f"""You are an expert software engineer.
Your task is to execute the current task based on the overall plan.
Use the tools provided to create, modify, or delete files as necessary.

### Overall Plan
{state['plan']}

### Current Task to Execute
{task}

### Working Directory
{state['working_dir']}

### Previous Feedback (if any)
{feedback_text}

### Memory / Context of previous actions
{memory_text}

Ensure you write clean, production-ready code. Once done, provide a brief summary of the exact files you created or modified.
"""
            }
        ]
    })
    
    coder_text = response["messages"][-1].content
    if isinstance(coder_text, list):
        coder_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in coder_text)
        
    print(f"\n[Coder Agent Reply]:\n{coder_text}\n")
        
    new_memory = new_memory + [coder_text]
    
    print("\n" + "-"*50)
    print("--- [Reviewer Agent] Reviewing Code ---")
    print("-"*50)
    
    review_result = review_agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": f"""You are a strict code reviewer. 
Review the coder's output against the plan and current task.

### Overall Plan
{state['plan']}

### Current Task
{task}

### Working Directory
{state['working_dir']}

### Coder's Output
{coder_text}

Did the coder successfully complete the task? Check for obvious errors, incomplete code, or missing files.
Provide constructive feedback if it failed.
"""
            }
        ]
    })
    
    review_text = review_result["messages"][-1].content
    if isinstance(review_text, list):
        review_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in review_text)
        
    review_result_structured = llm.with_structured_output(Review)
    review = review_result_structured.invoke(f"""
Analyze the following review message. Determine if the code passed the review and extract the feedback.

Review Message:
{review_text}
""")

    if not review.passed:
        print(f"\n[Review Failed]: {review.feedback}\n")
        return { 
            "feedback_on_current_task_ifany": review.feedback
        }
        
    print("\n[Review Passed]\n")
    return {
        "memory": new_memory,
        "current_task": state['current_task'] + 1,
        "feedback_on_current_task_ifany": ""
    }

@traceable
def should_continue(state: AgentState):
    if state["current_task"] >= len(state["tasks"]):
        return END
    return "coding"

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

if __name__ == "__main__":
    os.environ["AGENT_WORKING_DIR"] = "/Users/yash/Desktop/test_project"

    for event in graph.stream(
        {
            "user_query": "My tic tac toe app is not working, i cant click buttons and the grid is vertical not matrix like, fix the code",
            "plan": "",
            "memory": [],
            "working_dir": "/Users/yash/Desktop/test_project",
            "tasks": [],
            "current_task": 0,
            "feedback_on_current_task_ifany": "",
        },
        stream_mode="updates",
    ):
        pass # The agents already print their formatted outputs cleanly.

