from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class Message(BaseModel):
    message_id: str = Field(
        ...,
        description="대화 메시지 ID",
        examples=["message_12345"]
    )
    role: Literal['나', '파트너'] = Field(
        ...,
        description="대화 참여자 역할",
        examples=["나", "파트너"]
    )
    content: str = Field(
        ...,
        description="대화 내용",
        examples=[
            "안녕하세요. 저는 오원준이라고 해요.",
            "안녕하세요. 강유민입니다."
        ]
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="메시지 전송 시간"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_prompt(self) -> str:
        return f"{self.role}: {self.content}"

    def dict(self, *args, **kwargs):
        data = super().dict(*args, **kwargs)
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data