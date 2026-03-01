"""Import resolution and local function definition lookup."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeAlias

FunctionNode: TypeAlias = ast.FunctionDef | ast.AsyncFunctionDef
DefinitionNode: TypeAlias = FunctionNode | ast.ClassDef


class Resolver:
    """Resolve local function/class calls to their AST definitions.

    Caches parsed ASTs and source text to avoid redundant I/O.
    Only resolves imports that point to local project files;
    standard-library and third-party modules are silently skipped.
    """

    def __init__(self, base: Path) -> None:
        self._base = base.resolve()
        self._ast_cache: dict[str, ast.Module | None] = {}
        self._source_cache: dict[str, str | None] = {}
        self._import_cache: dict[str, dict[str, tuple[str, str]]] = {}

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def read_source(self, file: Path) -> str | None:
        """Read *file* and return its contents (cached)."""
        key = str(file.resolve())
        if key not in self._source_cache:
            try:
                self._source_cache[key] = file.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                self._source_cache[key] = None
        return self._source_cache[key]

    def parse_file(self, file: Path) -> ast.Module | None:
        """Parse *file* and return the AST (cached)."""
        key = str(file.resolve())
        if key not in self._ast_cache:
            source = self.read_source(file)
            if source is None:
                self._ast_cache[key] = None
            else:
                try:
                    self._ast_cache[key] = ast.parse(source, filename=key)
                except SyntaxError:
                    self._ast_cache[key] = None
        return self._ast_cache[key]

    def resolve_call(
        self,
        file: Path,
        node: ast.Call,
    ) -> tuple[Path, DefinitionNode] | None:
        """Try to resolve *node* to a local function/class definition.

        Returns ``(file_path, definition_node)`` or ``None``.
        """
        if isinstance(node.func, ast.Name):
            return self._resolve_simple_call(file, node.func.id)
        if isinstance(node.func, ast.Attribute) and isinstance(
            node.func.value, ast.Name
        ):
            return self._resolve_attr_call(file, node.func.value.id, node.func.attr)
        return None

    @staticmethod
    def call_display_name(node: ast.Call) -> str:
        """Return a human-readable display name for a Call node."""
        if isinstance(node.func, ast.Name):
            return f"{node.func.id}()"
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}()"
            return f"{node.func.attr}()"
        return "<call>()"

    @staticmethod
    def get_init(cls_node: ast.ClassDef) -> FunctionNode | None:
        """Return the ``__init__`` method of *cls_node*, or ``None``."""
        return Resolver.get_method(cls_node, "__init__")

    @staticmethod
    def get_method(cls_node: ast.ClassDef, name: str) -> FunctionNode | None:
        """Return the method named *name* from *cls_node*, or ``None``."""
        for item in cls_node.body:
            if (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == name
            ):
                return item
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_simple_call(
        self, file: Path, name: str
    ) -> tuple[Path, DefinitionNode] | None:
        """Resolve ``name()`` -- same-file def or imported name."""
        defn = self._find_def(file, name)
        if defn is not None:
            return (file.resolve(), defn)
        imports = self._get_imports(file)
        if name in imports:
            target_path, original_name = imports[name]
            target = Path(target_path)
            defn = self._find_def(target, original_name)
            if defn is not None:
                return (target, defn)
        return None

    def _resolve_attr_call(
        self, file: Path, obj_name: str, attr: str
    ) -> tuple[Path, DefinitionNode] | None:
        """Resolve ``obj_name.attr()`` -- module or class attribute access."""
        imports = self._get_imports(file)
        if obj_name in imports:
            target_path, _ = imports[obj_name]
            target = Path(target_path)
            defn = self._find_def(target, attr)
            if defn is not None:
                return (target, defn)

        # Fallback: obj_name may be a class (same file or imported).
        method = self._resolve_class_method(file, obj_name, attr)
        if method is not None:
            return method
        return None

    def _resolve_class_method(
        self, file: Path, class_name: str, method_name: str
    ) -> tuple[Path, FunctionNode] | None:
        """Try to resolve ``ClassName.method()`` to a method definition."""
        # 1. Same-file class
        cls = self._find_class(file, class_name)
        if cls is not None:
            method = self.get_method(cls, method_name)
            if method is not None:
                return (file.resolve(), method)

        # 2. Imported class
        imports = self._get_imports(file)
        if class_name in imports:
            target_path, original_name = imports[class_name]
            target = Path(target_path)
            lookup_name = original_name or class_name
            cls = self._find_class(target, lookup_name)
            if cls is not None:
                method = self.get_method(cls, method_name)
                if method is not None:
                    return (target, method)
        return None

    def _find_def(self, file: Path, name: str) -> DefinitionNode | None:
        """Find a top-level function or class definition by *name*."""
        tree = self.parse_file(file)
        if tree is None:
            return None
        for node in ast.iter_child_nodes(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.name == name
            ):
                return node
        return None

    def _find_class(self, file: Path, name: str) -> ast.ClassDef | None:
        """Find a top-level class definition by *name*."""
        tree = self.parse_file(file)
        if tree is None:
            return None
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                return node
        return None

    def _get_imports(self, file: Path) -> dict[str, tuple[str, str]]:
        """Map imported names to ``(resolved_file_path, original_name)``.

        For ``import foo``, the original_name is ``""`` (the module itself).
        For ``from foo import bar``, the original_name is ``"bar"``.
        """
        key = str(file.resolve())
        if key in self._import_cache:
            return self._import_cache[key]

        tree = self.parse_file(file)
        if tree is None:
            self._import_cache[key] = {}
            return {}

        result: dict[str, tuple[str, str]] = {}
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                self._process_import(node, file, result)
            elif isinstance(node, ast.ImportFrom):
                self._process_import_from(node, file, result)

        self._import_cache[key] = result
        return result

    def _process_import(
        self,
        node: ast.Import,
        file: Path,
        result: dict[str, tuple[str, str]],
    ) -> None:
        for alias in node.names:
            local_name = alias.asname or alias.name
            resolved = self._resolve_module(alias.name, file)
            if resolved is not None:
                result[local_name] = (str(resolved), "")

    def _process_import_from(
        self,
        node: ast.ImportFrom,
        file: Path,
        result: dict[str, tuple[str, str]],
    ) -> None:
        if node.level > 0:
            resolved = self._resolve_relative_import(node, file)
        elif node.module is not None:
            resolved = self._resolve_module(node.module, file)
        else:
            return
        if resolved is None:
            return
        for alias in node.names:
            local_name = alias.asname or alias.name
            result[local_name] = (str(resolved), alias.name)

    def _resolve_module(self, module_name: str, from_file: Path) -> Path | None:
        """Resolve a dotted module name to a local ``.py`` file."""
        parts = module_name.split(".")
        search_dirs = [from_file.resolve().parent, self._base]
        for search_dir in search_dirs:
            candidate = search_dir
            for part in parts:
                candidate = candidate / part
            py_file = candidate.with_suffix(".py")
            if py_file.is_file():
                return py_file.resolve()
            pkg_init = candidate / "__init__.py"
            if pkg_init.is_file():
                return pkg_init.resolve()
        return None

    def _resolve_relative_import(
        self, node: ast.ImportFrom, from_file: Path
    ) -> Path | None:
        """Resolve a relative import (``from . import ...``)."""
        base_dir = from_file.resolve().parent
        for _ in range(node.level - 1):
            base_dir = base_dir.parent
        if node.module:
            parts = node.module.split(".")
            candidate = base_dir
            for part in parts:
                candidate = candidate / part
            py_file = candidate.with_suffix(".py")
            if py_file.is_file():
                return py_file.resolve()
            pkg_init = candidate / "__init__.py"
            if pkg_init.is_file():
                return pkg_init.resolve()
        return None
