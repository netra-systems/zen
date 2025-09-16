# Claude Instance Orchestrator Enhancement Plan

## Objectives
- Offer an opt-in single-instance execution path that reuses the ergonomics of scripts/claude
- Allow arbitrary CLI command definitions so the orchestrator can launch tools beyond Claude (e.g., OpenAI Codex wrappers)
- Support dependent command chaining, including conditional/graph relationships, within one orchestration run

## Phase 0 – Discovery & Alignment
1. Trace how InstanceConfig is created (CLI flags vs config file) and how commands are launched via ClaudeInstanceOrchestrator.
2. Review scripts/claude behavior (arguments, env requirements, logging) to understand how to embed it.
3. Inventory current persistence hooks (CloudSQL, NetraOptimizer) to understand how new execution metadata should fit.
4. Capture stakeholders' requirements for chaining semantics (blocking vs async, failure policy) before implementation.

## Phase 1 – Single Instance Mode
- CLI/Config UX: add a --mode {single,batch} flag and mode field in config files; default to existing batch behavior.
- Command Source: allow --single-command to accept a named preset (claude) or raw command string; map preset claude to scripts/claude.
- Execution Path: short-circuit orchestration to launch exactly one instance with existing logging, token parsing, and result saving.
- Telemetry: ensure single-instance runs still emit summaries/results and optional NetraOptimizer records.
- Back-compat: document how existing multi-instance configs behave identically without new flags.

## Phase 2 – Generic CLI Runtime Support
- Schema Update: extend InstanceConfig with optional untime/interpreter fields to describe how to launch non-Claude tools (python, node, shell, container).
- Validation Layer: add per-runtime validation (e.g., ensure binary exists, optional --check-paths preflight).
- Environment Handling: support command-specific env vars, working directories, and resource limits.
- Output Parsing: implement adapter interface so non-Claude commands can plug in custom parsers (stdout regex, JSON schema, or no parsing).
- UX: enrich --list-commands to show available runtimes/presets (Claude, Codex, custom) and document config examples.

## Phase 3 – Dependent Command Chaining
- Data Model: introduce dependencies and optional conditions fields (success/failure, output predicates) in config.
- Planner: build DAG validation to detect cycles and toposort commands prior to execution.
- Execution Engine: orchestrate dependent runs with async tasks – block until parent dependencies resolve; support continue_on_failure per edge/group.
- Conditional Logic: allow lightweight expressions referencing prior results (status, exit code, parsed fields).
- Bundled Tasks: add shorthand for serial chains (sequence:) that expands to DAG nodes for simpler configs.
- Observability: surface dependency state in get_status_summary() and status reports; include graph metadata in saved results.

## Phase 4 – Tooling & Testing
- Unit Tests: cover new config parsing, DAG planner, runtime adapters, and single-instance fast path.
- Integration Tests: create sample configs for Claude single-instance, Codex command, and a chained workflow; verify orchestration logs/results.
- CLI Tests: exercise new flags (--mode, --single-command, runtime selections) via subprocess tests.
- Documentation: update README/help text, add quickstart snippets for single instance, Codex, and chaining scenarios.
- Release Notes: highlight breaking changes (none expected) and migration guidance.

## Risks & Open Questions
- Need confirmation on how scripts/claude is configured (API keys, workspace discovery) to ensure compatibility in orchestrator environment.
- Clarify expectations for mixed runtimes in one workflow (e.g., Claude output feeding Codex); may need standardized artifact passing.
- Evaluate whether NetraOptimizer schema can store runtime type and dependency graph metadata without migrations.
- Consider security posture when allowing arbitrary CLI commands (sandboxing, allowlists).

## Success Criteria
- Running python claude-instance-orchestrator.py --mode single --single-command claude proxies through scripts/claude without regressions.
- Config-defined Codex job executes and its output/exit status is visible in orchestration summaries.
- A sample DAG with conditional branches executes in the intended order, halts on failure when configured, and persists dependency-aware metadata.
