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
from fastapi import Depends


from ...core import (
    config,
    conversation_manager,
    logger
)
from ...utils import (
    history_utils,
    advice_utils
)
from ...services.session_services import (
    breaktime_advice,
    breaktime_advice_recommender,
    realtime_sentimental_analysis
)

from ...models.conversation_models import (
    UpdateConversationInput,
    InitConversationOutput,
    DeleteConversationOutput,
    RealtimeAnalysis,
    BreaktimeAdvice,
    BreaktimeAdviceStringTypeContent,
    BreaktimeAdviceListTypeContentItem,
    BreaktimeAdviceRecommendation,
    FinalReport
)



router = APIRouter(
    prefix="/conversation",
    tags=["conversation"]
)

@router.post(
    "/{conversation_id}",
    summary="대화 세션 초기화 및 생성",
    response_model=InitConversationOutput,
    status_code=status_codes.HTTP_201_CREATED,
)
async def init_conversation(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    try:
        conversation_manager.init_conversation(conversation_id=conversation_id)
        log.info(f"Conversation initialized: {conversation_id}")
        return InitConversationOutput(
            conversation_id=conversation_id,
            created_at=datetime.utcnow()
        )
        
    except Exception as exc:
        log.error(f"Failed to initialize conversation {conversation_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize conversation session."
        )


@router.delete(
    "/{conversation_id}",
    summary="대화 세션 삭제",
    response_model=DeleteConversationOutput,
    status_code=status_codes.HTTP_200_OK,
)
async def delete_conversation(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    try:
        conversation_manager.delete_conversation(conversation_id=conversation_id)
        log.info(f"Conversation deleted: {conversation_id}")
        return DeleteConversationOutput(
            conversation_id=conversation_id,
            deleted_at=datetime.utcnow()
        )
        
    except Exception as exc:
        log.error(f"Failed to delete conversation {conversation_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete conversation session."
        )

@router.post(
    "/{conversation_id}/messages",
    response_model=RealtimeAnalysis,
    summary="대화 메시지 추가",
)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationInput,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    try:
        conversation_memory = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
        await conversation_memory.add_message(message=request.message)
        sentiment_analysis = await realtime_sentimental_analysis.RealtimeSentimentalAnalysis.do(
            messages=conversation_memory.get_messages(n_messages=15)
        )
        history_utils.update_realtime_analysis(
            conversation_id=conversation_id,
            message=request.message,
            sentiment_analysis=sentiment_analysis
        )
        analysis = history_utils.get_realtime_analysis(conversation_id=conversation_id)
        return analysis
    
    except Exception as exc:
        log.error(f"Failed to update conversation {conversation_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update conversation."
        )


@router.get(
    "/{conversation_id}/realtime-analysis",
    response_model=RealtimeAnalysis,
    summary="대화 실시간 정보 조회"
)
async def get_realtime_analysis(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    try:
        analysis = history_utils.get_realtime_analysis(conversation_id=conversation_id)
        return analysis
    
    except Exception as exc:
        log.error(f"[RealtimeAnalysis] Failed for conversation_id={conversation_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve realtime analysis."
        )


@router.post(
    "/{conversation_id}/breaktime-advice/recommendation",
    response_model=BreaktimeAdviceRecommendation,
    summary="대화 내용을 기반으로 적합한 조언을 추천합니다.",
    status_code=status_codes.HTTP_200_OK,
)
async def recommend_breaktime_advice(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    try:
        conversation_memory = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
        recommendation = await breaktime_advice_recommender.BreaktimeAdviceRecommender.do(
            partner_memory=conversation_memory.partner_memory,
            messages=conversation_memory.get_messages(n_messages=15),
        )
        return recommendation
    
    except Exception as exc:
        log.error(f"Failed to recommend breaktime advice for conversation {conversation_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to recommend breaktime advice."
        )


@router.post(
    "/{conversation_id}/breaktime-advice/{advice_id}",
    response_model=BreaktimeAdvice,
    summary="조언 제공",
    description="advice_id에 해당하는 조언을 대화 내용 기반으로 제공합니다.",
    status_code=status_codes.HTTP_200_OK,
)
async def get_breaktime_advice(
    conversation_id: str,
    advice_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    if not advice_utils.is_advice_exists(advice_id=advice_id):
        log.warning(f"Advice not found: {advice_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Advice ID not found."
        )

    try:
        conversation_memory = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
        advice_metadata = advice_utils.ADVICE_METADATAS.get(advice_id)
        advice = await breaktime_advice.BreaktimeAdvice.do(
            advice_metadata=advice_metadata,
            partner_memory=conversation_memory.partner_memory,
            messages=conversation_memory.get_messages(n_messages=15)
        )
        return BreaktimeAdvice(
            advice_id=advice_id,
            advice=advice
        )
        
    except Exception as exc:
        log.error(f"Failed to get breaktime advice for conversation {conversation_id}, advice {advice_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get breaktime advice."
        )


@router.post(
    "/{conversation_id}/final-report",
    response_model=FinalReport,
    summary="대화 종료 후 최종 보고서 반환",
    status_code=status_codes.HTTP_200_OK,
)
async def get_final_report(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),
    log=Depends(logger.get_logger),
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    try:
        # TODO: 실제 보고서 생성 로직으로 대체
        dummy_report = "이것은 임의의 최종 보고서입니다."
        return FinalReport(content=dummy_report)
    
    except Exception as exc:
        log.error(f"Failed to generate final report for conversation {conversation_id}: {exc}")
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate final report."
        )