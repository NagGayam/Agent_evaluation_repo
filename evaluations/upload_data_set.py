import os 
from dotenv import load_dotenv
load_dotenv()
from pathlib import Path
from langfuse import get_client
import json 
import uuid

dataset = Path(__file__).parent/"datasets"/"RAGAS_Data_set.jsonl"
langfuse = get_client()

with open(dataset,"r",encoding="utf-8") as file :
    json_data = [json.loads(line)for line in file if line.strip()]

data_set = langfuse.create_dataset(
    name="RAGAS_data_set",
    description="This Data set is used for RAGAS evaluation",
)


for item in json_data:
    item_id = str(uuid.uuid5(
    uuid.NAMESPACE_URL,
    f"RAGAS_data_set:{item['metadata']['dataset_version']}:{item['id']}",
))
    langfuse.create_dataset_item(
        dataset_name="RAGAS_data_set",
        id=item_id,
        input={
            "user_input": item["user_input"],
        },
        expected_output={
            "reference": item["reference"],
            "reference_contexts": item["reference_contexts"],
            "reference_context_ids": item["reference_context_ids"],
        },
        metadata={
            **item["metadata"],
            "local_id": item["id"],
        },
    )
