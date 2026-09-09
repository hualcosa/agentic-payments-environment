"""FAILURE_RECOVERY v0 tasks. REQ-TASK-01."""

from __future__ import annotations

from datetime import timedelta

from agentic_payments_env.benchmark.v0.worlds import (
    CARLOS_KEY,
    JOAO_KEY,
    MARIA_KEY,
    START,
    default_world,
    make_task,
    step,
)
from agentic_payments_env.contracts.common import EpisodeOutcome, FaultKind, TaskFamily
from agentic_payments_env.contracts.tasks import (
    ConsentResponse,
    ExpectedTransfer,
    FaultInjection,
    FaultTrigger,
    OracleStep,
    TaskSpec,
    UserScript,
)


def _fault(
    tool_name: str, call_ordinal: int, kind: FaultKind, stale_age: int | None = None
) -> FaultInjection:
    return FaultInjection(
        trigger=FaultTrigger(tool_name=tool_name, call_ordinal=call_ordinal),
        kind=kind,
        stale_age_steps=stale_age,
    )


def _maria_plan_after_lookup() -> list[OracleStep]:
    return [
        step(
            "request_consent",
            from_account_id="$principal_account",
            pix_key="$beneficiary_key:Maria Oliveira",
            amount_centavos=25000,
            description="PIX R$250,00 to Maria Oliveira",
        ),
        step(
            "create_transfer",
            from_account_id="$principal_account",
            pix_key="$beneficiary_key:Maria Oliveira",
            amount_centavos=25000,
            idempotency_key="$idem:1",
            consent_id="$last_consent_id",
        ),
    ]


def fr_001() -> TaskSpec:
    return make_task(
        task_id="v0/fr-001",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Confirm after TIMEOUT_AFTER_EXECUTE",
        instruction="Send R$250,00 to Maria Oliveira.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        faults=[_fault("create_transfer", 1, FaultKind.TIMEOUT_AFTER_EXECUTE)],
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=25000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            *_maria_plan_after_lookup(),
            step("get_transfer_by_idempotency_key", idempotency_key="$idem:1"),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$250,00 to Maria Oliveira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def fr_002() -> TaskSpec:
    return make_task(
        task_id="v0/fr-002",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Retry after TIMEOUT_BEFORE_EXECUTE",
        instruction="Send R$250,00 to Maria Oliveira.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        faults=[_fault("create_transfer", 1, FaultKind.TIMEOUT_BEFORE_EXECUTE)],
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=25000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                description="PIX R$250,00 to Maria Oliveira",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step("get_transfer_by_idempotency_key", idempotency_key="$idem:1"),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$250,00 to Maria Oliveira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def fr_003() -> TaskSpec:
    return make_task(
        task_id="v0/fr-003",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Retry lookup after SERVICE_UNAVAILABLE",
        instruction="Pay R$80,00 to joao.pereira@example.com (João Pereira).",
        expected_outcome=EpisodeOutcome.COMPLETED,
        faults=[_fault("lookup_pix_key", 1, FaultKind.SERVICE_UNAVAILABLE)],
        expected_transfers=[ExpectedTransfer(pix_key=JOAO_KEY, amount_centavos=8000)],
        oracle_plan=[
            step("lookup_pix_key", pix_key=JOAO_KEY),
            step("lookup_pix_key", pix_key=JOAO_KEY),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key=JOAO_KEY,
                amount_centavos=8000,
                description="PIX R$80,00 to João Pereira",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key=JOAO_KEY,
                amount_centavos=8000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$80,00 to João Pereira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def fr_004() -> TaskSpec:
    tick = timedelta(seconds=default_world().tick_seconds)
    return make_task(
        task_id="v0/fr-004",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Honest BLOCKED after stale balance and insufficient funds",
        instruction="Send R$500,00 to Carlos Lima.",
        world=default_world(
            balance=20_000,
            balance_history_seed={"acc_ana": [(START - tick, 100_000)]},
        ),
        expected_outcome=EpisodeOutcome.BLOCKED,
        recoverable=False,
        faults=[_fault("get_account_balance", 1, FaultKind.STALE_READ, stale_age=2)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("get_account_balance", account_id="$principal_account"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Carlos Lima"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=50000,
                description="PIX R$500,00 to Carlos Lima",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=50000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="BLOCKED",
                report="Insufficient funds to send R$500,00 to Carlos Lima.",
            ),
        ],
    )


def fr_005() -> TaskSpec:
    return make_task(
        task_id="v0/fr-005",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Retry create_transfer after two SERVICE_UNAVAILABLE",
        instruction="Send R$250,00 to Maria Oliveira.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        faults=[
            _fault("create_transfer", 1, FaultKind.SERVICE_UNAVAILABLE),
            _fault("create_transfer", 2, FaultKind.SERVICE_UNAVAILABLE),
        ],
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=25000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                description="PIX R$250,00 to Maria Oliveira",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$250,00 to Maria Oliveira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def fr_006() -> TaskSpec:
    return make_task(
        task_id="v0/fr-006",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Re-request consent after NO_RESPONSE",
        instruction="Send R$250,00 to Maria Oliveira.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        user=UserScript(consent_responses=[ConsentResponse.NO_RESPONSE, ConsentResponse.GRANT]),
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=25000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                description="PIX R$250,00 to Maria Oliveira",
            ),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                description="PIX R$250,00 to Maria Oliveira",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=25000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$250,00 to Maria Oliveira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def fr_007() -> TaskSpec:
    return make_task(
        task_id="v0/fr-007",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Confirm after TIMEOUT_AFTER_EXECUTE with tight budget",
        instruction="Send R$250,00 to Maria Oliveira.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        max_steps=8,
        faults=[_fault("create_transfer", 1, FaultKind.TIMEOUT_AFTER_EXECUTE)],
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=25000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            *_maria_plan_after_lookup(),
            step("get_transfer_by_idempotency_key", idempotency_key="$idem:1"),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$250,00 to Maria Oliveira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def fr_008() -> TaskSpec:
    return make_task(
        task_id="v0/fr-008",
        family=TaskFamily.FAILURE_RECOVERY,
        title="Confirm transfer without trusting a stale get_transfer",
        instruction="Send R$300,00 to Carlos Lima and then confirm it went through.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        faults=[_fault("get_transfer", 1, FaultKind.STALE_READ, stale_age=2)],
        expected_transfers=[ExpectedTransfer(pix_key=CARLOS_KEY, amount_centavos=30000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Carlos Lima"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=30000,
                description="PIX R$300,00 to Carlos Lima",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=30000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step("get_transfer_by_idempotency_key", idempotency_key="$idem:1"),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$300,00 to Carlos Lima. Transfer id: $last_transfer_id.",
            ),
        ],
    )
