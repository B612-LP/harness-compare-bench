from json import dumps


class Tree:
    def __init__(self, label, children=None):
        self.label = label
        self.children = children if children is not None else []

    def __dict__(self):
        return {self.label: [c.__dict__() for c in sorted(self.children)]}

    def __str__(self, indent=None):
        return dumps(self.__dict__(), indent=indent)

    def __lt__(self, other):
        return self.label < other.label

    def __eq__(self, other):
        return self.__dict__() == other.__dict__()

    def _find_path(self, target):
        """Return the list of nodes from this root to target, or None."""
        if self.label == target:
            return [self]
        for child in self.children:
            sub = child._find_path(target)
            if sub is not None:
                return [self] + sub
        return None

    def from_pov(self, from_node):
        path = self._find_path(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")

        # Rebuild from the old root down to the new root (target).
        new_node = None
        for i in range(len(path)):
            node = path[i]
            if i < len(path) - 1:
                children = [c for c in node.children if c is not path[i + 1]]
            else:
                children = list(node.children)
            if new_node is not None:
                children = children + [new_node]
            new_node = Tree(node.label, children)
        return new_node

    def path_to(self, from_node, to_node):
        reoriented = self.from_pov(from_node)
        path = reoriented._find_path(to_node)
        if path is None:
            raise ValueError("No path found")
        return [node.label for node in path]
