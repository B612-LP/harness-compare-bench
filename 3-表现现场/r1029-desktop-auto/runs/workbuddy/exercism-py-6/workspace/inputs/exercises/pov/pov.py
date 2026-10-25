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

    def _find(self, label):
        """Return the list of nodes from this node down to `label`."""
        if self.label == label:
            return [self]
        for child in self.children:
            found = child._find(label)
            if found is not None:
                return [self] + found
        return None

    def from_pov(self, from_node):
        path = self._find(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")

        # Rebuild bottom-up: the target keeps its children, and each former
        # parent is appended as a child of its own former child, carrying its
        # remaining subtrees with it.
        representations = {id(path[-1]): Tree(path[-1].label, list(path[-1].children))}
        for index in range(len(path) - 2, -1, -1):
            node = path[index]
            child = path[index + 1]
            siblings = [c for c in node.children if c is not child]
            parent_tree = Tree(node.label, siblings)
            representations[id(child)].children.append(parent_tree)
            representations[id(node)] = parent_tree

        return representations[id(path[-1])]

    def path_to(self, from_node, to_node):
        source_path = self._find(from_node)
        if source_path is None:
            raise ValueError("Tree could not be reoriented")
        target_path = self._find(to_node)
        if target_path is None:
            raise ValueError("No path found")

        common = 0
        while (
            common < len(source_path)
            and common < len(target_path)
            and source_path[common] is target_path[common]
        ):
            common += 1

        upward = [node.label for node in reversed(source_path[common - 1:])]
        downward = [node.label for node in target_path[common:]]
        return upward + downward
