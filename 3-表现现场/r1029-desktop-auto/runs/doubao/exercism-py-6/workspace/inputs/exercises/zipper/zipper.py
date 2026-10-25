class Zipper:
    def __init__(self, node, crumbs):
        # crumbs: list of (parent node, "left" or "right") from root down
        self.node = node
        self.crumbs = crumbs

    @staticmethod
    def from_tree(tree):
        return Zipper(tree, [])

    def value(self):
        return self.node["value"]

    def set_value(self, value):
        self.node["value"] = value
        return self

    def left(self):
        if self.node["left"] is None:
            return None
        return Zipper(self.node["left"], self.crumbs + [(self.node, "left")])

    def set_left(self, tree):
        self.node["left"] = tree
        return self

    def right(self):
        if self.node["right"] is None:
            return None
        return Zipper(self.node["right"], self.crumbs + [(self.node, "right")])

    def set_right(self, tree):
        self.node["right"] = tree
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
        return zipper.node
