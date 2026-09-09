"""World fixture and mutable world-state contracts.

Satisfies: REQ-CON-01, REQ-CON-05, REQ-CON-07.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from agentic_payments_env.contracts.common import (
    Centavos,
    FrozenModel,
    MutableModel,
    TransferStatus,
    _require_aware,
    aware_datetime_validator,
    validate_centavos,
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
    beneficiaries: list[Beneficiary] = []  # noqa: RUF012
    transfers: list[Transfer] = []  # noqa: RUF012  # history; initiated_by=FIXTURE; COMPLETED only
    principal_customer_id: str  # the customer the agent acts for
    principal_account_id: str  # the account the instruction refers to by default
    balance_history_seed: dict[str, list[tuple[datetime, Centavos]]] = {}  # noqa: RUF012
    # optional older balance snapshots per account, so STALE_READ faults have history at step 1

    _aware = aware_datetime_validator("start_time")

    @model_validator(mode="after")
    def _aware_seed_timestamps(self) -> WorldFixture:
        for snapshots in self.balance_history_seed.values():
            for ts, _amount in snapshots:
                _require_aware(ts)
                validate_centavos(_amount)
        return self


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
    balance_history: dict[str, list[tuple[datetime, Centavos]]]  # per account, appended each step
    transfer_history: list[dict[str, TransferStatus]]  # index = step; transfer_id -> status
    id_counters: dict[str, int]
    initial_total_centavos: Centavos
    initial_balances: dict[str, Centavos]

    _aware = aware_datetime_validator("now")

    @model_validator(mode="after")
    def _aware_history_timestamps(self) -> WorldState:
        for snapshots in self.balance_history.values():
            for ts, _amount in snapshots:
                _require_aware(ts)
                validate_centavos(_amount)
        return self
