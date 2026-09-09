"""Tests for BRL formatting and parsing. REQ-DOM-01, REQ-DOM-03."""

from __future__ import annotations

import pytest

from agentic_payments_env.core.hashing import canonical_json, sha256_hex
from agentic_payments_env.core.money import format_brl, parse_brl

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
