"""Tests for integer-centavos BRL helpers and core hashing."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from agentic_payments_env.contracts.common import validate_centavos
from agentic_payments_env.contracts.domain import Account, ConsentScope
from agentic_payments_env.core.hashing import canonical_json, sha256_hex
from agentic_payments_env.core.money import format_brl, parse_brl
from agentic_payments_env.tools.schemas import CreateTransferArgs

ROUND_TRIP_VALUES = (
    0,
    1,
    99,
    100,
    101,
    999,
    1000,
    1001,
    1234,
    12345,
    123456,
    1_000_000,
    12_345_678,
    123_456_789,
    999_999_999,
    -1,
    -50,
    -100,
    -123456,
    2_000_000_000,
)


@pytest.mark.parametrize("centavos", ROUND_TRIP_VALUES)
def test_format_parse_round_trip(centavos: int) -> None:
    assert parse_brl(format_brl(centavos)) == centavos


def test_format_brl_examples() -> None:
    assert format_brl(123456) == "R$1.234,56"
    assert format_brl(-50) == "-R$0,50"
    assert format_brl(0) == "R$0,00"
    assert format_brl(1) == "R$0,01"
    assert format_brl(99) == "R$0,99"
    assert format_brl(100) == "R$1,00"
    assert format_brl(123456789) == "R$1.234.567,89"


def test_parse_brl_rejects_incomplete_decimal() -> None:
    with pytest.raises(ValueError):
        parse_brl("R$1.5")


def test_canonical_json_is_sorted_and_compact() -> None:
    dumped = canonical_json({"b": 2, "a": 1, "nested": {"z": 0, "y": 1}})
    assert dumped == '{"a":1,"b":2,"nested":{"y":1,"z":0}}'


def test_sha256_hex_utf8() -> None:
    assert sha256_hex("café") == sha256_hex("café")
    assert len(sha256_hex("x")) == 64


def test_no_float_or_decimal_in_core() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "agentic_payments_env" / "core"
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                assert not isinstance(node.value, float), path
            if isinstance(node, ast.Name):
                assert node.id not in {"float", "Decimal"}, path
            if isinstance(node, ast.Attribute):
                assert node.attr != "Decimal", path


@pytest.mark.parametrize("bad_value", [True, False, "100", 1.5, Decimal("100")])
def test_validate_centavos_rejects_non_int(bad_value: object) -> None:
    with pytest.raises(ValueError):
        validate_centavos(bad_value)


def test_account_rejects_bool_balance() -> None:
    with pytest.raises(ValidationError):
        Account(
            account_id="acc_001",
            customer_id="cus_001",
            balance_centavos=True,  # type: ignore[arg-type]
        )


def test_consent_scope_rejects_float_amount() -> None:
    with pytest.raises(ValidationError):
        ConsentScope(
            from_account_id="acc_001",
            pix_key="a@b.com",
            amount_centavos=100.0,  # type: ignore[arg-type]
        )


def test_create_transfer_args_rejects_string_amount() -> None:
    with pytest.raises(ValidationError):
        CreateTransferArgs(
            from_account_id="acc_001",
            pix_key="a@b.com",
            amount_centavos="100",  # type: ignore[arg-type]
            idempotency_key="k1",
        )
