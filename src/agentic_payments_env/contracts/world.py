"""World fixture and mutable state contracts. REQ-CON-06, REQ-CON-07."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from agentic_payments_env.contracts.common import (
    Centavos,
    FrozenModel,
    Initiator,
    MutableModel,
    TransferStatus,
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
    """Initial state description. Fully explicit; no inheritance between fixtures. REQ-DOM-10."""

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

    @model_validator(mode="after")
    def _validate_balance_history_seed(self) -> WorldFixture:
        for entries in self.balance_history_seed.values():
            for when, amount in entries:
                aware_datetime_validator(when)
                validate_centavos(amount)
        return self

    @model_validator(mode="after")
    def _validate_fixture_structure(self) -> WorldFixture:
        """Reject duplicate ids and invalid references before reset. REQ-CON-07, REQ-DOM-10/11."""
        customer_ids = [item.customer_id for item in self.customers]
        if len(customer_ids) != len(set(customer_ids)):
            msg = "duplicate customer_id in fixture customers"
            raise ValueError(msg)

        account_ids = [item.account_id for item in self.accounts]
        if len(account_ids) != len(set(account_ids)):
            msg = "duplicate account_id in fixture accounts"
            raise ValueError(msg)

        pix_keys = [item.pix_key for item in self.pix_directory]
        if len(pix_keys) != len(set(pix_keys)):
            msg = "duplicate pix_key in fixture directory"
            raise ValueError(msg)

        beneficiary_ids = [item.beneficiary_id for item in self.beneficiaries]
        if len(beneficiary_ids) != len(set(beneficiary_ids)):
            msg = "duplicate beneficiary_id in fixture beneficiaries"
            raise ValueError(msg)

        transfer_ids = [item.transfer_id for item in self.transfers]
        if len(transfer_ids) != len(set(transfer_ids)):
            msg = "duplicate transfer_id in fixture transfers"
            raise ValueError(msg)

        external_accounts = [item for item in self.accounts if item.account_id == "acc_external"]
        if len(external_accounts) != 1:
            msg = "fixture must contain exactly one acc_external account"
            raise ValueError(msg)
        if external_accounts[0].customer_id != "cus_external":
            msg = "acc_external must belong to cus_external"
            raise ValueError(msg)
        if "cus_external" not in customer_ids:
            msg = "fixture must include cus_external customer"
            raise ValueError(msg)

        account_lookup = {item.account_id: item for item in self.accounts}
        customer_lookup = {item.customer_id for item in self.customers}
        directory_lookup = {item.pix_key: item for item in self.pix_directory}

        if self.principal_customer_id not in customer_lookup:
            msg = "world.principal_customer_id not found in customers"
            raise ValueError(msg)
        principal_account = account_lookup.get(self.principal_account_id)
        if principal_account is None:
            msg = "world.principal_account_id not found in accounts"
            raise ValueError(msg)
        if principal_account.customer_id != self.principal_customer_id:
            msg = "world.principal_account_id does not belong to principal_customer_id"
            raise ValueError(msg)

        for record in self.pix_directory:
            if record.account_id not in account_lookup:
                msg = f"directory account_id not found: {record.account_id}"
                raise ValueError(msg)

        for beneficiary in self.beneficiaries:
            if beneficiary.customer_id not in customer_lookup:
                msg = f"beneficiary customer_id not found: {beneficiary.customer_id}"
                raise ValueError(msg)
            if beneficiary.pix_key not in directory_lookup:
                msg = f"beneficiary pix_key not in directory: {beneficiary.pix_key}"
                raise ValueError(msg)

        for transfer in self.transfers:
            if transfer.status != TransferStatus.COMPLETED:
                msg = "fixture transfers must be COMPLETED"
                raise ValueError(msg)
            if transfer.initiated_by != Initiator.FIXTURE:
                msg = "fixture transfers must have initiated_by=FIXTURE"
                raise ValueError(msg)
            if transfer.from_account_id not in account_lookup:
                msg = f"fixture transfer from_account_id not found: {transfer.from_account_id}"
                raise ValueError(msg)
            if transfer.to_account_id not in account_lookup:
                msg = f"fixture transfer to_account_id not found: {transfer.to_account_id}"
                raise ValueError(msg)
            directory_record = directory_lookup.get(transfer.to_pix_key)
            if (
                directory_record is not None
                and directory_record.account_id != transfer.to_account_id
            ):
                msg = "fixture transfer to_account_id does not match directory record"
                raise ValueError(msg)
            if directory_record is None and transfer.from_account_id != "acc_external":
                msg = f"fixture transfer to_pix_key not in directory: {transfer.to_pix_key}"
                raise ValueError(msg)
            if transfer.completed_at is None:
                msg = "fixture COMPLETED transfers require completed_at"
                raise ValueError(msg)

        return self


class WorldState(MutableModel):
    """The full hidden state. Mutated only by environment/tools code. REQ-DOM-10."""

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

    @model_validator(mode="after")
    def _validate_balance_history(self) -> WorldState:
        for entries in self.balance_history.values():
            for when, amount in entries:
                aware_datetime_validator(when)
                validate_centavos(amount)
        return self
