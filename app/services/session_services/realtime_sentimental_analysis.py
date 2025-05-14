import json
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass
import async_timeout

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
    make_last_target_message_prompt
)


log = logger.get_logger(__name__)


class RealtimeSentimentalAnalysisLLMOutput(BaseModel):
    score: Literal[0, 1, 2, 3, 4]


class RealtimeSentimentalAnalysis():
    PROMPT_NAME = "realtime_analysis/sentimental_analysis"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = RealtimeSentimentalAnalysisLLMOutput
    
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
                conversation_memory.prompt_messages(n_messages=cls.N_MESSAGES),
                f"### 🔍 분석할 메시지:\n{conversation_memory.messages[-1].to_prompt()}"
            ])
        }

        return [system_message, user_message]

    @classmethod
    async def do(
        cls,
        conversation_memory: conversation_memory.ConversationMemory,
        n_consistency: int = 3
    ) -> RealtimeSentimentalAnalysisLLMOutput:
        prompt_messages = cls._generate_prompt(conversation_memory)

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
                log.error(f"Exception in single_run: {e}")
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
            log.info(f"[{cls.__name__}]")
            log.info("↳ " + f"{output}")

        return output