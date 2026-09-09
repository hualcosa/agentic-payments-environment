"""Per-tool argument models. REQ-TOOL-01, REQ-TOOL-02, REQ-TOOL-08, REQ-DOM-06."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agentic_payments_env.contracts.common import Centavos, EpisodeOutcome, FrozenModel


class GetCustomerProfileArgs(FrozenModel):
    """No arguments. REQ-TOOL-02."""


class GetAccountBalanceArgs(FrozenModel):
    account_id: str


class ListBeneficiariesArgs(FrozenModel):
    """No arguments. REQ-TOOL-02."""


class LookupPixKeyArgs(FrozenModel):
    pix_key: str = Field(min_length=1, max_length=77)


class CheckTransferPolicyArgs(FrozenModel):
    from_account_id: str
    pix_key: str = Field(min_length=1, max_length=77)
    amount_centavos: Centavos = Field(gt=0)


class AddBeneficiaryArgs(FrozenModel):
    pix_key: str = Field(min_length=1, max_length=77)
    nickname: str = Field(min_length=1, max_length=80)


class RequestConsentArgs(FrozenModel):
    from_account_id: str
    pix_key: str = Field(min_length=1, max_length=77)
    amount_centavos: Centavos = Field(gt=0)
    description: str = Field(max_length=200)


class RequestStepUpAuthArgs(FrozenModel):
    """No arguments. REQ-TOOL-02."""


class CreateTransferArgs(FrozenModel):
    from_account_id: str
    pix_key: str = Field(min_length=1, max_length=77)
    amount_centavos: Centavos = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=64)
    consent_id: str | None = None
    memo: str = Field(default="", max_length=140)


class GetTransferArgs(FrozenModel):
    transfer_id: str


class GetTransferByIdempotencyKeyArgs(FrozenModel):
    idempotency_key: str = Field(min_length=1, max_length=64)


class ListTransfersArgs(FrozenModel):
    account_id: str
    limit: int = Field(default=20, ge=1, le=100)


class ReverseTransferArgs(FrozenModel):
    transfer_id: str
    reason: str = Field(max_length=140)


class AskUserArgs(FrozenModel):
    question: str = Field(min_length=1, max_length=500)


class FinishArgs(FrozenModel):
    outcome: EpisodeOutcome
    report: str = Field(max_length=2000)


ARGS_MODELS: dict[str, type[BaseModel]] = {
    "get_customer_profile": GetCustomerProfileArgs,
    "get_account_balance": GetAccountBalanceArgs,
    "list_beneficiaries": ListBeneficiariesArgs,
    "lookup_pix_key": LookupPixKeyArgs,
    "check_transfer_policy": CheckTransferPolicyArgs,
    "add_beneficiary": AddBeneficiaryArgs,
    "request_consent": RequestConsentArgs,
    "request_step_up_auth": RequestStepUpAuthArgs,
    "create_transfer": CreateTransferArgs,
    "get_transfer": GetTransferArgs,
    "get_transfer_by_idempotency_key": GetTransferByIdempotencyKeyArgs,
    "list_transfers": ListTransfersArgs,
    "reverse_transfer": ReverseTransferArgs,
    "ask_user": AskUserArgs,
    "finish": FinishArgs,
}
