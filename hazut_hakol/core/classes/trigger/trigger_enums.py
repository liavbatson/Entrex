from enum import Enum


class TriggerStatus(Enum):
    WAITING = "waiting"
    PENDING = "pending"
    ABORTED = "aborted"
    RUNNING = "running"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RESULTS_EXPIRED = "results_expired"
    WAIT_FOR_OPTIMIZATION = "wait_for_optimization"
    REDUNDANT = "redundant"


class TriggerType(Enum):
    SWEEP = "sweep"
    SORTIE = "sortie"
