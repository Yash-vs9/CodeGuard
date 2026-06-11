from langgraph.graph import StateGraph, START, END
from typing import TypedDict,List,Literal
from agents.code_planner import planner_agent
from agents.coder import coding_agent
from agents.reviewer_agent import review_agent
import os
from models.review import Review
from langchain_groq import ChatGroq
from models.task_list import TaskList
llm= ChatGroq(
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
    
    get_tasks=llm.with_structured_output(TaskList)
    result=get_tasks.invoke(f"""Read this plan and give all the tasks in the order in which they need to be executed first
                     to build a project, Like you can's do the task implement JWT without initialising backend
                     This is the plan {response} """)
    plan_text = response["messages"][-1].content
    if isinstance(plan_text, list):
        plan_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in plan_text)
    return {
            "tasks": result.tasks,
        "plan":plan_text,
        "current_task":0
    }

def coding(state:AgentState)->AgentState:
    tasks=state['tasks']
    task=tasks[state['current_task']]
    new_memory=state['memory']
    if(len(state["memory"])>10):
        memory=state['memory']
        summarised_memory=llm.invoke(
            f"Here is the text, your task is to summarise it in less tokens and keep important points {memory[:-2]}"
        )
        new_memory=[summarised_memory.content]+memory[-2:]



    print(new_memory)
    response= coding_agent.invoke({
        "messages":[
            {
                "role":"user",
                "content":f"""This is the plan {state['plan']}
                This is the first task you need to perform {task}
                This is the working directory: {state['working_dir']}
                This is the review if any : {state['feedback_on_current_task_ifany']}
                Memory: {chr(10).join(new_memory)}
                return what files you have created or added
"""
            }
        ]
    
    })
    coder_text = response["messages"][-1].content
    if isinstance(coder_text, list):
        coder_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in coder_text)
        
    new_memory = new_memory + [coder_text]
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
{coder_text}
"""
        }
    ]
})
    
    review_text = review_result["messages"][-1].content
    if isinstance(review_text, list):
        review_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in review_text)
        
    review_result_structured=llm.with_structured_output(Review)
    review=review_result_structured.invoke(f"""
    This is the message , Return if the code is passed or not and the feedback
                                           {review_text}
""")
    if(review.passed==False):
        return { 
                "feedback_on_current_task_ifany": review.feedback

        }
    return {
        "memory":new_memory,
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
            "memory": [],
            "working_dir": "/Users/yash/Desktop/test_project",
            "tasks": [],
            "current_task": 0,
            "feedback_on_current_task_ifany": "",
        },
        stream_mode="updates",
    ):
        print(event)
        

