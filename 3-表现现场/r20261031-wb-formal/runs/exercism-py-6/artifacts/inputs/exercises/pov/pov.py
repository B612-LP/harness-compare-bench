from json import dumps


def _clone(node):
    return Tree(node.label, [_clone(child) for child in node.children])


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
        if self.label == label:
            return [self]
        for child in self.children:
            found = child._find_path(label)
            if found is not None:
                return [self] + found
        return None

    def from_pov(self, from_node):
        path = self._find_path(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")

        root = _clone(path[-1])
        attach = root
        for index in range(len(path) - 2, -1, -1):
            ancestor = path[index]
            child_on_path = path[index + 1]
            siblings = [
                _clone(child)
                for child in ancestor.children
                if child is not child_on_path
            ]
            new_ancestor = Tree(ancestor.label, [])
            attach.children = attach.children + [new_ancestor]
            new_ancestor.children = siblings
            attach = new_ancestor
        return root

    def path_to(self, from_node, to_node):
        from_path = self._find_path(from_node)
        if from_path is None:
            raise ValueError("Tree could not be reoriented")
        to_path = self._find_path(to_node)
        if to_path is None:
            raise ValueError("No path found")

        from_labels = [node.label for node in from_path]
        to_labels = [node.label for node in to_path]
        common = 0
        while (
            common < len(from_labels)
            and common < len(to_labels)
            and from_labels[common] == to_labels[common]
        ):
            common += 1

        upward = list(reversed(from_labels[common:]))
        downward = to_labels[common - 1:]
        return upward + downward
