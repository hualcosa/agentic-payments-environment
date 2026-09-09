"""World fixture and mutable state contracts. REQ-CON-06, REQ-CON-07."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator

from agentic_payments_env.contracts.common import (
    Centavos,
    FrozenModel,
    MutableModel,
    TransferStatus,
    aware_datetime_validator,
)
from agentic_payments_env.contracts.domain import (
    Account,
    AuditEvent,
    Beneficiary,
    Consent,
    Customer,
    LedgerEntry,
    PixKeyRecord,
    PolicyConfig,
    StepUpChallenge,
    Transfer,
)


class WorldFixture(FrozenModel):
    """Initial state description. Fully explicit; no inheritance between fixtures."""

    start_time: datetime
    tick_seconds: int = Field(default=5, ge=1)
    policy: PolicyConfig = PolicyConfig()
    customers: list[Customer]
    accounts: list[Account]  # MUST include acc_external
    pix_directory: list[PixKeyRecord]
    beneficiaries: list[Beneficiary] = Field(default_factory=list)
    transfers: list[Transfer] = Field(default_factory=list)
    principal_customer_id: str
    principal_account_id: str
    balance_history_seed: dict[str, list[tuple[datetime, Centavos]]] = Field(default_factory=dict)

    @field_validator("start_time", mode="after")
    @classmethod
    def _validate_start_time(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)


class WorldState(MutableModel):
    """The full hidden state. Mutated only by environment/tools code."""

    now: datetime
    tick_seconds: int
    policy: PolicyConfig
    principal_customer_id: str
    principal_account_id: str
    customers: dict[str, Customer]
    accounts: dict[str, Account]
    pix_directory: dict[str, PixKeyRecord]
    beneficiaries: dict[str, Beneficiary]
    consents: dict[str, Consent]
    challenges: dict[str, StepUpChallenge]
    transfers: dict[str, Transfer]
    ledger: list[LedgerEntry]
    audit: list[AuditEvent]
    balance_history: dict[str, list[tuple[datetime, Centavos]]]
    transfer_history: list[dict[str, TransferStatus]]
    id_counters: dict[str, int]
    initial_total_centavos: Centavos
    initial_balances: dict[str, Centavos]

    @field_validator("now", mode="after")
    @classmethod
    def _validate_now(cls, value: datetime) -> datetime:
        return aware_datetime_validator(value)
