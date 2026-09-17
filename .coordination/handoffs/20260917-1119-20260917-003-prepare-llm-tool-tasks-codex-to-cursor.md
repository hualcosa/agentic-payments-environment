---
task_id: 20260917-003-prepare-llm-tool-tasks
from: codex/task-authoring
to: cursor
created_at: 2026-09-17T11:19:47Z
---

# Current state
Owner will execute the approved single-tool-turn work with Grok 4.6 in Cursor.
Codex wrote documentation only. 004/005/006 are unclaimed backlog, not implemented.
Branch codex/sync-workspace; base dae3b9598570d80d0e8a1f86aa8cb962e25b2d55.
Local .gitignore, AGENTS.md, docs/00-index.md and pyproject.toml are modified;
coordination, Cursor rules, Claude entrypoint, strategic context and Serena config
are untracked. Preserve all of them. Pytest's pythonpath fix is already applied.
No new commits or pushes were made. These artifacts are local, not available in a
fresh clone or bare-HEAD worktree unless explicitly transferred.

# Changed files
- .coordination/plans/2026-09-17-llm-tool-protocol.md: approved contract and task graph.
- .coordination/decisions/ADR-0001-single-tool-turn.md: owner-selected behavior.
- .coordination/tasks/backlog/20260917-004-llm-agent-protocol.md: agent and unit regressions.
- .coordination/tasks/backlog/20260917-005-provider-tool-protocol.md: adapters and payload tests.
- .coordination/tasks/backlog/20260917-006-llm-protocol-integration.md: combined validation.
- .coordination/context/project.md: next-work pointers, not an implementation claim.

# Verification
See preparation task 003 for checks actually run. Earlier implementation baseline:
427 tests and offline oracle 31/31 passed; these do not validate unimplemented tasks.
Each task requires fresh focused/full verification and recorded output tails.

# Blockers and risks
No known ownership conflict. Mere open Claude processes are explicitly not a blocker;
do not terminate them. Real overlapping claims still require coordination.
Parallel writers must use isolated worktrees; don't lose dirty-context/pytest changes.
Shared claim commits and all other commits/pushes still need explicit authorization.
Default recommendation for one Cursor executor: serial execution in current checkout.

# Exact next action
Read AGENTS.md and .coordination/README.md, then the approved plan and task 004.
Verify Git and active claims; move task 004 from backlog to in-progress, set
harness cursor, owner cursor/llm-agent-protocol and actual UTC claimed_at/updated_at.
Implement only 004's declared files and run its tests/gates. Next claim 005, then
006 after both implementations are integrated. Do not claim or mark all three done
at once. No real API calls, paid experiments, dependencies or publication here.
