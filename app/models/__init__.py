"""Database model helpers and collection initialization for MongoDB."""

from __future__ import annotations

from app.extensions import db


def init_db_collections():
    """Ensure the application collections exist and add the indexes used by the app."""
    mongo_db = db.db

    existing = set(mongo_db.list_collection_names())
    for collection_name in ("user", "files", "images"):
        if collection_name not in existing:
            mongo_db.create_collection(collection_name)

    user_collection = mongo_db["user"]
    user_collection.create_index("username", unique=True)
    user_collection.create_index("email", unique=True, sparse=True)
    user_collection.create_index("connection_code", unique=True, sparse=True)
    user_collection.create_index("connection_code_normalized", unique=True, sparse=True)

    files_collection = mongo_db["files"]
    files_collection.create_index([("user", 1), ("date", 1), ("file", 1)])
    files_collection.create_index("category")
    files_collection.create_index("shared_one")

    images_collection = mongo_db["images"]
    images_collection.create_index("user")
    images_collection.create_index("filename")

    return {
        "user": user_collection,
        "files": files_collection,
        "images": images_collection,
    }


__all__ = ["init_db_collections"]
