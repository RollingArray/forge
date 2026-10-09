"""
File: email_template_service.py
Purpose: Render reusable FORGE HTML email templates.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


class EmailTemplateService:
    """Render HTML email templates using a shared template environment."""

    def __init__(self) -> None:
        template_root = Path(__file__).resolve().parents[1] / "templates"
        self._environment = Environment(
            loader=FileSystemLoader(str(template_root)),
            autoescape=select_autoescape(
                enabled_extensions=("html", "xml"),
                default_for_string=True,
            ),
        )

    def render(self, template_name: str, context: dict) -> str:
        """Render an email template with its message-specific context."""
        template = self._environment.get_template(template_name)
        return template.render(**context)
