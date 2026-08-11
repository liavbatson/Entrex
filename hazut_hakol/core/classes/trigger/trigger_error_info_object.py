import traceback
from enum import Enum
from typing import Dict

from hazut_hakol.core.entrex_base_errors import EntrexDataError


class EntrexErrorTypes(Enum):
    DATA = "data"
    BUG = "bug"
    UNPROVIDED = "unprovided"


class TriggerErrorInfo:
    def __init__(self, exception_object: Exception = None):
        if exception_object is None:
            self._fail_type = EntrexErrorTypes.UNPROVIDED
            self._error_class = None
            self._error_info = None
        elif isinstance(exception_object, EntrexDataError):
            self._fail_type = EntrexErrorTypes.DATA
            self._error_class = type(exception_object).__name__
            self._error_info = str(exception_object)
        else:
            self._fail_type = EntrexErrorTypes.BUG
            self._error_class = f"{type(exception_object).__name__}"
            self._error_info = traceback.format_exc()

    def to_json(self):
        return {
            "fail_type": self._fail_type.value,
            "error_class": self._error_class,
            "error_info": self._error_info
        }

    @staticmethod
    def from_json(raw_input: Dict[str, str]):
        error_info_obj = TriggerErrorInfo()
        if raw_input is not None:
            error_info_obj._fail_type = EntrexErrorTypes(raw_input["fail_type"])
            error_info_obj._error_class = raw_input["error_class"]
            error_info_obj._error_info = raw_input["error_info"]
        return error_info_obj
