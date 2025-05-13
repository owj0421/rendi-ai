from openai import AsyncOpenAI
from google.cloud import speech

from .config import (
    settings
)


async_openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY
)
# google_speech_client = speech.SpeechAsyncClient(
#     credentials=GOOGLE_API_KEY
# )
