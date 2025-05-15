from datetime import datetime
from typing import Dict, Optional, List, Literal

from pydantic import BaseModel, Field

from ..elements import Message
from ...utils.prompt_utils import load_prompt
from ...core import clients, logger

log = logger.get_logger(__name__)

# === Constants ===

N_MESSAGES = 15
PARTNER_MEMORY_CATEGORIES = [
    "취미/관심사",
    "고민",
    "가족/친구",
    "직업/학업",
    "성격/가치관",
    "이상형/연애관",
    "생활습관",
]

# === Models ===

class PartnerMemoryRelevance(BaseModel):
    """
    파트너 메시지가 메모리에 기억될 필요가 있는지 여부를 나타내는 모델.
    """
    should_remember: bool


class PartnerMemoryUpdateInstruction(BaseModel):
    """
    파트너 메세지가 메모리에 업데이트될 필요가 있는지 여부와
    업데이트할 카테고리 및 내용을 포함하는 모델.
    """
    should_update: bool
    category: Optional[Literal[
        '취미/관심사',
        '고민',
        '가족/친구',
        '직업/학업',
        '성격/가치관',
        '이상형/연애관',
        '생활습관',
    ]]
    content: Optional[str] = None
    

class PartnerMemory(BaseModel):
    content: Dict[str, List[str]]
    

# === ConversationMemory ===

class ConversationMemory:
    """
    대화 메모리를 관리하는 클래스.
    """
    def __init__(
        self,
        my_info: Optional[Dict] = None,
        partner_info: Optional[Dict] = None,
    ):
        self.my_info = my_info or {}
        self.partner_info = partner_info or {}
        self.start_time = datetime.now()
        self.messages: List[Message] = []
        self.partner_memory: PartnerMemory = PartnerMemory(
            content={
                category: [] for category in PARTNER_MEMORY_CATEGORIES
            }
        )

    def add_message(self, message: Message) -> None:
        # 중복 메시지 필터링은 외부에서 처리한다고 가정
        self.messages.append(message)

    def get_recent_messages(self, n: Optional[int] = None) -> List[Message]:
        return self.messages[-n:] if n else self.messages

    def is_message_exists(self, message: Message) -> bool:
        return self.messages and self.messages[-1].message_id >= message.message_id

    def update_partner_memory(
        self,
        instruction: PartnerMemoryUpdateInstruction,
    ) -> None:
        if instruction.should_update and instruction.category and instruction.content:
            self.partner_memory.content[instruction.category].append(instruction.content)

    def get_elapsed_time_str(self) -> str:
        elapsed = datetime.now() - self.start_time
        hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}시간 {minutes}분 {seconds}초"

    def prompt_conversation_info(self) -> str:
        return (
            "### 📝 대화 정보:\n"
            f"⏰ 대화 경과 시간: {self.get_elapsed_time_str()}\n"
            f"💬 총 메시지 수: {len(self.messages)}회\n"
        )

    def prompt_messages(self, n_messages: Optional[int] = None) -> str:
        prompt = "### 💬 대화 내용:\n"
        messages_to_show = self.get_recent_messages(n_messages)
        if n_messages and len(self.messages) > n_messages:
            prompt += "...이전 메시지 일부 생략...\n"
        for msg in messages_to_show:
            prompt += msg.to_prompt()
        return prompt

    def prompt_partner_memory(self) -> str:
        prompt = "### 📝 파트너에 대한 메모:\n"
        for category, memos in self.partner_memory.content.items():
            if not memos:
                continue
            prompt += f"<{category}>와 관련된 메모:\n"
            for idx, memo in enumerate(memos):
                prompt += f"- {idx}: {memo}\n"
        return prompt
        

class PartnerMemoryRelevanceClassifier:
    PROMPT_NAME = "memory/partner_message_relevance_classifier"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"

    @classmethod
    def _generate_prompt(cls, conversation_memory: ConversationMemory) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER).format(
                categories=", ".join(PARTNER_MEMORY_CATEGORIES)
            )
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                conversation_memory.prompt_messages(n_messages=N_MESSAGES),
                f"### 🔍 분석할 메시지:\n{conversation_memory.messages[-1].to_prompt()}"
            ])
        }
        return [system_message, user_message]
    
    @classmethod
    async def do(cls, conversation_memory: ConversationMemory) -> PartnerMemoryRelevance:
        prompt_messages = cls._generate_prompt(conversation_memory)

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=PartnerMemoryRelevance,
        )
        response = response.choices[0].message.parsed

        return response


class PartnerMemoryUpdateInstructionGenerator:
    PROMPT_NAME = "memory/partner_memory_update_instruction_generator"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-mini"

    @classmethod
    def _generate_prompt(cls, conversation_memory: ConversationMemory) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER).format(
                categories=", ".join(PARTNER_MEMORY_CATEGORIES)
            )
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                conversation_memory.prompt_partner_memory(),
                conversation_memory.prompt_messages(n_messages=N_MESSAGES),
                f"### 🔍 분석할 메시지:\n{conversation_memory.messages[-1].to_prompt()}"
            ])
        }

        return [system_message, user_message]
    
    @classmethod
    async def do(cls, conversation_memory: ConversationMemory) -> None:
        prompt_messages = cls._generate_prompt(conversation_memory)

        response = await clients.async_openai_client.beta.chat.completions.parse(
            messages=prompt_messages,
            model=cls.LLM_MODEL,
            response_format=PartnerMemoryUpdateInstruction,
        )
        response = response.choices[0].message.parsed
            
        return response

# === Functions ===
    
async def update_partner_memory_pipeline(
    conversation_memory: ConversationMemory,
) -> PartnerMemoryUpdateInstruction:
    
    if conversation_memory.messages[-1].role != "파트너":
        instruction = PartnerMemoryUpdateInstruction(
            should_update=False,
            category=None,
            content=None
        )
    else:
        relevance = await PartnerMemoryRelevanceClassifier.do(
            conversation_memory=conversation_memory
        )
        
        if relevance.should_remember:
            instruction = await PartnerMemoryUpdateInstructionGenerator.do(
                conversation_memory=conversation_memory
            )
        else:
            instruction = PartnerMemoryUpdateInstruction(
                should_update=False,
                category=None,
                content=None
            )
    
    conversation_memory.update_partner_memory(
        instruction=instruction
    )
    