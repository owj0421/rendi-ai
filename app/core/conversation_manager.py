from typing import Dict

from . import logger
from .conversation_memory import ConversationMemory

class ConversationManager:
    def __init__(self) -> None:
        self._conversation_memories: Dict[str, ConversationMemory] = {}

    def is_conversation_exists(self, conversation_id: str) -> bool:
        return conversation_id in self._conversation_memories

    def init_conversation(self, conversation_id: str) -> None:
        if self.is_conversation_exists(conversation_id):
            raise ValueError(f"Conversation with ID {conversation_id} already exists.")
        self._conversation_memories[conversation_id] = ConversationMemory()
        logger.logger.info(f"Conversation initialized with ID: {conversation_id}")

    def delete_conversation(self, conversation_id: str) -> None:
        if not self.is_conversation_exists(conversation_id):
            raise ValueError(f"Conversation memory with ID {conversation_id} does not exist.")
        del self._conversation_memories[conversation_id]
        logger.logger.info(f"Conversation deleted with ID: {conversation_id}")

    def get_conversation_memory(self, conversation_id: str) -> ConversationMemory:
        if not self.is_conversation_exists(conversation_id):
            raise ValueError(f"Conversation memory with ID {conversation_id} does not exist.")
        return self._conversation_memories[conversation_id]

conversation_manager = ConversationManager()