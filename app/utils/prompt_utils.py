import os
import pathlib
from typing import Literal

PROMPT_DIR = pathlib.Path(__file__).parent / "prompts"

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