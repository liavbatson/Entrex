from typing import List


class EntrexGraphNode:
    _predecessors = []

    @classmethod
    def get_taskor_name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_predecessors(cls) -> List[str]:
        return [taskor_cls.get_taskor_name() for taskor_cls in cls._predecessors]