import os
from agents import OpenAIChatCompletionsModel, AsyncOpenAI
from app.core.config import settings

def get_gemini_model():
    """
    Initializes and returns an OpenAIChatCompletionsModel instance
    pointing to Google's OpenAI-compatible Gemini endpoint.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY in environment or .env file.")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.GEMINI_BASE_URL,
        max_retries=settings.GEMINI_MAX_RETRIES
    )

    return OpenAIChatCompletionsModel(
        model=settings.GEMINI_MODEL,
        openai_client=client
    )
