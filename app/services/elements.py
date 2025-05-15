from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

# === Message ===

class Message(BaseModel):
    """
    대화 메시지를 표현하는 모델 클래스.
    메시지 ID, 역할, 내용, 전송 시간을 포함합니다.
    """

    message_id: str = Field(
        ...,
        description="대화 메시지 ID",
        examples=["message_12345"]
    )
    role: Literal['나', '파트너'] = Field(
        ...,
        description="대화 참여자 역할",
        examples=["나"]
    )
    content: str = Field(
        ...,
        description="대화 내용",
        examples=["안녕하세요. 저는 오원준이라고 해요."]
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="메시지 전송 시간"
    )

    class Config:
        """
        Pydantic 모델 설정 클래스.
        JSON 직렬화를 위한 커스텀 인코더를 정의합니다.
        """
        json_encoders = {
            datetime: lambda v: v.isoformat()  # datetime 객체를 ISO 8601 형식으로 변환
        }

    def to_prompt(self) -> str:
        """
        메시지를 프롬프트 형식의 문자열로 변환합니다.
        """
        return f"{self.role}: {self.content}"

    def dict(self, *args, **kwargs) -> dict:
        """
        메시지 객체를 딕셔너리로 변환합니다.
        timestamp 필드는 ISO 8601 형식의 문자열로 변환됩니다.
        """
        data = super().dict(*args, **kwargs)
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        return data