from abc import ABC, abstractmethod
from pathlib import Path


class AssetSenderInterface(ABC):
    @abstractmethod
    def send_single_asset(self, product_path: Path):
        ...