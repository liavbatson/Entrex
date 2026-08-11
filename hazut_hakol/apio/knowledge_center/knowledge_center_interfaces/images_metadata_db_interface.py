from typing import List

from loguru import logger
from pymongo.collection import Collection

from hazut_hakol.core.classes.barak import Sweep


class ImagesMetadataDBInterface:
    def __init__(self, images_metadata_collection: Collection):
        self._images_metadata_collection = images_metadata_collection

    def get_collection(self) -> Collection:
        return self._images_metadata_collection

    def _get_metadata(self) -> dict:
        return self._images_metadata_collection.find()[0] if self._images_metadata_collection.count_documents({}) > 0 else {}

    def image_exists(self, sweep_gid: str) -> bool:
        if self._images_metadata_collection.find_one({'sweep_gid': sweep_gid}):
            return True
        return False
    
    def add_image_metadata_to_db(self, image_metadata: Sweep) -> None:
        if not self.image_exists(sweep_gid=image_metadata.sweep_gid):
            self._images_metadata_collection.insert_one(document=image_metadata.to_mongo_document())
            logger.info(f"Sweep uploaded to db: {image_metadata.sweep_gid}")
        else:
            logger.warning(f"Sweep already exists in db: {image_metadata.sweep_gid}")

    def get_sweeps_metadata(self, sweeps_gids: List[str]) -> List[Sweep]:
        sweeps = self._images_metadata_collection.find({
            'sweep_gid': {"$in": sweeps_gids}
        })
        sweeps = [Sweep.from_mongo_document(sweep) for sweep in sweeps]
        return sweeps

    def delete_image_from_db(self, sweep_gid: str) -> None:
        self._images_metadata_collection.delete_one({'sweep_gid': sweep_gid})
