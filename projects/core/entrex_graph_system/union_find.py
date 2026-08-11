from typing import Dict, List


class UnionFind:
    def __init__(self, items: List[str] = None):
        if items:
            self.parent = {item: item for item in items}
        else:
            self.parent = {}
        self.num_components = 0

    def add(self, item: str):
        if item not in self.parent:
            self.parent[item] = item
            self.num_components += 1

    def find(self, x: str) -> str:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  
        return self.parent[x]

    def union(self, x: str, y: str):
        self.add(x)
        self.add(y)
        px, py = self.find(x), self.find(y)
        if px != py:
            self.parent[px] = py
            self.num_components -= 1

    def get_connected_components(self) -> Dict[str, List[str]]:
        components: Dict[str, List[str]] = {}
        for item in self.parent:
            root = self.find(item)
            components.setdefault(root, []).append(item)
        return components

    def get_component(self, item: str) -> List[str]:
        root = self.find(item)
        return self.get_connected_components()[root]