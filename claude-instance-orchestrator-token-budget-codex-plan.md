# Codex Plan: Claude Orchestrator Token Budgets

## Context Snapshot
- scripts/claude-instance-orchestrator.py already tracks per-instance token totals via _parse_token_usage (stream JSON) and _parse_final_output_token_usage (batch) while InstanceStatus persists aggregated counts.
- Rolling console updates originate from _print_status_report, and per-line streaming visuals flow through _stream_output_parallel -> format_instance_line.
- CLI loading (main) supports JSON configs for InstanceConfig definitions but has no notion of token limits or throttling hooks yet.

## Goal Breakdown
- Enforce a **per-command token ceiling** that can be declared in config files and optionally overridden via CLI defaults.
- Enforce a **global token ceiling** that terminates or pauses orchestration once the sum of all commands reaches the budget.
- Enforce a **rolling-period ceiling** (e.g., hourly) that gates launches and streaming consumption when the window is saturated.
- Surface **visual feedback** for each budget in both periodic status reports and per-command streaming updates.

## Implementation Plan

### 1. Configuration & CLI Surface
- Extend InstanceConfig to accept optional max_token_budget (per command) and document the JSON schema update.
- Introduce orchestrator-level settings: max_total_tokens, max_period_tokens, token_period_seconds, and budget_enforcement_mode (warn-only vs terminate) stored on ClaudeInstanceOrchestrator.
- Add matching CLI flags (--max-total-tokens, --max-period-tokens, --token-period-seconds, --budget-mode, --default-command-budget) with sensible defaults (None / warn-only) and thread them into orchestrator construction.
- Ensure dry-run output prints the resolved limits so operators can confirm configuration without running commands.

### 2. Budget Tracking Infrastructure
- Create a TokenBudgetTracker helper (new class or methods on orchestrator) that records:
  - Running grand total and per-command totals.
  - A deque of (timestamp, command, tokens) events to support sliding-window totals.
  - Convenience accessors that compute remaining allowance for each limit.
- Update _parse_token_usage (stream) and _parse_final_output_token_usage (batch) to emit incremental token deltas (track the last seen totals in InstanceStatus so derived deltas are exact).
- Feed each delta into the tracker, pruning stale entries on every insert to keep the window calculations lightweight.

### 3. Enforcement Mechanics
- Before launching an instance in _run_instance_with_delay, consult the tracker to skip launches whose per-command budget is already exhausted; mark them as failed with a clear reason.
- While streaming output, after each delta update check:
  - Command budget: if exceeded, issue a warning, terminate the subprocess (process.terminate() with timeout/fallback kill), and mark status as failed with a budget error.
  - Global budget: if exceeded, cancel remaining launches and terminate all running processes.
  - Period budget: if window sum exceeds allowance, either pause launches or terminate running instances depending on budget_enforcement_mode (plan assumes terminate or skip until tokens fall below threshold).
- Bubble enforcement events into the status reporter so they appear in summaries and final JSON results.

### 4. Visual & Reporting Enhancements
- Enhance _print_status_report to add columns for budget / remaining when limits are active, plus ASCII progress bars (for example, 20-character [####-----]) that reflect usage percentage.
- Modify _stream_output_parallel to append short budget summaries (Tokens: 900/1200 (75%) [####-----]) to the periodic console lines when limits are configured.
- Update the final run summary and save_results metadata to include budget configuration, final usage, and whether any ceiling was breached.
- Respect --quiet by hiding decorative visuals while still logging breaches via logger.warning.

### 5. Validation & Documentation
- Add focused unit-style helpers (could be lightweight functions under tests/ or ad-hoc scripts) that feed synthetic token events into the tracker to cover: per-command breach, global breach, window pruning, and warn-only mode.
- Smoke test via --dry-run and a short real run with mocked commands to confirm enforcement paths do not deadlock async flows.
- Update README / docs snippets plus example config file illustrating new fields and CLI options.

## Risks & Follow-ups
- Clarify whether cached tokens should count fully toward budgets (default assumption: yes, treat them as usage).
- Decide if period budget should pause (queue) launches instead of terminating; implementation will keep hooks flexible to adjust later.
- Consider persisting budget state to disk if orchestration restarts mid-period—out of scope unless explicitly requested.
