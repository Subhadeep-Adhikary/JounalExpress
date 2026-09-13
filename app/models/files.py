"""MongoDB collection blueprints for journal entries and stored images."""

from __future__ import annotations

from typing import Any, Dict, List

from bson import ObjectId

from app.extensions import db

Files = db.db.files
Images = db.db.images


def file_schema() -> Dict[str, Any]:
    """Return the expected document shape for journal entry records."""
    return {
        "_id": ObjectId,
        "user": "string",
        "category": "personal | shared",
        "date": "string",
        "file": "string",
        "title": "string",
        "place": "string",
        "image": [],
        "content_rows": {"ciphertext": "bytes", "nonce": "bytes"},
        "created_by": "string",
        "shared_one": "string",
        "shared_with": [],
        "content": "legacy string fallback",
    }


def file_keys() -> List[str]:
    """List the essential properties used throughout the journaling workflow."""
    return [
        "_id",
        "user",
        "category",
        "date",
        "file",
        "title",
        "place",
        "image",
        "content_rows",
        "created_by",
        "shared_one",
        "shared_with",
        "content",
    ]


def image_schema() -> Dict[str, Any]:
    """Return the expected document shape for the images collection."""
    return {
        "_id": ObjectId,
        "user": "string",
        "filename": "string",
        "content_type": "string",
        "data": "encrypted binary payload",
    }


def image_keys() -> List[str]:
    """List the main fields stored for uploaded image references."""
    return ["_id", "user", "filename", "content_type", "data"]


__all__ = ["Files", "Images", "file_schema", "file_keys", "image_schema", "image_keys"]
