from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field


class MyInfo(BaseModel):
    name: str = Field(..., description="나(조언 요청자)의 이름")
    age: int = Field(..., description="Age of the advisee")
    interests: List[str] = Field(..., description="Interests of the advisee")
    
    def to_prompt(self) -> str:
        return (
            f"- 나이: {self.age}\n",
            f"- 관심사: {', '.join(self.interests)}"
        )
    

class Message(BaseModel):
    message_id: str = Field(
        ..., description="대화 메시지 ID",
        examples=[
            "message_12345"
        ]
    )
    role: Literal['나', '파트너'] = Field(
        ..., description="대화 참여자 역할",
        examples=[
            "나",
            "파트너"
        ]
    )
    content: str = Field(
        ..., description="대화 내용",
        examples=[
            "안녕하세요. 저는 오원준이라고 해요.",
            "안녕하세요. 강유민입니다."
        ]
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_prompt(self) -> str:
        return (
            f"({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}) {self.role}: {self.content}\n"
        )