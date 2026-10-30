from copy import deepcopy


class Zipper:
    def __init__(self, tree, parent=None, side=None):
        self._tree = tree
        self._parent = parent
        self._side = side

    @staticmethod
    def from_tree(tree):
        return Zipper(deepcopy(tree))

    def value(self):
        return self._tree["value"]

    def set_value(self, value):
        self._tree["value"] = value
        return self

    def left(self):
        if self._tree["left"] is None:
            return None
        return Zipper(self._tree["left"], self, "left")

    def set_left(self, value):
        self._tree["left"] = deepcopy(value)
        return self

    def right(self):
        if self._tree["right"] is None:
            return None
        return Zipper(self._tree["right"], self, "right")

    def set_right(self, value):
        self._tree["right"] = deepcopy(value)
        return self

    def up(self):
        if self._parent is None:
            return None
        return self._parent

    def to_tree(self):
        node = self
        while node._parent is not None:
            node = node._parent
        return deepcopy(node._tree)
