def _copy(node):
    """Deep copy a tree node ({'value', 'left', 'right'})."""
    if node is None:
        return None
    return {
        "value": node["value"],
        "left": _copy(node["left"]),
        "right": _copy(node["right"]),
    }


class Zipper:
    def __init__(self, focus, crumbs=None):
        self._focus = focus
        # Each crumb is (parent_node, side) with side in {"left", "right"}.
        self._crumbs = crumbs if crumbs is not None else []

    @staticmethod
    def from_tree(tree):
        return Zipper(_copy(tree), [])

    def value(self):
        return self._focus["value"]

    def set_value(self, value):
        focus = _copy(self._focus)
        focus["value"] = value
        return Zipper(focus, list(self._crumbs))

    def left(self):
        child = self._focus["left"]
        if child is None:
            return None
        return Zipper(_copy(child), self._crumbs + [(self._focus, "left")])

    def right(self):
        child = self._focus["right"]
        if child is None:
            return None
        return Zipper(_copy(child), self._crumbs + [(self._focus, "right")])

    def set_left(self, tree):
        focus = _copy(self._focus)
        focus["left"] = _copy(tree)
        return Zipper(focus, list(self._crumbs))

    def set_right(self, tree):
        focus = _copy(self._focus)
        focus["right"] = _copy(tree)
        return Zipper(focus, list(self._crumbs))

    def up(self):
        if not self._crumbs:
            return None
        parent, side = self._crumbs[-1]
        parent = _copy(parent)
        parent[side] = _copy(self._focus)
        return Zipper(parent, self._crumbs[:-1])

    def to_tree(self):
        node = _copy(self._focus)
        for parent, side in reversed(self._crumbs):
            parent = _copy(parent)
            parent[side] = node
            node = parent
        return node
