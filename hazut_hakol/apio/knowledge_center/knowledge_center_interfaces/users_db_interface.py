from pymongo.collection import Collection

from hazut_hakol.core.classes.user import User
from hazut_hakol.core.utils import UserPermissions


class UserDBInterface:
    def __init__(self, users_collection: Collection):
        self._users_collection = users_collection

    def get_collection(self) -> Collection:
        return self._users_collection

    def add_user(self, user: User):
        self._users_collection.insert_one(document=user.to_mongo_document())

    def get_user(self, username: str):
        user = self._users_collection.find_one({"username": username})
        if user["user_permissions"].is_upper():
            user["user_permissions"] = user["user_permissions"].lower()
            self.update_user(username, UserPermissions(user["user_permissions"].lower()))
        return User.from_mongo_document(user)

    def update_user(self, username: str, permission: UserPermissions):
        self._users_collection.update_one(
            {"username": username},
            {"$set": {"user_permissions": permission.value}}
        )

    def user_exists(self, username: str):
        if self._users_collection.find_one({"username": username}) is not None:
            return True
        return False