"""Jinja2 template renderer for email notifications."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=["html.j2"]),
    keep_trailing_newline=True,
)


def render_template(name: str, context: dict) -> str:
    """Render *name* (relative to the templates directory) with *context*."""
    return _env.get_template(name).render(**context)
