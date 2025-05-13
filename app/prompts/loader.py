import os
from typing import Literal


CHAT_PROMPT_FORMAT = "{prompt_name}_{prompt_type}_v{prompt_ver}.txt"


def load_prompt(
    prompt_name: str,
    prompt_type: Literal['system', 'user'],
    prompt_ver: int = 1
) -> str:
    """Load a prompt from a file."""
    prompt_file = CHAT_PROMPT_FORMAT.format(
        prompt_name=prompt_name,
        prompt_type=prompt_type,
        prompt_ver=prompt_ver
    )
    prompt_path = os.path.join(os.path.dirname(__file__), prompt_file)

    with open(prompt_path, 'r', encoding='utf-8') as file:
        return file.read()
    
    