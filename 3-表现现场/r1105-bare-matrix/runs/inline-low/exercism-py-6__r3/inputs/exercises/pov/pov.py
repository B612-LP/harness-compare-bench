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

    def _adjacency(self):
        adj = {}

        def visit(node):
            if node.label not in adj:
                adj[node.label] = []
            for child in node.children:
                if child.label not in adj:
                    adj[child.label] = []
                adj[node.label].append(child.label)
                adj[child.label].append(node.label)
                visit(child)

        visit(self)
        return adj

    def from_pov(self, from_node):
        adj = self._adjacency()
        if from_node not in adj:
            raise ValueError("Tree could not be reoriented")

        def build(label, parent):
            node = Tree(label)
            for neighbour in adj[label]:
                if neighbour != parent:
                    node.children.append(build(neighbour, label))
            return node

        return build(from_node, None)

    def path_to(self, from_node, to_node):
        adj = self._adjacency()
        if from_node not in adj:
            raise ValueError("Tree could not be reoriented")
        if to_node not in adj:
            raise ValueError("No path found")

        stack = [(from_node, [from_node])]
        visited = set()
        while stack:
            label, path = stack.pop()
            if label == to_node:
                return path
            visited.add(label)
            for neighbour in adj[label]:
                if neighbour not in visited:
                    stack.append((neighbour, path + [neighbour]))
        raise ValueError("No path found")
