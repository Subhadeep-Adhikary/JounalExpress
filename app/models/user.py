"""MongoDB collection blueprint for application users."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.extensions import db

User = db.db.user


def user_schema() -> Dict[str, Any]:
    """Return the expected document shape for the user collection."""
    return {
        "username": "string",
        "email": "string",
        "password": "string",
        "created_at": None,
        "connection_code": None,
        "connection_code_normalized": None,
        "connected_users": [],
        "connection_requests": [],
        "connections": [],
        "connected_accounts": [],
    }


def user_keys() -> List[str]:
    """List the main fields used by the app for user records."""
    return [
        "username",
        "email",
        "password",
        "created_at",
        "connection_code",
        "connection_code_normalized",
        "connected_users",
        "connection_requests",
        "connections",
        "connected_accounts",
    ]


def user_index_fields() -> Dict[str, Optional[str]]:
    """Document the indexed/searchable fields commonly used in queries."""
    return {
        "username": "unique",
        "email": "unique",
        "connection_code": "indexed",
        "connection_code_normalized": "indexed",
    }


__all__ = ["User", "user_schema", "user_keys", "user_index_fields"]
