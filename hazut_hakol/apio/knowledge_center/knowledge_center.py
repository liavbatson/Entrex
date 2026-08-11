from enum import Enum

from loguru import logger

from hazut_hakol.apio.interfaces.mongo_interface import MongoInterface
from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.entrex_metadata_db_interface import \
    EntrexMetadataDBInterface
from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.roi_db_interface import RoiDBInterface
from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.taskor_heartbeat_interface import \
    TaskorHeartbeatDBInterface
from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.trigger_interface import TriggerDBInterface
from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.users_db_interface import UserDBInterface
from hazut_hakol.apio.knowledge_center.knowledge_center_interfaces.images_metadata_db_interface import \
    ImagesMetadataDBInterface
from hazut_hakol.core.utils import Environment
from projects.core.on_demand_mutation_mechanism.mutation_db_interface import MutationDBInterface

MONGO_CONNECTION_STRING = {
    Environment.PRODUCTION: "",
    Environment.STAGING: "",
    Environment.DEVELOPMENT: "mongodb+srv://moshemushon423_db_user:ekLKN5HMpgbNb734@entrex.6qxvklf.mongodb.net/",
    Environment.TESTING: ""
}


class Collections(Enum):
    ENTREX_METADATA_COLLECTION = "entrex_metadata"
    ROI_COLLECTION = "ROI"
    TRIGGER_COLLECTION = "trigger"
    USERS_COLLECTION = "users"
    MUTATION_COLLECTION = "mutation"
    TASKOR_HEARTBEAT_COLLECTION = "taskor_heartbeat"
    IMAGES_METADATA_COLLECTION = "images_metadata"


DATABASE = {
    Environment.PRODUCTION: "",
    Environment.STAGING: "",
    Environment.DEVELOPMENT: "Entrex",
    Environment.TESTING: ""
}


class KnowledgeCenter:
    def __init__(self, mode: Environment):
        logger.info(f"MONGO ENV: {mode}")
        self.mongo_connection = MongoInterface.get_mongo_connection(
            connection_string=MONGO_CONNECTION_STRING[mode],
            database=DATABASE[mode]
        )

        self.entrex_metadata_db_interface: EntrexMetadataDBInterface = EntrexMetadataDBInterface(
            metadata_collection=self.mongo_connection.get_collection(Collections.ENTREX_METADATA_COLLECTION.value)
        )

        self.roi_db_interface: RoiDBInterface = RoiDBInterface(
            roi_collection=self.mongo_connection.get_collection(Collections.ROI_COLLECTION.value)
        )

        self.trigger_db_interface: TriggerDBInterface = TriggerDBInterface(
            trigger_collection=self.mongo_connection.get_collection(Collections.TRIGGER_COLLECTION.value),
            roi_db_interface=self.roi_db_interface
        )

        self.users_db_interface: UserDBInterface = UserDBInterface(
            users_collection=self.mongo_connection.get_collection(Collections.USERS_COLLECTION.value)
        )

        self.mutation_db_interface: MutationDBInterface = MutationDBInterface(
            mutation_collection=self.mongo_connection.get_collection(Collections.MUTATION_COLLECTION.value)
        )

        self.taskor_heartbeat_db_interface: TaskorHeartbeatDBInterface = TaskorHeartbeatDBInterface(
            taskor_heartbeat_collection=self.mongo_connection.get_collection(
                Collections.TASKOR_HEARTBEAT_COLLECTION.value)
        )

        self.images_metadata_db_interface: ImagesMetadataDBInterface = ImagesMetadataDBInterface(
            images_metadata_collection=self.mongo_connection.get_collection(
                Collections.IMAGES_METADATA_COLLECTION.value)
        )
