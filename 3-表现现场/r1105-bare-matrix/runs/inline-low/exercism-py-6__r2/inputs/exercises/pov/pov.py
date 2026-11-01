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

    @staticmethod
    def _clone(node):
        return Tree(node.label, [Tree._clone(c) for c in node.children])

    def _path_labels(self, label, node=None):
        if node is None:
            node = self
        if node.label == label:
            return [label]
        for child in node.children:
            path = self._path_labels(label, child)
            if path is not None:
                return [node.label] + path
        return None

    def from_pov(self, from_node):
        labels = self._path_labels(from_node)
        if labels is None:
            raise ValueError("Tree could not be reoriented")

        root = Tree._clone(self)
        nodes = [root]
        for lab in labels[1:]:
            for child in nodes[-1].children:
                if child.label == lab:
                    nodes.append(child)
                    break

        k = len(nodes) - 1
        kept = []
        for i in range(k):
            kept.append([c for c in nodes[i].children if c.label != nodes[i + 1].label])
        kept.append(list(nodes[k].children))

        if k > 0:
            nodes[k].children = kept[k] + [nodes[k - 1]]
            for i in range(k - 1, 0, -1):
                nodes[i].children = kept[i] + [nodes[i - 1]]
            nodes[0].children = kept[0]

        return nodes[k]

    def path_to(self, from_node, to_node):
        path_from = self._path_labels(from_node)
        if path_from is None:
            raise ValueError("Tree could not be reoriented")
        path_to_node = self._path_labels(to_node)
        if path_to_node is None:
            raise ValueError("No path found")

        i = 0
        while (
            i < len(path_from)
            and i < len(path_to_node)
            and path_from[i] == path_to_node[i]
        ):
            i += 1
        return list(reversed(path_from[i - 1:])) + path_to_node[i:]
