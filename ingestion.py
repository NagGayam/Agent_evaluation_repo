"""Ingest the selected FABRIC English Q&A into local Chroma.

Review without embedding calls or Chroma writes:
    python ingestion.py --dry-run

Ingest (requires OPENAI_API_KEY in the environment or project .env):
    python ingestion.py

One complete Q&A becomes one document. Oversized records cause validation to
fail before ingestion, rather than silently truncating or splitting answers.
Reruns upsert the same IDs; they re-embed all records and incur API usage again.
Partial batches remain saved if a later request fails; rerunning is safe.
"""

import argparse
from collections import Counter
import json
import os
from pathlib import Path

import tiktoken

from settings import (
    ROOT, MODEL, DIMENSIONS, MAX_INPUT_TOKENS, chroma_path, chroma_collection,
)

EXPECTED_RECORDS = 120
METADATA_FIELDS = (
    "category", "subcategory", "difficulty", "source", "dataset", "split",
    "financial_verification", "selection_version",
)


def prepare_documents(path):
    """Validate every record before making any embedding calls or DB writes."""
    encoding = tiktoken.encoding_for_model(MODEL)
    documents = []
    seen = set()
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Line {line_number}: expected a JSON object")
            for field in ("id", "question_en", "answer", *METADATA_FIELDS):
                value = record.get(field)
                if field == "selection_version":
                    if type(value) is not int or value < 1:
                        raise ValueError(f"Line {line_number}: invalid selection_version")
                elif not isinstance(value, str) or not value.strip():
                    raise ValueError(f"Line {line_number}: missing/blank string {field}")

            record_id = record["id"].strip()
            if record_id in seen:
                raise ValueError(f"Duplicate ID: {record_id}")
            seen.add(record_id)
            if record["category"].strip().casefold() == "guardrails":
                raise ValueError(f"Safety record {record_id} must remain outside the KB")
            if record["dataset"] != "agenticclass/fabric" or record["split"] != "train":
                raise ValueError(f"Unexpected dataset/split for {record_id}")

            text = f"Question: {record['question_en'].strip()}\n\nAnswer: {record['answer'].strip()}"
            # Treat special-token-looking text as ordinary dataset content.
            tokens = len(encoding.encode(text, disallowed_special=()))
            if tokens > MAX_INPUT_TOKENS:
                raise ValueError(
                    f"{record_id}: {tokens} tokens exceeds {MAX_INPUT_TOKENS}. "
                    "Review and split this record explicitly before ingestion."
                )
            metadata = {field: record[field] for field in METADATA_FIELDS}
            metadata.update(record_id=record_id, embedding_model=MODEL,
                            embedding_dimensions=DIMENSIONS, token_count=tokens)
            documents.append({"id": record_id, "text": text, "metadata": metadata})

    if len(documents) != EXPECTED_RECORDS:
        raise ValueError(f"Expected {EXPECTED_RECORDS} records; found {len(documents)}")
    return documents


def ingest(documents, db_path, collection_name, batch_size):
    """Embed explicitly so Chroma never substitutes its default embedding model."""
    import chromadb
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ValueError("Set OPENAI_API_KEY in the environment or project .env")

    expected_metadata = {
        "embedding_model": MODEL,
        "embedding_dimensions": DIMENSIONS,
        "document_format": "question_answer_v1",
        "distance_metric": "cosine",
    }
    chroma = chromadb.PersistentClient(path=str(db_path))
    collection = chroma.get_or_create_collection(
        name=collection_name,
        embedding_function=None,
        metadata=expected_metadata,
        configuration={"hnsw": {"space": "cosine"}},
    )
    for key, value in expected_metadata.items():
        if (collection.metadata or {}).get(key) != value:
            raise ValueError(
                f"Existing collection has incompatible {key}. Use a new --collection name."
            )

    expected_ids = {doc["id"] for doc in documents}
    existing_ids = set(collection.get(include=[])["ids"])
    if existing_ids - expected_ids:
        raise ValueError(
            "Collection contains IDs outside this selection. Use a new --collection "
            "name; this script does not delete existing records."
        )

    # 32 * 8191 < 300,000 tokens, below the aggregate request token limit.
    effective_batch_size = min(batch_size, chroma.get_max_batch_size())
    with OpenAI(timeout=60.0, max_retries=2) as client:
        for offset in range(0, len(documents), effective_batch_size):
            batch = documents[offset:offset + effective_batch_size]
            response = client.embeddings.create(
                model=MODEL, dimensions=DIMENSIONS,
                input=[doc["text"] for doc in batch], encoding_format="float",
            )
            items = sorted(response.data, key=lambda item: item.index)
            if [item.index for item in items] != list(range(len(batch))):
                raise RuntimeError("Embedding response indices do not match the input batch")
            vectors = [item.embedding for item in items]
            if any(len(vector) != DIMENSIONS for vector in vectors):
                raise RuntimeError("Unexpected embedding dimensions")
            collection.upsert(
                ids=[doc["id"] for doc in batch],
                documents=[doc["text"] for doc in batch],
                metadatas=[doc["metadata"] for doc in batch],
                embeddings=vectors,
            )
            print(f"Stored {offset + len(batch)}/{len(documents)} documents")

    stored = collection.get(include=["documents", "metadatas"])
    by_id = dict(zip(stored["ids"], zip(stored["documents"], stored["metadatas"])))
    if set(by_id) != expected_ids:
        raise RuntimeError("Stored IDs do not match the selected records")
    for doc in documents:
        if by_id[doc["id"]] != (doc["text"], doc["metadata"]):
            raise RuntimeError(f"Stored document/metadata mismatch: {doc['id']}")
    print(f"Verified {collection.count()} documents in {db_path} / {collection_name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/fabric_kb_120.jsonl")
    parser.add_argument("--db-path", type=Path, default=chroma_path())
    parser.add_argument("--collection", default=chroma_collection())
    parser.add_argument("--batch-size", type=int, choices=range(1, 33), default=32,
                        metavar="1-32")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate and count tokens; no embedding API calls or Chroma writes")
    args = parser.parse_args()
    documents = prepare_documents(args.input)
    counts = [doc["metadata"]["token_count"] for doc in documents]
    print(f"Validated {len(documents)} records -> {len(documents)} complete Q&A chunks")
    print(f"Tokens: total={sum(counts)}, min={min(counts)}, max={max(counts)}")
    print("Categories:", dict(Counter(doc["metadata"]["category"] for doc in documents)))
    long_ids = [doc["id"] for doc in documents if doc["metadata"]["token_count"] > 1000]
    if long_ids:
        print("Records over 1000 tokens (kept intact):", ", ".join(long_ids))
    print(f"Embedding model: {MODEL}; dimensions: {DIMENSIONS}")
    if args.dry_run:
        print("Dry run complete. No embeddings requested; Chroma was not opened.")
        return
    ingest(documents, args.db_path, args.collection, args.batch_size)


if __name__ == "__main__":
    main()
