"""LLM completion via litellm — supports any provider with a single call."""

from collections.abc import Generator

import litellm


def complete(model: str, system: str, messages: list) -> str:
    """Call any LLM and return the response text.

    Args:
        model: litellm model string, e.g. "anthropic/claude-opus-4-6" or
               "openai/gpt-4o". The matching API key must be set as an
               environment variable (ANTHROPIC_API_KEY, OPENAI_API_KEY, …).
        system: System prompt text.
        messages: List of objects with .role and .content attributes.

    Returns:
        The model's reply as a plain string.
    """
    api_messages = [{"role": "system", "content": system}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]
    response = litellm.completion(model=model, messages=api_messages, max_tokens=2048)
    return response.choices[0].message.content


def stream_complete(
    model: str, system: str, messages: list
) -> Generator[str, None, None]:
    """Call any LLM with streaming and yield text chunks as they arrive.

    Args:
        model: litellm model string (same format as ``complete``).
        system: System prompt text.
        messages: List of objects with .role and .content attributes.

    Yields:
        Non-empty text chunks from the model's streamed response.
    """
    api_messages = [{"role": "system", "content": system}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]
    response = litellm.completion(
        model=model, messages=api_messages, max_tokens=2048, stream=True
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
