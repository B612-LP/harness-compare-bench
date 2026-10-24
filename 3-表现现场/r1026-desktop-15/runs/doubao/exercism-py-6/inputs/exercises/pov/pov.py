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
        stack = [(self, [self])]
        while stack:
            node, path = stack.pop()
            if node.label == target:
                return path
            for child in node.children:
                stack.append((child, path + [child]))
        return None

    def from_pov(self, from_node):
        path = self._find_path(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")

        def clone(node):
            return Tree(node.label, [clone(c) for c in node.children])

        # Build from the old root down toward the new root; each node
        # adopts the already-rebuilt subtree of its predecessor as a child.
        built = None
        for i, node in enumerate(path):
            if i < len(path) - 1:
                children = [
                    clone(c) for c in node.children if c is not path[i + 1]
                ]
            else:
                children = [clone(c) for c in node.children]
            if built is not None:
                children.append(built)
            built = Tree(node.label, children)
        return built

    def path_to(self, from_node, to_node):
        reoriented = self.from_pov(from_node)
        path = reoriented._find_path(to_node)
        if path is None:
            raise ValueError("No path found")
        return [node.label for node in path]
