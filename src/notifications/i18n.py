"""i18n support for parent confirmation emails.

German is the canonical source language (de.yaml).  For any other language
the German labels are translated on-demand via an LLM call and cached
in-process for the lifetime of the server — no static translation files to
maintain, any language the parent writes in is supported automatically.
"""

import json
import logging
from pathlib import Path

import litellm
import yaml

logger = logging.getLogger(__name__)

_I18N_DIR = Path(__file__).parent / "i18n"

# In-memory translation cache keyed by language code.
_cache: dict[str, dict] = {}

# Pure data values that must never be sent to the LLM for translation.
_PASSTHROUGH_KEYS = {"reg_fee_amount", "deposit_amount"}

_SYSTEM_PROMPT = """\
You are a translation assistant for a Swiss playgroup registration system.
Translate the following JSON label strings from German into {language}.

Rules:
- Return ONLY a valid JSON object with the exact same keys and structure.
- Preserve all {{placeholder}} variables exactly as-is (e.g. {{name}}).
- Preserve all HTML tags and entities exactly (e.g. <strong>, &nbsp;).
- Keep proper nouns untranslated: "Spielgruppe Pumuckl", "Familienverein Fällanden".
- Do not include any explanation or text outside the JSON."""


def get_strings(language: str, model: str) -> dict:
    """Return the label string table for *language*.

    For German, loads directly from de.yaml (no LLM call).
    For all other languages, translates the German labels via LLM and caches
    the result in memory.  Falls back to German if the LLM call fails.
    """
    if language == "de":
        return _load_german()

    if language in _cache:
        return _cache[language]

    german = _load_german()
    translated = _translate(german, language, model)
    _cache[language] = translated
    return translated


def clear_cache() -> None:
    """Evict all cached translations (intended for use in tests)."""
    _cache.clear()


def _load_german() -> dict:
    with (_I18N_DIR / "de.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _translate(german: dict, language: str, model: str) -> dict:
    """Translate the German label dict into *language* via LLM.

    Returns the German dict unchanged if the LLM call fails or returns
    malformed JSON.
    """
    passthrough = {k: german[k] for k in _PASSTHROUGH_KEYS if k in german}
    to_translate = {k: v for k, v in german.items() if k not in _PASSTHROUGH_KEYS}

    system = _SYSTEM_PROMPT.format(language=language)
    payload = json.dumps(to_translate, ensure_ascii=False, indent=2)

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": payload},
            ],
            max_tokens=2048,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences that some models add
        if raw.startswith("```"):
            raw = raw[raw.index("\n") + 1 :]
            raw = raw[: raw.rfind("```")]

        translated: dict = json.loads(raw)
        translated.update(passthrough)
        return translated

    except Exception:
        logger.exception(
            "Failed to translate email labels into %s — falling back to German", language
        )
        return german
