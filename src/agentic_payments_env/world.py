"""Runtime world state: clock, ledger, invariants, and hashing.

Satisfies: REQ-DOM-04, REQ-DOM-05, REQ-DOM-07, REQ-DOM-16, REQ-DOM-19, REQ-ENV-07,
REQ-CON-07.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Any

from pydantic import PrivateAttr

from agentic_payments_env.contracts.common import (
    ActorKind,
    AuthLevel,
    Centavos,
    Initiator,
    TransferStatus,
)
from agentic_payments_env.contracts.domain import (
    Account,
    AuditEvent,
    Customer,
    LedgerEntry,
    Transfer,
)
from agentic_payments_env.contracts.world import WorldFixture
from agentic_payments_env.contracts.world import WorldState as WorldStateContract
from agentic_payments_env.core.hashing import canonical_json, sha256_hex
from agentic_payments_env.errors import InvariantViolation, TaskValidationError


class WorldState(WorldStateContract):
    """Mutable simulated world; constructed only via ``from_fixture``. REQ-CON-07."""

    _fixture_entry_count: int = PrivateAttr(default=0)
    _fixture_transfer_ids: set[str] = PrivateAttr(default_factory=set)
    _fixture_beneficiary_ids: set[str] = PrivateAttr(default_factory=set)
    _creation_meta: dict[str, tuple[int, str]] = PrivateAttr(default_factory=dict)

    @classmethod
    def from_fixture(cls, fixture: WorldFixture) -> WorldState:
        """Load a fully explicit fixture into dicts and seed histories. REQ-CON-07."""
        accounts = {account.account_id: account for account in fixture.accounts}
        if "acc_external" not in accounts:
            raise TaskValidationError("fixture must include acc_external")
        for record in fixture.pix_directory:
            if record.account_id not in accounts:
                raise TaskValidationError(
                    f"pix_directory account_id {record.account_id!r} does not exist"
                )
        for transfer in fixture.transfers:
            if transfer.status != TransferStatus.COMPLETED:
                raise TaskValidationError("fixture transfers must be COMPLETED")
            if transfer.initiated_by != Initiator.FIXTURE:
                raise TaskValidationError("fixture transfers must have initiated_by=FIXTURE")

        state = cls(
            now=fixture.start_time,
            tick_seconds=fixture.tick_seconds,
            policy=fixture.policy,
            principal_customer_id=fixture.principal_customer_id,
            principal_account_id=fixture.principal_account_id,
            customers={customer.customer_id: customer for customer in fixture.customers},
            accounts=accounts,
            pix_directory={record.pix_key: record for record in fixture.pix_directory},
            beneficiaries={ben.beneficiary_id: ben for ben in fixture.beneficiaries},
            consents={},
            challenges={},
            transfers={transfer.transfer_id: transfer for transfer in fixture.transfers},
            ledger=[],
            audit=[],
            balance_history={},
            transfer_history=[],
            id_counters={},
            initial_total_centavos=0,
            initial_balances={},
        )
        for transfer in fixture.transfers:
            debit = LedgerEntry(
                entry_id=state.next_id("led"),
                transfer_id=transfer.transfer_id,
                account_id=transfer.from_account_id,
                delta_centavos=-transfer.amount_centavos,
                posted_at=transfer.completed_at or fixture.start_time,
            )
            credit = LedgerEntry(
                entry_id=state.next_id("led"),
                transfer_id=transfer.transfer_id,
                account_id=transfer.to_account_id,
                delta_centavos=transfer.amount_centavos,
                posted_at=transfer.completed_at or fixture.start_time,
            )
            state.ledger.append(debit)
            state.ledger.append(credit)
        state._fixture_entry_count = len(state.ledger)
        state._fixture_transfer_ids = set(state.transfers)
        state._fixture_beneficiary_ids = set(state.beneficiaries)
        state.initial_balances = {
            account_id: account.balance_centavos for account_id, account in state.accounts.items()
        }
        state.initial_total_centavos = state.total_centavos()
        history: dict[str, list[tuple[Any, Centavos]]] = {}
        for account_id, account in state.accounts.items():
            seeded = list(fixture.balance_history_seed.get(account_id, ()))
            seeded.append((fixture.start_time, account.balance_centavos))
            history[account_id] = seeded
        state.balance_history = history
        state.transfer_history = [
            {tid: transfer.status for tid, transfer in state.transfers.items()}
        ]
        return state

    def next_id(self, prefix: str) -> str:
        """Allocate the next deterministic id for ``prefix``. REQ-DOM-04, REQ-DOM-05."""
        n = self.id_counters.get(prefix, 0) + 1
        self.id_counters[prefix] = n
        return f"{prefix}_{n:06d}"

    def tick(self) -> None:
        """Advance the clock and snapshot balances and transfer statuses. REQ-DOM-08."""
        self.now = self.now + timedelta(seconds=self.tick_seconds)
        for account_id, account in self.accounts.items():
            self.balance_history.setdefault(account_id, []).append(
                (self.now, account.balance_centavos)
            )
        self.transfer_history.append(
            {tid: transfer.status for tid, transfer in self.transfers.items()}
        )

    def emit(
        self,
        *,
        step_index: int,
        actor: ActorKind,
        kind: str,
        entity_ids: list[str] | None = None,
        payload: dict[str, Any] | None = None,
        visible_to_agent: bool = True,
    ) -> AuditEvent:
        """Append an audit event with the next gap-free seq. REQ-DOM-15."""
        event = AuditEvent(
            seq=len(self.audit) + 1,
            timestamp=self.now,
            step_index=step_index,
            actor=actor,
            kind=kind,
            entity_ids=list(entity_ids or []),
            payload=dict(payload or {}),
            visible_to_agent=visible_to_agent,
        )
        self.audit.append(event)
        self._track_creation(step_index=step_index, kind=kind, entity_ids=event.entity_ids)
        return event

    @staticmethod
    def _normative_creation_kind(entity_id: str, kind: str) -> str | None:
        """Return ``kind`` when it is the normative creation event for ``entity_id``."""
        if entity_id.startswith("tx_") and kind in {"TRANSFER_CREATED", "TRANSFER_REVERSED"}:
            return kind
        if entity_id.startswith("cons_") and kind == "CONSENT_REQUESTED":
            return kind
        if entity_id.startswith("chal_") and kind == "STEP_UP_REQUESTED":
            return kind
        if entity_id.startswith("ben_") and kind == "BENEFICIARY_ADDED":
            return kind
        if entity_id.startswith("led_") and kind in {"TRANSFER_COMPLETED", "TRANSFER_REVERSED"}:
            return kind
        return None

    def _track_creation(self, *, step_index: int, kind: str, entity_ids: list[str]) -> None:
        """Record normative creation step/kind for runtime entities. INV-04."""
        for entity_id in entity_ids:
            creation_kind = self._normative_creation_kind(entity_id, kind)
            if creation_kind is None:
                continue
            skip = (
                (
                    entity_id.startswith("tx_")
                    and (
                        entity_id in self._fixture_transfer_ids
                        or (
                            creation_kind == "TRANSFER_REVERSED"
                            and entity_id in self._creation_meta
                        )
                    )
                )
                or (entity_id.startswith("ben_") and entity_id in self._fixture_beneficiary_ids)
                or (
                    entity_id.startswith("led_")
                    and entity_id
                    in {entry.entry_id for entry in self.ledger[: self._fixture_entry_count]}
                )
            )
            if skip:
                continue
            self._creation_meta[entity_id] = (step_index, creation_kind)

    def principal(self) -> Customer:
        """Return the customer the agent acts for."""
        return self.customers[self.principal_customer_id]

    def owned_account(self, account_id: str) -> Account | None:
        """Return ``account_id`` if it belongs to the principal, else None."""
        account = self.accounts.get(account_id)
        if account is None or account.customer_id != self.principal_customer_id:
            return None
        return account

    def daily_used(self, account_id: str) -> Centavos:
        """Sum COMPLETED non-reversed outgoing transfers for ``account_id`` today."""
        today = self.now.date()
        used = 0
        for transfer in self.transfers.values():
            if transfer.from_account_id != account_id:
                continue
            if transfer.status != TransferStatus.COMPLETED:
                continue
            if transfer.reversal_of is not None:
                continue
            stamped = transfer.completed_at or transfer.created_at
            if stamped.date() != today:
                continue
            used += transfer.amount_centavos
        return used

    def effective_auth_level(self) -> AuthLevel:
        """STEP_UP only while ``step_up_valid_until`` is still in the future."""
        auth = self.principal().auth
        if auth.level != AuthLevel.STEP_UP:
            return AuthLevel.BASIC
        if auth.step_up_valid_until is None or self.now >= auth.step_up_valid_until:
            return AuthLevel.BASIC
        return AuthLevel.STEP_UP

    def post_transfer(self, transfer: Transfer) -> Transfer:
        """Settle a PENDING transfer: ledger, balances, COMPLETED. REQ-DOM-16.

        Does not emit audit; the transfer tool attaches consent/auth payload.
        """
        if transfer.status != TransferStatus.PENDING:
            raise InvariantViolation("INV-POST", "post_transfer requires PENDING status")
        amount = transfer.amount_centavos
        from_acc = self.accounts[transfer.from_account_id]
        to_acc = self.accounts[transfer.to_account_id]
        debit = LedgerEntry(
            entry_id=self.next_id("led"),
            transfer_id=transfer.transfer_id,
            account_id=from_acc.account_id,
            delta_centavos=-amount,
            posted_at=self.now,
        )
        credit = LedgerEntry(
            entry_id=self.next_id("led"),
            transfer_id=transfer.transfer_id,
            account_id=to_acc.account_id,
            delta_centavos=amount,
            posted_at=self.now,
        )
        self.ledger.append(debit)
        self.ledger.append(credit)
        self.accounts[from_acc.account_id] = from_acc.model_copy(
            update={"balance_centavos": from_acc.balance_centavos - amount}
        )
        self.accounts[to_acc.account_id] = to_acc.model_copy(
            update={"balance_centavos": to_acc.balance_centavos + amount}
        )
        completed = transfer.model_copy(
            update={"status": TransferStatus.COMPLETED, "completed_at": self.now}
        )
        self.transfers[completed.transfer_id] = completed
        return completed

    def total_centavos(self) -> Centavos:
        """Sum of every account balance, including acc_external. INV-01."""
        return sum(account.balance_centavos for account in self.accounts.values())

    def check_invariants(self) -> None:
        """Raise ``InvariantViolation`` if INV-01..08 fail. REQ-DOM-19."""
        if self.total_centavos() != self.initial_total_centavos:
            raise InvariantViolation(
                "INV-01",
                "sum of account balances does not match initial_total_centavos",
            )
        entries_by_transfer: dict[str, list[LedgerEntry]] = defaultdict(list)
        runtime_by_account: dict[str, int] = dict.fromkeys(self.accounts, 0)
        for index, entry in enumerate(self.ledger):
            entries_by_transfer[entry.transfer_id].append(entry)
            if index >= self._fixture_entry_count:
                runtime_by_account[entry.account_id] = (
                    runtime_by_account.get(entry.account_id, 0) + entry.delta_centavos
                )
        for transfer in self.transfers.values():
            if transfer.status not in (TransferStatus.COMPLETED, TransferStatus.REVERSED):
                continue
            entries = entries_by_transfer.get(transfer.transfer_id, [])
            if len(entries) != 2:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} requires exactly two ledger entries",
                )
            debits = [item for item in entries if item.delta_centavos < 0]
            credits = [item for item in entries if item.delta_centavos > 0]
            if len(debits) != 1 or len(credits) != 1:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} requires one debit and one credit",
                )
            debit, credit = debits[0], credits[0]
            if debit.delta_centavos == 0 or credit.delta_centavos == 0:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} has zero-valued ledger entry",
                )
            if debit.account_id != transfer.from_account_id:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} debit account mismatch",
                )
            if credit.account_id != transfer.to_account_id:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} credit account mismatch",
                )
            if debit.delta_centavos != -transfer.amount_centavos:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} debit amount mismatch",
                )
            if credit.delta_centavos != transfer.amount_centavos:
                raise InvariantViolation(
                    "INV-02",
                    f"transfer {transfer.transfer_id} credit amount mismatch",
                )
            if debit.delta_centavos + credit.delta_centavos != 0:
                raise InvariantViolation(
                    "INV-02",
                    f"ledger entries for {transfer.transfer_id} do not sum to zero",
                )
        for account_id, account in self.accounts.items():
            expected = self.initial_balances[account_id] + runtime_by_account.get(account_id, 0)
            if account.balance_centavos != expected:
                raise InvariantViolation(
                    "INV-02",
                    f"ledger balance mismatch for {account_id}",
                )
        for account in self.accounts.values():
            if account.balance_centavos < 0:
                raise InvariantViolation("INV-03", f"negative balance on {account.account_id}")
        self._check_audit_completeness()
        seqs = [event.seq for event in self.audit]
        if seqs != list(range(1, len(self.audit) + 1)):
            raise InvariantViolation("INV-05", "audit seq values are not 1..n gap-free")
        timestamps = [event.timestamp for event in self.audit]
        if timestamps != sorted(timestamps):
            raise InvariantViolation("INV-05", "audit timestamps are decreasing")
        seen_consents: set[str] = set()
        for transfer in self.transfers.values():
            if transfer.consent_id is None:
                continue
            if transfer.consent_id in seen_consents:
                raise InvariantViolation("INV-06", "two transfers share a consent_id")
            seen_consents.add(transfer.consent_id)
        seen_keys: set[str] = set()
        for transfer in self.transfers.values():
            if transfer.idempotency_key in seen_keys:
                raise InvariantViolation("INV-07", "two transfers share an idempotency_key")
            seen_keys.add(transfer.idempotency_key)
        reversal_of_counts: dict[str, int] = {}
        for transfer in self.transfers.values():
            if transfer.reversal_of is not None:
                reversal_of_counts[transfer.reversal_of] = (
                    reversal_of_counts.get(transfer.reversal_of, 0) + 1
                )
                original = self.transfers.get(transfer.reversal_of)
                if original is None or original.reversed_by != transfer.transfer_id:
                    raise InvariantViolation(
                        "INV-08",
                        f"{transfer.transfer_id} reversal_of is not paired",
                    )
            if transfer.reversed_by is not None:
                reversal = self.transfers.get(transfer.reversed_by)
                if reversal is None or reversal.reversal_of != transfer.transfer_id:
                    raise InvariantViolation(
                        "INV-08",
                        f"{transfer.transfer_id} reversed_by is not paired",
                    )
        for original_id, count in reversal_of_counts.items():
            if count > 1:
                raise InvariantViolation("INV-08", f"{original_id} reversed more than once")

    def _check_audit_completeness(self) -> None:
        runtime_entities: list[tuple[str, int, str]] = []
        for transfer_id in self.transfers:
            if transfer_id in self._fixture_transfer_ids:
                continue
            meta = self._creation_meta.get(transfer_id)
            if meta is None:
                meta = self._derive_creation_meta(transfer_id)
            if meta is not None:
                runtime_entities.append((transfer_id, meta[0], meta[1]))
        for consent_id in self.consents:
            meta = self._creation_meta.get(consent_id) or self._derive_creation_meta(consent_id)
            if meta is not None:
                runtime_entities.append((consent_id, meta[0], meta[1]))
        for challenge_id in self.challenges:
            meta = self._creation_meta.get(challenge_id) or self._derive_creation_meta(challenge_id)
            if meta is not None:
                runtime_entities.append((challenge_id, meta[0], meta[1]))
        for beneficiary_id in self.beneficiaries:
            if beneficiary_id in self._fixture_beneficiary_ids:
                continue
            meta = self._creation_meta.get(beneficiary_id) or self._derive_creation_meta(
                beneficiary_id
            )
            if meta is not None:
                runtime_entities.append((beneficiary_id, meta[0], meta[1]))
        for entry in self.ledger[self._fixture_entry_count :]:
            meta = self._creation_meta.get(entry.entry_id) or self._derive_creation_meta(
                entry.entry_id
            )
            if meta is not None:
                runtime_entities.append((entry.entry_id, meta[0], meta[1]))

        for entity_id, step_index, kind in runtime_entities:
            if not any(
                event.step_index == step_index
                and event.kind == kind
                and entity_id in event.entity_ids
                for event in self.audit
            ):
                raise InvariantViolation(
                    "INV-04",
                    f"{entity_id} lacks {kind} audit at step {step_index}",
                )

    def _derive_creation_meta(self, entity_id: str) -> tuple[int, str] | None:
        """Derive creation step/kind from audit when tracking missed an emit. INV-04."""
        candidates: list[tuple[int, str]] = []
        for event in self.audit:
            if entity_id not in event.entity_ids:
                continue
            if self._normative_creation_kind(entity_id, event.kind) is not None:
                candidates.append((event.step_index, event.kind))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])

    def canonical_json(self) -> str:
        """Canonical JSON of state excluding ``audit``. REQ-ENV-07, REQ-CON-04."""
        dumped = self.model_dump(mode="json", exclude={"audit"})
        return canonical_json(dumped)

    def hash(self) -> str:
        """SHA-256 of ``canonical_json``. REQ-ENV-07."""
        return sha256_hex(self.canonical_json())
