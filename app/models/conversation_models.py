from pydantic import BaseModel, Field
from typing import List, Union

from ..core.conversation_elements import Message

class AddMessageRequest(BaseModel):
    message: Message = Field(
        ..., description="대화 메시지",
        examples=[
            Message(message_id="41", role="파트너", content="오, 그럼 저랑 잘 맞는 조합인가요?"
            )
        ]
    )

class GetRealtimeAnalysisRequest(BaseModel):
    conversation_id: str = Field(
        ..., 
        description="대화 ID",
        examples=["test_conversation_id"]
    )
    message: Message = Field(
        default_factory=list, 
        description="소개팅 중 주고받은 대화 내용",
        examples=[
            Message(message_id="41", role="파트너", content="오, 그럼 저랑 잘 맞는 조합인가요?")
        ]
    )
    
class GetRealtimeAnalysisResponse(BaseModel):
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

class GetBreaktimeAdviceRequest(BaseModel):
    conversation_id: str = Field(
        ...,
        description="대화 ID",
        examples=["test_conversation_id"]
    )

class StringTypeBreaktimeAdviceContent(BaseModel):
    advice: str = Field(..., description="카드 내용")

class ListTypeBreaktimeAdviceContentElement(BaseModel):
    value: str = Field(..., description="카드 내용")
    detail: str = Field(..., description="카드 내용 상세")

class ListTypeBreaktimeAdviceContent(BaseModel):
    advice: List[ListTypeBreaktimeAdviceContentElement] = Field(
        ..., description="카드 내용"
    )

class GetBreaktimeAdviceResponse(BaseModel):
    advice_id: str = Field(
        ..., description="카드 ID", examples=["1"]
    )
    content: Union[StringTypeBreaktimeAdviceContent, ListTypeBreaktimeAdviceContent] = Field(
        ..., description="카드 내용",
        examples=[
            StringTypeBreaktimeAdviceContent(
                advice="파트너의 대화 참여도 점수는 0.85입니다."
            )
        ]
    )

class GetBreaktimeAdviceRecommendationRequest(BaseModel):
    conversation_id: str = Field(
        ..., description="대화 ID", examples=["test_conversation_id"]
    )

class GetBreaktimeAdviceMetadata(BaseModel):
    advice_id: str = Field(..., description="카드 ID", examples=["1"])
    emoji: str = Field(..., description="이모지", examples=["😊"])
    title: str = Field(..., description="카드 제목", examples=["대화 참여도 점수"])
    description: str = Field(..., description="카드 설명", examples=["대화 참여도 점수는 0.85입니다."])

class BreaktimeAdviceRecommendationResponse(BaseModel):
    recommendation: List[GetBreaktimeAdviceMetadata] = Field(
        ..., description="추천 카드",
        examples=[
            [
                GetBreaktimeAdviceMetadata(
                    advice_id="1",
                    emoji="😊",
                    title="대화 참여도 점수",
                    description="대화 참여도 점수는 0.85입니다."
                ),
                GetBreaktimeAdviceMetadata(
                    advice_id="2",
                    emoji="😄",
                    title="대화 참여도 점수",
                    description="대화 참여도 점수는 0.75입니다."
                )
            ]
        ]
    )