"""Search the existing FABRIC collection; no ingestion or answer generation.

    python -m agent.retrieval "How much of my bank deposit is insured?"
    python -m agent.retrieval "What is an ELSS lock-in?" --top-k 5 --json

Each query makes one OpenAI embedding request. Ranked matches are returned
without a relevance cutoff; distance is not a confidence or correctness score.
"""

import argparse
import json
import os
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from openai import OpenAI
import tiktoken

from agent.settings import MODEL, DIMENSIONS, MAX_INPUT_TOKENS, chroma_path, chroma_collection


def open_collection(db_path=None, collection_name=None):
    """Get an existing collection, without creating a missing database/collection."""
    path = Path(db_path).expanduser().resolve() if db_path is not None else chroma_path()
    name = collection_name if collection_name is not None else chroma_collection()
    if not (path / "chroma.sqlite3").is_file():
        raise ValueError(f"No local Chroma database at {path}. Check .env or run python -m ingestion.ingest.")
    client = chromadb.PersistentClient(path=str(path))
    try:
        collection = client.get_collection(name=name, embedding_function=None)
    except NotFoundError as exc:
        raise ValueError(f"Collection {name!r} was not found. Check .env or run python -m ingestion.ingest.") from exc
    expected = {
        "embedding_model": MODEL,
        "embedding_dimensions": DIMENSIONS,
        "document_format": "question_answer_v1",
        "distance_metric": "cosine",
    }
    for key, value in expected.items():
        if (collection.metadata or {}).get(key) != value:
            raise ValueError(f"Collection setting {key!r} does not match ingestion settings.")
    if collection.count() == 0:
        raise ValueError("Collection is empty. Run python -m ingestion.ingest first.")
    return collection


def retrieve(question: str, top_k: int = 3, *, db_path=None, collection_name=None) -> list[dict]:
    """Embed one question and return ranked documents, sources, metadata and distances."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a nonblank string")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    question = question.strip()
    encoding = tiktoken.encoding_for_model(MODEL)
    if len(encoding.encode(question, disallowed_special=())) > MAX_INPUT_TOKENS:
        raise ValueError(f"Question exceeds the {MAX_INPUT_TOKENS}-token limit")

    # Validate the database before paying for a query embedding.
    collection = open_collection(db_path, collection_name)
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ValueError("Set OPENAI_API_KEY in the environment or project .env")
    with OpenAI(timeout=60.0, max_retries=2) as client:
        response = client.embeddings.create(
            model=MODEL, dimensions=DIMENSIONS, input=[question], encoding_format="float",
        )
    if len(response.data) != 1 or response.data[0].index != 0:
        raise RuntimeError("Unexpected query embedding response")
    vector = response.data[0].embedding
    if len(vector) != DIMENSIONS:
        raise RuntimeError("Query embedding dimensions do not match the collection")

    result = collection.query(
        query_embeddings=[vector], n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    matches = []
    for index, record_id in enumerate(result["ids"][0]):
        metadata = result["metadatas"][0][index] or {}
        matches.append({
            "record_id": record_id,
            "document": result["documents"][0][index],
            "source": metadata.get("source", ""),
            "category": metadata.get("category", ""),
            "distance": result["distances"][0][index],
            "metadata": metadata,
        })
    return matches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", help="Question to search for; enclose it in quotes")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--db-path", type=Path, help="Override CHROMA_PERSIST_DIRECTORY")
    parser.add_argument("--collection", help="Override CHROMA_COLLECTION_NAME")
    parser.add_argument("--json", action="store_true", help="Print reusable results as JSON")
    args = parser.parse_args()
    try:
        matches = retrieve(args.question, args.top_k,
                           db_path=args.db_path, collection_name=args.collection)
    except ValueError as exc:
        parser.exit(1, f"Retrieval failed: {exc}\n")
    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
        return
    print(f"Found {len(matches)} ranked matches (lower cosine distance means closer).")
    for rank, match in enumerate(matches, start=1):
        print(f"\n{rank}. {match['record_id']} | {match['category']} | distance={match['distance']:.4f}")
        print(match["document"])
        print(f"Source: {match['source']}")
        print(f"Financial verification: {match['metadata'].get('financial_verification', 'unknown')}")


if __name__ == "__main__":
    main()
