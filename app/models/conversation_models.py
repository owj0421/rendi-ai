from pydantic import BaseModel, Field
from typing import List, Union
from datetime import datetime

from ..core.conversation_elements import Message

# --- Request Models ---

class UpdateConversationInput(BaseModel):
    message: Message = Field(
        ..., 
        description="대화 기록에 추가할 메세지",
        examples=[
            Message(
                message_id="41", 
                role="파트너", 
                content="오, 그럼 저랑 잘 맞는 조합인가요?"
            )
        ]
    )
    
    
# --- Response Models ---


class InitConversationOutput(BaseModel):
    conversation_id: str
    created_at: datetime

class DeleteConversationOutput(BaseModel):
    conversation_id: str
    deleted_at: datetime


class RealtimeAnalysis(BaseModel):
    partner_engagement_score: float = Field(
        ..., 
        description="파트너의 대화 참여도 점수", 
        examples=[0.85]
    )
    my_engagement_score: float = Field(
        ..., 
        description="나의 대화 참여도 점수", 
        examples=[0.75]
    )
    my_talk_share: float = Field(
        ..., 
        description="나의 대화 점유율", 
        examples=[0.65]
    )

class BreaktimeAdviceStringTypeContent(BaseModel):
    content: str = Field(
        ..., 
        description="카드 내용"
    )

class BreaktimeAdviceListTypeContentItem(BaseModel):
    summary: str = Field(
        ..., 
        description="핵심 문장 또는 요약"
    )
    detail: str = Field(
        ..., 
        description="자세한 설명 또는 부연 설명"
    )

class BreaktimeAdviceListTypeContent(BaseModel):
    content: List[BreaktimeAdviceListTypeContentItem] = Field(
        ..., 
        description="핵심 문장과 자세한 설명이 포함된 카드 내용 리스트"
    )

class BreaktimeAdvice(BaseModel):
    advice_id: str = Field(
        ..., 
        description="카드 ID", 
        examples=["1"]
    )
    advice: Union[BreaktimeAdviceStringTypeContent, BreaktimeAdviceListTypeContent] = Field(
        ..., 
        description="카드 내용",
        examples=[
            BreaktimeAdviceStringTypeContent(
                content="파트너의 대화 참여도 점수는 0.85입니다."
            )
        ]
    )


class BreaktimeAdviceMetadata(BaseModel):
    advice_id: str = Field(
        ..., 
        description="카드 ID", 
        examples=["1"]
    )
    emoji: str = Field(
        ..., 
        description="이모지", 
        examples=["😊"]
    )
    title: str = Field(
        ..., 
        description="카드 제목", 
        examples=["대화 참여도 점수"]
    )
    description: str = Field(
        ..., 
        description="카드 설명", 
        examples=["대화 참여도 점수는 0.85입니다."]
    )


class BreaktimeAdviceRecommendation(BaseModel):
    recommendation: List[BreaktimeAdviceMetadata] = Field(
        ..., 
        description="추천 카드",
        examples=[
            [
                BreaktimeAdviceMetadata(
                    advice_id="1",
                    emoji="😊",
                    title="대화 참여도 점수",
                    description="대화 참여도 점수는 0.85입니다."
                ),
                BreaktimeAdviceMetadata(
                    advice_id="2",
                    emoji="😄",
                    title="대화 참여도 점수",
                    description="대화 참여도 점수는 0.75입니다."
                )
            ]
        ]
    )
    
    
class FinalReport(BaseModel):
    content: str = Field(
        ..., 
        description="최종 보고서 내용",
        examples=[
            "보고서 내용입니다."
        ]
    )