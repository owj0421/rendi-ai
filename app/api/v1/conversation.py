import asyncio
from fastapi import APIRouter, HTTPException
from starlite import Response, status_codes
from typing import List, Dict
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from ...services.session_services import (
    breaktime_advice,
    breaktime_advice_recommender,
    realtime_sentimental_analysis,
    context_aware_search
)

from ...core import (
    conversation_elements,
    config,
    logger
)
from ...models.conversation import (
    analysis_io,
    advice_io
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
    "",
    summary="",
    description="""
"""
)
async def init_conversation(
    conversation_id: str = "test_conversation_id",
):
    if history_utils.is_conversation_exists(
        conversation_id=conversation_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_409_CONFLICT,
            detail="Conversation already exists."
        )
    
    # 대화 내역 초기화
    history_utils.init_conversation(
        conversation_id=conversation_id
    )
    
    return Response(status_code=status_codes.HTTP_201_CREATED)


@router.delete(
    "",
    summary="",
    description="""
"""
)
async def delete_conversation(
    conversation_id: str = "test_conversation_id",
):
    if not history_utils.is_conversation_exists(
        conversation_id=conversation_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    # 대화 내역 삭제
    history_utils.delete_conversation(
        conversation_id=conversation_id
    )
    
    return Response(status_code=status_codes.HTTP_204_NO_CONTENT)


@router.post(
    "/realtime-analysis",
    response_model=analysis_io.RealtimeAnalysisResponse,
    summary="",
    description="""
"""
)
async def get_realtime_analysis(
    conversation_id: str = "test_conversation_id",
):
    if not history_utils.is_conversation_exists(
        conversation_id=conversation_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    # 분석 결과
    analysis_result = history_utils.get_realtime_analysis(
        conversation_id=conversation_id
    )
    
    return analysis_result


@router.put(
    "/realtime-analysis",
    response_model=analysis_io.RealtimeAnalysisResponse,
    summary="",
    description="""
"""
)
async def update_realtime_analysis(
    analysis_input: analysis_io.RealtimeAnalysisRequest,
):
    if not history_utils.is_conversation_exists(
        conversation_id=analysis_input.conversation_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    if history_utils.is_message_exists(
        conversation_id=analysis_input.conversation_id,
        message=analysis_input.message
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_304_NOT_MODIFIED,
            detail="Duplicate message detected."
        )
        
    # 메세지를 대화 내역에 추가
    history_utils.update_message(
        conversation_id=analysis_input.conversation_id,
        message=analysis_input.message
    )
    
    messages = history_utils.get_messages(
        conversation_id=analysis_input.conversation_id,
        n_window=15 # TODO: 파라미터 조정 필요
    )

    # 대화 내역을 기반으로 감정 분석 수행
    result = await realtime_sentimental_analysis.RealtimeSentimentalAnalysis.do(
        messages=messages
    )
    
    if config.settings.DEBUG:
        logger.logger.info(f"Quick analysis result: {result}")
        
    if not isinstance(result, realtime_sentimental_analysis.RealtimeSentimentalAnalysisLLMOutput):
        raise HTTPException(
            status_code=status_codes.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid response from analysis service."
        )
    
    # 감정 분석 결과를 대화 내역에 업데이트
    history_utils.update_realtime_analysis(
        conversation_id=analysis_input.conversation_id,
        message=analysis_input.message,
        sentiment_analysis=result
    )
    
    # 분석 결과
    output = history_utils.get_realtime_analysis(
        conversation_id=analysis_input.conversation_id
    )
    
    return output


@router.post(
    "/breaktime-advice/recommendation",
    response_model=advice_io.BreaktimeAdviceRecommendationResponse,
    summary="",
    description="""
"""
)
async def recommend_breaktime_advice(
    conversation_id: str = "test_conversation_id",
):
    if not history_utils.is_conversation_exists(
        conversation_id=conversation_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    # 대화 내역 가져오기
    messages = history_utils.get_messages(
        conversation_id=conversation_id,
        n_window=None # 전체 다 가져옴
    )
    
    # 대화 내역을 기반으로 카드 추천
    results = await breaktime_advice_recommender.BreaktimeAdviceRecommender.do(
        messages=messages
    )
    
    output = advice_io.BreaktimeAdviceRecommendationResponse(
        recommendation=[]
    )
    for id in results.final_answer:
        if id not in advice_utils.ADVICE_METADATAS:
            continue
        preview_element = advice_io.BreaktimeAdviceMetadata(
            advice_id=id,
            emoji=advice_utils.ADVICE_METADATAS[id]["emoji"],
            title=advice_utils.ADVICE_METADATAS[id]["title"],
            description=advice_utils.ADVICE_METADATAS[id]["description"],
        )
        output.recommendation.append(preview_element)
    
    if config.settings.DEBUG:
        logger.logger.info(f"Detailed analysis result: {output}")
    
    return output


@router.post(
    "/breaktime-advice/{advice_id}",
    summary="",
    description="""
"""
)
async def get_breaktime_advice(
    advice_id: str = 'advice_1',
    conversation_id: str = "test_conversation_id",
):
    if not history_utils.is_conversation_exists(
        conversation_id=conversation_id
    ):
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Conversation not found."
        )
    
    # 대화 내역 가져오기
    messages = history_utils.get_messages(
        conversation_id=conversation_id,
        n_window=None # 전체 다 가져옴
    )
    
    advice_dict = advice_utils.ADVICE_METADATAS.get(advice_id)
    if not advice_dict:
        raise HTTPException(
            status_code=status_codes.HTTP_404_NOT_FOUND,
            detail="Analysis ID not found."
        )
    
    advice_task = breaktime_advice.BreaktimeAdvice(
        **advice_dict
    )

    content = await advice_task.do(
        messages=messages
    )
    
    if config.settings.DEBUG:
        logger.logger.info(f"Detailed analysis result: {content}")
    
    return advice_io.BreaktimeAdviceResponse(
        advice_id=advice_id,
        content=content,
        **advice_dict
    )