# Zen `agent_cli` Parallel Inclusion Master Plan

## 1. Mission Overview

- **Objective**: Introduce `scripts/agent_cli.py` into the Zen CLI (`zen` command) as an opt-in parallel workflow reachable via `zen --apex …` / `zen -a …`, while leaving existing Zen behaviors untouched.
- **Scope**: Wire up command dispatch, support forwarding of complex agent arguments, enable optional JSONL log submission, and ensure packaging/doc coverage. No broad refactors; minimal, intentional touch points only.
- **Success Criteria**:
  - `zen --apex <args>` shells directly into the existing agent CLI logic with zero regressions across current Zen commands.
  - New log-forwarding helper loads the latest 5 `.jsonl` logs by default (platform-aware) and can be unit-tested independently.
  - Users can override log counts, target project, log root path, or username via new flags without altering legacy CLI flows.
  - All additions are documented, reviewed for cross-platform robustness, and shipped with lightweight automated coverage.

## 2. Constraints & Guardrails

- **Minimal impact mandate**: Avoid modifying core Zen command parsing beyond the necessary branching for `--apex` / `-a`. No structural rewrites of Zen internals.
- **Agent CLI stability**: Do not reorganize `agent_cli.py` heavily. Add `main(argv=None)` entry point and imports only where essential.
- **Cross-platform compatibility**: Implement log path resolution that supports macOS (`~/.claude/Projects/...`) and Windows (`C:\Users\<user>\.claude\Projects\...`) without requiring platform-specific code paths in consumer modules.
- **Dependency hygiene**: Reuse standard library modules exclusively for new functionality; avoid bringing in third-party dependencies to maintain agent portability.
- **Testing separation**: New testable logic (log loading, path resolution, payload composition) must live outside the CLI script to allow direct unit tests.
- **CLI UX parity**: Keep existing agent CLI argument semantics identical when executed via `python scripts/agent_cli.py`; Zen wrapper must pass arguments unaltered.

## 3. Recon & Discovery Tasks

- Inventory current Zen CLI entry points (`zen/__main__.py`, `zen/cli.py`, or package entry_points in `pyproject.toml/setup.cfg`) to locate the primary argument parser and dispatch routine.
- Confirm how the existing CLI handles unknown options to ensure `--apex` introduces no conflicts (e.g., check for argparse subparsers vs. custom parsing).
- Identify where `scripts/agent_cli.py` resides within the repository; review its current structure, argument parsing, and output handling.
- Trace any existing log-loading utilities or helper modules to avoid duplicating functionality and to align naming patterns.
- Audit packaging artifacts to see if `scripts/` is included in distributions; determine if manifest adjustments are necessary so `agent_cli.py` remains accessible post-install.

## 4. Zen CLI Wiring Plan

- Extend the Zen argument parser with a boolean flag pair (`--apex`, `-a`) that, when set, bypasses standard command execution and invokes the agent CLI flow.
- Preserve positional/option parsing order so that `zen --apex --message ...` remains valid even if other global options exist.
- Implement a wrapper function (e.g., `run_apex(args: List[str])`) that imports `scripts.agent_cli` and dispatches its `main()` or equivalent without re-parsing arguments in Zen; pass through untouched remainder of CLI arguments.
- Ensure the wrapper prints/returns exit codes emitted by `agent_cli.py` so the shell receives accurate status information.
- Add unit coverage or smoke tests for the new CLI path, possibly using Zen’s existing CLI test harness (if present) with subprocess invocation through `python -m zen --apex ...`.
- Consider potential environment variable dependencies (e.g., API keys); confirm the Zen wrapper does not clobber or alter environment context before invoking the agent CLI.

## 5. `agent_cli.py` Touch Points (Minimal Changes)

- Introduce a `def main(argv: Optional[Sequence[str]] = None) -> int:` entry point that existing `if __name__ == "__main__":` block can call, enabling reuse from Zen without running as a script.
- Refactor any top-level code (if present) into functions or guard under the `__main__` check to avoid unintended execution when imported.
- Inject optional hook for log payload enrichment (`inject_logs_into_message`, etc.) but keep it short to respect the minimal-change directive.
- Confirm `agent_cli.py` uses `argparse` (or equivalent) and adjust only by adding new optional arguments for log handling; no reordering or renaming of current options.
- Guard new imports (e.g., `from scripts.agent_logs import collect_recent_logs`) to avoid circular dependencies or heavy modules loading during startup.

## 6. Log Collection Helper Design

- Create a new module, e.g., `scripts/agent_logs.py`, responsible for:
  - Detecting the base `.claude` directory for the active platform using `Path.home()` for macOS/Linux, and `Path(os.environ.get("USERPROFILE", Path.home()))` for Windows.
  - Resolving the `Projects` subdirectory and determining the target project folder either from arguments or by scanning for the most recently modified directory.
  - Accepting explicit overrides: `base_path`, `project_name`, `username`, `limit`.
  - Enumerating `.jsonl` files inside the chosen project folder, sorting them by modification time descending, and reading up to `limit` files (default 5).
  - Parsing logs line-by-line into JSON objects, skipping lines that fail `json.loads` and capturing parsing exceptions for optional debugging output.
  - Returning a list of log entries (dicts) ready for serialization, or `None` if no logs found and logs were optional.
- Write pure helper functions (e.g., `_get_default_user()`, `_resolve_projects_root(platform_info, username)`) to facilitate unit testing and to keep business logic separate from CLI concerns.
- Add small logging/warning mechanism (via `logging` module) to inform users when logs are missing, truncated, or malformed; keep output on stderr to avoid interfering with CLI responses.

## 7. CLI Argument Extensions

- In `agent_cli.py`, update the parser to include:
  - `--send-logs` / `--logs` (action=`store_true`) to toggle log transmission.
  - `--logs-count` (int, default 1, validated to be positive). For best results, use 1 log at a time with payloads under 1MB.
  - `--logs-project` (string) to select a specific project folder.
  - `--logs-path` (path) direct override for the logs directory; if provided, skip platform resolution.
  - `--logs-user` (string) to explicitly set the Windows username portion of the path.
  - Optional `--logs-platform` for testing or cross-platform debugging (accepts `mac`, `windows`, maybe `linux`).
- Ensure new arguments do not clash with existing options and maintain alphabetical or grouping order consistent with current CLI documentation.
- Update message payload composition logic: when `--send-logs` is true, call `collect_recent_logs`, serialize to JSON (preserving original structure) and attach to message under `jsonl_logs`.
- Handle serialization carefully: convert the list of dicts into a JSON string mirroring existing expectations (escaped string vs. actual array) with minimal change to the message format.
- Provide graceful fallback when logs cannot be collected (e.g., print warning and continue without logs).

## 8. Cross-Platform & Path Handling Considerations

- On macOS/Linux: default path `Path.home() / ".claude" / "Projects" / <project>`.
- On Windows: default base `Path(os.environ["USERPROFILE"]) / ".claude" / "Projects" / <project>`; allow override via `--logs-user` to construct `Path("C:/Users/<user>/.claude/Projects")`.
- Detect OS using `platform.system()`; allow forcing via CLI override for test automation on CI that mocks platform directories.
- Implement path normalization to handle case-insensitive filesystems and UNC paths gracefully (use `Path.resolve()` when possible).
- Guard against directory traversal or unsafe input by sanitizing `project_name` and ensuring final path resides under the `.claude/Projects` root unless explicitly overridden.
- Document known limitations (e.g., Behavior on Linux if `.claude` is absent) and recommended mitigation steps.

## 9. Testing Strategy

- **Unit tests**:
  - Cover `collect_recent_logs` with synthetic directories using `tmp_path` fixtures; verify platform resolution, project selection (default vs. explicit), file ordering, and error handling.
  - Test JSON parsing resilience (malformed lines skipped, truncated logs).
- **Integration/CLI tests**:
  - Use `subprocess.run(["python", "-m", "zen", "--apex", "--message", ...])` on a fixtures directory to assert the payload includes `jsonl_logs`.
  - Validate `--apex` fallback when logs unavailable (should still execute successfully).
  - Confirm existing `zen` commands remain unaffected (smoke test `zen --help` or a trivial command).
- **Manual verification**:
  - macOS-style path simulation on mac test profile.
  - Windows path simulation, ensuring username detection functions without requiring actual user directories (use environment variable injection in tests).
- Ensure tests are added to existing suite without introducing new dependencies; integrate with CI instructions if necessary.

## 10. Documentation & Developer Enablement

- Update `docs/agent_cli/README.md` or create an addendum describing the new log-sending flags and how to invoke via `zen --apex`.
- Modify Zen’s top-level CLI documentation (if any, e.g., `README.md`, `docs/zen/usage.md`) with a concise section on the new parallel agent workflow.
- Include examples for:
  - Default invocation: `zen --apex --message '{"prompt": "..."}'`.
  - Enabling logs: `zen -a --send-logs` (uses default of 1 log file for optimal analysis).
  - Overriding project path: `zen --apex --send-logs --logs-path "/tmp/mock_logs"`.
- Note the non-intrusive nature of the integration (no changes to existing workflows) and suggest when to use the apex pathway.
- Document limitations/assumptions (requires `.claude/Projects` structure, default username detection may need overrides in shared environments).

## 11. Risk Assessment & Mitigations

- **Argument collision risk**: If Zen already uses `-a`, identify conflicts early and choose an alternative short flag or gating logic.
- **Packaging omissions**: Ensure `scripts/agent_cli.py` and the new helper module are included in distributions; adjust manifest or `package_data`.
- **Path resolution failures**: Provide clear error messaging and fallback instructions when `.claude` directories are missing.
- **Log size concerns**: Consider capping per-log file size or total payload; add TODO for potential streaming/compression if logs become large.
- **Security/privacy**: Call out that log forwarding may include sensitive data; advise verifying policy compliance before enabling by default.
- **Windows path edge cases**: Guard for usernames containing spaces or special characters; ensure quoting/escaping works when invoking from shells.
- **Testing coverage gaps**: Highlight the need to add automated tests before release; absence is a deployment risk.

## 12. Execution Timeline (Indicative)

1. **Day 1**: Recon Zen CLI + agent CLI; draft wrapper approach; sketch helper API.
2. **Day 2**: Implement Zen CLI flag and wrapper, create `agent_logs.py`, introduce `collect_recent_logs`.
3. **Day 3**: Integrate helper with `agent_cli.py`, add new CLI options, ensure payload composition works.
4. **Day 4**: Build unit tests for helper, CLI smoke tests, refine cross-platform logic.
5. **Day 5**: Update documentation, run full test suite, gather feedback, finalize patch set.

## 13. Validation & Rollout Checklist

- [ ] Run `zen --help` to confirm new flags appear (with concise descriptions).
- [ ] Execute `zen --apex --message ...` without logs to verify existing behavior.
- [ ] Execute `zen --apex --send-logs` in environments with mock `.claude` data; inspect transmitted payload for correct log content.
- [ ] Confirm fallback when logs absent (warning emitted, command still succeeds).
- [ ] Ensure `python scripts/agent_cli.py ...` still operates identically when invoked directly (with and without new log flags).
- [ ] Review docs for accuracy and grammar; link to plan if helpful.
- [ ] Solicit peer review focusing on minimal change adherence and cross-platform handling.

## 14. Open Questions & Follow-Ups

- Do we need Linux-specific guidance (if `.claude` exists there) even though requirements mention macOS/Windows?
- Should logs be truncated/obfuscated automatically, or is raw pass-through acceptable?
- Is there a need for telemetry/analytics when logs fail to load (for future observability)?
- Should `zen --apex` accept subcommands or be mutually exclusive with other Zen options (determine after examining current CLI design)?
- Future refactor consideration: separate testing utilities vs. client functionality deeper within `agent_cli` once logs feature stabilizes.

## 15. Acceptance Criteria Summary

- `zen` command gains an apex mode that delegates to agent CLI without breaking legacy flows.
- Log collection helper delivers recent JSONL events from `.claude/Projects` based on platform defaults with user overrides.
- Agent CLI includes new, optional flags to control log submission, defaulting to the latest 5 logs from the most recently used project.
- Documentation, tests, and release notes adequately cover the new functionality and risks.
- All modifications remain tightly scoped, respecting the minimal-change directive.

