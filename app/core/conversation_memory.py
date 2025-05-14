from pydantic import BaseModel, Field
from typing import Dict, Optional, Any, Union, List, Tuple, Callable, Literal
from datetime import datetime
from collections import Counter, defaultdict
import asyncio

from .conversation_elements import Message
from ..utils.prompt_utils import load_prompt, make_last_target_message_prompt, make_partner_memory_prompt
from . import clients, logger, config


log = logger.get_logger(__name__)


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
    
    
class PartnerMemoryUpdatorLLMOutput(BaseModel):
    update: bool
    memo: Optional[str] = None


class ConversationMemory:
    EWMA_ALPHA = 0.25
    
    def __init__(
        self,
        my_info: Optional[Dict[str, Any]] = None,
        partner_info: Optional[Dict[str, Any]] = None,
    ):
        self.my_info: Dict[str, Any] = my_info or {}
        self.partner_info: Dict[str, Any] = partner_info or {}
        self.start_time: datetime = datetime.now()
        
        self.messages: List[Message] = []
        
        self.partner_memory: Dict[str, List[str]] = {
            category: [] 
            for category in PARTNER_MEMORY_CATEGORIES
        }
        
        self.scores: Dict[str, int] = {
            "partner_engagement_score": 0,
            "my_engagement_score": 0,
            "my_talk_share": 0,
        }
    
    # "### 📝 대화 정보"
    def prompt_conversation_info(self) -> str:
        prompt_str = "### 📝 대화 정보:\n"
        
        elapsed_time = datetime.now() - self.start_time
        elapsed_seconds = int(elapsed_time.total_seconds())
        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        prompt_str += f"⏰ 대화 경과 시간: {hours}시간 {minutes}분 {seconds}초\n"
        
        n_messages = len(self.messages)
        prompt_str += f"💬 총 메시지 수: {n_messages}회\n"
        
        return prompt_str
    
    # f"<{category}>와 관련된 메모"
    def prompt_partner_memory_by_category(self, category: str) -> str:
        prompt_str = f"<{category}>와 관련된 메모:\n"
        
        if category not in PARTNER_MEMORY_CATEGORIES:
            raise ValueError(f"Invalid category: {category}")
        for idx, content in enumerate(self.partner_memory[category]):
            prompt_str += f"- {idx}: {content}\n"
        return prompt_str
    
    # "### 📝 파트너에 대한 메모"
    def prompt_partner_memory(self) -> str:
        prompt_str = "### 📝 파트너에 대한 메모:\n"
        
        for category in PARTNER_MEMORY_CATEGORIES:
            if not self.partner_memory[category]:
                continue
            prompt_str += self.prompt_partner_memory_by_category(category)
            
        return prompt_str

    # "### 💬 대화 내용"
    def prompt_messages(self, n_messages: Optional[int] = None) -> str:
        prompt_str = "### 💬 대화 내용:\n"
        
        total_messages = len(self.messages)
        if n_messages is None or n_messages >= total_messages:
            messages_to_show = self.messages
        else:
            prompt_str += "...이전 메시지 일부 생략...\n"
            messages_to_show = self.messages[-n_messages:]
        for message in messages_to_show:
            prompt_str += message.to_prompt()
            
        return prompt_str
        
    def is_message_exists(self, message: Message) -> bool:
        if not self.messages:
            return False
        return self.messages[-1].message_id >= message.message_id

    def get_messages(self, n_messages: Optional[int] = None) -> List[Message]:
        if n_messages is None:
            return self.messages
        return self.messages[-n_messages:]

    def add_message(self, message: Message) -> None:
        self.messages.append(message)

        if message.role != "파트너":
            return
    
    def update_partner_memory(
        self,
        target_category: str,
        llm_output: PartnerMemoryUpdatorLLMOutput,
    ) -> None:
        if llm_output.update and llm_output.memo:
            self.partner_memory[target_category].append(llm_output.memo)

    def update_scores(
        self,
        message: Message,
        sentimental_analysis_output
    ) -> None:
        cur_score = sentimental_analysis_output.score

        # EWMA 적용
        if message.role == "파트너":
            prev = self.scores.get("partner_engagement_score", 0)
            if prev == 0:
                self.scores["partner_engagement_score"] = cur_score
            else:
                self.scores["partner_engagement_score"] = (
                    self.EWMA_ALPHA * cur_score + (1 - self.EWMA_ALPHA) * prev
                )
        elif message.role == "나":
            prev = self.scores.get("my_engagement_score", 0)
            if prev == 0:
                self.scores["my_engagement_score"] = cur_score
            else:
                self.scores["my_engagement_score"] = (
                    self.EWMA_ALPHA * cur_score + (1 - self.EWMA_ALPHA) * prev
                )

        # talk share 계산
        total_length = sum(len(msg.content) for msg in self.messages)
        my_length = sum(len(msg.content) for msg in self.messages if msg.role == "나")
        if total_length > 0:
            self.scores["my_talk_share"] = my_length / total_length
        else:
            self.scores["my_talk_share"] = 0

    def get_scores(self) -> Dict[str, Any]:
        return self.scores
        
        

class PartnerMessageCategorizer:
    PROMPT_NAME = "memory/partner_message_categorizer"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"
    LLM_RESPONSE_FORMAT = PartnerMessageCategorizerLLMOutput
    
    N_MESSAGES = 5

    @classmethod
    def _generate_prompt(
        cls,
        conversation_memory: ConversationMemory,
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER).format(
                summary_categories=", ".join(PARTNER_MEMORY_CATEGORIES)
            )
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
        conversation_memory: ConversationMemory,
    ):
        prompt_messages = cls._generate_prompt(conversation_memory)

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=cls.LLM_RESPONSE_FORMAT,
        )
        response = response.choices[0].message.parsed

        return response


class PartnerMemoryUpdater:
    PROMPT_NAME = "memory/partner_message_memory_updater"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-mini"
    LLM_RESPONSE_FORMAT = PartnerMemoryUpdatorLLMOutput
    
    N_MESSAGES = 5

    @classmethod
    def _generate_prompt(
        cls,
        target_category: str,
        conversation_memory: ConversationMemory,
    ) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER).format(
                summary_categories=", ".join(PARTNER_MEMORY_CATEGORIES)
            )
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                conversation_memory.prompt_partner_memory_by_category(target_category),
                conversation_memory.prompt_messages(n_messages=cls.N_MESSAGES),
                f"### 🔍 분석할 메시지:\n{conversation_memory.messages[-1].to_prompt()}"
            ])
        }

        return [system_message, user_message]
    
    @classmethod
    async def do(
        cls,
        target_category: str,
        conversation_memory: ConversationMemory,
    ) -> None:
        prompt_messages = cls._generate_prompt(target_category, conversation_memory)

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=cls.LLM_RESPONSE_FORMAT,
        )
        response = response.choices[0].message.parsed
            
        return response