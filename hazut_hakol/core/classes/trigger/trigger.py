from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, FrozenSet, List

from bson import ObjectId

from hazut_hakol.core.classes.roi import Roi
from hazut_hakol.core.classes.trigger.trigger_enums import TriggerStatus, TriggerType
from hazut_hakol.core.classes.trigger.trigger_error_info_object import TriggerErrorInfo
from projects.core.on_demand_mutation_mechanism.trigger_mutation_mixin import TriggerMutationMixin
from hazut_hakol.core.classes.trigger.trigger_life_cycle import TriggerLifeCycle

MUTATION_SIGN_CONSTANT = ":#mutation-"


class Trigger(TriggerMutationMixin):
    def __init__(self, taskor_name: str, trigger_type: TriggerType, trigger_id: str, status: TriggerStatus,
                 priority: int, rois: List[Roi], update_time: datetime, creation_time: datetime,
                 is_orchestrator_processed: bool, extra_results: Optional[Dict] = None,
                 fail_error_message: TriggerErrorInfo = None, trigger_life_cycle: Optional[TriggerLifeCycle] = None,
                 _id: Optional[str] = None):
        super().__init__(trigger_id)
        self._id = _id if _id else ObjectId()
        self._marked_changed_fields = {}
        self._status: TriggerStatus
        self.taskor_name = taskor_name
        self.trigger_type = trigger_type
        self.trigger_id = trigger_id
        self.trigger_life_cycle = trigger_life_cycle or TriggerLifeCycle()
        self.status = status
        self.priority = priority
        self._rois = rois
        self._roi_ids = frozenset([ObjectId(roi._id) for roi in rois])
        self.update_time = update_time
        self.creation_time = creation_time
        self.is_orchestrator_processed = is_orchestrator_processed
        self.extra_results = extra_results
        self.fail_error_message = fail_error_message

    @property
    def status(self) -> TriggerStatus:
        return self._status

    @status.setter
    def status(self, value: TriggerStatus):
        should_mark_field = hasattr(self, "_status") or self.trigger_life_cycle.timeline
        self.trigger_life_cycle.change_state(value)
        self._status = value
        if should_mark_field:
            self._mark_field("trigger_life_cycle", self.trigger_life_cycle)
            self._mark_field("status", self._status)

    @property
    def roi_ids(self) -> FrozenSet[ObjectId]:
        return self._roi_ids

    @property
    def rois(self, value: List[Roi]):
        self._rois = value
        self._roi_ids = frozenset([ObjectId(roi._id) for roi in self._rois])
        self._mark_field("roi_ids", self._roi_ids)

    @classmethod
    def create_new(cls, taskor_name: str, trigger_type: TriggerType, trigger_id: str, status: TriggerStatus,
                   priority: int, rois: List[Roi]):
        trigger_instance = Trigger(
            taskor_name=taskor_name,
            trigger_type=trigger_type,
            trigger_id=trigger_id,
            status=status,
            priority=priority,
            rois=rois,
            update_time=datetime.now(timezone.utc),
            creation_time=datetime.now(timezone.utc),
            is_orchestrator_processed=False
        )
        trigger_instance._mark_all_fields()
        return trigger_instance

    @classmethod
    def from_mongo_document(cls, trigger_raw: Dict, rois: List[Roi]):
        if not trigger_raw:
            return None

        trigger_instance = Trigger(
            _id=trigger_raw["_id"],
            taskor_name=trigger_raw["taskor_name"],
            trigger_type=TriggerType(trigger_raw["trigger_type"]),
            trigger_id=trigger_raw["trigger_id"],
            status=TriggerStatus(trigger_raw["status"]),
            priority=trigger_raw["priority"],
            rois=rois,
            update_time=trigger_raw["update_time"].replace(tzinfo=timezone.utc),
            creation_time=trigger_raw["creation_time"].replace(tzinfo=timezone.utc),
            is_orchestrator_processed=trigger_raw["is_orchestrator_processed"],
            extra_results=trigger_raw.get("extra_results", None),
            fail_error_message=TriggerErrorInfo.from_json(trigger_raw.get("fail_error_message", None)),
            trigger_life_cycle=TriggerLifeCycle.from_json(
                trigger_raw["trigger_life_cycle"]
            ) if "trigger_life_cycle" in trigger_raw else None
        )
        return trigger_instance

    @contextmanager
    def running_phase(self, phase_name: str):
        self.trigger_life_cycle.change_running_phase(phase_name)
        self._mark_field("trigger_life_cycle", self.trigger_life_cycle)

        try:
            yield
        finally:
            if phase_name in self.trigger_life_cycle.running_timeline:
                self.trigger_life_cycle.running_timeline[phase_name].ended_at = datetime.now(timezone.utc)
                self._mark_field("trigger_life_cycle", self.trigger_life_cycle)

    def _mark_field(self, name, value):
        if name.startswith("_"):
            pass
        elif isinstance(value, Enum):
            self._marked_changed_fields[name] = value.value
        elif isinstance(value, FrozenSet):
            self._marked_changed_fields[name] = list(value)
        elif isinstance(value, TriggerErrorInfo):
            self._marked_changed_fields[name] = value.to_json()
        elif isinstance(value, TriggerLifeCycle):
            self._marked_changed_fields[name] = value.to_json()
        else:
            self._marked_changed_fields[name] = value

    def _mark_all_fields(self):
        all_fields = dict(self.__dict__.items())
        all_fields['status'] = self.status
        all_fields['roi_ids'] = self.roi_ids
        for name, value in all_fields.items():
            self._mark_field(name, value)

    def __setattr__(self, name, value):
        if name in self.__class__.__dict__ and isinstance(self.__class__.__dict__[name], property):
            object.__setattr__(self, name, value)
            return
        if hasattr(self, name):
            self._mark_field(name, value)
        super().__setattr__(name, value)

    def get_marked_fields(self) -> Dict:
        return self._marked_changed_fields.copy()

    def clean_marked_fields(self):
        self._marked_changed_fields.clear()
