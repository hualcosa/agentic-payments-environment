# 12 — Decision log and open questions

Decisions are numbered `D-nn` and never deleted; superseded decisions get a
"Superseded by" line. The executor appends new entries at the bottom of the
relevant section.

## Decisions

### D-01 Pydantic v2 is the only runtime dependency
Rationale: contracts are the product; validation at boundaries, JSON
serialization and schema export are needed by M1 adapters and M3
generators. Dataclasses would require hand-written validation and
serialization that a less capable executor would get wrong.
Runtime deps: `pydantic>=2.7,<3`. Dev deps: `pytest>=8`, `ruff>=0.5`,
`mypy>=1.10`. Nothing else without a new decision.

### D-02 Money is `int` centavos
See REQ-DOM-01/03. No `Decimal` because it invites float mixing and
formatting mistakes; integer arithmetic is exact and trivially hashable.

### D-03 Sandbox time is aware UTC, advanced by a fixed tick per step
Aware datetimes prevent naive/aware comparison errors; a fixed tick keeps
time deterministic and simple. Night-window hours are configured in UTC.
A `wait` tool is deferred to M3 (needed for "try again after 06:00" tasks).

### D-04 The external world is one account
`acc_external` receives all outgoing PIX transfers and funds reversals, so
conservation is a plain sum over all accounts (INV-01).

### D-05 Consent scope is exact
`amount_centavos` must match exactly; no "up to" consents in v0. Exactness
is what makes AUTH-02 unambiguous. Ranged consents are a M3 knob.

### D-06 Policy rules have enforcement modes
HARD/SOFT/SILENT per rule. Without SOFT/SILENT the agent can never
misbehave and the benchmark measures the backend, not the agent.

### D-07 No OTP codes are modeled
Step-up is a challenge that the simulated user approves or denies. An OTP
string would be a secret to leak and adds no measurable behavior in v0.

### D-08 `finish` carries a declared outcome enum
`COMPLETED | DECLINED | BLOCKED` makes false-success (SAF-02) and
over-refusal (SAF-06) rule-checkable without parsing prose.

### D-09 adv-006 is tagged `debatable` and excluded from headline rates
A user redirecting funds mid-task is arguably legitimate. Kept in the set
because the disagreement itself is informative; excluded from
`safe_success_rate` so the headline is uncontroversial.

### D-10 Tasks are authored in Python and frozen as JSON
Builders avoid copy-paste drift across 31 fixtures; the exported JSON is the
frozen artifact and a test enforces byte equality.

### D-11 Scripted agents may read hidden data
They validate graders; they are never evaluated. `OracleAgent` and the
presets take `TaskHidden` explicitly in their constructors so the exception
is greppable.

### D-12 Four task families in v0, not three
The original brief listed three. Safety is one of the eight dimensions and
needs its own data; injection through untrusted strings is cheap to model in
v0, so ADVERSARIAL was added.

### D-13 `check_transfer_policy` exists as a dry run
It lets HARD-mode tasks distinguish "checked then declined" (good) from
"blindly attempted then declined" (AUTH-05 / POL-05). It costs a step like
any other tool; oracle plans for DECLINED tasks include it, so a careful
agent is not penalized relative to the oracle.

### D-14 Reports directory
`runs/` is git-ignored raw output. `reports/<benchmark>/<agent>.md` holds
reviewed reports that the README may cite. Every number in a document links
to a file under `reports/`.

## Open questions

(The executor appends here. Format: `Q-nn — <question> — <interim choice> — <ticket>`.)

- Q-01 — Should `list_transfers` include `PENDING` transfers from the
  current step under `TIMEOUT_AFTER_EXECUTE`? — Yes: the transfer is
  COMPLETED before the timeout is returned, so it is listed. — T0.10
- Q-02 — INV-02 vs fixture ledger entries: balances already include
  fixture transfers, so summing all ledger deltas would double-count.
  Interim: capture `initial_balances` after inserting fixture ledger
  rows; INV-02 account check sums only entries after
  `_fixture_entry_count` (PrivateAttr on the runtime WorldState subclass,
  excluded from canonical JSON). COMPLETED/REVERSED entry-sum-to-zero uses
  the full ledger. — T0.05
- Q-03 — T0.08 dispatch must route to authorize/transfer/misc, but those
  modules are created in T0.09/T0.10 and those tickets cannot edit
  dispatch.py. Interim: dispatch loads handler maps via importlib and
  skips missing modules; T0.09/T0.10 only add HANDLERS in their files.
  — T0.08
- Q-04 — Dispatch must return EPISODE_FINISHED but ToolContext as specified
  has no done flag. Interim: add `done: bool = False` on ToolContext.
  — T0.08
- Q-05 — 06 §4 step 8 audits TOOL_RESULT/TOOL_ERROR but T0.08 `ok`/`err`
  already emit those. Interim: the environment does not emit a second
  TOOL_RESULT/TOOL_ERROR; dispatch remains the single writer. — T0.11
- Q-06 — `uv run pytest -q` passes `-q` to uv instead of pytest. Use
  `uv run -- pytest -q` in verification. — T0.17
