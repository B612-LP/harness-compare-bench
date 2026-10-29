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

    # -- helpers ---------------------------------------------------------
    def _find(self, label):
        if self.label == label:
            return self
        for child in self.children:
            found = child._find(label)
            if found is not None:
                return found
        return None

    def _parents(self, parent=None, mapping=None):
        if mapping is None:
            mapping = {}
        mapping[id(self)] = parent
        for child in self.children:
            child._parents(self, mapping)
        return mapping

    @staticmethod
    def _build(node, came_from, parents):
        parent = parents.get(id(node))
        children = [
            Tree._build(child, node, parents)
            for child in node.children
            if child is not came_from
        ]
        if parent is not None and parent is not came_from:
            children.append(Tree._build(parent, node, parents))
        return Tree(node.label, children)

    def _path(self, target, trail):
        trail = trail + [self.label]
        if self.label == target:
            return trail
        for child in self.children:
            found = child._path(target, trail)
            if found is not None:
                return found
        return None

    # -- perspective -----------------------------------------------------
    def from_pov(self, from_node):
        node = self._find(from_node)
        if node is None:
            raise ValueError("Tree could not be reoriented")
        return Tree._build(node, None, self._parents())

    def path_to(self, from_node, to_node):
        if self._find(from_node) is None:
            raise ValueError("Tree could not be reoriented")
        rerooted = self.from_pov(from_node)
        path = rerooted._path(to_node, [])
        if path is None:
            raise ValueError("No path found")
        return path
