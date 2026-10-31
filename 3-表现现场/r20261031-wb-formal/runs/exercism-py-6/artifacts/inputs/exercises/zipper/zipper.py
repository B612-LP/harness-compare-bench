import copy


class Zipper:
    def __init__(self, focus, crumbs=None):
        self._focus = focus
        self._crumbs = crumbs if crumbs is not None else []

    @staticmethod
    def from_tree(tree):
        return Zipper(copy.deepcopy(tree))

    def value(self):
        return self._focus["value"]

    def set_value(self, value):
        focus = copy.deepcopy(self._focus)
        focus["value"] = value
        return Zipper(focus, list(self._crumbs))

    def left(self):
        child = self._focus.get("left")
        if child is None:
            return None
        return Zipper(copy.deepcopy(child), self._crumbs + [(self._focus, "left")])

    def set_left(self, tree):
        focus = copy.deepcopy(self._focus)
        focus["left"] = copy.deepcopy(tree)
        return Zipper(focus, list(self._crumbs))

    def right(self):
        child = self._focus.get("right")
        if child is None:
            return None
        return Zipper(copy.deepcopy(child), self._crumbs + [(self._focus, "right")])

    def set_right(self, tree):
        focus = copy.deepcopy(self._focus)
        focus["right"] = copy.deepcopy(tree)
        return Zipper(focus, list(self._crumbs))

    def up(self):
        if not self._crumbs:
            return None
        parent, side = self._crumbs[-1]
        return Zipper(copy.deepcopy(parent), list(self._crumbs[:-1]))

    def to_tree(self):
        node = copy.deepcopy(self._focus)
        for parent, side in reversed(self._crumbs):
            rebuilt = copy.deepcopy(parent)
            rebuilt[side] = node
            node = rebuilt
        return node
