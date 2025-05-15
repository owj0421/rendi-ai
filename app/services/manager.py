from typing import Dict
from ..core import logger
from .session_services.memory import ConversationMemory
from .session_services.score import ConversationScorer

log = logger.get_logger(__name__)

# === ConversationManager ===

class ConversationManager:
    """
    대화 관리 클래스.
    대화 메모리와 스코어러를 관리하며, 대화의 초기화, 삭제, 조회 기능을 제공합니다.
    """

    def __init__(self) -> None:
        # 대화 ID별로 ConversationMemory와 ConversationScorer를 저장하는 딕셔너리
        self._conversation_memories: Dict[str, ConversationMemory] = {}
        self._conversation_scorers: Dict[str, ConversationScorer] = {}

    def is_conversation_exists(self, conversation_id: str) -> bool:
        """
        주어진 대화 ID가 존재하는지 확인합니다.

        Args:
            conversation_id (str): 확인할 대화 ID.

        Returns:
            bool: 대화가 존재하면 True, 그렇지 않으면 False.
        """
        return conversation_id in self._conversation_memories

    def init_conversation(self, conversation_id: str) -> None:
        """
        새로운 대화를 초기화하거나 기존 대화를 재초기화합니다.

        Args:
            conversation_id (str): 초기화할 대화 ID.

        Raises:
            ValueError: 대화 ID가 유효하지 않은 경우.
        """
        if not conversation_id:
            log.error("유효하지 않은 대화 ID입니다.")
            raise ValueError("대화 ID는 비어 있을 수 없습니다.")

        if self.is_conversation_exists(conversation_id):
            log.info(f"대화 ID {conversation_id}가 이미 존재합니다. 재초기화합니다.")
            self.delete_conversation(conversation_id)

        # ConversationMemory와 ConversationScorer를 초기화
        self._conversation_memories[conversation_id] = ConversationMemory()
        self._conversation_scorers[conversation_id] = ConversationScorer()
        log.info(f"대화가 초기화되었습니다. ID: {conversation_id}")

    def delete_conversation(self, conversation_id: str) -> None:
        """
        주어진 대화 ID에 해당하는 대화와 관련 데이터를 삭제합니다.

        Args:
            conversation_id (str): 삭제할 대화 ID.
        """
        removed = False

        # 대화 메모리 삭제
        if self._conversation_memories.pop(conversation_id, None) is not None:
            removed = True

        # 대화 스코어러 삭제
        if self._conversation_scorers.pop(conversation_id, None) is not None:
            removed = True

        if removed:
            log.info(f"대화가 삭제되었습니다. ID: {conversation_id}")
        else:
            log.warning(f"존재하지 않는 대화 ID를 삭제하려고 시도했습니다. ID: {conversation_id}")

    def get_conversation_memory(self, conversation_id: str) -> ConversationMemory:
        """
        주어진 대화 ID에 해당하는 대화 메모리를 반환합니다.

        Args:
            conversation_id (str): 조회할 대화 ID.

        Returns:
            ConversationMemory: 대화 메모리 객체.

        Raises:
            ValueError: 대화 메모리가 존재하지 않는 경우.
        """
        memory = self._conversation_memories.get(conversation_id)
        if memory is None:
            log.error(f"대화 메모리가 존재하지 않습니다. ID: {conversation_id}")
            raise ValueError(f"대화 메모리가 존재하지 않습니다. ID: {conversation_id}")
        return memory

    def get_conversation_scorer(self, conversation_id: str) -> ConversationScorer:
        """
        주어진 대화 ID에 해당하는 대화 스코어러를 반환합니다.

        Args:
            conversation_id (str): 조회할 대화 ID.

        Returns:
            ConversationScorer: 대화 스코어러 객체.

        Raises:
            ValueError: 대화 스코어러가 존재하지 않는 경우.
        """
        scorer = self._conversation_scorers.get(conversation_id)
        if scorer is None:
            log.error(f"대화 스코어러가 존재하지 않습니다. ID: {conversation_id}")
            raise ValueError(f"대화 스코어러가 존재하지 않습니다. ID: {conversation_id}")
        return scorer


# 싱글톤 패턴으로 ConversationManager 인스턴스 생성
conversation_manager = ConversationManager()


def get_conversation_manager() -> ConversationManager:
    """
    FastAPI 의존성 주입을 위한 ConversationManager 반환 함수.

    Returns:
        ConversationManager: 싱글톤 ConversationManager 인스턴스.
    """
    return conversation_manager
