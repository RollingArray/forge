"""
File: activity_types.py
Purpose: FORGE activity event type constants.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from enum import StrEnum


class ActivityType(StrEnum):
    """Define supported FORGE activity event types."""

    USER_SIGNED_IN = "USER_SIGNED_IN"
