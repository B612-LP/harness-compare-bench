# pov

树的「换根视角」：给定一棵带标签的树和一个节点，返回以该节点为新根的树；并给出两节点间路径。

- 骨架里的 `Tree` 类已实现 `__str__` / `__eq__` / `__lt__` 等，**不要改动这些**，只补 `from_pov` 与 `path_to`。
- `from_pov(label)`：目标节点成为根，原父节点成为其子节点，其余子树保持关系；目标不存在抛 `ValueError("Tree could not be reoriented")`。
- `path_to(from_node, to_node)`：返回节点标签列表（含首尾），路径按树上的相邻关系；源不存在抛 `ValueError("Tree could not be reoriented")`，目标不存在抛 `ValueError("No path found")`。

实现目标文件：`pov.py`（`Tree` 类）。
