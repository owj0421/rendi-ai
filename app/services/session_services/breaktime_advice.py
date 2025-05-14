import json
import pathlib
import asyncio
import itertools
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Literal, Optional
from dataclasses import dataclass
from collections import Counter, defaultdict

from . import conversation_elements, conversation_memory

from ...models import conversation_models

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
    make_advice_metadata_prompt,
    make_last_target_message_prompt,
    make_message_prompt,
    make_partner_memory_prompt,
)


log = logger.get_logger(__name__)


class BreaktimeAdvice():
    PROMPT_NAME = "breaktime_advice/advice"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = conversation_models.BreaktimeAdviceStringTypeContent | conversation_models.BreaktimeAdviceListTypeContent
    
    N_MESSAGES = 5

    @classmethod
    def _generate_prompt(
        cls,
        advice_metadata: dict[str, str],
        conversation_memory: conversation_memory.ConversationMemory
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                make_advice_metadata_prompt(advice_metadata),
                conversation_memory.prompt_conversation_info(),
                conversation_memory.prompt_partner_memory(),
                conversation_memory.prompt_messages(n_messages=cls.N_MESSAGES),
            ])
        }

        return [system_message, user_message]

    @classmethod
    async def do(
        cls,
        advice_metadata: dict[str, str],
        conversation_memory: conversation_memory.ConversationMemory,
    ) -> conversation_models.BreaktimeAdviceStringTypeContent | conversation_models.BreaktimeAdviceListTypeContent:
        prompt_messages = cls._generate_prompt(
            advice_metadata=advice_metadata,
            conversation_memory=conversation_memory
        )
        
        response_format = (
            conversation_models.BreaktimeAdviceStringTypeContent
            if advice_metadata['content_type'] == "string" else
            conversation_models.BreaktimeAdviceListTypeContent
        )

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=response_format
        )
        response = response.choices[0].message.parsed
        
        if config.settings.DEBUG:
            log.warning(f"[{cls.__name__}]")
            log.warning("↳ " + f"{response}")
            
        return response