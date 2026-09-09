"""AST checks for public API docstrings. REQ-TEST-01."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

REQ = re.compile(r"REQ-[A-Z]+-\d+")
SRC_ROOT = Path("src/agentic_payments_env")


@dataclass(frozen=True)
class SymbolRef:
    path: Path
    qualname: str
    lineno: int


def _is_protocol_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if not node.body:
        return True
    return (
        len(node.body) == 1
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and node.body[0].value.value is Ellipsis
    )


def _public_symbols(path: Path) -> tuple[str | None, list[tuple[ast.AST, str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    module_doc = ast.get_docstring(tree)
    symbols: list[tuple[ast.AST, str]] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            symbols.append((node, node.name))
            for item in node.body:
                if isinstance(
                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not item.name.startswith("_"):
                    symbols.append((item, f"{node.name}.{item.name}"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith(
            "_"
        ):
            symbols.append((node, node.name))
    return module_doc, symbols


def _effective_docstring(
    node: ast.AST,
    qualname: str,
    *,
    module_doc: str | None,
    class_doc: str | None,
) -> str | None:
    own = ast.get_docstring(node)
    if own:
        return own
    if isinstance(node, ast.ClassDef):
        return module_doc
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if _is_protocol_stub(node):
            return class_doc or module_doc
        if "." in qualname and class_doc:
            return class_doc
        return module_doc
    return module_doc


def find_missing_req_docstrings() -> list[SymbolRef]:
    missing: list[SymbolRef] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        module_doc, symbols = _public_symbols(path)
        class_docs: dict[str, str | None] = {}
        for node, qualname in symbols:
            if isinstance(node, ast.ClassDef):
                class_docs[qualname] = ast.get_docstring(node)
        for node, qualname in symbols:
            if isinstance(node, ast.ClassDef):
                class_doc = ast.get_docstring(node)
            else:
                parent = qualname.rsplit(".", 1)[0] if "." in qualname else None
                class_doc = class_docs.get(parent or "")
            doc = _effective_docstring(
                node,
                qualname,
                module_doc=module_doc,
                class_doc=class_doc,
            )
            if not doc or not doc.strip() or not REQ.search(doc):
                missing.append(SymbolRef(path=path, qualname=qualname, lineno=node.lineno))
    return missing


def test_public_symbols_have_req_docstrings() -> None:
    """Every public class/function/method documents owning REQ ids."""
    missing = find_missing_req_docstrings()
    assert not missing, (
        "Missing purpose+REQ docstrings:\n"
        + "\n".join(
            f"  {item.path.relative_to(SRC_ROOT.parent)}:{item.lineno} {item.qualname}"
            for item in missing[:40]
        )
        + (f"\n  ... and {len(missing) - 40} more" if len(missing) > 40 else "")
    )
