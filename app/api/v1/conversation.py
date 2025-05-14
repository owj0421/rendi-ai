import asyncio
from fastapi import APIRouter, HTTPException
from starlite import Response, status_codes
from typing import List, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from ...models import conversation_models

from ...services.session_services import (
    breaktime_advice,
    breaktime_advice_recommender,
    realtime_sentimental_analysis
)

from ...core import (
    config,
    conversation_manager,
    logger
)
from ...models import (
    conversation_models,
)
from ...utils import (
    history_utils,
    advice_utils
)


router = APIRouter(
    prefix="/conversation",
    tags=["conversation"]
)


@router.post(
    "/{conversation_id}",
    summary="대화 세션 초기화 & 대화 생성",
)
async def init_conversation(
    conversation_id: str
):
    conversation_manager.conversation_manager.init_conversation(
        conversation_id=conversation_id
    )

    return JSONResponse(
        status_code=status_codes.HTTP_201_CREATED,
        content={
            "conversation_id": conversation_id,
            "created_at": datetime.now().isoformat()
        }
    )




@router.delete(
    "/{conversation_id}",
    summary="대화 세션 삭제"
)
async def delete_conversation(
    conversation_id: str
):
    conversation_manager.conversation_manager.delete_conversation(
        conversation_id=conversation_id
    )
        
    return JSONResponse(
        status_code=status_codes.HTTP_204_NO_CONTENT,
        content={
            "conversation_id": conversation_id,
            "deleted_at": datetime.now().isoformat()
        }
    )




@router.post(
    "/{conversation_id}/messages",
    response_model=conversation_models.GetRealtimeAnalysisResponse,
    summary="대화 메시지 추가",
)
async def update_conversation(
    conversation_id: str,
    request: conversation_models.AddMessageRequest,
):
    conversation_memory = conversation_manager.conversation_manager.get_conversation_memory(
        conversation_id=conversation_id
    )
    
    await conversation_memory.add_message(
        message=request.message
    )

    sentiment_analysis = await realtime_sentimental_analysis.RealtimeSentimentalAnalysis.do(
        messages=conversation_memory.get_messages(n_messages=15)
    )
    
    history_utils.update_realtime_analysis(
        conversation_id=conversation_id,
        message=request.message,
        sentiment_analysis=sentiment_analysis
    )
        
    return history_utils.get_realtime_analysis(
        conversation_id=conversation_id
    )



@router.post(
    "/{conversation_id}/realtime-analysis",
    response_model=conversation_models.GetRealtimeAnalysisResponse,
    summary="대화 실시간 정보를 Get"
)
async def get_realtime_analysis(
    conversation_id: str
):
    conversation_memory = conversation_manager.conversation_manager.get_conversation_memory(
        conversation_id=conversation_id
    )
    
    return history_utils.get_realtime_analysis(
        conversation_id=conversation_id
    )
    



@router.post(
    "/{conversation_id}/breaktime-advice/recommendation",
    response_model=conversation_models.BreaktimeAdviceRecommendationResponse,
    summary="대화 내용을 기반으로 적합한 조언을 추천합니다.",
)
async def recommend_breaktime_advice(
    conversation_id: str
):
    conversation_memory = conversation_manager.conversation_manager.get_conversation_memory(
        conversation_id=conversation_id
    )
    
    output = await breaktime_advice_recommender.BreaktimeAdviceRecommender.do(
        partner_memory=conversation_memory.partner_memory,
        messages=conversation_memory.get_messages(n_messages=15),
    )

    return output




@router.post(
    "/{conversation_id}/breaktime-advice/{advice_id}",
    summary="",
    description="""
"""
)
async def get_breaktime_advice(
    advice_id: str,
    conversation_id: str
):
    conversation_memory = conversation_manager.conversation_manager.get_conversation_memory(
        conversation_id=conversation_id
    )
    
    if not advice_utils.is_advice_exists(advice_id=advice_id):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Analysis ID not found."
        )

    content = await breaktime_advice.BreaktimeAdvice.do(
        advice_metadata=advice_utils.ADVICE_METADATAS.get(advice_id),
        partner_memory=conversation_memory.partner_memory,
        messages=conversation_memory.get_messages(n_messages=15)
    )
    
    return conversation_models.GetBreaktimeAdviceResponse(
        advice_id=advice_id,
        content=content
    )
    
class GetFinalReportResponse(BaseModel):
    report: str = Field(..., description="최종 보고서 내용")


@router.post(
    "/{conversation_id}/final-report",
    response_model=GetFinalReportResponse,
    summary="대화 종료 후 최종 보고서 반환"
)
async def get_final_report(
    conversation_id: str
):
    # TODO: 실제 보고서 생성 로직으로 대체
    dummy_report = "이것은 임의의 최종 보고서입니다."
    return GetFinalReportResponse(
        report=dummy_report
    )