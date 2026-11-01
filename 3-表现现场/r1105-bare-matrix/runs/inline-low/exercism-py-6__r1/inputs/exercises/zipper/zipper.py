import copy


class Zipper:
    def __init__(self, focus, crumbs):
        self.focus = focus
        self.crumbs = crumbs

    @staticmethod
    def from_tree(tree):
        return Zipper(copy.deepcopy(tree), [])

    def value(self):
        return self.focus["value"]

    def set_value(self, value):
        focus = copy.deepcopy(self.focus)
        focus["value"] = value
        return Zipper(focus, self.crumbs)

    def left(self):
        if self.focus.get("left") is None:
            return None
        parent = copy.deepcopy(self.focus)
        child = copy.deepcopy(self.focus["left"])
        return Zipper(child, self.crumbs + [(parent, "left")])

    def set_left(self, tree):
        focus = copy.deepcopy(self.focus)
        focus["left"] = copy.deepcopy(tree)
        return Zipper(focus, self.crumbs)

    def right(self):
        if self.focus.get("right") is None:
            return None
        parent = copy.deepcopy(self.focus)
        child = copy.deepcopy(self.focus["right"])
        return Zipper(child, self.crumbs + [(parent, "right")])

    def set_right(self, tree):
        focus = copy.deepcopy(self.focus)
        focus["right"] = copy.deepcopy(tree)
        return Zipper(focus, self.crumbs)

    def up(self):
        if not self.crumbs:
            return None

        parent, direction = self.crumbs[-1]
        new_parent = copy.deepcopy(parent)
        new_parent[direction] = copy.deepcopy(self.focus)
        return Zipper(new_parent, self.crumbs[:-1])

    def to_tree(self):
        node = copy.deepcopy(self.focus)
        for parent, direction in reversed(self.crumbs):
            new_parent = copy.deepcopy(parent)
            new_parent[direction] = node
            node = new_parent
        return node
