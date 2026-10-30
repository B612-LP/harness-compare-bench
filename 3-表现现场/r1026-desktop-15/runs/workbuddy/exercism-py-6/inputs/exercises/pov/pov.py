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

    def _find_path(self, label):
        """Path of nodes from this node down to the node carrying `label`."""
        if self.label == label:
            return [self]
        for child in self.children:
            path = child._find_path(label)
            if path is not None:
                return [self] + path
        return None

    @staticmethod
    def _copy(node):
        return Tree(node.label, [Tree._copy(child) for child in node.children])

    def from_pov(self, from_node):
        path = self._find_path(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")

        # Climb from the target towards the old root: each former parent becomes
        # a child of the level below, keeping its other children in place.
        result = Tree(path[-1].label, [Tree._copy(node) for node in path[-1].children])
        current = result
        for index in range(len(path) - 1, 0, -1):
            parent = path[index - 1]
            child = path[index]
            siblings = [
                Tree._copy(sibling) for sibling in parent.children if sibling is not child
            ]
            parent_node = Tree(parent.label, siblings)
            current.children.append(parent_node)
            current = parent_node
        return result

    def path_to(self, from_node, to_node):
        source_path = self._find_path(from_node)
        if source_path is None:
            raise ValueError("Tree could not be reoriented")
        target_path = self._find_path(to_node)
        if target_path is None:
            raise ValueError("No path found")

        source_labels = [node.label for node in source_path]
        target_labels = [node.label for node in target_path]

        common = 0
        while (
            common < len(source_labels)
            and common < len(target_labels)
            and source_labels[common] == target_labels[common]
        ):
            common += 1

        # Up from the source to the lowest common ancestor, then down to the target.
        return list(reversed(source_labels[common - 1:])) + target_labels[common:]
