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

    def _path_from_root(self, label):
        """返回从 self 到 label 所在节点的节点路径；找不到返回 None。"""
        if self.label == label:
            return [self]
        for child in self.children:
            found = child._path_from_root(label)
            if found is not None:
                return [self] + found
        return None

    def from_pov(self, from_node):
        path = self._path_from_root(from_node)
        if path is None:
            raise ValueError("Tree could not be reoriented")
        if len(path) == 1:
            return Tree(self.label, list(self.children))

        # 以目标节点为新根，原根方向逐层重挂
        new_root = Tree(path[-1].label, list(path[-1].children))
        current = new_root
        for index in range(len(path) - 2, -1, -1):
            parent = path[index]
            child_on_path = path[index + 1]
            siblings = [node for node in parent.children if node is not child_on_path]
            new_parent = Tree(parent.label, siblings)
            current.children.append(new_parent)
            current = new_parent
        return new_root

    def path_to(self, from_node, to_node):
        source_path = self._path_from_root(from_node)
        if source_path is None:
            raise ValueError("Tree could not be reoriented")
        target_path = self._path_from_root(to_node)
        if target_path is None:
            raise ValueError("No path found")

        # 找最近公共祖先（按节点路径的标签前缀）
        common = 0
        while (
            common < len(source_path)
            and common < len(target_path)
            and source_path[common].label == target_path[common].label
        ):
            common += 1

        upward = [node.label for node in source_path[common:]][::-1]
        downward = [node.label for node in target_path[common:]]
        return upward + downward