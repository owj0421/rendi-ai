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
    logger
)
from ...utils import (
    advice_utils
)
from ...services.session_services import (
    breaktime_advice,
    breaktime_advice_recommender,
    conversation_elements,
    conversation_manager,
    conversation_memory,
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

log = logger.get_logger(__name__)

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
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager)
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
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager)
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
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    mem = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    mem.add_message(message=request.message)
    
    async def categorize_and_update():
        if mem.messages[-1].role != "파트너":
            return
        categorizer_output = await conversation_memory.PartnerMessageCategorizer.do(
            conversation_memory=mem
        )
        if categorizer_output.is_useful_to_remember:
            updater_output = await conversation_memory.PartnerMemoryUpdater.do(
                target_category=categorizer_output.target_category,
                conversation_memory=mem
            )
            mem.update_partner_memory(
                target_category=categorizer_output.target_category,
                llm_output=updater_output
            )

    async def analyze_and_update_scores():
        sentiment_analysis_output = await realtime_sentimental_analysis.RealtimeSentimentalAnalysis.do(
            conversation_memory=mem
        )
        mem.update_scores(
            message=mem.messages[-1],
            sentimental_analysis_output=sentiment_analysis_output
        )

    await asyncio.gather(
        categorize_and_update(),
        analyze_and_update_scores()
    )
    scores = mem.get_scores()
    
    return RealtimeAnalysis(**scores)


@router.post(
    "/{conversation_id}/realtime-memo",
    response_model=conversation_models.RealtimeMemo,
    summary="대화 실시간 메모 조회",
    status_code=status_codes.HTTP_200_OK,
)
async def get_realtime_memo(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    mem = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    
    return conversation_models.RealtimeMemo(memo=mem.partner_memory)
    


@router.get(
    "/{conversation_id}/realtime-analysis",
    response_model=RealtimeAnalysis,
    summary="대화 실시간 정보 조회"
)
async def get_realtime_analysis(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    analysis = history_utils.get_realtime_analysis(conversation_id=conversation_id)
    return analysis


@router.post(
    "/{conversation_id}/breaktime-advice/recommendation",
    response_model=BreaktimeAdviceRecommendation,
    summary="대화 내용을 기반으로 적합한 조언을 추천합니다.",
    status_code=status_codes.HTTP_200_OK,
)
async def recommend_breaktime_advice(
    conversation_id: str,
    conversation_manager: conversation_manager.ConversationManager=Depends(conversation_manager.get_conversation_manager),

):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    mem = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    recommendation = await breaktime_advice_recommender.BreaktimeAdviceRecommender.do(
        
        conversation_memory=mem
    )
    return recommendation


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

    advice_metadata = advice_utils.ADVICE_METADATAS[advice_id]
    mem = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    
    advice = await breaktime_advice.BreaktimeAdvice.do(
        advice_metadata=advice_metadata,
        conversation_memory=mem
    )
    return BreaktimeAdvice(
        advice_id=advice_id,
        advice=advice
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

):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    # TODO: 실제 보고서 생성 로직으로 대체
    dummy_report = "이것은 임의의 최종 보고서입니다."
    return FinalReport(content=dummy_report)