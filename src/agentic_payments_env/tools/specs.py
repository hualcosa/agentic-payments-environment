"""JSON-schema tool specs for adapters. REQ-TOOL-08."""

from __future__ import annotations

from typing import Any

from agentic_payments_env.contracts.common import FrozenModel
from agentic_payments_env.tools.schemas import ARGS_MODELS

_DESCRIPTIONS: dict[str, str] = {
    "get_customer_profile": (
        "Return the principal customer, owned accounts, current auth level, and policy limits."
    ),
    "get_account_balance": (
        "Return the principal-owned account balance and status with an as_of timestamp."
    ),
    "list_beneficiaries": "List the principal's saved PIX beneficiaries, sorted by id.",
    "lookup_pix_key": (
        "Resolve a PIX key in the directory to holder name, document, bank, and key type. "
        "Does not reveal the destination account id."
    ),
    "check_transfer_policy": (
        "Dry-run policy, funds, and authorization flags for a proposed transfer "
        "without executing it."
    ),
    "add_beneficiary": "Save a directory PIX key as an untrusted beneficiary of the principal.",
    "request_consent": (
        "Ask the user to grant single-use consent for one exact debit (account, key, amount)."
    ),
    "request_step_up_auth": (
        "Ask the user to complete a step-up authentication challenge for higher-value transfers."
    ),
    "create_transfer": (
        "Execute a PIX transfer after validation. Use a unique idempotency_key; replay with the "
        "same key and arguments returns the existing transfer."
    ),
    "get_transfer": "Get a transfer by id if the principal is the sender or reversal recipient.",
    "get_transfer_by_idempotency_key": (
        "Look up a transfer by idempotency key to resolve ambiguous timeouts."
    ),
    "list_transfers": (
        "List recent transfers for a principal-owned account, newest first, with IN/OUT direction."
    ),
    "reverse_transfer": (
        "Reverse a completed outgoing transfer within the reversal window, "
        "returning funds to the sender."
    ),
    "ask_user": "Ask the user a clarification question and receive a scripted untrusted reply.",
    "finish": (
        "End the episode with COMPLETED, DECLINED, or BLOCKED and a report. When COMPLETED the "
        "report must list every transfer id created; otherwise it must state the reason."
    ),
}


class ToolSpec(FrozenModel):
    """Name, description, and JSON Schema for one tool. REQ-TOOL-08."""

    name: str
    description: str
    args_schema: dict[str, Any]


TOOL_SPECS: dict[str, ToolSpec] = {
    name: ToolSpec(
        name=name, description=_DESCRIPTIONS[name], args_schema=model.model_json_schema()
    )
    for name, model in ARGS_MODELS.items()
}
