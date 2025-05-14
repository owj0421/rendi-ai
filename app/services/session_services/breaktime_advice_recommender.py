import json
import pathlib
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict

from . import conversation_elements, conversation_memory

from ...core import (
    clients,
    config,
    logger
)
from ...models import (
    conversation_models
)
from ...utils.prompt_utils import (
    load_prompt,
    make_last_target_message_prompt,
    make_message_prompt,
    make_advice_metadata_prompt,
    make_advice_metadata_list_prompt,
    make_partner_memory_prompt
)
from ...utils import (
    advice_utils
)

log = logger.get_logger(__name__)

MAX_RECOMMENDATIONS = 5

# TODO: 소개팅 경과 시간

class BreaktimeAdviceRecommenderLLMOutput(BaseModel):
    final_answer: list[str]


class BreaktimeAdviceRecommender:
    PROMPT_NAME = "breaktime_advice/ranker"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = BreaktimeAdviceRecommenderLLMOutput
    N_MESSAGES = 5

    @classmethod
    def _generate_prompt(
        cls,
        conversation_memory: conversation_memory.ConversationMemory
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                make_advice_metadata_list_prompt(advice_utils.ADVICE_METADATAS),
                conversation_memory.prompt_conversation_info(),
                conversation_memory.prompt_partner_memory(),
                conversation_memory.prompt_messages(n_messages=cls.N_MESSAGES),
            ])
        }

        return [system_message, user_message]


    @classmethod
    async def do(
        cls,
        conversation_memory: conversation_memory.ConversationMemory,
        n_consistency: int = 5
    ) -> BreaktimeAdviceRecommenderLLMOutput:
        prompt_messages = cls._generate_prompt(conversation_memory)

        async def single_run():
            try:
                response = await clients.async_openai_client.beta.chat.completions.parse(
                    messages=prompt_messages,
                    model=cls.LLM_MODEL,
                    response_format=cls.LLM_RESPONSE_FORMAT
                )
                response = response.choices[0].message.parsed
                return response
            except Exception as e:
                if config.settings.DEBUG:
                    print(f"[{cls.__name__}] Error: {e}")
                return None

        results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))
        ranked_lists = [
            r.final_answer for r in results if isinstance(r, cls.LLM_RESPONSE_FORMAT)
        ]
        if not ranked_lists:
            raise ValueError("No valid responses received.")

        # 각 요소별로 순위의 합을 계산
        rank_sum = defaultdict(int)
        count = defaultdict(int)
        for ranked in ranked_lists:
            for idx, item in enumerate(ranked):
                rank_sum[item] += idx + 1  # 순위는 1부터 시작
                count[item] += 1

        # 순위의 합이 작은 순서대로 정렬
        sorted_items = sorted(
            rank_sum.items(),
            key=lambda x: (x[1], x[0])
        )
        final_ranking = [item for item, _ in sorted_items[:MAX_RECOMMENDATIONS]]

        output = advice_utils.get_advice_metadata(
            advice_ids=final_ranking
        )
        
        if config.settings.DEBUG:
            print(f"[{cls.__name__}]")
            print("↳ " + f"{output}")
        
        return output