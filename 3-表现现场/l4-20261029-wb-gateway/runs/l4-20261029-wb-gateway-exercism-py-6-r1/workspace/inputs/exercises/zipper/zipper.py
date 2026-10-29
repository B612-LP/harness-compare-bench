import copy


class Zipper:
    """A zipper over binary trees of {"value", "left", "right"} dicts.

    Each instance is immutable: navigation and modification return a new
    zipper, so unrelated branches can be reused freely.
    """

    def __init__(self, tree, path=()):
        self._tree = tree
        self._path = tuple(path)

    @staticmethod
    def from_tree(tree):
        return Zipper(copy.deepcopy(tree) if tree is not None else None, ())

    # -- helpers ---------------------------------------------------------
    def _node(self):
        node = self._tree
        for step in self._path:
            if node is None:
                return None
            node = node[step]
        return node

    def _replace(self, node, path=None):
        tree = copy.deepcopy(self._tree)
        path = self._path if path is None else path
        if not path:
            return node
        parent = tree
        for step in path[:-1]:
            parent = parent[step]
        parent[path[-1]] = node
        return tree

    def _with_node(self, node):
        return Zipper(self._replace(node), self._path)

    # -- inspection ------------------------------------------------------
    def value(self):
        node = self._node()
        return None if node is None else node["value"]

    # -- navigation ------------------------------------------------------
    def left(self):
        node = self._node()
        if node is None or node.get("left") is None:
            return None
        return Zipper(self._tree, self._path + ("left",))

    def right(self):
        node = self._node()
        if node is None or node.get("right") is None:
            return None
        return Zipper(self._tree, self._path + ("right",))

    def up(self):
        if not self._path:
            return None
        return Zipper(self._tree, self._path[:-1])

    # -- modification ----------------------------------------------------
    def set_value(self, value):
        node = self._node()
        if node is None:
            return None
        updated = dict(node)
        updated["value"] = value
        return self._with_node(updated)

    def set_left(self, tree):
        node = self._node()
        if node is None:
            return None
        updated = dict(node)
        updated["left"] = copy.deepcopy(tree)
        return self._with_node(updated)

    def set_right(self, tree):
        node = self._node()
        if node is None:
            return None
        updated = dict(node)
        updated["right"] = copy.deepcopy(tree)
        return self._with_node(updated)

    # -- extraction ------------------------------------------------------
    def to_tree(self):
        return copy.deepcopy(self._tree)
