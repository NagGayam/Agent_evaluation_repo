"""Upload the prepared DeepEval cases to Langfuse."""

import json
from pathlib import Path
import uuid

from dotenv import load_dotenv
from langfuse import get_client


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env", override=False)
langfuse = get_client()
DATASET_NAME = "DeepEval_Data_set"
data = ROOT / "evaluations" / "datasets" / "DeepEval_Data_set.jsonl"


def main():
    with open(data, "r", encoding="utf-8") as file:
        test_data = [json.loads(row) for row in file if row.strip()]

    langfuse.create_dataset(
        name=DATASET_NAME,
        description="Agent tool correctness and task completeness G-Eval cases",
    )

    for row in test_data:
        item_id = str(uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"{DATASET_NAME}:{row['metadata']['dataset_version']}:{row['id']}",
        ))
        langfuse.create_dataset_item(
            dataset_name=DATASET_NAME,
            id=item_id,
            input=row["input"],
            expected_output=row["expected_output"],
            metadata={**row["metadata"], "local_id": row["id"]},
        )
        print(f"Uploaded: {row['id']}")

    print(f"Completed uploading {len(test_data)} items to {DATASET_NAME}.")


if __name__ == "__main__":
    try:
        main()
    finally:
        langfuse.flush()
