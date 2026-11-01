class Zipper:
    def __init__(self, focus, path):
        self._focus = focus
        self._path = path

    @staticmethod
    def from_tree(tree):
        return Zipper(tree, [])

    def value(self):
        return self._focus["value"]

    def set_value(self, value):
        self._focus["value"] = value
        return self

    def left(self):
        child = self._focus.get("left")
        if child is None:
            return None
        breadcrumb = (self._focus["value"], "left", self._focus.get("right"))
        return Zipper(child, self._path + [breadcrumb])

    def set_left(self, tree):
        self._focus["left"] = tree
        return self

    def right(self):
        child = self._focus.get("right")
        if child is None:
            return None
        breadcrumb = (self._focus["value"], "right", self._focus.get("left"))
        return Zipper(child, self._path + [breadcrumb])

    def set_right(self, tree):
        self._focus["right"] = tree
        return self

    def up(self):
        if not self._path:
            return None
        parent_value, direction, sibling = self._path[-1]
        parent = {"value": parent_value, "left": None, "right": None}
        if direction == "left":
            parent["left"] = self._focus
            parent["right"] = sibling
        else:
            parent["right"] = self._focus
            parent["left"] = sibling
        return Zipper(parent, self._path[:-1])

    def to_tree(self):
        zipper = self
        while zipper._path:
            zipper = zipper.up()
        return zipper._focus
