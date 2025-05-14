import json
import pathlib

from ..models import conversation_models

from ..models import (
    conversation_models
)

ADVICE_METADATAS_PATH = pathlib.Path(__file__).parent.parent / "advice_metadatas.json"

ADVICE_METADATAS = json.loads(
    ADVICE_METADATAS_PATH.read_text(encoding="utf-8")
)

def is_advice_exists(
    advice_id: str
) -> bool:
    """
    Checks if the advice ID exists in the metadata.
    """
    return advice_id in ADVICE_METADATAS


def get_advice_metadata(
    advice_ids: list[str]
) -> conversation_models.BreaktimeAdviceRecommendation:
    """
    Returns the metadata for a specific advice ID.
    """
    output = conversation_models.BreaktimeAdviceRecommendation(
        recommendation=[]
    )
    for id in advice_ids:
        if id not in ADVICE_METADATAS:
            continue
        
        preview_element = conversation_models.BreaktimeAdviceMetadata(
            advice_id=id,
            emoji=ADVICE_METADATAS[id]["emoji"],
            title=ADVICE_METADATAS[id]["title"],
            description=ADVICE_METADATAS[id]["description"],
        )
        output.recommendation.append(preview_element)
        
    return output