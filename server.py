from fastapi import FastAPI
app= FastAPI()
from graph.graph import app_graph
from pydantic import BaseModel
class AnalyzeRequest(BaseModel):
    user_query:str
    project_path:str

@app.post("/analyze")
def analyze(request: AnalyzeRequest):

    result = app_graph.invoke(
        {
            "user_query": request.user_query,
            "project_path": request.project_path,
        }
    )

    return {
        "report": result["final_report"]
    }