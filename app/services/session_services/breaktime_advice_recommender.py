import json
import pathlib
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict

from ...core import (
    conversation_elements,
    clients,
    config,
)
from ...models.conversation import (
    analysis_io
)
from ...prompts.loader import (
    load_prompt
)
from ...utils import (
    advice_utils
)


# TODO: 소개팅 경과 시간

class BreaktimeAdviceRecommenderLLMOutput(BaseModel):
    final_answer: list[str]


class BreaktimeAdviceRecommender:
    PROMPT_NAME = "breaktime_advice/ranker"
    PROMPT_VER = 1

    @classmethod
    def _generate_prompt(
        cls,
        messages: List[conversation_elements.Message],
        max_advice_count: int = 5
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }

        analysis_str = advice_utils.get_advice_metadata_prompt()
        
        messages_str = "\n".join([message.to_prompt() for message in messages])
        
        user_message = {
            "role": "user",
            "content": (
                f"{analysis_str}\n\n"
                "그리고 아래는 대화 메시지입니다:\n"
                f"{messages_str}\n\n"
                "위 메시지를 바탕으로, 가장 필요한 카드 id를 중요도 순서대로 정렬해서 리스트로 출력해 주세요."
                f" (최대 {max_advice_count}개)\n\n"
            )
        }

        return [system_message, user_message]

    @classmethod
    async def do(
        cls,
        messages: List[conversation_elements.Message],
        n_consistency: int = 5,
        max_advice_count: int = 5
    ) -> BreaktimeAdviceRecommenderLLMOutput:
        
        prompt_messages = cls._generate_prompt(messages, max_advice_count)

        async def single_run():
            response = await clients.async_openai_client.beta.chat.completions.parse(
                messages=prompt_messages,
                model="gpt-4.1-nano",
                response_format=BreaktimeAdviceRecommenderLLMOutput,
                # temperature=0.0,
            )
            response = response.choices[0].message

            if hasattr(response, "refusal") and response.refusal:
                return response.refusal
            else:
                return response.parsed

        results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))

        ranked_lists = [
            r.final_answer for r in results if isinstance(r, BreaktimeAdviceRecommenderLLMOutput)
        ]
        if not ranked_lists:
            raise ValueError("No valid responses received.")

        ranked_lists = sum(ranked_lists, [])
        counter = Counter(ranked_lists)
        final_ranking = [item for item, _ in counter.most_common(max_advice_count)]

        return BreaktimeAdviceRecommenderLLMOutput(
            final_answer=final_ranking[:max_advice_count]
        )