from abc import ABC

from pydantic import BaseModel


class TaskorMutationBaseModel(BaseModel, ABC):
    pass


class TaskorMutationMinimalSupportMixin(ABC):
    pass


class TaskorMutationMaximalSupportMixin(TaskorMutationMinimalSupportMixin, ABC):
    _taskor_mutation_class: type = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        if cls._taskor_mutation_class is None:
            raise TypeError(
                f"{cls.__name__} must define a class taskor_mutation"
            )
        if not issubclass(cls._taskor_mutation_class, TaskorMutationBaseModel):
            raise TypeError(
                f"{cls._taskor_mutation_class} must derive from TaskorMutationBaseModel"
            )

    @classmethod
    def get_taskor_mutation_base_model(cls):
        return cls._taskor_mutation_class
