"""zipper 参考解：带父指针的可变 zipper（焦点树 + 直接修改 + 回到整棵树）。"""

import copy


class Zipper:
    def __init__(self, tree, parent=None):
        self._tree = tree
        self._parent = parent

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
        return Zipper(child, self)

    def set_left(self, tree):
        self._tree["left"] = copy.deepcopy(tree)
        return self

    def right(self):
        child = self._tree.get("right")
        if child is None:
            return None
        return Zipper(child, self)

    def set_right(self, tree):
        self._tree["right"] = copy.deepcopy(tree)
        return self

    def up(self):
        return self._parent

    def to_tree(self):
        node = self
        while node._parent is not None:
            node = node._parent
        return copy.deepcopy(node._tree)