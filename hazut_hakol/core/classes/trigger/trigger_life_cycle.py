from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional, Dict

from hazut_hakol.core.classes.trigger.trigger_enums import TriggerStatus

TRIGGERS_STATUS_ORDER = {
    TriggerStatus.WAITING: 0,
    TriggerStatus.WAIT_FOR_OPTIMIZATION: 0,
    TriggerStatus.PENDING: 1,
    TriggerStatus.RUNNING: 2,
    TriggerStatus.COMPLETED: 3,
    TriggerStatus.FAILED: 3,
    TriggerStatus.SKIPPED: 3,
    TriggerStatus.ABORTED: 3,
    TriggerStatus.RESULTS_EXPIRED: 3,
    TriggerStatus.REDUNDANT: 3
}


@dataclass
class StatePeriod:
    started_at: datetime
    ended_at: Optional[datetime] = None

    def duration_seconds(self) -> float:
        if self.ended_at is None:
            return 0.0
        end = self.ended_at
        return (end - self.started_at).total_seconds()


@dataclass
class TriggerLifeCycle:
    timeline: Dict[TriggerStatus, StatePeriod] = field(default_factory=dict)
    running_timeline: Dict[str, StatePeriod] = field(default_factory=dict)

    def change_state(self, state: TriggerStatus):
        if self.timeline:
            last_state = list(self.timeline.keys())[-1]
            if last_state == state:
                return

            if TRIGGERS_STATUS_ORDER[state] < TRIGGERS_STATUS_ORDER[last_state]:
                states_to_remove = [
                    tracked_state
                    for tracked_state in self.timeline
                    if TRIGGERS_STATUS_ORDER[tracked_state] >= TRIGGERS_STATUS_ORDER[state]
                ]
                for tracked_state in states_to_remove:
                    self.timeline.pop(tracked_state)

                if TRIGGERS_STATUS_ORDER[state] <= TRIGGERS_STATUS_ORDER[TriggerStatus.RUNNING]:
                    self.running_timeline.clear()

            if self.timeline:
                last_state = list(self.timeline.keys())[-1]

                if self.timeline[last_state].ended_at is None:
                    self.timeline[last_state].ended_at = datetime.now(timezone.utc)

        self.timeline[state] = StatePeriod(started_at=datetime.now(timezone.utc))

    def change_running_phase(self, phase_name: str, timestamp: Optional[datetime] = None):
        timestamp = timestamp or datetime.now(timezone.utc)
        self.running_timeline[phase_name] = StatePeriod(started_at=timestamp)

    def to_json(self) -> Dict:
        return {
            "states": {
                t.value: {
                    "started_at": self.timeline[t].started_at,
                    "ended_at": self.timeline[t].ended_at,
                    "duration_sec": self.timeline[t].duration_seconds()
                } for t in self.timeline
            },
            "running": {
                phase: {
                    "started_at": self.running_timeline[phase].started_at,
                    "ended_at": self.running_timeline[phase].ended_at,
                    "duration_sec": self.running_timeline[phase].duration_seconds()
                } for phase in self.running_timeline
            }
        }

    @classmethod
    def from_json(cls, data: Dict) -> "TriggerLifeCycle":
        lifecycle = cls()
        if "states" in data:
            for state_str, state_data in data["states"].items():
                state = TriggerStatus(state_str)
                started_at = state_data["started_at"]
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)

                ended_at = state_data.get("ended_at")
                if ended_at and ended_at.tzinfo is None:
                    ended_at = ended_at.replace(tzinfo=timezone.utc)

                lifecycle.timeline[state] = StatePeriod(
                    started_at=started_at,
                    ended_at=ended_at
                )

        if "running" in data:
            for phase_name, phase_data in data["running"].items():
                started_at = phase_data["started_at"]
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)

                ended_at = phase_data.get("ended_at")
                if ended_at and ended_at.tzinfo is None:
                    ended_at = ended_at.replace(tzinfo=timezone.utc)

                lifecycle.running_timeline[phase_name] = StatePeriod(
                    started_at=started_at,
                    ended_at=ended_at
                )

        return lifecycle
