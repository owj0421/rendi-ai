from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional


class QueryClassifierOutput(BaseModel):
    final_answer: Literal["Conversation", "Web"]
    

class QueryRewriterOutput(BaseModel):
    final_answer: str