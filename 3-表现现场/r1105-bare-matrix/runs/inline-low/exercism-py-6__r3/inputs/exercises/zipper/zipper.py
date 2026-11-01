class Zipper:
    def __init__(self, tree, path=None):
        self._tree = tree
        self._path = path if path is not None else []

    @staticmethod
    def from_tree(tree):
        return Zipper(tree, [])

    def value(self):
        return self._tree["value"]

    def set_value(self, value):
        new_tree = self._copy(self._tree)
        new_tree["value"] = value
        return Zipper(new_tree, list(self._path))

    def left(self):
        child = self._tree.get("left")
        if child is None:
            return None
        context = ("left", self._tree.get("value"), self._tree.get("right"))
        return Zipper(child, self._path + [context])

    def set_left(self, tree):
        new_tree = self._copy(self._tree)
        new_tree["left"] = self._copy(tree) if tree is not None else None
        return Zipper(new_tree, list(self._path))

    def right(self):
        child = self._tree.get("right")
        if child is None:
            return None
        context = ("right", self._tree.get("value"), self._tree.get("left"))
        return Zipper(child, self._path + [context])

    def set_right(self, tree):
        new_tree = self._copy(self._tree)
        new_tree["right"] = self._copy(tree) if tree is not None else None
        return Zipper(new_tree, list(self._path))

    def up(self):
        if not self._path:
            return None
        direction, parent_value, sibling = self._path[-1]
        parent = {"value": parent_value, "left": None, "right": None}
        if direction == "left":
            parent["left"] = self._tree
            parent["right"] = sibling
        else:
            parent["left"] = sibling
            parent["right"] = self._tree
        return Zipper(parent, self._path[:-1])

    def to_tree(self):
        zipper = self
        while zipper._path:
            zipper = zipper.up()
        return zipper._tree

    def _copy(self, tree):
        if tree is None:
            return None
        return {
            "value": tree["value"],
            "left": self._copy(tree.get("left")),
            "right": self._copy(tree.get("right")),
        }
