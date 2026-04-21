"""
Unified LLM client for calling MiniMax via Anthropic-compatible API.
"""

import time
import anthropic
import config


def call_llm(prompt: str, system: str = "", max_tokens: int = 1024, stream: bool = False):
    """
    Call MiniMax API via Anthropic-compatible SDK.

    Args:
        prompt: The user prompt
        system: Optional system message
        max_tokens: Maximum tokens to generate
        stream: Whether to stream the response

    Returns:
        Response object (streaming or complete)
    """
    client = anthropic.Anthropic(
        auth_token=config.MINIMAX_API_KEY,
        base_url=config.MINIMAX_BASE_URL,
    )

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=config.MINIMAX_MODEL,
                max_tokens=max_tokens,
                messages=messages,
                stream=stream,
            )
            return response
        except Exception as e:
            if attempt < 2:
                time.sleep(2**attempt)
                continue
            raise e


def extract_text_from_response(response) -> str:
    """
    Extract text content from a non-streaming response.

    Args:
        response: The response from call_llm with stream=False

    Returns:
        Extracted text string
    """
    for block in response.content:
        if block.type == "text" and getattr(block, "text", None):
            return block.text
    # Fallback: return thinking content if no text block
    for block in response.content:
        if block.type == "thinking" and getattr(block, "thinking", None):
            return block.thinking[:500]
    return "[No response content]"
