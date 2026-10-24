import copy


class Zipper:
    def __init__(self, tree, crumbs):
        self.tree = tree
        self.crumbs = crumbs

    @staticmethod
    def from_tree(tree):
        return Zipper(copy.deepcopy(tree), [])

    def value(self):
        return self.tree["value"]

    def set_value(self, value):
        self.tree["value"] = value
        return self

    def left(self):
        if self.tree["left"] is None:
            return None
        return Zipper(self.tree["left"], self.crumbs + [(self.tree, "left")])

    def set_left(self, tree):
        self.tree["left"] = copy.deepcopy(tree)
        return self

    def right(self):
        if self.tree["right"] is None:
            return None
        return Zipper(self.tree["right"], self.crumbs + [(self.tree, "right")])

    def set_right(self, tree):
        self.tree["right"] = copy.deepcopy(tree)
        return self

    def up(self):
        if not self.crumbs:
            return None
        parent, _ = self.crumbs[-1]
        return Zipper(parent, self.crumbs[:-1])

    def to_tree(self):
        zipper = self
        while zipper.crumbs:
            zipper = zipper.up()
        return zipper.tree
