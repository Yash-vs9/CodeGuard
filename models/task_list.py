from pydantic import BaseModel

class TaskList(BaseModel):
    tasks: list[str]