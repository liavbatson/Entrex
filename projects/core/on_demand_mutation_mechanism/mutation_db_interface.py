import copy
import hashlib
import json
from collections import OrderedDict
from typing import Dict, Any, Optional, Mapping
from pydantic.json import pydantic_encoder
from pymongo.collection import Collection


class MutationDBInterface:
    def __init__(self, mutation_collection: Collection):
        self._mutation_collection = mutation_collection

    def get_collection(self) -> Collection:
        return self._mutation_collection

    def add_mutation_dict(self, mutation_dict: Dict[str, Any]) -> str:
        sorted_copy = self._sort_nested_dict(copy.deepcopy(mutation_dict))
        json_ready = self._make_json_ready(sorted_copy)
        json_string = json.dumps(json_ready, separators=(',', ':'), ensure_ascii=False)
        hash_object = hashlib.sha256(json_string.encode('utf-8'))
        hash_key = hash_object.hexdigest()
        self._mutation_collection.replace_one(
            {'_id': hash_key},
            {"mutation": mutation_dict},
            upsert=True
        )
        return hash_key

    def get_taskor_mutation(self, mutation_hash: str, taskor_name: str) -> Optional[Dict]:
        mutation_doc = self._mutation_collection.find_one({'_id': mutation_hash})
        if not mutation_doc:
            raise RuntimeError(f"Mutation # {mutation_hash} not exists in db.")
        mutation_dict = mutation_doc["mutation"]
        if taskor_name in mutation_dict:
            return mutation_dict[taskor_name]
        else:
            return None

    def delete_mutation_dict(self, mutation_hash: str) -> None:
        self._mutation_collection.delete_one({'_id': mutation_hash})

    @staticmethod
    def _make_json_ready(data: Mapping[str, Any]) -> dict:
        json_str = json.dumps(
            data,
            default=pydantic_encoder,
            separators=(',', ':'),
            ensure_ascii=False
        )
        return json.loads(json_str)

    def _sort_nested_dict(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            sorted_items = sorted(obj.items())
            return OrderedDict(
                (key, self._sort_nested_dict(value))
                for key, value in sorted_items
            )
        elif isinstance(obj, list):
            return [self._sort_nested_dict(item) for item in obj]
        else:
            return obj