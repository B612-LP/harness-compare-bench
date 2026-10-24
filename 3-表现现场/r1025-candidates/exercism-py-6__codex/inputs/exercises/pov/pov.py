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

    def from_pov(self, from_node):
        nodes, parents = self._index_tree()
        if from_node not in nodes:
            raise ValueError("Tree could not be reoriented")

        def rebuild(node, previous):
            parent = parents[node.label]
            children = [
                rebuild(child, node)
                for child in node.children
                if child is not previous
            ]
            if parent is not None and parent is not previous:
                children.append(rebuild(parent, node))
            return Tree(node.label, children)

        return rebuild(nodes[from_node], None)

    def path_to(self, from_node, to_node):
        nodes, parents = self._index_tree()
        if from_node not in nodes:
            raise ValueError("Tree could not be reoriented")
        if to_node not in nodes:
            raise ValueError("No path found")

        def ancestry(label):
            path = []
            while label is not None:
                path.append(label)
                parent = parents[label]
                label = parent.label if parent is not None else None
            return path

        source_path = ancestry(from_node)
        destination_path = ancestry(to_node)
        destination_labels = set(destination_path)

        meeting = next(label for label in source_path if label in destination_labels)
        destination_tail = []
        for label in destination_path:
            if label == meeting:
                break
            destination_tail.append(label)

        return source_path[: source_path.index(meeting) + 1] + list(
            reversed(destination_tail)
        )

    def _index_tree(self):
        nodes = {}
        parents = {}

        def walk(node, parent):
            nodes[node.label] = node
            parents[node.label] = parent
            for child in node.children:
                walk(child, node)

        walk(self, None)
        return nodes, parents
