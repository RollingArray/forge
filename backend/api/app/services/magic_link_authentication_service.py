"""
File: magic_link_authentication_service.py
Purpose: Orchestrate passwordless FORGE sign-in.
"""

import json
import os
from pathlib import Path
from urllib.parse import urlencode

from app.constants.activity import ActivityType
from app.core.authentication_errors import DomainNotAllowedError
from app.core.authentication_settings import load_authentication_configuration
from app.core.token_service import TokenService
from app.interfaces.auth_session import AuthSession
from app.services.activity_service import ActivityService
from app.services.ad_profile_service import ADProfileLookupError, ADProfileService
from app.services.email_delivery_service import EmailDeliveryService
from app.services.json_user_repository import JsonUserRepository
from app.services.magic_link_store import MagicLinkStore


class MagicLinkAuthenticationService:
    """Handle email-link requests and authenticated link verification."""

    def __init__(self) -> None:
        api_root = Path(__file__).resolve().parents[2]
        with (api_root / "config" / "email.json").open(
            "r", encoding="utf-8"
        ) as file:
            email_configuration = json.load(file)

        link_config = email_configuration["magic_link"]
        self._frontend_base_url = os.environ.get(
            "FORGE_FRONTEND_BASE_URL",
            link_config.get("frontend_base_url", ""),
        ).strip().rstrip("/")

        if not self._frontend_base_url.startswith(("http://", "https://")):
            raise ValueError("Configure a valid FORGE frontend base URL.")

        self._token_store = MagicLinkStore(
            expiration_minutes=int(link_config["expiration_minutes"])
        )
        self._email_delivery = EmailDeliveryService()
        self._ad_profile_service = ADProfileService()
        self._user_repository = JsonUserRepository()
        self._token_service = TokenService()
        self._activity_service = ActivityService()
        self._allowed_domains = {
            domain.strip().lower()
            for domain in load_authentication_configuration().allowed_domains
        }

    def request_magic_link(self, email: str) -> None:
        """Email a sign-in link to an allowed organization address."""
        normalized_email = email.strip().lower()

        if (
            not normalized_email
            or normalized_email.count("@") != 1
            or not normalized_email.split("@", 1)[0]
        ):
            raise DomainNotAllowedError("A valid organization email is required.")

        domain = normalized_email.rsplit("@", 1)[1]
        if domain not in self._allowed_domains:
            raise DomainNotAllowedError(
                f"Email domain '{domain}' is not allowed."
            )

        token, _ = self._token_store.create(normalized_email)
        verification_url = (
            f"{self._frontend_base_url}/login/verify?"
            f"{urlencode({'token': token})}"
        )

        try:
            self._email_delivery.send_magic_link(
                recipient=normalized_email,
                verification_url=verification_url,
            )
        except Exception:
            self._token_store.revoke(token)
            raise

    def verify_magic_link(self, token: str) -> AuthSession:
        """Verify a link, enrich the user, then issue an access token."""
        email = self._token_store.get_email(token)
        if email is None:
            raise ValueError("This sign-in link is invalid or has expired.")

        # Do not consume the link until the corporate lookup succeeds.
        try:
            profile = self._ad_profile_service.get_profile(email)
        except ADProfileLookupError:
            raise

        # Atomic consumption ensures concurrent verifications issue one session.
        consumed_email = self._token_store.consume(token)
        if consumed_email is None or consumed_email != email:
            raise ValueError("This sign-in link has already been used or expired.")

        user = self._user_repository.get_by_email(email)
        if user is None:
            user = self._user_repository.create(
                email=email,
                display_name=profile.full_name,
            )

        user = self._user_repository.update_profile(
            email=email,
            profile=profile.model_dump(by_alias=True),
        )

        access_token = self._token_service.create_access_token(user)
        self._activity_service.record(
            owner_user_id=user.user_id,
            actor_user_id=user.user_id,
            activity_type=ActivityType.USER_SIGNED_IN,
            title="Signed in to FORGE",
            description="User verified their email sign-in link",
        )

        return AuthSession(
            access_token=access_token,
            token_type="Bearer",
            user=user,
        )
