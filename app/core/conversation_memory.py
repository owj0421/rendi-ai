from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, Union, List, Tuple, Callable, Literal
from datetime import datetime
from collections import Counter, defaultdict
import asyncio

from .conversation_elements import Message
from ..utils.prompt_utils import load_prompt, make_last_target_message_prompt, make_partner_memory_prompt
from . import clients, logger, config


log = logger.get_logger(__name__)


N_MESSAGES = 5
PARTNER_MEMORY_CATEGORIES = [
    "취미/관심사",      # 취미, 좋아하는 것, 선호하는 활동 등
    "고민",    # 상대방이 털어놓은 고민, 걱정거리, 힘든 점
    "가족/친구",   # 가족관계, 친구 이야기, 주변 사람들에 대한 언급
    "직업/학업",   # 직장, 직업, 전공, 학교, 공부 관련 이야기
    "성격/가치관", # 성격적 특징, 중요하게 생각하는 가치, 인생관
    "이상형/연애관", # 이상형, 연애에 대한 생각, 연애 경험
    "생활습관",    # 평소 습관, 일상 루틴, 건강, 식습관 등
]


class PartnerMessageCategorizerLLMOutput(BaseModel):
    is_useful_to_remember: bool  # 소개팅 대화 중 해당 대화가 나중에 기억해두었을 때 유용한지 여부
    target_category: Optional[Literal[
        '취미/관심사',
        '고민',
        '가족/친구',
        '직업/학업',
        '성격/가치관',
        '이상형/연애관',
        '생활습관',
    ]] = None  # 유용하다면 어느 카테고리로 가야하는지


class PartnerMessageCategorizer:
    PROMPT_NAME = "memory/partner_message_categorizer"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = PartnerMessageCategorizerLLMOutput

    @classmethod
    def _generate_prompt(
        cls,
        messages: List[Message]
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER).format(
                summary_categories=", ".join(PARTNER_MEMORY_CATEGORIES)
            )
        }
        user_message = {
            "role": "user",
            "content": make_last_target_message_prompt(messages)
        }

        return [system_message, user_message]
    
    @classmethod
    async def do(
        cls,
        messages: List[Message]
    ):
        prompt_messages = cls._generate_prompt(
            messages
        )

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=cls.LLM_RESPONSE_FORMAT,
        )
        response = response.choices[0].message.parsed

        if config.settings.DEBUG:
            log.info(f"[{cls.__name__}]")
            log.info(f"↳ {response}")

        return response


class PartnerMemoryUpdatorLLMOutput(BaseModel):
    update: bool
    memo: Optional[str] = None


class PartnerMemoryUpdater:
    PROMPT_NAME = "memory/partner_message_memory_updater"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-mini"
    LLM_RESPONSE_FORMAT = PartnerMemoryUpdatorLLMOutput

    @classmethod
    def _generate_prompt(
        cls,
        target_category: str,
        previous_memory: list[str],
        messages: List[Message],
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        previous_memory_str = (
            f"아래는 파트너에 대해 '{target_category}' 카테고리로 메모한 내용입니다.\n"
            f'{"\n".join(f"- {idx}: {content}"for idx, content in enumerate(previous_memory))}\n\n'
        )
        user_message = {
            "role": "user",
            "content": previous_memory_str + make_last_target_message_prompt(messages)
        }

        return [system_message, user_message]
    
    @classmethod
    async def do(
        cls,
        target_category: str,
        partner_memory: Dict[str, list[str]],
        messages: List[Message],
    ) -> None:
        prompt_messages = cls._generate_prompt(
            target_category=target_category,
            previous_memory=partner_memory[target_category],
            messages=messages
        )

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=cls.LLM_RESPONSE_FORMAT,
        )
        response = response.choices[0].message.parsed
        
        if response.update and response.memo:
            partner_memory[target_category].append(response.memo)
            
        if config.settings.DEBUG:
            log.info(f"[{cls.__name__}]")
            log.info("↳ " + f"{make_partner_memory_prompt(partner_memory)}")
            
        return


class ConversationMemory:
    def __init__(
        self,
        my_info: Optional[Dict[str, Any]] = None,
        partner_info: Optional[Dict[str, Any]] = None,
    ):
        self.my_info: Dict[str, Any] = my_info or {}
        self.partner_info: Dict[str, Any] = partner_info or {}
        self.start_time: datetime = datetime.now()
        self.messages: List[Message] = []
        self.partner_memory: Dict[str, List[str]] = {category: [] for category in PARTNER_MEMORY_CATEGORIES}

    def is_message_exists(self, message: Message) -> bool:
        if not self.messages:
            return False
        return self.messages[-1].message_id >= message.message_id

    def get_messages(self, n_messages: Optional[int] = None) -> List[Message]:
        if n_messages is None:
            return self.messages
        return self.messages[-n_messages:]

    async def add_message(self, message: Message) -> None:
        self.messages.append(message)

        if message.role != "파트너":
            return

        response = await PartnerMessageCategorizer.do(
            messages=self.get_messages(n_messages=N_MESSAGES),
        )

        if not response.is_useful_to_remember or not response.target_category:
            return

        await PartnerMemoryUpdater.do(
            target_category=response.target_category,
            partner_memory=self.partner_memory,
            messages=self.get_messages(n_messages=N_MESSAGES),
        )
