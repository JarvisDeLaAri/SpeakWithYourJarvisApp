"""OpenClaw LLM integration for Pipecat.

Uses OpenClaw's Chat Completions API (OpenAI-compatible).
Routes to main session = real Jarvis with full memory + personality.
"""

from loguru import logger
from pipecat.services.openai.llm import OpenAILLMService


def create_openclaw_llm(openclaw_url: str, openclaw_token: str) -> OpenAILLMService:
    """Create an OpenAI-compatible LLM service pointing at OpenClaw gateway.

    Args:
        openclaw_url: Full URL to OpenClaw gateway (e.g. http://127.0.0.1:28789)
        openclaw_token: Gateway authentication token

    Returns:
        OpenAILLMService configured for OpenClaw
    """
    # OpenClaw's Chat Completions endpoint is OpenAI-compatible
    base_url = f"{openclaw_url}/v1"

    logger.info(f"OpenClaw LLM: connecting to {openclaw_url}")

    return OpenAILLMService(
        api_key=openclaw_token,
        base_url=base_url,
        model="passthrough",  # OpenClaw uses its own model routing
    )
