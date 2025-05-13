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
    analysis_io,
    advice_io
)
from ...prompts.loader import (
    load_prompt
)


class BreaktimeAdvice():
    PROMPT_NAME = "breaktime_advice/advice"
    PROMPT_VER = 1
    
    def __init__(
        self,
        emoji: str,
        title: str,
        description: str,
        content_type: Literal["string", "list"]
    ):
        self.EMOJI = emoji
        self.TITLE = title
        self.DESCRIPTION = description
        self.CONTENT_TYPE = content_type

    def _generate_prompt(
        self,
        messages: List[conversation_elements.Message]
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(self.PROMPT_NAME, "system", self.PROMPT_VER)
        }
        
        messages_str = "\n".join([message.to_prompt() for message in messages])

        user_message = {
            "role": "user",
            "content": (
                f"Task:\n"
                f"{self.DESCRIPTION}\n\n"
                f"Conversation History:\n"
                f"{messages_str}\n\n"
            )
        }

        return [system_message, user_message]

    async def do(
        self,
        messages: List[conversation_elements.Message]
    ) -> advice_io.StringTypeBreaktimeAdviceContent | advice_io.ListTypeBreaktimeAdviceContent:
        
        prompt_messages = self._generate_prompt(messages)
        
        response_format = (
            advice_io.StringTypeBreaktimeAdviceContent
            if self.CONTENT_TYPE == "string" else
            advice_io.ListTypeBreaktimeAdviceContent
        )

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model="gpt-4.1-mini",
            temperature=0.0,
            response_format=response_format
        )
        response_message = response.choices[0].message

        if hasattr(response_message, "refusal") and response_message.refusal:
            return response_message.refusal
        else:
            return response_message.parsed