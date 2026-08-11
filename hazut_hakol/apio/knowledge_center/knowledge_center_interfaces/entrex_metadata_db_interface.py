from datetime import datetime

from pymongo.collection import Collection


class EntrexMetadataDBInterface:
    def __init__(self, metadata_collection: Collection):
        self._metadata_collection = metadata_collection

    def get_collection(self) -> Collection:
        return self._metadata_collection

    def _get_metadata(self) -> dict:
        return self._metadata_collection.find()[0] if self._metadata_collection.count_documents({}) > 0 else {}

    def get_latest_syncbeat(self, syncbeat: datetime) -> None:
        self._metadata_collection.update_one(
            {"latest_syncbeat": {"$exists": True}},
            {"$set": {"latest_syncbeat": syncbeat}},
            upsert=True
        )

    def delete_latest_syncbeat(self) -> None:
        self._metadata_collection.delete_one(
            {"latest_syncbeat": {"$exists": True}}
        )
