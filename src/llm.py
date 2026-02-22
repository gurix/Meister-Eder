"""LLM completion via litellm — supports any provider with a single call."""

from collections.abc import Generator

import litellm


async def acomplete(
    model: str,
    system: str,
    messages: list,
    thinking_budget: int | None = None,
) -> str:
    """Call any LLM asynchronously and return the response text.

    This is the async equivalent of ``complete()`` — use this from async
    handlers (e.g. Chainlit's ``@cl.on_message``) to avoid blocking the
    event loop and losing framework context variables.

    Args:
        model: litellm model string, e.g. "anthropic/claude-opus-4-6".
        system: System prompt text.
        messages: List of objects with .role and .content attributes.
        thinking_budget: When set, enables extended thinking (Anthropic models
            only). See ``complete()`` for details.

    Returns:
        The model's reply as a plain string.
    """
    api_messages = [{"role": "system", "content": system}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]

    kwargs: dict = {"model": model, "messages": api_messages, "max_tokens": 2048}
    if thinking_budget is not None:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        kwargs["max_tokens"] = thinking_budget + 4096

    response = await litellm.acompletion(**kwargs)
    return response.choices[0].message.content


def complete(
    model: str,
    system: str,
    messages: list,
    thinking_budget: int | None = None,
) -> str:
    """Call any LLM and return the response text.

    Args:
        model: litellm model string, e.g. "anthropic/claude-opus-4-6" or
               "openai/gpt-4o". The matching API key must be set as an
               environment variable (ANTHROPIC_API_KEY, OPENAI_API_KEY, …).
        system: System prompt text.
        messages: List of objects with .role and .content attributes.
        thinking_budget: When set, enables extended thinking (Anthropic models
            only). The value is the token budget for the thinking phase; the
            final ``max_tokens`` is set to ``thinking_budget + 4096`` so the
            model has enough room to both think and reply.

    Returns:
        The model's reply as a plain string.
    """
    api_messages = [{"role": "system", "content": system}]
    api_messages += [{"role": m.role, "content": m.content} for m in messages]

    kwargs: dict = {"model": model, "messages": api_messages, "max_tokens": 2048}
    if thinking_budget is not None:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        # max_tokens must exceed budget_tokens or the API returns an error.
        kwargs["max_tokens"] = thinking_budget + 4096

    response = litellm.completion(**kwargs)
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
