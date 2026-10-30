import copy


class Zipper:
    def __init__(self, tree, parent=None, side=None):
        self._tree = tree
        self._parent = parent
        self._side = side

    @staticmethod
    def from_tree(tree):
        return Zipper(copy.deepcopy(tree))

    def value(self):
        return self._tree["value"]

    def set_value(self, value):
        self._tree["value"] = value
        return self

    def left(self):
        child = self._tree.get("left")
        if child is None:
            return None
        return Zipper(child, self, "left")

    def set_left(self, tree):
        self._tree["left"] = copy.deepcopy(tree)
        return self

    def right(self):
        child = self._tree.get("right")
        if child is None:
            return None
        return Zipper(child, self, "right")

    def set_right(self, tree):
        self._tree["right"] = copy.deepcopy(tree)
        return self

    def up(self):
        if self._parent is None:
            return None
        return Zipper(self._parent._tree, self._parent._parent, self._parent._side)

    def to_tree(self):
        node = self
        while node._parent is not None:
            node = node._parent
        return copy.deepcopy(node._tree)
