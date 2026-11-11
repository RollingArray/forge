#!/usr/bin/env python3
"""Create isolated FORGE E2E sessions without an HTTP bootstrap endpoint."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

api_root = Path(sys.argv[1]).resolve()
output_path = Path(sys.argv[2]).resolve()

if not (api_root / "app" / "main.py").is_file():
    raise SystemExit(f"Invalid candidate API directory: {api_root}")

sys.path.insert(0, str(api_root))
os.chdir(api_root)

from app.core.token_service import TokenService
from app.models.auth_session_model import AuthSessionModel
from app.models.auth_user_model import AuthUserModel
from app.services.json_user_repository import JsonUserRepository

identities = {
    "owner": ("forge.owner@collins.com", "FORGE E2E Owner"),
    "contributor": ("forge.contributor@collins.com", "FORGE E2E Contributor"),
    "viewer": ("forge.viewer@collins.com", "FORGE E2E Viewer"),
}

repository = JsonUserRepository()
token_service = TokenService()
sessions = {}

for identity, (email, display_name) in identities.items():
    user = repository.get_by_email(email)
    if user is None:
        user = repository.create(email=email, display_name=display_name)

    token = token_service.create_access_token(user)
    session = AuthSessionModel(
        access_token=token,
        token_type="Bearer",
        user=AuthUserModel(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            employee_id=user.employee_id,
            profile=user.profile,
        ),
    )
    sessions[identity] = session.model_dump(mode="json", by_alias=True)

output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(
    json.dumps(sessions, indent=2) + "\n",
    encoding="utf-8",
)
output_path.chmod(0o600)

print(f"Created {len(sessions)} isolated E2E sessions.")
print(f"Session file: {output_path}")
