import json
import pathlib

ADVICE_METADATAS_PATH = pathlib.Path(__file__).parent.parent / "advice_metadatas.json"

ADVICE_METADATAS = json.loads(
    ADVICE_METADATAS_PATH.read_text(encoding="utf-8")
)

def get_advice_metadata_prompt() -> str:
    """
    Returns a prompt string listing all advice metadata in a clear, LLM-friendly format.
    """
    prompt = ["아래는 제공가능한 조언의 정보입니다. ID, 제목, 설명으로 구성되어 있습니다.\n"]
    for advice_id, metadata in ADVICE_METADATAS.items():
        prompt.append(
            f"[ID: {advice_id}]\n제목: {metadata.get('title', '')}\n설명: {metadata.get('description', '')}\n"
        )
    return "\n".join(prompt)