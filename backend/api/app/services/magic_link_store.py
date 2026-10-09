"""
File: magic_link_store.py
Purpose: Secure, single-use magic-link token lifecycle.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


@dataclass(frozen=True)
class MagicLinkRecord:
    """Metadata associated with a hashed magic-link token."""

    email: str
    expires_at: datetime


class MagicLinkStore:
    """Thread-safe in-memory store for single-use magic-link tokens."""

    def __init__(self, expiration_minutes: int = 5) -> None:
        if expiration_minutes <= 0:
            raise ValueError("Expiration must be greater than zero.")

        self._expiration = timedelta(minutes=expiration_minutes)
        self._records: dict[str, MagicLinkRecord] = {}
        self._lock = Lock()

    def create(self, email: str) -> tuple[str, datetime]:
        """Create a random token and store only its hash."""
        normalized_email = email.strip().lower()

        if not normalized_email or "@" not in normalized_email:
            raise ValueError("A valid email address is required.")

        token = secrets.token_urlsafe(32)
        token_hash = self._hash(token)
        expires_at = datetime.now(timezone.utc) + self._expiration

        with self._lock:
            self._remove_expired_locked(datetime.now(timezone.utc))
            self._records[token_hash] = MagicLinkRecord(
                email=normalized_email,
                expires_at=expires_at,
            )

        return token, expires_at

    def revoke(self, token: str) -> None:
        """Invalidate a token that could not be delivered."""
        if not token:
            return

        with self._lock:
            self._records.pop(self._hash(token), None)

    def get_email(self, token: str) -> str | None:
        """Check a token without consuming it."""
        if not token or not token.strip():
            return None

        token_hash = self._hash(token)

        with self._lock:
            record = self._records.get(token_hash)
            if record is None:
                return None

            if record.expires_at <= datetime.now(timezone.utc):
                del self._records[token_hash]
                return None

            return record.email

    def consume(self, token: str) -> str | None:
        """Consume a valid token once and return its associated email."""
        if not token or not token.strip():
            return None

        token_hash = self._hash(token)

        with self._lock:
            record = self._records.get(token_hash)

            if record is None:
                return None

            now = datetime.now(timezone.utc)

            if record.expires_at <= now:
                del self._records[token_hash]
                return None

            # Removal occurs under the same lock as lookup.
            del self._records[token_hash]
            return record.email

    def _remove_expired_locked(self, now: datetime) -> None:
        expired_hashes = [
            token_hash
            for token_hash, record in self._records.items()
            if record.expires_at <= now
        ]

        for token_hash in expired_hashes:
            del self._records[token_hash]

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
