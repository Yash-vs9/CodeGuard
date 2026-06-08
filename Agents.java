from langchain.tools import tool
from pydantic import BaseModel, Field
from graph.graph import AgentState
class Agents(BaseModel):
    security_agent: bool
    logic_agent: bool
    code_quality_agent: bool

@tool
def select_required_agent(agents:Agents,state:AgentState)->AgentState:
    """This tool allows you to select only those agents which are needed,
        class Agents(BaseModel):
            security_agent: bool
            logic_agent: bool
            code_quality_agent: bool

        This is the class you have, If user only wants to run logic_agent then write True in that field else False
    """
    return {
        "agents_required":agents
    }
