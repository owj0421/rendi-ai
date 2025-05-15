import asyncio
from dataclasses import dataclass
from typing import List, Dict, Literal

from pydantic import BaseModel

from . import memory
from ..elements import Message
from ...core import clients, logger
from ...utils.prompt_utils import load_prompt

log = logger.get_logger(__name__)

# === Constants ===

EWMA_ALPHA = 0.25
USER_ROLE = "나"
PARTNER_ROLE = "파트너"

# === Models ===

class MessageSentimentScore(BaseModel):
    """
    메시지 감정 점수를 나타내는 모델.
    점수는 0에서 4 사이의 정수로 표현됩니다.
    """
    score: Literal[0, 1, 2, 3, 4]


class ConversationScores(BaseModel):
    """
    대화 참여도 점수를 나타내는 데이터 클래스.
    """
    user_engagement: float = 0.0  # 사용자의 참여도
    partner_engagement: float = 0.0  # 파트너의 참여도
    user_talk_share: float = 0.0  # 사용자의 발화 비율


# === ConversationScorer ===

class ConversationScorer:
    """
    대화에 대한 점수를 계산하고 업데이트하는 클래스.
    """
    def __init__(self, alpha: float = EWMA_ALPHA):
        self.alpha = alpha
        self._scores = ConversationScores()

    def update(self, conversation_memory: memory.ConversationMemory, sentiment: MessageSentimentScore) -> None:
        if not conversation_memory.messages:
            return

        latest_message = conversation_memory.messages[-1]

        if latest_message.role == USER_ROLE:
            self._scores.user_engagement = self._update_ewma(self._scores.user_engagement, sentiment.score)
        elif latest_message.role == PARTNER_ROLE:
            self._scores.partner_engagement = self._update_ewma(self._scores.partner_engagement, sentiment.score)

        self._update_talk_share(conversation_memory.messages)
        
    def get_scores(self) -> ConversationScores:
        return self._scores

    def _update_ewma(self, previous: float, new: float) -> float:
        return new if previous == 0.0 else self.alpha * new + (1 - self.alpha) * previous

    def _update_talk_share(self, messages: List[Message]) -> None:
        total = sum(len(msg.content) for msg in messages)
        user = sum(len(msg.content) for msg in messages if msg.role == USER_ROLE)
        self._scores.user_talk_share = user / total if total > 0 else 0.0
        

# === RealtimeSentimentalAnalyzer ===

class RealtimeSentimentalAnalyzer:
    """
    실시간 감정 분석을 수행하는 클래스.
    """
    PROMPT_NAME = "score/sentimental_analysis"
    PROMPT_VER = 1
    LLM_MODEL = "gpt-4.1-nano"

    @classmethod
    def _generate_prompt(cls, conversation_memory: memory.ConversationMemory) -> List[Dict[str, str]]:
        system_message = {
            "role": "system",
            "content": load_prompt(cls.PROMPT_NAME, "system", cls.PROMPT_VER)
        }
        user_message = {
            "role": "user",
            "content": '\n---\n'.join([
                conversation_memory.prompt_messages(n_messages=5),
                f"### 🔍 분석할 메시지:\n{conversation_memory.messages[-1].to_prompt()}"
            ])
        }
        return [system_message, user_message]

    @classmethod
    async def do(cls, conversation_memory: memory.ConversationMemory, n_consistency: int = 3) -> MessageSentimentScore:
        prompt_messages = cls._generate_prompt(conversation_memory)

        async def single_run():
            try:
                response = await clients.async_openai_client.beta.chat.completions.parse(
                    messages=prompt_messages,
                    model=cls.LLM_MODEL,
                    response_format=MessageSentimentScore
                )
                return response.choices[0].message.parsed
            except Exception as e:
                log.error(f"Exception in single_run: {e}")
                return None

        results = await asyncio.gather(*(single_run() for _ in range(n_consistency)))
        scores = [r.score for r in results if isinstance(r, MessageSentimentScore)]

        avg_score = int(round(sum(scores) / len(scores)))
        output = MessageSentimentScore(score=avg_score)

        return output
    
# === Functions ===

async def update_conversation_scores_pipeline(
    conversation_scorer: ConversationScorer,
    conversation_memory: memory.ConversationMemory,
) -> None:
    """
    대화 메모리의 메시지에 대한 감정 점수를 업데이트합니다.
    
    Args:
        conversation_memory (ConversationMemory): 대화 메모리 객체.
    """
    sentiment_analysis_output = await RealtimeSentimentalAnalyzer.do(
        conversation_memory=conversation_memory
    )
    
    conversation_scorer.update(
        conversation_memory=conversation_memory,
        sentiment=sentiment_analysis_output
    )