"""Shared ingestion/retrieval settings. Existing environment variables override .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)

# Keep the model fixed for this collection: changing it requires re-embedding.
MODEL = "text-embedding-3-small"
DIMENSIONS = 1536
MAX_INPUT_TOKENS = 8191


def chroma_path():
    """Resolve relative database paths against the project, not the terminal cwd."""
    value = os.environ.get("CHROMA_PERSIST_DIRECTORY", "chroma_db").strip()
    if not value:
        raise ValueError("CHROMA_PERSIST_DIRECTORY cannot be blank")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else ROOT / path).resolve()


def chroma_collection():
    name = os.environ.get("CHROMA_COLLECTION_NAME", "fabric_qa_small_v1").strip()
    if not name:
        raise ValueError("CHROMA_COLLECTION_NAME cannot be blank")
    return name
