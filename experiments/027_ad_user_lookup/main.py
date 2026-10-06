"""
File: main.py
Purpose: Pure-Python Active Directory user lookup experiment.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from ldap3 import (
    ALL,
    Connection,
    Server,
)
from ldap3.utils.conv import escape_filter_chars
from pydantic import BaseModel


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("ADUserExperiment")


# ============================================================
# LDAP CONFIGURATION
# ============================================================

LDAP_SERVER = "user.adxrt.com"

LDAP_SEARCH_BASE = (
    "OU=Staged,"
    "OU=Employees,"
    "OU=.Users,"
    "DC=user,"
    "DC=adxrt,"
    "DC=com"
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="FORGE AD User Lookup Experiment",
    description=(
        "Pure-Python Active Directory lookup using ldap3."
    ),
    version="0.1.0",
)


# ============================================================
# RESPONSE MODEL
# ============================================================

class ADUser(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    sam_account_name: Optional[str] = None
    user_principal_name: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    employee_id: Optional[str] = None
    distinguished_name: Optional[str] = None
    manager: Optional[str] = None


# ============================================================
# LDAP HELPERS
# ============================================================

def get_attribute(
    entry,
    attribute: str,
) -> Optional[str]:
    """Safely retrieve a single LDAP attribute."""

    try:
        value = getattr(entry, attribute, None)

        if value is None:
            return None

        return str(value.value) if value.value is not None else None

    except Exception:
        logger.exception(
            "Unable to read LDAP attribute: %s",
            attribute,
        )
        return None


# ============================================================
# LDAP SEARCH
# ============================================================

def search_user_by_email(
    email: str,
) -> list[ADUser]:
    """Search Active Directory for a user."""

    email = email.strip()

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Email address is required.",
        )

    safe_email = escape_filter_chars(email)

    logger.info(
        "Searching AD for: %s",
        email,
    )

    server = Server(
        LDAP_SERVER,
        get_info=ALL,
    )

    connection = Connection(
        server,
        auto_bind=False,
    )

    try:
        # ----------------------------------------------------
        # Open LDAP connection.
        #
        # Authentication will be added separately once the
        # supported authentication mechanism is confirmed.
        # ----------------------------------------------------

        connection.open()

        logger.info(
            "LDAP connection opened: %s",
            LDAP_SERVER,
        )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        search_filter = (
            "(&(objectCategory=person)"
            "(objectClass=user)"
            "(|"
            f"(mail={safe_email})"
            f"(userPrincipalName={safe_email})"
            f"(sAMAccountName={safe_email})"
            "))"
        )

        logger.info(
            "LDAP search base: %s",
            LDAP_SEARCH_BASE,
        )

        connection.search(
            search_base=LDAP_SEARCH_BASE,
            search_filter=search_filter,
            attributes=[
                "mail",
                "displayName",
                "givenName",
                "sn",
                "sAMAccountName",
                "userPrincipalName",
                "title",
                "department",
                "telephoneNumber",
                "mobile",
                "employeeID",
                "distinguishedName",
                "manager",
            ],
        )

        logger.info(
            "LDAP search completed. Results found: %s",
            len(connection.entries),
        )

        users: list[ADUser] = []

        for entry in connection.entries:
            users.append(
                ADUser(
                    email=get_attribute(
                        entry,
                        "mail",
                    ),
                    display_name=get_attribute(
                        entry,
                        "displayName",
                    ),
                    first_name=get_attribute(
                        entry,
                        "givenName",
                    ),
                    last_name=get_attribute(
                        entry,
                        "sn",
                    ),
                    sam_account_name=get_attribute(
                        entry,
                        "sAMAccountName",
                    ),
                    user_principal_name=get_attribute(
                        entry,
                        "userPrincipalName",
                    ),
                    title=get_attribute(
                        entry,
                        "title",
                    ),
                    department=get_attribute(
                        entry,
                        "department",
                    ),
                    phone=get_attribute(
                        entry,
                        "telephoneNumber",
                    ),
                    mobile=get_attribute(
                        entry,
                        "mobile",
                    ),
                    employee_id=get_attribute(
                        entry,
                        "employeeID",
                    ),
                    distinguished_name=get_attribute(
                        entry,
                        "distinguishedName",
                    ),
                    manager=get_attribute(
                        entry,
                        "manager",
                    ),
                )
            )

        return users

    except HTTPException:
        raise

    except Exception as error:
        logger.exception(
            "Active Directory search failed.",
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve user information "
                "from Active Directory."
            ),
        ) from error

    finally:
        connection.unbind()


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def root():
    """Return experiment information."""

    return {
        "application": "FORGE AD User Lookup Experiment",
        "version": "0.1.0",
        "ldap_server": LDAP_SERVER,
        "search_base": LDAP_SEARCH_BASE,
        "authentication": "Not configured yet",
        "endpoints": {
            "get_user": "/user?email=user@company.com",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get(
    "/user",
    response_model=list[ADUser],
)
def get_user_by_email(
    email: str = Query(
        ...,
        description="Employee email address or AD login identifier",
        min_length=1,
    ),
):
    """Retrieve an employee from Active Directory."""

    users = search_user_by_email(email)

    if not users:
        raise HTTPException(
            status_code=404,
            detail=(
                "No Active Directory user found for: "
                f"{email}"
            ),
        )

    return users


@app.get("/health")
def health_check():
    """Return experiment health."""

    return {
        "status": "healthy",
        "service": "FORGE AD User Lookup Experiment",
    }


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
    )
