from datetime import datetime, timedelta

from loguru import logger
from pymongo.collection import Collection


class TaskorHeartbeatDBInterface:
    def __init__(self, taskor_heartbeat_collection: Collection):
        self._taskor_heartbeat_collection = taskor_heartbeat_collection

    def get_collection(self) -> Collection:
        return self._taskor_heartbeat_collection

    def update_heartbeat(self, taskor_name: str, pod_name: str, heartbeat_time: datetime) -> None:
        self._taskor_heartbeat_collection.update_one(
            {"taskor_name": taskor_name},
            {
                "$set": {f'pods.{pod_name}': heartbeat_time}
            },
            upsert=True
        )

    def delete_old_heartbeats(self, time_interval_minutes: int = 10) -> None:
        cutoff_date = datetime.now() - timedelta(minutes=time_interval_minutes)
        docs_to_delete = []
        for doc in self._taskor_heartbeat_collection.find({'pods': {'$exists': True, '$ne': {}}}):
            pods = doc.get('pods', {})
            pods_to_keep = {}
            for pod_name, pod_datetime in pods.items():
                if pod_datetime >= cutoff_date:
                    pods_to_keep[pod_name] = pod_datetime
                else:
                    logger.info(f"Removing pod '{pod_name}' (date: {pod_datetime})")

            if len(pods_to_keep) == 0:
                docs_to_delete.append(doc['_id'])
                logger.info(f"Marking document '{doc['taskor_name']}' for deletion (all pods old)")
            elif len(pods_to_keep) < len(pods):
                self._taskor_heartbeat_collection.update_one(
                    {'_id': doc['_id']},
                    {'$set': {'pods': pods_to_keep}}
                )
                logger.info(f"Updated '{doc['taskor_name']}': {len(pods)} -> {len(pods_to_keep)} pods")

        if docs_to_delete:
            result = self._taskor_heartbeat_collection.delete_one({'_id': {'$in': docs_to_delete}})
            logger.info(f"Deleted {result.deleted_count} documents with no remaining pods")
