from typing import Dict


class BarakAsset:
    def __init__(
            self,
            id: str,
            asset_type: str,
            url: str
    ):
        self.id = id
        self.asset_type = asset_type
        self.url = url

    def __str__(self):
        return (
            f"ID: {self.id}\n"
            f"Type: {self.asset_type}\n"
            f"Url: {self.url}\n"
        )

    def __repr__(self):
        return (
            f"ID: {self.id}\n"
            f"Type: {self.asset_type}\n"
            f"Url: {self.url}\n"
        )

    def to_dict(self) -> Dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, asset_raw: Dict):
        cls_obj = cls(**asset_raw)
        return cls_obj

    @classmethod
    def parse_from_barak_dict(cls, asset_metadata_raw: Dict):
        return BarakAsset(
            id=asset_metadata_raw["ID"],
            asset_type=asset_metadata_raw["Type"],
            url=asset_metadata_raw["Url"]
        )

    @classmethod
    def parse_assets(cls, assets_raw):
        asset_dict = {}
        if assets_raw is None:
            return asset_dict

        for asset_raw in assets_raw:
            asset = BarakAsset.parse_from_barak_dict(asset_raw)
            asset_dict[asset.asset_type] = asset
        return asset_dict
