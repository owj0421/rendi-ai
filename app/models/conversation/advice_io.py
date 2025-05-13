from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal
from datetime import datetime

from ...core.conversation_elements import (
    Message,
)
    

class BreaktimeAdviceRequest(BaseModel):
    conversation_id: str = Field(
        ..., 
        description="대화 ID",
        examples=[
            "test_conversation_id"
        ]
    )
    
    
class StringTypeBreaktimeAdviceContent(BaseModel):
    advice: str = Field(
        ..., description="카드 내용"
    )


class ListTypeBreaktimeAdviceContentElement(BaseModel):
    value: str = Field(
        ..., description="카드 내용",
    )
    detail: str = Field(
        ..., description="카드 내용 상세",
    )


class ListTypeBreaktimeAdviceContent(BaseModel):
    advice: list[ListTypeBreaktimeAdviceContentElement] = Field(
        ..., description="카드 내용"
    )
    
    
class BreaktimeAdviceResponse(BaseModel):
    advice_id: str = Field(
        ..., description="카드 ID",
        examples=[
            "1",
        ]
    )
    content_type: Literal["string", "list"] = Field(
        ..., description="카드 내용 타입",
        examples=[
            "string",
        ]
    )
    content: StringTypeBreaktimeAdviceContent | ListTypeBreaktimeAdviceContent = Field(
        ..., description="카드 내용",
        examples=[
            StringTypeBreaktimeAdviceContent(
                advice="파트너의 대화 참여도 점수는 0.85입니다."
            )
        ]
    )
    
    
class BreaktimeAdviceRecommendationRequest(BaseModel):
    conversation_id: str = Field(
        ..., 
        description="대화 ID",
        examples=[
            "test_conversation_id"
        ]
    )


class BreaktimeAdviceMetadata(BaseModel):
    advice_id: str = Field(
        ..., description="카드 ID",
        examples=[
            "1",
        ]
    )
    emoji: str = Field(
        ..., description="이모지",
        examples=[
            "😊",
        ]
    )
    title: str = Field(
        ..., description="카드 제목",
        examples=[
            "대화 참여도 점수",
        ]
    )
    description: str = Field(
        ..., description="카드 설명",
        examples=[
            "대화 참여도 점수는 0.85입니다.",
        ]
    )


class BreaktimeAdviceRecommendationResponse(BaseModel):
    recommendation: list[BreaktimeAdviceMetadata] = Field(
        ..., description="추천 카드",
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