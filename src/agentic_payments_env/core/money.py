"""BRL centavo formatting and parsing. REQ-DOM-01, REQ-DOM-03."""

from __future__ import annotations

import re


def format_brl(centavos: int) -> str:
    """Format integer centavos as Brazilian Real display string."""
    negative = centavos < 0
    amount = abs(centavos)
    reais = amount // 100
    cents = amount % 100
    reais_str = f"{reais:,}".replace(",", ".")
    formatted = f"R${reais_str},{cents:02d}"
    if negative:
        return f"-{formatted}"
    return formatted


def parse_brl(text: str) -> int:
    """Parse a Brazilian Real display string into integer centavos."""
    stripped = text.strip()
    negative = stripped.startswith("-")
    if negative:
        stripped = stripped[1:].strip()
    if not stripped.startswith("R$"):
        msg = f"invalid BRL format: {text!r}"
        raise ValueError(msg)
    body = stripped[2:]
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})*,\d{2}", body):
        msg = f"invalid BRL format: {text!r}"
        raise ValueError(msg)
    reais_part, cents_part = body.rsplit(",", 1)
    reais = int(reais_part.replace(".", ""))
    cents = int(cents_part)
    total = reais * 100 + cents
    return -total if negative else total
