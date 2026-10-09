"""
File: email_delivery_service.py
Purpose: Deliver FORGE authentication emails through configured SMTP.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.services.email_template_service import EmailTemplateService


class EmailDeliveryService:
    """Send passwordless sign-in emails using configured SMTP."""

    def __init__(self) -> None:
        api_root = Path(__file__).resolve().parents[2]

        with (api_root / "config" / "email.json").open(
            "r",
            encoding="utf-8",
        ) as configuration_file:
            configuration = json.load(configuration_file)

        self._smtp = configuration["smtp"]
        self._expiration_minutes = int(
            configuration["magic_link"]["expiration_minutes"]
        )
        self._template_service = EmailTemplateService()

        if self._expiration_minutes <= 0:
            raise ValueError(
                "Magic-link expiration must be greater than zero."
            )

    def send_magic_link(
        self,
        recipient: str,
        verification_url: str,
    ) -> None:
        """Send the secure FORGE sign-in link."""

        host = self._smtp["host"].strip()
        sender = self._smtp["sender"].strip()
        display_name = self._smtp.get("display_name", "FORGE").strip()

        if not host or not sender:
            raise RuntimeError(
                "SMTP host and sender must be configured in email.json."
            )

        if not recipient.strip() or not verification_url.strip():
            raise ValueError(
                "Recipient and verification URL are required."
            )

        html_body = self._template_service.render(
            "email/messages/magic_link.html",
            {
                "MAGIC_LINK": verification_url,
                "EXPIRATION_MINUTES": self._expiration_minutes,
            },
        )

        text_body = (
            "You requested access to FORGE.\n\n"
            "Use the secure link below to verify your email "
            "address and sign in.\n\n"
            f"{verification_url}\n\n"
            f"This link expires in {self._expiration_minutes} minutes.\n\n"
            "If you did not request this link, ignore this email."
        )

        message = EmailMessage()
        message["Subject"] = "Your secure FORGE sign-in link"
        message["From"] = f"{display_name} <{sender}>"
        message["To"] = recipient
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")
        html_part = message.get_payload()[-1]
        assets_dir = Path(__file__).resolve().parents[1] / "assets" / "email"
        html_part.add_related(
            (assets_dir / "forge-logo.png").read_bytes(),
            maintype="image", subtype="png", cid="<forge-logo>",
            filename="forge-logo.png", disposition="inline",
        )
        html_part.add_related(
            (assets_dir / "collins-logo.png").read_bytes(),
            maintype="image", subtype="png", cid="<collins-logo>",
            filename="collins-logo.png", disposition="inline",
        )
        port = int(self._smtp["port"])
        timeout = int(self._smtp.get("timeout_seconds", 15))
        use_starttls = bool(self._smtp.get("use_starttls", False))
        username = self._smtp.get("username", "").strip()

        with smtplib.SMTP(
            host,
            port,
            timeout=timeout,
        ) as smtp:
            smtp.ehlo()

            if use_starttls:
                smtp.starttls()
                smtp.ehlo()

            if username:
                password = os.environ.get("FORGE_SMTP_PASSWORD", "")
                if not password:
                    raise RuntimeError(
                        "FORGE_SMTP_PASSWORD is required when "
                        "SMTP authentication is enabled."
                    )
                smtp.login(username, password)

            smtp.send_message(message)
