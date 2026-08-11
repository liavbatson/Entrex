MUTATION_SIGN_CONSTANT = "#mutation-"


class TriggerMutationMixin:
    def __init__(self, trigger_id):
        if MUTATION_SIGN_CONSTANT in trigger_id:
            self._clean_trigger_id = trigger_id.split(MUTATION_SIGN_CONSTANT)[0]
            self._on_demand_mutation_hash = trigger_id.split(MUTATION_SIGN_CONSTANT)[1]
        else:
            self._clean_trigger_id = trigger_id
            self._on_demand_mutation_hash = None

    def get_clean_trigger_id(self):
        return self._clean_trigger_id

    def get_on_demand_mutation_hash(self):
        return self._on_demand_mutation_hash

    def is_mutation(self) -> bool:
        return self._on_demand_mutation_hash is not None

    @staticmethod
    def merge_trigger_id_if_mutation_present(base_trigger_id: str, mutation_hash: str) -> str:
        if not mutation_hash:
            return base_trigger_id
        else:
            return base_trigger_id + MUTATION_SIGN_CONSTANT + mutation_hash
