from typing import Dict

from bson import ObjectId
from hazut_hakol.core.utils import UserPermissions


class User:
    def __init__(self, username: str, mail: str, hierarchy: str, _id: ObjectId = None,
                 user_permissions: UserPermissions = UserPermissions.VIEWER):
        self._id = _id if _id else ObjectId()
        self.username = username
        self.mail = mail
        self.hierarchy = hierarchy
        self.user_permissions = user_permissions

    def __str__(self):
        return (f"User(user_id={self._id}, username={self.username}, mail={self.mail}, hierarchy={self.hierarchy}, "
                f"user_permissions={self.user_permissions}")

    def __repr__(self):
        return (f"User(user_id={self._id}, username={self.username}, mail={self.mail}, hierarchy={self.hierarchy}, "
                f"user_permissions={self.user_permissions}")

    @classmethod
    def from_mongo_document(cls, user: Dict):
        user_instance = User(
            _id=user["_id"],
            username=user["username"],
            mail=user["mail"],
            hierarchy=user["hierarchy"],
            user_permissions=user["user_permissions"]
        )
        return user_instance

    def to_mongo_document(self) -> Dict:
        return {
            "_id": self._id,
            "username": self.username,
            "mail": self.mail,
            "hierarchy": self.hierarchy,
            "user_permissions": self.user_permissions
        }
