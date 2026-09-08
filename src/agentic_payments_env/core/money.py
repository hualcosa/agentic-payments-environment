"""Integer-centavos formatting and parsing for BRL display.

Satisfies: REQ-DOM-01, REQ-DOM-03.
"""

from __future__ import annotations


def format_brl(centavos: int) -> str:
    """Format integer centavos as Brazilian real display. REQ-DOM-01, REQ-DOM-03."""
    negative = centavos < 0
    magnitude = abs(centavos)
    whole, frac = divmod(magnitude, 100)
    whole_digits = str(whole)
    grouped: list[str] = []
    while whole_digits:
        grouped.append(whole_digits[-3:])
        whole_digits = whole_digits[:-3]
    whole_str = ".".join(reversed(grouped))
    formatted = f"R${whole_str},{frac:02d}"
    if negative:
        return f"-{formatted}"
    return formatted


def parse_brl(text: str) -> int:
    """Parse a Brazilian real display string into integer centavos. REQ-DOM-01, REQ-DOM-03.

    Used only by tests and the CLI.
    """
    raw = text.strip()
    negative = raw.startswith("-")
    if negative:
        raw = raw[1:]
    if not raw.startswith("R$"):
        raise ValueError(f"not a BRL amount: {text!r}")
    body = raw[2:]
    if "," not in body:
        raise ValueError(f"BRL amount must include centavos: {text!r}")
    whole, frac = body.rsplit(",", 1)
    if len(frac) != 2 or not frac.isdigit():
        raise ValueError(f"BRL amount must have exactly two centavo digits: {text!r}")
    if whole == "" or not whole.replace(".", "").isdigit():
        raise ValueError(f"invalid BRL whole part: {text!r}")
    digits = whole.replace(".", "")
    value = int(digits) * 100 + int(frac)
    return -value if negative else value
