import os
import pathlib
from typing import Literal

from ..core.conversation_elements import Message

PROMPT_DIR = pathlib.Path(__file__).parent.parent / "prompts"

CHAT_PROMPT_FORMAT = "{prompt_name}_{prompt_type}_v{prompt_ver}.txt"


def load_prompt(
    prompt_name: str,
    prompt_type: Literal['system', 'user'],
    prompt_ver: int = 1
) -> str:
    """Load a prompt from a file."""
    prompt_filename = CHAT_PROMPT_FORMAT.format(
        prompt_name=prompt_name,
        prompt_type=prompt_type,
        prompt_ver=prompt_ver
    )
    prompt_path = os.path.join(PROMPT_DIR, prompt_filename)

    with open(prompt_path, 'r', encoding='utf-8') as file:
        return file.read()


    
def make_partner_memory_prompt(
    partner_memory: dict[str, list[str]]
):
    memory_section = "아래는 '파트너'에 대한 요약입니다.\n"
    memory_section += "----------------------\n"
    for category, items in partner_memory.items():
        memory_section += f"{category}:\n"
        for item in items:
            memory_section += f"  - {item}\n"
    memory_section += "----------------------\n\n"
    
    return memory_section


def make_message_prompt(
    messages: list[Message]
):
    """Make a standard message prompt."""
    if not messages:
        return ""
    
    message_section = "아래는 '나'와 '파트너'의 최근 대화 내역입니다. (시간 순)\n"
    message_section += "----------------------\n"
    message_section += "\n".join([msg.to_prompt() for msg in messages])
    message_section += "\n----------------------\n\n"

    return message_section
  
    
def make_last_target_message_prompt(
    messages: list[Message]
):
    """Make the last message target prompt."""
    if not messages:
        return ""
    
    last_message = messages[-1]
    context_messages = messages[:-1]

    context_section = ""
    if context_messages:
        context_section = (
            "아래는 '나'와 '파트너'의 최근 대화 내역입니다. (시간 순)\n"
            "----------------------\n"
            f'{"\n".join([msg.to_prompt() for msg in context_messages])}'
            "\n----------------------\n\n"
        )
    
    target_section = (
        "위 대화 이후, 파트너가 아래와 같이 발화했습니다.\n"
        "이 발화에 대해 언급한 작업을 수행해 주세요.\n"
        "----------------------\n"
        f"{last_message.to_prompt()}"
        "\n----------------------\n\n"
    )

    return context_section + target_section


def make_advice_metadata_prompt(
    advice_metadata: dict[str, str]
):
    """Make the advice metadata prompt."""
    advice_section = "아래는 '나'가 소개팅 도중 요청한 조언 정보입니다.\n"
    advice_section += "----------------------\n"
    advice_section += "\n".join([f"{key}: {value}" for key, value in advice_metadata.items()])
    advice_section += "\n----------------------\n\n"

    return advice_section


def make_advice_metadata_list_prompt(
    advice_metadata: dict[str, dict[str, str]]
):
    """Make the advice metadata prompt."""
    advice_section = "아래는 '나'에게 제공가능한 조언의 목록입니다.\n"
    advice_section += "----------------------\n"
    for advice_id, metadata in advice_metadata.items():
        advice_section += f"ID: {advice_id}\n"
        advice_section += "\n".join([f"- {key}: {value}" for key, value in metadata.items()])
        advice_section += "\n\n"
    advice_section += "\n----------------------\n\n"

    return advice_section