import copy


class Zipper:
    def __init__(self, tree, path):
        self._tree = tree
        self._path = path

    @staticmethod
    def from_tree(tree):
        return Zipper(copy.deepcopy(tree), [])

    def _node(self):
        node = self._tree
        for direction in self._path:
            node = node["left"] if direction == "L" else node["right"]
        return node

    def value(self):
        return self._node()["value"]

    def set_value(self, value):
        self._node()["value"] = value
        return self

    def left(self):
        if self._node()["left"] is None:
            return None
        return Zipper(self._tree, self._path + ["L"])

    def set_left(self, tree):
        self._node()["left"] = copy.deepcopy(tree)
        return self

    def right(self):
        if self._node()["right"] is None:
            return None
        return Zipper(self._tree, self._path + ["R"])

    def set_right(self, tree):
        self._node()["right"] = copy.deepcopy(tree)
        return self

    def up(self):
        if not self._path:
            return None
        return Zipper(self._tree, self._path[:-1])

    def to_tree(self):
        return copy.deepcopy(self._tree)
