import json
import pathlib
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict

from ...models import conversation_models

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
    make_advice_metadata_prompt,
    make_last_target_message_prompt,
    make_message_prompt,
    make_partner_memory_prompt,
)


class BreaktimeAdvice():
    PROMPT_NAME = "breaktime_advice/advice"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = conversation_models.StringTypeBreaktimeAdviceContent | conversation_models.ListTypeBreaktimeAdviceContent

    @classmethod
    def _generate_prompt(
        cls,
        advice_metadata: dict[str, Any],
        partner_memory: dict[str, list[str]],
        messages: List[conversation_elements.Message]
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": (
                f"{make_advice_metadata_prompt(advice_metadata)}"
                f"{make_partner_memory_prompt(partner_memory)}"
                f"{make_message_prompt(messages)}"
            )
        }

        return [system_message, user_message]

    @classmethod
    async def do(
        cls,
        advice_metadata: dict[str, Any],
        partner_memory: dict[str, list[str]],
        messages: List[conversation_elements.Message]
    ) -> conversation_models.StringTypeBreaktimeAdviceContent | conversation_models.ListTypeBreaktimeAdviceContent:
        prompt_messages = cls._generate_prompt(
            advice_metadata, 
            partner_memory, 
            messages
        )
        
        response_format = (
            conversation_models.StringTypeBreaktimeAdviceContent
            if advice_metadata['content_type'] == "string" else
            conversation_models.ListTypeBreaktimeAdviceContent
        )

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=response_format
        )
        response = response.choices[0].message.parsed
        
        if config.settings.DEBUG:
            logger.logger.warning(f"[{cls.__name__}]")
            logger.logger.warning("↳ " + f"{response}")
            
        return response