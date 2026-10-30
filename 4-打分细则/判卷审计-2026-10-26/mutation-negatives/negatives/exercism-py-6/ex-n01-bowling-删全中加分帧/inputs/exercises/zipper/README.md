# zipper

实现二叉树 zipper：以「当前焦点节点」为中心，支持上下左右移动与就地修改，最后能取回整棵树。

- `Zipper.from_tree(tree)` 从嵌套字典（`{"value": .., "left": .., "right": ..}`）建立 zipper。
- 方法：`value()`、`set_value(v)`、`left()`、`right()`、`up()`、`set_left(t)`、`set_right(t)`、`to_tree()`。
- 走到死路（如叶子节点继续下行）或根节点继续上行时返回 `None`；修改返回可继续链式调用的 zipper。

实现目标文件：`zipper.py`（`Zipper` 类）。
