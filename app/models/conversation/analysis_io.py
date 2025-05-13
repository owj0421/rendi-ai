from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal
from datetime import datetime

from ...core.conversation_elements import (
    Message,
)


class RealtimeAnalysisRequest(BaseModel):
    conversation_id: str = Field(
        ..., 
        description="대화 ID",
        examples=[
            "test_conversation_id"
        ]
    )
    message: Message = Field(
        default_factory=list, 
        description="소개팅 중 주고받은 대화 내용",
        examples=[
            Message(message_id="41", role="파트너", content="오, 그럼 저랑 잘 맞는 조합인가요?", timestamp=datetime.now()),
        ]
    )
    
    
class RealtimeAnalysisResponse(BaseModel):
    partner_engagement_score: float = Field(
        ..., 
        description="파트너의 대화 참여도 점수",
        examples=[
            0.85,
        ]
    )
    my_engagement_score: float = Field(
        ..., 
        description="나의 대화 참여도 점수",
        examples=[
            0.75,
        ]
    )
    my_talk_share: float = Field(
        ..., 
        description="나의 대화 점유율",
        examples=[
            0.65,
        ]
    )