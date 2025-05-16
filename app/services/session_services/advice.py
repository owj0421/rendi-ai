import json
import pathlib
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional, Union
from dataclasses import dataclass
from collections import Counter, defaultdict

from .. import elements
from . import memory

from ...core import (
    clients,
    config,
    logger
)
from ...utils.prompt_utils import (
    load_prompt,
)

log = logger.get_logger(__name__)

# ========== Models ==========

class AdviceMetadata(BaseModel):
    advice_id: str
    emoji: str
    title: str
    description: str
    prompt_instruction: str


class AdviceRecommendation(BaseModel):
    advice_ids: List[str]


class AdviceContentItem(BaseModel):
    title: str
    description: str
    
    
class Advice(BaseModel):
    content: Union[List[AdviceContentItem]]
    
# ========== Constants =========

N_MESSAGES = 15
MAX_RECOMMENDATIONS = 5

ADVICE_METADATAS_PATH = pathlib.Path(__file__).parent.parent.parent / "advice_metadatas.json"
ADVICE_METADATAS_JSON = json.loads(ADVICE_METADATAS_PATH.read_text(encoding="utf-8"))
ADVICE_METADATAS = {
    advice_id: AdviceMetadata(
        advice_id=advice_id,
        **metadata
    ) for advice_id, metadata in ADVICE_METADATAS_JSON.items()
}
    
# ========= Functions =========

def get_advice_metadata(
    advice_id: str
) -> Optional[AdviceMetadata]:
    """
    Retrieves the advice metadata for a given advice ID.
    Tries to match safely by normalizing and fallback to case-insensitive search.
    """
    if not advice_id or not isinstance(advice_id, str):
        return None

    normalized_id = advice_id.strip()
    # First, try exact match
    metadata = ADVICE_METADATAS.get(normalized_id)
    if metadata:
        return metadata

    # Try case-insensitive match
    for key, value in ADVICE_METADATAS.items():
        if key.lower() == normalized_id.lower():
            return value

    # Try whitespace-insensitive match
    normalized_id_ws = ''.join(normalized_id.split())
    for key, value in ADVICE_METADATAS.items():
        if ''.join(key.split()).lower() == normalized_id_ws.lower():
            return value

    return None

def is_advice_exists(
    advice_id: str
) -> bool:
    """
    Checks if the advice ID exists in the metadata.
    """
    return advice_id in ADVICE_METADATAS

def advice_metadata_to_str(
    advice_id: str
) -> str:
    advice_metadata = get_advice_metadata(advice_id)
    advice_str = (
        f"ID: {advice_metadata.advice_id}\n"
        f"- 제목: {advice_metadata.emoji} {advice_metadata.title}\n"
        f"- 설명: {advice_metadata.description}\n"
        f"- 요구사항: {advice_metadata.prompt_instruction}\n"
    )
    
    return advice_str

def prompt_advice_metadata(advice_id: str):
    advice_section = (
        f"### 💡 '나'가 소개팅 도중 요청한 조언:\n"
        "----------------------\n"
        f"{advice_metadata_to_str(advice_id)}"
        "----------------------\n\n"
    )

    return advice_section

def prompt_advice_metadata_list():
    advice_section = "### 💡 '나'에게 소개팅 도중 제공 가능한 조언 목록:\n"
    advice_section += "----------------------\n"
    advice_section += '\n'.join([advice_metadata_to_str(advice_id) for advice_id in ADVICE_METADATAS])
    advice_section += "----------------------\n\n"

    return advice_section

# ========= BreaktimeAdviceGenerator =========

class BreaktimeAdviceGenerator():
    PROMPT_NAME = "advice/advice_generator"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"

    @classmethod
    def _generate_prompt(cls, advice_id: str, conversation_memory: memory.ConversationMemory) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                prompt_advice_metadata(advice_id),
                conversation_memory.prompt_conversation_info(),
                conversation_memory.prompt_partner_memory(),
                conversation_memory.prompt_messages(n_messages=N_MESSAGES),
            ])
        }

        return [system_message, user_message]

    @classmethod
    async def do(cls, advice_id: str, conversation_memory: memory.ConversationMemory) -> Advice:
        prompt_messages = cls._generate_prompt(
            advice_id=advice_id,
            conversation_memory=conversation_memory
        )
        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=Advice
        )
        response = response.choices[0].message.parsed

        return response
    
# ========= BreaktimeAdviceRecommendationGenerator =========

class BreaktimeAdviceRecommender:
    PROMPT_NAME = "advice/advice_recommender"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"

    @classmethod
    def _generate_prompt(cls, conversation_memory: memory.ConversationMemory) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                prompt_advice_metadata_list(),
                conversation_memory.prompt_conversation_info(),
                conversation_memory.prompt_partner_memory(),
                conversation_memory.prompt_messages(n_messages=N_MESSAGES),
            ])
        }

        return [system_message, user_message]


    @classmethod
    async def do(
        cls,
        conversation_memory: memory.ConversationMemory,
        n_consistency: int = 5
    ) -> List[AdviceMetadata]:
        prompt_messages = cls._generate_prompt(conversation_memory)

        async def single_run():
            try:
                response = await clients.async_openai_client.beta.chat.completions.parse(
                    messages=prompt_messages,
                    model=cls.LLM_MODEL,
                    response_format=AdviceRecommendation,
                )
                response = response.choices[0].message.parsed
                return response
            except Exception as e:
                if config.settings.DEBUG:
                    print(f"[{cls.__name__}] Error: {e}")
                return None

        results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))
        advice_ids = [
            r.advice_ids for r in results if isinstance(r, AdviceRecommendation)
        ]
        if not advice_ids:
            raise ValueError("No valid responses received.")

        # 각 요소별로 순위의 합을 계산
        rank_sum = defaultdict(int)
        count = defaultdict(int)
        for ranked in advice_ids:
            for idx, item in enumerate(ranked):
                rank_sum[item] += idx + 1  # 순위는 1부터 시작
                count[item] += 1

        # 순위의 합이 작은 순서대로 정렬
        sorted_items = sorted(
            rank_sum.items(),
            key=lambda x: (x[1], x[0])
        )
        final_ranking = [item for item, _ in sorted_items[:MAX_RECOMMENDATIONS]]

        output = []
        for advice_id in final_ranking:
            if not is_advice_exists(advice_id):
                continue
            advice_metadata = get_advice_metadata(advice_id)
            if advice_metadata:
                output.append(advice_metadata)
            
        return output