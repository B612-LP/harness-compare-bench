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

    def _build_graph(self):
        graph = {}

        def visit(node):
            graph.setdefault(node.label, [])
            for child in node.children:
                graph.setdefault(child.label, [])
                graph[node.label].append(child.label)
                graph[child.label].append(node.label)
                visit(child)

        visit(self)
        return graph

    def from_pov(self, from_node):
        graph = self._build_graph()

        if from_node not in graph:
            raise ValueError("Tree could not be reoriented")

        def build(label, parent):
            tree = Tree(label)
            for neighbor in graph[label]:
                if neighbor != parent:
                    tree.children.append(build(neighbor, label))
            return tree

        return build(from_node, None)

    def path_to(self, from_node, to_node):
        graph = self._build_graph()

        if from_node not in graph:
            raise ValueError("Tree could not be reoriented")
        if to_node not in graph:
            raise ValueError("No path found")

        stack = [(from_node, [from_node])]
        visited = {from_node}

        while stack:
            node, path = stack.pop()
            if node == to_node:
                return path

            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append((neighbor, path + [neighbor]))

        raise ValueError("No path found")
