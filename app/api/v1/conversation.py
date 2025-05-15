import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlite import Response, status_codes

from ...core import config, logger
from ...schemas.conversation import (
    InitConversationOutput,
    DeleteConversationOutput,
    UpdateConversationInput,
    UpdateConversationOutput,
    GetRealtimeMemoryOutput,
    GetRealtimeAnalysisOutput,
    GetBreaktimeAdviceOutput,
    RecommendBreaktimeAdviceOutput,
    GetFinalReportOutput,
)
from ...services import elements, manager
from ...services.session_services import (
    advice as advice_service,
    memory as memory_service,
    score as score_service,
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
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager)
):
    conversation_manager.init_conversation(conversation_id=conversation_id)
    log.info(f"Conversation initialized: {conversation_id}")
    
    return InitConversationOutput(
        conversation_id=conversation_id,
        created_at=datetime.utcnow()
    )


@router.delete(
    "/{conversation_id}",
    summary="대화 세션 삭제",
    response_model=DeleteConversationOutput,
    status_code=status_codes.HTTP_200_OK,
)
async def delete_conversation(
    conversation_id: str,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    conversation_manager.delete_conversation(conversation_id=conversation_id)
    log.info(f"Conversation deleted: {conversation_id}")
    return DeleteConversationOutput(
        conversation_id=conversation_id,
        deleted_at=datetime.utcnow()
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=UpdateConversationOutput,
    summary="대화 메시지 추가",
)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationInput,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    c_m = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    s_m = conversation_manager.get_conversation_scorer(conversation_id=conversation_id)
    c_m.add_message(message=request.message)
    await asyncio.gather(
        memory_service.update_partner_memory_pipeline(
            conversation_memory=c_m
        ),
        score_service.update_conversation_scores_pipeline(
            conversation_scorer=s_m,
            conversation_memory=c_m
        ),
    )
    
    return UpdateConversationOutput(
        scores=s_m.get_scores()
    )


@router.post(
    "/{conversation_id}/realtime-memory",
    response_model=GetRealtimeMemoryOutput,
    summary="실시간 메모리 조회",
    status_code=status_codes.HTTP_200_OK,
)
async def get_realtime_memory(
    conversation_id: str,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    c_m = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    
    return GetRealtimeMemoryOutput(
        partner_memory=c_m.partner_memory
    )
    


@router.get(
    "/{conversation_id}/realtime-analysis",
    response_model=GetRealtimeAnalysisOutput,
    summary="대화 실시간 정보 조회"
)
async def get_realtime_analysis(
    conversation_id: str,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager)
):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    s_m = conversation_manager.get_conversation_scorer(conversation_id=conversation_id)
    
    return GetRealtimeAnalysisOutput(
        scores=s_m.get_scores()
    )


@router.post(
    "/{conversation_id}/breaktime-advice/recommendation",
    response_model=RecommendBreaktimeAdviceOutput,
    summary="대화 내용을 기반으로 적합한 조언을 추천합니다.",
    status_code=status_codes.HTTP_200_OK,
)
async def recommend_breaktime_advice(
    conversation_id: str,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager),

):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    c_m = conversation_manager.get_conversation_memory(conversation_id=conversation_id)
    advice_metadatas = await advice_service.BreaktimeAdviceRecommender.do(
        conversation_memory=c_m
    )
    
    return RecommendBreaktimeAdviceOutput(
        advice_metadatas=advice_metadatas
    )


@router.post(
    "/{conversation_id}/breaktime-advice/{advice_id}",
    response_model=GetBreaktimeAdviceOutput,
    summary="조언 제공",
    description="advice_id에 해당하는 조언을 대화 내용 기반으로 제공합니다.",
    status_code=status_codes.HTTP_200_OK,
)
async def get_breaktime_advice(
    conversation_id: str,
    advice_id: str,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager),

):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
        
    c_m = conversation_manager.get_conversation_memory(conversation_id=conversation_id)

    advice = await advice_service.BreaktimeAdviceGenerator.do(
        advice_id=advice_id,
        conversation_memory=c_m
    )
    
    return GetBreaktimeAdviceOutput(
        advice_id=advice_id,
        advice=advice
    )


@router.post(
    "/{conversation_id}/final-report",
    response_model=GetFinalReportOutput,
    summary="대화 종료 후 최종 보고서 반환",
    status_code=status_codes.HTTP_200_OK,
)
async def get_final_report(
    conversation_id: str,
    conversation_manager: manager.ConversationManager=Depends(manager.get_conversation_manager),

):
    if not conversation_manager.is_conversation_exists(conversation_id=conversation_id):
        log.warning(f"Conversation not found: {conversation_id}")
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )

    # TODO: 실제 보고서 생성 로직으로 대체
    dummy_report = "이것은 임의의 최종 보고서입니다."
    
    return GetFinalReportOutput(
        final_report=dummy_report
    )