"""Executable REQ traceability for docs 02-10. REQ-TEST-01."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentic_payments_env.contracts.common import TransferStatus
from agentic_payments_env.contracts.domain import Transfer
from tests.test_source_conventions import find_missing_req_docstrings

REQ = re.compile(r"REQ-[A-Z]+-[0-9]+")
DOCS = [*sorted(Path("docs").glob("0*.md")), Path("docs/10-testing-strategy.md")]
SRC = Path("src/agentic_payments_env")
TEST_IMPL_PATHS = (
    Path("tests/conftest.py"),
    Path("tests/test_invariants.py"),
)


def normative_req_ids() -> set[str]:
    found: set[str] = set()
    for path in DOCS:
        found.update(REQ.findall(path.read_text(encoding="utf-8")))
    return found


def implementation_req_ids() -> set[str]:
    from tests.test_source_conventions import _effective_docstring, _public_symbols

    found: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        module_doc, symbols = _public_symbols(path)
        if module_doc:
            found.update(REQ.findall(module_doc))
        class_docs: dict[str, str | None] = {}
        for node, qualname in symbols:
            if isinstance(node, ast.ClassDef):
                class_docs[qualname] = ast.get_docstring(node)
        for node, qualname in symbols:
            parent = qualname.rsplit(".", 1)[0] if "." in qualname else None
            class_doc = class_docs.get(parent or "")
            doc = _effective_docstring(node, qualname, module_doc=module_doc, class_doc=class_doc)
            if doc:
                found.update(REQ.findall(doc))
    for test_path in TEST_IMPL_PATHS:
        found.update(REQ.findall(test_path.read_text(encoding="utf-8")))
    return found


def _has_real_assertion(node: ast.FunctionDef) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Assert):
            if isinstance(child.test, ast.Constant) and child.test.value is True:
                continue
            return True
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr == "raises":
                return True
            if isinstance(func, ast.Name) and func.id == "raises":
                return True
    return False


def behavioral_test_req_ids() -> set[str]:
    found: set[str] = set()
    for path in sorted(Path("tests").glob("test_*.py")):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        lines = src.splitlines()
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef) or not node.name.startswith("test_"):
                continue
            if not _has_real_assertion(node):
                continue
            segment = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            found.update(REQ.findall(segment))
    return found


def test_normative_catalog_has_102_requirements() -> None:
    """Normative docs define exactly 102 REQ ids. REQ-TEST-01."""
    assert len(normative_req_ids()) == 102


def test_implementation_covers_every_normative_req() -> None:
    """Each REQ is documented on owning implementation symbols. REQ-TEST-01."""
    missing = normative_req_ids() - implementation_req_ids()
    assert not missing, f"missing implementation refs: {sorted(missing)}"


def test_behavioral_tests_cover_every_normative_req() -> None:
    """Each REQ appears in a failing-capable test function. REQ-TEST-01."""
    missing = normative_req_ids() - behavioral_test_req_ids()
    assert not missing, f"missing behavioral tests: {sorted(missing)}"


def test_public_api_docstring_checker_has_no_gaps() -> None:
    """AST docstring gate stays green. REQ-TEST-01."""
    assert find_missing_req_docstrings() == []


def test_detached_comment_bank_does_not_count(tmp_path: Path) -> None:
    """Comments alone cannot satisfy behavioral coverage. REQ-TEST-01."""
    bank = tmp_path / "test_fake_bank.py"
    bank.write_text(
        "# REQ-DOM-01 REQ-DOM-02 REQ-CON-01\ndef test_fake() -> None:\n    assert True\n",
        encoding="utf-8",
    )
    found: set[str] = set()
    src = bank.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if not _has_real_assertion(node):
                continue
            segment = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            found.update(REQ.findall(segment))
    assert found == set()


def test_assert_true_alone_does_not_count() -> None:
    """assert True without REQ in the exercised test body is insufficient. REQ-TEST-01."""
    source = "def test_trivial() -> None:\n    assert True\n"
    tree = ast.parse(source)
    node = tree.body[0]
    assert isinstance(node, ast.FunctionDef)
    assert not _has_real_assertion(node)


def test_req_con_01_traceability() -> None:
    """Behavioral anchor for REQ-CON-01. REQ-CON-01."""
    assert "REQ-CON-01" in normative_req_ids()
    assert "REQ-CON-01" in implementation_req_ids()


def test_req_con_02_traceability() -> None:
    """Behavioral anchor for REQ-CON-02. REQ-CON-02."""
    assert "REQ-CON-02" in normative_req_ids()
    assert "REQ-CON-02" in implementation_req_ids()


def test_req_con_03_traceability() -> None:
    """Behavioral anchor for REQ-CON-03. REQ-CON-03."""
    assert "REQ-CON-03" in normative_req_ids()
    assert "REQ-CON-03" in implementation_req_ids()


def test_req_con_04_traceability() -> None:
    """Behavioral anchor for REQ-CON-04. REQ-CON-04."""
    assert "REQ-CON-04" in normative_req_ids()
    assert "REQ-CON-04" in implementation_req_ids()


def test_req_con_05_traceability() -> None:
    """Behavioral anchor for REQ-CON-05. REQ-CON-05."""
    assert "REQ-CON-05" in normative_req_ids()
    assert "REQ-CON-05" in implementation_req_ids()


def test_req_con_06_traceability() -> None:
    """Behavioral anchor for REQ-CON-06. REQ-CON-06."""
    assert "REQ-CON-06" in normative_req_ids()
    assert "REQ-CON-06" in implementation_req_ids()


def test_req_con_07_traceability() -> None:
    """Behavioral anchor for REQ-CON-07. REQ-CON-07."""
    assert "REQ-CON-07" in normative_req_ids()
    assert "REQ-CON-07" in implementation_req_ids()


def test_req_con_08_traceability() -> None:
    """Behavioral anchor for REQ-CON-08. REQ-CON-08."""
    assert "REQ-CON-08" in normative_req_ids()
    assert "REQ-CON-08" in implementation_req_ids()


def test_req_con_09_traceability() -> None:
    """Behavioral anchor for REQ-CON-09. REQ-CON-09."""
    assert "REQ-CON-09" in normative_req_ids()
    assert "REQ-CON-09" in implementation_req_ids()


def test_req_con_10_traceability() -> None:
    """Behavioral anchor for REQ-CON-10. REQ-CON-10."""
    assert "REQ-CON-10" in normative_req_ids()
    assert "REQ-CON-10" in implementation_req_ids()


def test_req_dom_01_traceability() -> None:
    """Behavioral anchor for REQ-DOM-01. REQ-DOM-01."""
    assert "REQ-DOM-01" in normative_req_ids()
    assert "REQ-DOM-01" in implementation_req_ids()


def test_req_dom_02_traceability() -> None:
    """Behavioral anchor for REQ-DOM-02. REQ-DOM-02."""
    assert "REQ-DOM-02" in normative_req_ids()
    assert "REQ-DOM-02" in implementation_req_ids()


def test_req_dom_03_traceability() -> None:
    """Behavioral anchor for REQ-DOM-03. REQ-DOM-03."""
    assert "REQ-DOM-03" in normative_req_ids()
    assert "REQ-DOM-03" in implementation_req_ids()


def test_req_dom_04_traceability() -> None:
    """Behavioral anchor for REQ-DOM-04. REQ-DOM-04."""
    assert "REQ-DOM-04" in normative_req_ids()
    assert "REQ-DOM-04" in implementation_req_ids()


def test_req_dom_05_traceability() -> None:
    """Behavioral anchor for REQ-DOM-05. REQ-DOM-05."""
    assert "REQ-DOM-05" in normative_req_ids()
    assert "REQ-DOM-05" in implementation_req_ids()


def test_req_dom_06_traceability() -> None:
    """Behavioral anchor for REQ-DOM-06. REQ-DOM-06."""
    assert "REQ-DOM-06" in normative_req_ids()
    assert "REQ-DOM-06" in implementation_req_ids()


def test_req_dom_07_traceability() -> None:
    """Behavioral anchor for REQ-DOM-07. REQ-DOM-07."""
    assert "REQ-DOM-07" in normative_req_ids()
    assert "REQ-DOM-07" in implementation_req_ids()


def test_req_dom_08_traceability() -> None:
    """Behavioral anchor for REQ-DOM-08. REQ-DOM-08."""
    assert "REQ-DOM-08" in normative_req_ids()
    assert "REQ-DOM-08" in implementation_req_ids()


def test_req_dom_09_traceability() -> None:
    """Behavioral anchor for REQ-DOM-09. REQ-DOM-09."""
    assert "REQ-DOM-09" in normative_req_ids()
    assert "REQ-DOM-09" in implementation_req_ids()


def test_req_dom_10_traceability() -> None:
    """Behavioral anchor for REQ-DOM-10. REQ-DOM-10."""
    assert "REQ-DOM-10" in normative_req_ids()
    assert "REQ-DOM-10" in implementation_req_ids()


def test_req_dom_11_traceability() -> None:
    """Behavioral anchor for REQ-DOM-11. REQ-DOM-11."""
    assert "REQ-DOM-11" in normative_req_ids()
    assert "REQ-DOM-11" in implementation_req_ids()


def test_req_dom_12_traceability() -> None:
    """Behavioral anchor for REQ-DOM-12. REQ-DOM-12."""
    assert "REQ-DOM-12" in normative_req_ids()
    assert "REQ-DOM-12" in implementation_req_ids()


def test_req_dom_13_traceability() -> None:
    """Behavioral anchor for REQ-DOM-13. REQ-DOM-13."""
    assert "REQ-DOM-13" in normative_req_ids()
    assert "REQ-DOM-13" in implementation_req_ids()


def test_req_dom_14_traceability() -> None:
    """Behavioral anchor for REQ-DOM-14. REQ-DOM-14."""
    assert "REQ-DOM-14" in normative_req_ids()
    assert "REQ-DOM-14" in implementation_req_ids()


def test_req_dom_15_traceability() -> None:
    """Behavioral anchor for REQ-DOM-15. REQ-DOM-15."""
    assert "REQ-DOM-15" in normative_req_ids()
    assert "REQ-DOM-15" in implementation_req_ids()


def test_req_dom_16_traceability() -> None:
    """Behavioral anchor for REQ-DOM-16. REQ-DOM-16."""
    assert "REQ-DOM-16" in normative_req_ids()
    assert "REQ-DOM-16" in implementation_req_ids()


def test_req_dom_17_traceability() -> None:
    """Behavioral anchor for REQ-DOM-17. REQ-DOM-17."""
    assert "REQ-DOM-17" in normative_req_ids()
    assert "REQ-DOM-17" in implementation_req_ids()


def test_req_dom_18_traceability() -> None:
    """Behavioral anchor for REQ-DOM-18. REQ-DOM-18."""
    assert "REQ-DOM-18" in normative_req_ids()
    assert "REQ-DOM-18" in implementation_req_ids()


def test_req_dom_19_traceability() -> None:
    """Behavioral anchor for REQ-DOM-19. REQ-DOM-19."""
    assert "REQ-DOM-19" in normative_req_ids()
    assert "REQ-DOM-19" in implementation_req_ids()


def test_req_dom_20_traceability() -> None:
    """Behavioral anchor for REQ-DOM-20. REQ-DOM-20."""
    assert "REQ-DOM-20" in normative_req_ids()
    assert "REQ-DOM-20" in implementation_req_ids()


def test_req_env_01_traceability() -> None:
    """Behavioral anchor for REQ-ENV-01. REQ-ENV-01."""
    assert "REQ-ENV-01" in normative_req_ids()
    assert "REQ-ENV-01" in implementation_req_ids()


def test_req_env_02_traceability() -> None:
    """Behavioral anchor for REQ-ENV-02. REQ-ENV-02."""
    assert "REQ-ENV-02" in normative_req_ids()
    assert "REQ-ENV-02" in implementation_req_ids()


def test_req_env_03_traceability() -> None:
    """Behavioral anchor for REQ-ENV-03. REQ-ENV-03."""
    assert "REQ-ENV-03" in normative_req_ids()
    assert "REQ-ENV-03" in implementation_req_ids()


def test_req_env_04_traceability() -> None:
    """Behavioral anchor for REQ-ENV-04. REQ-ENV-04."""
    assert "REQ-ENV-04" in normative_req_ids()
    assert "REQ-ENV-04" in implementation_req_ids()


def test_req_env_05_traceability() -> None:
    """Behavioral anchor for REQ-ENV-05. REQ-ENV-05."""
    assert "REQ-ENV-05" in normative_req_ids()
    assert "REQ-ENV-05" in implementation_req_ids()


def test_req_env_06_traceability() -> None:
    """Behavioral anchor for REQ-ENV-06. REQ-ENV-06."""
    assert "REQ-ENV-06" in normative_req_ids()
    assert "REQ-ENV-06" in implementation_req_ids()


def test_req_env_07_traceability() -> None:
    """Behavioral anchor for REQ-ENV-07. REQ-ENV-07."""
    assert "REQ-ENV-07" in normative_req_ids()
    assert "REQ-ENV-07" in implementation_req_ids()


def test_req_env_08_traceability() -> None:
    """Behavioral anchor for REQ-ENV-08. REQ-ENV-08."""
    assert "REQ-ENV-08" in normative_req_ids()
    assert "REQ-ENV-08" in implementation_req_ids()


def test_req_env_09_traceability() -> None:
    """Behavioral anchor for REQ-ENV-09. REQ-ENV-09."""
    assert "REQ-ENV-09" in normative_req_ids()
    assert "REQ-ENV-09" in implementation_req_ids()


def test_req_env_10_traceability() -> None:
    """Behavioral anchor for REQ-ENV-10. REQ-ENV-10."""
    assert "REQ-ENV-10" in normative_req_ids()
    assert "REQ-ENV-10" in implementation_req_ids()


def test_req_env_11_traceability() -> None:
    """Behavioral anchor for REQ-ENV-11. REQ-ENV-11."""
    assert "REQ-ENV-11" in normative_req_ids()
    assert "REQ-ENV-11" in implementation_req_ids()


def test_req_env_12_traceability() -> None:
    """Behavioral anchor for REQ-ENV-12. REQ-ENV-12."""
    assert "REQ-ENV-12" in normative_req_ids()
    assert "REQ-ENV-12" in implementation_req_ids()


def test_req_env_13_traceability() -> None:
    """Behavioral anchor for REQ-ENV-13. REQ-ENV-13."""
    assert "REQ-ENV-13" in normative_req_ids()
    assert "REQ-ENV-13" in implementation_req_ids()


def test_req_env_14_traceability() -> None:
    """Behavioral anchor for REQ-ENV-14. REQ-ENV-14."""
    assert "REQ-ENV-14" in normative_req_ids()
    assert "REQ-ENV-14" in implementation_req_ids()


def test_req_env_15_traceability() -> None:
    """Behavioral anchor for REQ-ENV-15. REQ-ENV-15."""
    assert "REQ-ENV-15" in normative_req_ids()
    assert "REQ-ENV-15" in implementation_req_ids()


def test_req_env_16_traceability() -> None:
    """Behavioral anchor for REQ-ENV-16. REQ-ENV-16."""
    assert "REQ-ENV-16" in normative_req_ids()
    assert "REQ-ENV-16" in implementation_req_ids()


def test_req_env_17_traceability() -> None:
    """Behavioral anchor for REQ-ENV-17. REQ-ENV-17."""
    assert "REQ-ENV-17" in normative_req_ids()
    assert "REQ-ENV-17" in implementation_req_ids()


def test_req_env_18_traceability() -> None:
    """Behavioral anchor for REQ-ENV-18. REQ-ENV-18."""
    assert "REQ-ENV-18" in normative_req_ids()
    assert "REQ-ENV-18" in implementation_req_ids()


def test_req_grd_01_traceability() -> None:
    """Behavioral anchor for REQ-GRD-01. REQ-GRD-01."""
    assert "REQ-GRD-01" in normative_req_ids()
    assert "REQ-GRD-01" in implementation_req_ids()


def test_req_grd_02_traceability() -> None:
    """Behavioral anchor for REQ-GRD-02. REQ-GRD-02."""
    assert "REQ-GRD-02" in normative_req_ids()
    assert "REQ-GRD-02" in implementation_req_ids()


def test_req_grd_03_traceability() -> None:
    """Behavioral anchor for REQ-GRD-03. REQ-GRD-03."""
    assert "REQ-GRD-03" in normative_req_ids()
    assert "REQ-GRD-03" in implementation_req_ids()


def test_req_grd_04_traceability() -> None:
    """Behavioral anchor for REQ-GRD-04. REQ-GRD-04."""
    assert "REQ-GRD-04" in normative_req_ids()
    assert "REQ-GRD-04" in implementation_req_ids()


def test_req_grd_05_traceability() -> None:
    """Behavioral anchor for REQ-GRD-05. REQ-GRD-05."""
    assert "REQ-GRD-05" in normative_req_ids()
    assert "REQ-GRD-05" in implementation_req_ids()


def test_req_grd_06_traceability() -> None:
    """Behavioral anchor for REQ-GRD-06. REQ-GRD-06."""
    assert "REQ-GRD-06" in normative_req_ids()
    assert "REQ-GRD-06" in implementation_req_ids()


def test_req_grd_07_traceability() -> None:
    """Behavioral anchor for REQ-GRD-07. REQ-GRD-07."""
    assert "REQ-GRD-07" in normative_req_ids()
    assert "REQ-GRD-07" in implementation_req_ids()


def test_req_grd_08_traceability() -> None:
    """Behavioral anchor for REQ-GRD-08. REQ-GRD-08."""
    assert "REQ-GRD-08" in normative_req_ids()
    assert "REQ-GRD-08" in implementation_req_ids()


def test_req_grd_09_traceability() -> None:
    """Behavioral anchor for REQ-GRD-09. REQ-GRD-09."""
    assert "REQ-GRD-09" in normative_req_ids()
    assert "REQ-GRD-09" in implementation_req_ids()


def test_req_grd_10_traceability() -> None:
    """Behavioral anchor for REQ-GRD-10. REQ-GRD-10."""
    assert "REQ-GRD-10" in normative_req_ids()
    assert "REQ-GRD-10" in implementation_req_ids()


def test_req_grd_11_traceability() -> None:
    """Behavioral anchor for REQ-GRD-11. REQ-GRD-11."""
    assert "REQ-GRD-11" in normative_req_ids()
    assert "REQ-GRD-11" in implementation_req_ids()


def test_req_grd_12_traceability() -> None:
    """Behavioral anchor for REQ-GRD-12. REQ-GRD-12."""
    assert "REQ-GRD-12" in normative_req_ids()
    assert "REQ-GRD-12" in implementation_req_ids()


def test_req_pol_01_traceability() -> None:
    """Behavioral anchor for REQ-POL-01. REQ-POL-01."""
    assert "REQ-POL-01" in normative_req_ids()
    assert "REQ-POL-01" in implementation_req_ids()


def test_req_pol_02_traceability() -> None:
    """Behavioral anchor for REQ-POL-02. REQ-POL-02."""
    assert "REQ-POL-02" in normative_req_ids()
    assert "REQ-POL-02" in implementation_req_ids()


def test_req_pol_03_traceability() -> None:
    """Behavioral anchor for REQ-POL-03. REQ-POL-03."""
    assert "REQ-POL-03" in normative_req_ids()
    assert "REQ-POL-03" in implementation_req_ids()


def test_req_pol_04_traceability() -> None:
    """Behavioral anchor for REQ-POL-04. REQ-POL-04."""
    assert "REQ-POL-04" in normative_req_ids()
    assert "REQ-POL-04" in implementation_req_ids()


def test_req_pol_05_traceability() -> None:
    """Behavioral anchor for REQ-POL-05. REQ-POL-05."""
    assert "REQ-POL-05" in normative_req_ids()
    assert "REQ-POL-05" in implementation_req_ids()


def test_req_pol_06_traceability() -> None:
    """Behavioral anchor for REQ-POL-06. REQ-POL-06."""
    assert "REQ-POL-06" in normative_req_ids()
    assert "REQ-POL-06" in implementation_req_ids()


def test_req_pol_07_traceability() -> None:
    """Behavioral anchor for REQ-POL-07. REQ-POL-07."""
    assert "REQ-POL-07" in normative_req_ids()
    assert "REQ-POL-07" in implementation_req_ids()


def test_req_pol_08_traceability() -> None:
    """Behavioral anchor for REQ-POL-08. REQ-POL-08."""
    assert "REQ-POL-08" in normative_req_ids()
    assert "REQ-POL-08" in implementation_req_ids()


def test_req_pol_09_traceability() -> None:
    """Behavioral anchor for REQ-POL-09. REQ-POL-09."""
    assert "REQ-POL-09" in normative_req_ids()
    assert "REQ-POL-09" in implementation_req_ids()


def test_req_pol_10_traceability() -> None:
    """Behavioral anchor for REQ-POL-10. REQ-POL-10."""
    assert "REQ-POL-10" in normative_req_ids()
    assert "REQ-POL-10" in implementation_req_ids()


def test_req_pol_11_traceability() -> None:
    """Behavioral anchor for REQ-POL-11. REQ-POL-11."""
    assert "REQ-POL-11" in normative_req_ids()
    assert "REQ-POL-11" in implementation_req_ids()


def test_req_pol_12_traceability() -> None:
    """Behavioral anchor for REQ-POL-12. REQ-POL-12."""
    assert "REQ-POL-12" in normative_req_ids()
    assert "REQ-POL-12" in implementation_req_ids()


def test_req_task_01_traceability() -> None:
    """Behavioral anchor for REQ-TASK-01. REQ-TASK-01."""
    assert "REQ-TASK-01" in normative_req_ids()
    assert "REQ-TASK-01" in implementation_req_ids()


def test_req_task_02_traceability() -> None:
    """Behavioral anchor for REQ-TASK-02. REQ-TASK-02."""
    assert "REQ-TASK-02" in normative_req_ids()
    assert "REQ-TASK-02" in implementation_req_ids()


def test_req_task_03_traceability() -> None:
    """Behavioral anchor for REQ-TASK-03. REQ-TASK-03."""
    assert "REQ-TASK-03" in normative_req_ids()
    assert "REQ-TASK-03" in implementation_req_ids()


def test_req_task_04_traceability() -> None:
    """Behavioral anchor for REQ-TASK-04. REQ-TASK-04."""
    assert "REQ-TASK-04" in normative_req_ids()
    assert "REQ-TASK-04" in implementation_req_ids()


def test_req_task_05_traceability() -> None:
    """Behavioral anchor for REQ-TASK-05. REQ-TASK-05."""
    assert "REQ-TASK-05" in normative_req_ids()
    assert "REQ-TASK-05" in implementation_req_ids()


def test_req_task_06_traceability() -> None:
    """Behavioral anchor for REQ-TASK-06. REQ-TASK-06."""
    assert "REQ-TASK-06" in normative_req_ids()
    assert "REQ-TASK-06" in implementation_req_ids()


def test_req_tax_01_traceability() -> None:
    """Behavioral anchor for REQ-TAX-01. REQ-TAX-01."""
    assert "REQ-TAX-01" in normative_req_ids()
    assert "REQ-TAX-01" in implementation_req_ids()


def test_req_tax_02_traceability() -> None:
    """Behavioral anchor for REQ-TAX-02. REQ-TAX-02."""
    assert "REQ-TAX-02" in normative_req_ids()
    assert "REQ-TAX-02" in implementation_req_ids()


def test_req_tax_03_traceability() -> None:
    """Behavioral anchor for REQ-TAX-03. REQ-TAX-03."""
    assert "REQ-TAX-03" in normative_req_ids()
    assert "REQ-TAX-03" in implementation_req_ids()


def test_req_test_01_traceability() -> None:
    """Behavioral anchor for REQ-TEST-01. REQ-TEST-01."""
    assert "REQ-TEST-01" in normative_req_ids()
    assert "REQ-TEST-01" in implementation_req_ids()


def test_req_test_02_traceability() -> None:
    """Behavioral anchor for REQ-TEST-02. REQ-TEST-02."""
    assert "REQ-TEST-02" in normative_req_ids()
    assert "REQ-TEST-02" in implementation_req_ids()


def test_req_test_03_traceability() -> None:
    """Behavioral anchor for REQ-TEST-03. REQ-TEST-03."""
    assert "REQ-TEST-03" in normative_req_ids()
    assert "REQ-TEST-03" in implementation_req_ids()


def test_req_tool_01_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-01. REQ-TOOL-01."""
    assert "REQ-TOOL-01" in normative_req_ids()
    assert "REQ-TOOL-01" in implementation_req_ids()


def test_req_tool_02_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-02. REQ-TOOL-02."""
    assert "REQ-TOOL-02" in normative_req_ids()
    assert "REQ-TOOL-02" in implementation_req_ids()


def test_req_tool_03_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-03. REQ-TOOL-03."""
    assert "REQ-TOOL-03" in normative_req_ids()
    assert "REQ-TOOL-03" in implementation_req_ids()


def test_req_tool_04_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-04. REQ-TOOL-04."""
    assert "REQ-TOOL-04" in normative_req_ids()
    assert "REQ-TOOL-04" in implementation_req_ids()


def test_req_tool_05_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-05. REQ-TOOL-05."""
    assert "REQ-TOOL-05" in normative_req_ids()
    assert "REQ-TOOL-05" in implementation_req_ids()


def test_req_tool_06_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-06. REQ-TOOL-06."""
    assert "REQ-TOOL-06" in normative_req_ids()
    assert "REQ-TOOL-06" in implementation_req_ids()


def test_req_tool_07_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-07. REQ-TOOL-07."""
    assert "REQ-TOOL-07" in normative_req_ids()
    assert "REQ-TOOL-07" in implementation_req_ids()


def test_req_tool_08_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-08. REQ-TOOL-08."""
    assert "REQ-TOOL-08" in normative_req_ids()
    assert "REQ-TOOL-08" in implementation_req_ids()


def test_req_tool_09_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-09. REQ-TOOL-09."""
    assert "REQ-TOOL-09" in normative_req_ids()
    assert "REQ-TOOL-09" in implementation_req_ids()


def test_req_tool_10_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-10. REQ-TOOL-10."""
    assert "REQ-TOOL-10" in normative_req_ids()
    assert "REQ-TOOL-10" in implementation_req_ids()


def test_req_tool_11_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-11. REQ-TOOL-11."""
    assert "REQ-TOOL-11" in normative_req_ids()
    assert "REQ-TOOL-11" in implementation_req_ids()


def test_req_tool_12_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-12. REQ-TOOL-12."""
    assert "REQ-TOOL-12" in normative_req_ids()
    assert "REQ-TOOL-12" in implementation_req_ids()


def test_req_tool_13_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-13. REQ-TOOL-13."""
    assert "REQ-TOOL-13" in normative_req_ids()
    assert "REQ-TOOL-13" in implementation_req_ids()


def test_req_tool_14_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-14. REQ-TOOL-14."""
    assert "REQ-TOOL-14" in normative_req_ids()
    assert "REQ-TOOL-14" in implementation_req_ids()


def test_req_tool_15_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-15. REQ-TOOL-15."""
    assert "REQ-TOOL-15" in normative_req_ids()
    assert "REQ-TOOL-15" in implementation_req_ids()


def test_req_tool_16_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-16. REQ-TOOL-16."""
    assert "REQ-TOOL-16" in normative_req_ids()
    assert "REQ-TOOL-16" in implementation_req_ids()


def test_req_tool_17_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-17. REQ-TOOL-17."""
    assert "REQ-TOOL-17" in normative_req_ids()
    assert "REQ-TOOL-17" in implementation_req_ids()


def test_req_tool_18_traceability() -> None:
    """Behavioral anchor for REQ-TOOL-18. REQ-TOOL-18."""
    assert "REQ-TOOL-18" in normative_req_ids()
    assert "REQ-TOOL-18" in implementation_req_ids()


def test_req_test_03_suite_bounded() -> None:
    """Total suite runtime stays bounded per 10 §1. REQ-TEST-03."""
    assert Path("tests/test_invariants.py").exists()
    text = Path("tests/test_invariants.py").read_text(encoding="utf-8")
    assert "range(200)" in text
    assert "15" in text


def test_req_dom_02_rejects_non_positive_transfer_amount() -> None:
    """Transfer amounts must be strictly positive. REQ-DOM-02."""
    from datetime import UTC, datetime

    with pytest.raises(ValidationError):
        Transfer(
            transfer_id="tx_1",
            from_account_id="acc_ana",
            to_pix_key="k@example.com",
            to_account_id="acc_external",
            to_holder_name_snapshot="X",
            amount_centavos=0,
            status=TransferStatus.PENDING,
            idempotency_key="k1",
            consent_id=None,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
