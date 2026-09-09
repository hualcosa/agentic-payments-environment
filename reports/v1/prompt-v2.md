# Prompt v2 vs v1 on benchmark v1 held-out

Intervention 1 is `prompts/v2.md` (hash via `load_prompt("v2")`). The added
contract bullet forbids retrying a smaller amount after a policy rejection
without `check_transfer_policy`, and treats that pattern as structuring.

**not yet measured** on the 200 frozen v1 tasks with live models (3 seeds,
confidence intervals, catastrophic rates separate). FakeChatModel is not a
model result. Do not cite numeric deltas until a reviewed `apenv bench`
report exists for both prompt ids.
