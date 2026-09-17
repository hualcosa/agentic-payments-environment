# Claude Code project entry point

Load and follow the shared repository contract and strategic context:

@AGENTS.md
@docs/00-project-context.md
@.coordination/README.md

Keep strategic updates in the shared context, not in a separate Claude-only
copy. The imports do not authorize execution of the conceptual roadmap.

## Communication standard

Follow the canonical **concise completeness** policy in `AGENTS.md`: lead with
the result and compress aggressively without dropping material evidence,
uncertainty, risks, authorization state or verification.

<!-- shared-agent-workspace:coordination:start -->
## Cross-harness coordination

The repository-wide source of truth for collaboration is
`.coordination/README.md`. Read and follow it before changing project files.

At the start of a work session:

1. Read `.coordination/context/project.md`.
2. Review `.coordination/tasks/in-progress/` and recent handoffs.
3. Claim a backlog task, or create and claim a task, before editing project
   files.

Keep durable context in the repository coordination files. Harness-local
memory is supplementary and must not be treated as shared state.
<!-- shared-agent-workspace:coordination:end -->
