import json
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass
import async_timeout

from ...core import (
    conversation_elements,
    clients,
    config,
    logger
)
from ...models import (
    conversation_models
)
from ...utils.prompt_utils import (
    load_prompt,
    make_last_target_message_prompt
)


class RealtimeSentimentalAnalysisLLMOutput(BaseModel):
    score: Literal[0, 1, 2, 3, 4]


class RealtimeSentimentalAnalysis():
    PROMPT_NAME = "realtime_analysis/sentimental_analysis"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = RealtimeSentimentalAnalysisLLMOutput

    @classmethod
    def _generate_prompt(
        cls,
        messages: List[conversation_elements.Message]
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": make_last_target_message_prompt(messages)
        }

        return [system_message, user_message]

    @classmethod
    async def do(
        cls,
        messages: List[conversation_elements.Message],
        n_consistency: int = 3
    ) -> RealtimeSentimentalAnalysisLLMOutput:
        prompt_messages = cls._generate_prompt(
            messages
        )

        async def single_run():
            try:
                response = await clients.async_openai_client.beta.chat.completions.parse(
                    messages=prompt_messages,
                    model=cls.LLM_MODEL,
                    response_format=cls.LLM_RESPONSE_FORMAT,
                    # temperature=0.0,
                )
                response = response.choices[0].message.parsed
                return response
            except Exception as e:
                logger.logger.error(f"Exception in single_run: {e}")
                return None

        results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))
        scores = [
            r.score for r in results if isinstance(r, RealtimeSentimentalAnalysisLLMOutput)
        ]
        if not scores:
            raise ValueError("No valid responses received.")

        avg_score = sum(scores) / len(scores)
        avg_score = int(round(avg_score))
        output = RealtimeSentimentalAnalysisLLMOutput(score=avg_score)
        
        if config.settings.DEBUG:
            logger.logger.info(f"[{cls.__name__}]")
            logger.logger.info("↳ " + f"{output}")

        return output