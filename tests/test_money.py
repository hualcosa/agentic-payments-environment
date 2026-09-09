"""Tests for BRL formatting and parsing. REQ-DOM-01, REQ-DOM-03."""

from __future__ import annotations

from decimal import Decimal

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
    1234,
    12345,
    123456,
    1234567,
    12345678,
    123456789,
    -1,
    -50,
    -100,
    -123456789,
    50,
    5,
    999999999,
)


@pytest.mark.parametrize("centavos", ROUND_TRIP_VALUES)
def test_format_parse_round_trip(centavos: int) -> None:
    assert parse_brl(format_brl(centavos)) == centavos


def test_format_examples() -> None:
    assert format_brl(123456) == "R$1.234,56"
    assert format_brl(-50) == "-R$0,50"
    assert format_brl(0) == "R$0,00"


def test_parse_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        parse_brl("R$1.5")


def test_canonical_json_sorted() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_sha256_hex_stable() -> None:
    digest = sha256_hex("hello")
    assert len(digest) == 64
    assert digest == sha256_hex("hello")


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
