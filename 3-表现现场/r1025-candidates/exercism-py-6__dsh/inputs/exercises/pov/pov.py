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
        if self.label == label:
            return [self]
        for child in self.children:
            path = child._find_path(label)
            if path is not None:
                return [self] + path
        return None

    def _clone(self):
        return Tree(self.label, [child._clone() for child in self.children])

    def from_pov(self, from_node):
        path = self._find_path(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")

        new_nodes = []
        for index, node in enumerate(path):
            if index == len(path) - 1:
                kept = [child._clone() for child in node.children]
            else:
                path_child = path[index + 1]
                kept = [
                    child._clone()
                    for child in node.children
                    if child is not path_child
                ]
            new_nodes.append(Tree(node.label, kept))

        for index in range(len(new_nodes) - 1, 0, -1):
            new_nodes[index].children.append(new_nodes[index - 1])
        return new_nodes[-1]

    def path_to(self, from_node, to_node):
        source_path = self._find_path(from_node)
        if source_path is None:
            raise ValueError("Tree could not be reoriented")
        target_path = self._find_path(to_node)
        if target_path is None:
            raise ValueError("No path found")

        common = 0
        while (
            common < len(source_path)
            and common < len(target_path)
            and source_path[common].label == target_path[common].label
        ):
            common += 1

        upward = [node.label for node in reversed(source_path[common - 1:])]
        downward = [node.label for node in target_path[common:]]
        return upward + downward
