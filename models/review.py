from typing import TypedDict,List,Literal
from pydantic import BaseModel


class Review(BaseModel):
    passed: bool
    feedback: str