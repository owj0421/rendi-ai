import json
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass

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
    
    
class RealtimeSentimentalAnalysisLLMOutput(BaseModel):
    final_answer: Literal["긍정", "부정", "중립"]


class RealtimeSentimentalAnalysis():
    PROMPT_NAME = "realtime_analysis/sentimental_analysis"
    PROMPT_VER = 1
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
        
        messages_str = "\n".join([message.to_prompt() for message in messages])

        user_message = {
            "role": "user",
            "content": load_prompt(cls.PROMPT_NAME, "user", cls.PROMPT_VER).format(messages=messages_str)
        }

        return [system_message, user_message]

    @classmethod
    async def do(
        cls,
        messages: List[conversation_elements.Message],
        n_consistency: int = 5
    ) -> RealtimeSentimentalAnalysisLLMOutput:
        prompt_messages = cls._generate_prompt(messages)

        async def single_run():
            response = await clients.async_openai_client.beta.chat.completions.parse(
                messages=prompt_messages,
                model="gpt-4.1-nano",
                response_format=cls.LLM_RESPONSE_FORMAT,
                temperature=0.0,
            )
            response = response.choices[0].message

            if hasattr(response, "refusal") and response.refusal:
                return response.refusal
            else:
                return response.parsed

        results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))

        final_answers = [
            r.final_answer for r in results if isinstance(r, RealtimeSentimentalAnalysisLLMOutput)
        ]

        if not final_answers:
            return results[0] if results else "No response"

        most_common = max(set(final_answers), key=final_answers.count)
        
        return RealtimeSentimentalAnalysisLLMOutput(
            final_answer=most_common
        )