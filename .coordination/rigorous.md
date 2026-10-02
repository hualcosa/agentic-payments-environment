# Rigorous execution (load only when selected)

This procedure supplements [the core](README.md) only for a user-selected rigorous
scope. Existing requirements, authorizations and gates are not waived. Same
harness/model is allowed; roles require independent contexts, not model diversity.

## Before implementation: protected acceptance baseline

An independent author derives bounded behavioral acceptance from requirements and
public contracts: outcomes, boundaries and invariants, not private internals or
arbitrary test counts. In the formal task record mode, criteria, protected
`acceptance_tests` paths, verification commands, impacted consumers and safety core.
Do not leave executable tasks without applicable commands.

Independently review the acceptance-only change for criteria, integrity and scope;
verify collection/setup and record expected failures from unimplemented behavior.
Freeze the accepted baseline **before** implementation. Only this baseline may be
accepted expected-red; unrelated/setup failures are not exempt. Integrate under
existing commit permissions when possible. Without an authorized Git baseline,
use an isolated staged snapshot and hashes, record expected-red checks, and label
it bootstrap evidence—not exact-HEAD approval. No fabricated initial commit.

Docs-only work uses an agreed observable verification plan (links, rendered/output
artifacts, affected tooling) and independent review; no separate application-test
author or artificial app tests. This exception does not skip required checks.

## Implementation and acceptance integrity

Implementer reads but must not author/modify protected acceptance tests; add its
own unit/regression tests outside protected paths. Focus execution during
implementation, broaden by impact as the core requires. Suspected spec/acceptance
errors must be reported, not worked around. Acceptance corrections come from an
independent author, are separately reviewed/accepted and adopted into the trusted
baseline before implementation resumes; demonstrate fail-before/pass-after where
feasible. New requirements require a new scope/mode decision, not invented blockers.
Implementer must not narrow mandatory commands, protected paths, safety core or
selection policy to get a pass. Independent reviewer/integrator checks against
the accepted pre-implementation definition; recompute after rebases/environment
changes. Own tests never replace independent acceptance.

## Final-version review

Reviewer uses a separate context and receives requirements, criteria, final
code/diff or snapshot and actual verification—not implementer reasoning/history.
Read criteria **before** diff; assess correctness, boundaries, test integrity
(weakening/skips/special cases), scope and observable artifacts even with green
tests. Style preferences are not blockers. Record reproducers for concrete gaps.
No mandatory second test-authoring pass or extra orchestration/risk role.

Acceptance requires passing mandatory verification **and independent review**.
Only reviewer authors verdict; a runner may persist it verbatim for a read-only
reviewer. Record reviewer/model when exposed, limitations and exact reviewed HEAD
(or file-inventory/snapshot hashes for uncommitted bootstrap). Latest final-version
verdict must pass. Any product change after review needs new review; bookkeeping
receipts do not approve unreviewed product changes. Keep receipts separate from
reviewed product content. No exact-HEAD claim for hash-bound bootstrap evidence.

## Corrections and stop rule

On fail, the **same implementer may fix** within agreed scope; independent reviewer
reassesses the whole new final version. A micro-correction does not prompt another
mode choice; material scope/risk/concurrency changes do. Protected acceptance
corrections still need the independent author and review above. Reviewer unavailable
or error means stop, never self-approve. After **two unsuccessful correction
rounds**, stop for human intervention. Re-reviewing the full change does not always
mean running the full suite; execution scope follows actual impact and core gates.

## Integration

For accepted auxiliary-branch work, inspect main/worker state, integrate serially
to local main (prefer fast-forward), rerun mandatory/impacted checks and record
revision before cleanup. Dirty/diverged/owned/conflicting main means stop and ask.
A rebase or relevant product change invalidates prior final-version review.
Never infer authorization to commit, push, publish or provision from this mode.
Project-specific runner/model/budget commands belong in local context/decisions,
not universal adapters. This procedure is policy, not an installed enforcement
engine.
