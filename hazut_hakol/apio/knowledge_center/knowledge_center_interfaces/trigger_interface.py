from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict

from bson import ObjectId
from pymongo import UpdateOne, ReturnDocument
from pymongo.collection import Collection

from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.roi_db_interface import RoiDBInterface
from hazut_hakol.core.classes.trigger import Trigger, TriggerStatus


class TriggerDBInterface:
    def __init__(self, trigger_collection: Collection, roi_db_interface: RoiDBInterface):
        self._trigger_collection = trigger_collection
        self._roi_collection = roi_db_interface

    def get_collection(self) -> Collection:
        return self._trigger_collection

    def update_triggers(self, triggers: List[Trigger]) -> None:
        if len(triggers) == 0:
            return

        ops = []
        update_time = datetime.now(tz=timezone.utc)
        for trigger in triggers:
            trigger.update_time = update_time
            marked_fields = trigger.get_marked_fields()
            update = {"$set": marked_fields}
            is_new_trigger = "creation_time" in marked_fields.keys()

            ops.append(
                UpdateOne(
                    filter={"_id": trigger._id},
                    update=update,
                    upsert=is_new_trigger
                )
            )
        self._trigger_collection.bulk_write(ops)

    def get_triggers(self, taskor_name: str, status: Optional[TriggerStatus] = None) -> List[Trigger]:
        if status:
            trigger_raws = list(self._trigger_collection.find({"taskor_name": taskor_name, "status": status}))
        else:
            trigger_raws = list(self._trigger_collection.find({"taskor_name": taskor_name}))
        return self._from_mongo_documents(trigger_raws)

    def find_triggers_for_id(self, trigger_id: str, taskor_names: List[str] = None) -> List[Trigger]:
        if taskor_names is None:
            trigger_raws = list(self._trigger_collection.find({
                "trigger_id": trigger_id
            }))
            triggers = self._from_mongo_documents(trigger_raws)
        else:
            trigger_raws = list(self._trigger_collection.find({
                "trigger_id": trigger_id,
                "taskor_name": {"$in": taskor_names}
            }))
            triggers = self._from_mongo_documents(trigger_raws)
            if len(triggers) > len(taskor_names):
                raise RuntimeError("Fetched more triggers to a single trigger_id than amount of taskor_names provided")
        return triggers

    def find_triggers_for_ids(self, trigger_ids: List[str]) -> List[Trigger]:
        trigger_raws = list(self._trigger_collection.find({
            "trigger_id": {"$in": trigger_ids}
        }))
        return self._from_mongo_documents(trigger_raws)

    def find_triggers_waiting_for_optimization(self, taskor_names: List[str], since: Optional[datetime] = None) -> List[Trigger]:
        since = since or datetime.now(tz=timezone.utc) - timedelta(hours=24)
        trigger_raws = list(self._trigger_collection.find({
            "status": TriggerStatus.WAIT_FOR_OPTIMIZATION.value,
            "taskor_name": {"$in": taskor_names},
            "update_time": {"$gt": since}
        }))
        return self._from_mongo_documents(trigger_raws)

    def find_ongoing_triggers_by_roi_ids(self, roi_ids: List[str]) -> List[Trigger]:
        yesterday = datetime.now(tz=timezone.utc) - timedelta(hours=24)
        trigger_raws = list(self._trigger_collection.find({
            "status": {"$in": [
                TriggerStatus.PENDING.value,
                TriggerStatus.RUNNING.value,
                TriggerStatus.COMPLETED.value,
                TriggerStatus.RESULTS_EXPIRED.value
            ]},
            "roi_ids": {"$in": [ObjectId(roi) for roi in roi_ids]},
            "update_time": {"$gt": yesterday}
        }))
        return self._from_mongo_documents(trigger_raws)

    def find_triggers_by_roi_waiting_for_optimization(self, roi_id: ObjectId) -> List[Trigger]:
        trigger_raws = list(self._trigger_collection.find({
            "status": TriggerStatus.WAIT_FOR_OPTIMIZATION.value,
            "roi_ids": {"$in": [roi_id]}
        }))
        return self._from_mongo_documents(trigger_raws)

    def get_pending_trigger_and_acknowledge(self, taskor_name: str) -> Optional[Trigger]:
        update_time = datetime.now(tz=timezone.utc)
        most_prioritized_trigger_raw = self._trigger_collection.find_one_and_update(
            filter={"taskor_name": taskor_name, "status": TriggerStatus.PENDING.value},
            sort=[("priority", 1), ("update_time", 1)],
            update={"$set": {
                "status": TriggerStatus.RUNNING.value,
                "update_time": update_time
            }},
            return_document=ReturnDocument.AFTER
        )
        if most_prioritized_trigger_raw is not None:
            trigger = self._from_mongo_document(most_prioritized_trigger_raw)
            self.update_triggers([trigger])
            return trigger
        return None

    def get_waiting_for_registration_sweeps(self) -> List[Trigger]:
        waiting_for_registration = list(self._trigger_collection.find(
            {"status": TriggerStatus.WAIT_FOR_OPTIMIZATION.value}
        ))
        return self._from_mongo_documents(waiting_for_registration)

    def get_triggers_needing_orchestrator_processing(self) -> List[Trigger]:
        return self._get_triggers_needing_orchestrator_processing_by_status([TriggerStatus.COMPLETED])

    def get_failed_triggers_needing_orchestrator_processing(self) -> List[Trigger]:
        return self._get_triggers_needing_orchestrator_processing_by_status(
            [TriggerStatus.FAILED, TriggerStatus.SKIPPED, TriggerStatus.ABORTED]
        )

    def _get_triggers_needing_orchestrator_processing_by_status(self, statuses: List[TriggerStatus]) -> List[Trigger]:
        needing_orchestrator_triggers = list(self._trigger_collection.find(
            filter={"status": {"$in": [statuses.value for status in statuses]},
                    "is_orchestrator_processed": False}
        ))
        return self._from_mongo_documents(needing_orchestrator_triggers)

    def delete_triggers(self, triggers: List[Trigger]):
        trigger_ids = [trigger._id for trigger in triggers]
        self._trigger_collection.delete_many(
            filter={
                "_id": {"$in": trigger_ids}
            }
        )

    def get_triggers_candidates_for_cleaning(self, older_than_datetime: datetime, services_names: List[str]) -> List[Trigger]:
        trigger_raws = list(self._trigger_collection.find(
            {
                "taskor_name": {"$in": services_names},
                "status": {"$in": [TriggerStatus.COMPLETED.value, TriggerStatus.FAILED.value]},
                "update_time": {"$lt": older_than_datetime},
                "is_orchestrator_processed": Trigger
            }
        ))
        return self._from_mongo_documents(trigger_raws)

    def cascade_delete_roi(self, roi_id: ObjectId) -> None:
        self._trigger_collection.update_many(
            filter={"roi_ids": roi_id},
            update={"$pull": {"roi_ids": roi_id}}
        )

    def get_triggers_by_statuses_and_older_than(self, older_than_datetime: datetime, statuses_to_abort: List[TriggerStatus]) -> List[Trigger]:
        trigger_raws = list(self._trigger_collection.find(
            {
                "status": {"$in": [status.value for status in statuses_to_abort]},
                "update_time": {"$lt": older_than_datetime}
            }
        ))
        return self._from_mongo_documents(trigger_raws)

    def get_triggers_needing_auto_deletion(self, older_than_datetime: datetime) -> List[Trigger]:
        trigger_raws = list(self._trigger_collection.find(
            {
                "update_time": {"$lt": older_than_datetime}
            }
        ))
        return self._from_mongo_documents(trigger_raws)

    def active_triggers_from_mongo(self) -> List[Trigger]:
        active_triggers_from_mongo = list(self._trigger_collection.find(
            {
                "status": {"$in": ["running", "pending", "waiting"]}
            }
        ))
        return self._from_mongo_documents(active_triggers_from_mongo)

    def find_with_query(self, query: Dict, projection: Dict) -> List[Trigger]:
        trigger_raws = list(self._trigger_collection.find(query, projection))
        return self._from_mongo_documents(trigger_raws)

    def _from_mongo_document(self, trigger_raw) -> Trigger:
        triggers = self._from_mongo_documents([trigger_raw])
        return triggers[0]

    def _from_mongo_documents(self, triggers_raw) -> List[Trigger]:
        rois = self._roi_collection.get_rois(list({ObjectId(roi) for trigger in triggers_raw for roi in trigger["roi_ids"]}))
        rois_mapping = {roi._id: roi for roi in rois}

        triggers = [
            Trigger.from_mongo_document(
                trigger_raw,
                [rois_mapping[roi_id] for roi_id in triggers_raw["roi_ids"]]
            ) for trigger_raw in triggers_raw
        ]
        return triggers