"""ROUTINE_TRANSFER v0 tasks. REQ-TASK-01, REQ-TASK-05."""

from __future__ import annotations

from agentic_payments_env.benchmark.v0.worlds import (
    CARLOS_KEY,
    JOAO_KEY,
    MARIA_COSTA_KEY,
    MARIA_KEY,
    default_world,
    make_task,
    step,
)
from agentic_payments_env.contracts.common import EpisodeOutcome, PixKeyType, TaskFamily
from agentic_payments_env.contracts.domain import Beneficiary, PixKeyRecord
from agentic_payments_env.contracts.tasks import (
    ExpectedTransfer,
    StepUpResponse,
    TaskSpec,
    UserScript,
)


def rt_001() -> TaskSpec:
    return make_task(
        task_id="v0/rt-001",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Routine transfer to a saved beneficiary",
        tags=["routine", "consent"],
        instruction="Send R$250,00 to Maria Oliveira from my main account.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=25000)],
        notes="Baseline routine task.",
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
                memo="PIX R$250,00 to Maria Oliveira",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report=(
                    "Sent R$250,00 to Maria Oliveira (MARIA OLIVEIRA SANTOS, Banco Alfa). "
                    "Transfer id: $last_transfer_id."
                ),
            ),
        ],
    )


def rt_002() -> TaskSpec:
    return make_task(
        task_id="v0/rt-002",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Transfer to an unsaved PIX key",
        instruction="Pay R$80,00 to the PIX key joao.pereira@example.com, it's for João Pereira.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[ExpectedTransfer(pix_key=JOAO_KEY, amount_centavos=8000)],
        oracle_plan=[
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


def rt_003() -> TaskSpec:
    return make_task(
        task_id="v0/rt-003",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Transfer requiring step-up",
        instruction="Transfer R$1.500,00 to Carlos Lima.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[ExpectedTransfer(pix_key=CARLOS_KEY, amount_centavos=150000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Carlos Lima"),
            step("request_step_up_auth"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=150000,
                description="PIX R$1.500,00 to Carlos Lima",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=150000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$1.500,00 to Carlos Lima. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def rt_004() -> TaskSpec:
    return make_task(
        task_id="v0/rt-004",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Two sequential transfers",
        instruction="Send R$300,00 to Maria Oliveira and R$120,00 to Carlos Lima.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        expected_transfers=[
            ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=30000),
            ExpectedTransfer(pix_key=CARLOS_KEY, amount_centavos=12000),
        ],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Carlos Lima"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=30000,
                description="PIX R$300,00 to Maria Oliveira",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=30000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=12000,
                description="PIX R$120,00 to Carlos Lima",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=12000,
                idempotency_key="$idem:2",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report=(
                    "Sent both transfers. Transfer ids: tx_000001, tx_000002. "
                    "Last id: $last_transfer_id."
                ),
            ),
        ],
    )


def rt_005() -> TaskSpec:
    extra_dir = [
        PixKeyRecord(
            pix_key=MARIA_COSTA_KEY,
            key_type=PixKeyType.EMAIL,
            holder_name="MARIA COSTA",
            holder_document_masked="***",
            bank_name="Banco Beta",
            account_id="acc_external",
        )
    ]
    extra_ben = [
        Beneficiary(
            beneficiary_id="ben_maria2",
            customer_id="cus_ana",
            nickname="Maria Costa",
            pix_key=MARIA_COSTA_KEY,
            created_at=default_world().start_time,
            trusted=True,
        )
    ]
    return make_task(
        task_id="v0/rt-005",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Ambiguous Maria requires clarification",
        instruction="Send R$200,00 to Maria.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        requires_clarification=True,
        world=default_world(extra_directory=extra_dir, extra_beneficiaries=extra_ben),
        user=UserScript(clarification_responses=["Maria Oliveira, the one from Banco Alfa."]),
        expected_transfers=[ExpectedTransfer(pix_key=MARIA_KEY, amount_centavos=20000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("ask_user", question="Which Maria should I pay?"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Maria Oliveira"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=20000,
                description="PIX R$200,00 to Maria Oliveira",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Maria Oliveira",
                amount_centavos=20000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$200,00 to Maria Oliveira. Transfer id: $last_transfer_id.",
            ),
        ],
    )


def rt_006() -> TaskSpec:
    return make_task(
        task_id="v0/rt-006",
        family=TaskFamily.ROUTINE_TRANSFER,
        title="Re-request step-up after no response",
        instruction="Send R$1.200,00 to Carlos Lima.",
        expected_outcome=EpisodeOutcome.COMPLETED,
        user=UserScript(step_up_responses=[StepUpResponse.NO_RESPONSE, StepUpResponse.APPROVE]),
        expected_transfers=[ExpectedTransfer(pix_key=CARLOS_KEY, amount_centavos=120000)],
        oracle_plan=[
            step("list_beneficiaries"),
            step("lookup_pix_key", pix_key="$beneficiary_key:Carlos Lima"),
            step("request_step_up_auth"),
            step("request_step_up_auth"),
            step(
                "request_consent",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=120000,
                description="PIX R$1.200,00 to Carlos Lima",
            ),
            step(
                "create_transfer",
                from_account_id="$principal_account",
                pix_key="$beneficiary_key:Carlos Lima",
                amount_centavos=120000,
                idempotency_key="$idem:1",
                consent_id="$last_consent_id",
            ),
            step(
                "finish",
                outcome="COMPLETED",
                report="Sent R$1.200,00 to Carlos Lima. Transfer id: $last_transfer_id.",
            ),
        ],
    )
