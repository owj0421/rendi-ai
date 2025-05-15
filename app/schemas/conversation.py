from pydantic import BaseModel, Field
from typing import List, Union
from datetime import datetime

from ..services.elements import Message
from ..services.session_services import (
    memory as memory_service,
    score as score_service,
    advice as advice_service
)

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
    
class UpdateConversationOutput(BaseModel):
    scores: score_service.ConversationScores
    
class GetRealtimeMemoryOutput(BaseModel):
    partner_memory: memory_service.PartnerMemory
    
class GetRealtimeAnalysisOutput(BaseModel):
    scores: score_service.ConversationScores

class GetBreaktimeAdviceOutput(BaseModel):
    advice_id: str
    advice: advice_service.Advice

class RecommendBreaktimeAdviceOutput(BaseModel):
    advice_metadatas: List[advice_service.AdviceMetadata]
    
class GetFinalReportOutput(BaseModel):
    final_report: str