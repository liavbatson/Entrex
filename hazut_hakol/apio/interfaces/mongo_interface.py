import pymongo.errors as pymongo_errors
from loguru import logger
from pymongo import MongoClient

open_mongo_connection = {}


class MongoInterface:
    def __init__(self, connection_string, database: str):
        logger.info(f"Trying to connect to mongo")
        self.client = MongoClient(
            connection_string,
            maxPoolSize=5
        )
        try:
            self.client.admin.command("ping")
            logger.info(f"Connected to mongo connect")
        except pymongo_errors.ServerSelectionTimeoutError as e:
            logger.info(f"Failed to mongo connect", e)

        self._db = self.client[database]

    def get_collection(self, collection_name: str):
        return self._db[collection_name]

    @classmethod
    def get_mongo_connection(cls, connection_string, database):
        connection_key = (connection_string, database)
        if connection_key not in open_mongo_connection:
            logger.debug("Creating new mongo connection")
            mongo_connection = MongoInterface(connection_string, database)
            open_mongo_connection[connection_key] = mongo_connection
        return open_mongo_connection[connection_key]
