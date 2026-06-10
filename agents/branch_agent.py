from langchain_groq import ChatGroq
from models.branch import Branch
from langchain_core.messages import SystemMessage, HumanMessage

llm= ChatGroq(
    model="qwen/qwen3-32b",
    temperature=0.2,
    
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
)
SYSTEM_PROMPT= """
You are a intelligent agent,
Tell what the user is saying, if user wants to create a project/feature then return "builder" ,
if user wants to analyse a pre built project then return "analyzer"
only return one of these ["analyzer","builder"]
"""
query=input("enter...")
chat=llm.with_structured_output(Branch)
response=chat.invoke(
    [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=query)
    ]
)
print(response)


