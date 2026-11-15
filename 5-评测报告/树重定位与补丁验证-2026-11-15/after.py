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
        """Return list of nodes from root to the node with target label."""
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

        # Start at the new root (the target node) with its original children.
        rebuilt = Tree(path[-1].label, list(path[-1].children))
        for i in range(len(path) - 2, -1, -1):
            original = path[i]
            next_on_path = path[i + 1]
            siblings = [
                child for child in original.children if child is not next_on_path
            ]
            parent_node = Tree(original.label, siblings)
            rebuilt = Tree(
                rebuilt.label,
                list(rebuilt.children) + [parent_node],
            )
        return rebuilt

    def path_to(self, from_node, to_node):
        reoriented = self.from_pov(from_node)
        path = reoriented._find_path(to_node)
        if path is None:
            raise ValueError("No path found")
        return [node.label for node in path]
