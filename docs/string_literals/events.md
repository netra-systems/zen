# ⚡ Events Literals

Event handlers, event types, and lifecycle events

*Generated on 2025-08-21 22:03:59*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 406 |
| Subcategories | 4 |
| Average Confidence | 0.475 |

## 📋 Subcategories

- [general (369 literals)](#subcategory-general)
- [handler (6 literals)](#subcategory-handler)
- [lifecycle (7 literals)](#subcategory-lifecycle)
- [type (24 literals)](#subcategory-type)

## Subcategory: general {subcategory-general}

**Count**: 369 literals

### 🟡 Medium (0.5-0.8) (126 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `
\#\#\# Frontend Handlers Available
` | websocket_coherence_review.py:267 | _build_event_inventory | `
        functi...`, `severity-` |
| `
\[CRITICAL\] EMERGENCY ACTIONS REQUI...` | boundary_enforcer_cli_handler.py:155 | FailureHandler.check_emerge... | `
        functi...`, `severity-` |
| `
\[INFO\] JSON report saved to: ` | boundary_enforcer_cli_handler.py:146 | JSONOutputHandler.save_json... | `
        functi...`, `severity-` |
| `
Examples:
  \# Check specific workfl...` | verify_workflow_status.py:205 | CLIHandler._get_usage_examples | `
        functi...`, `severity-` |
| `
Examples:
  python check\_architectu...` | cli.py:33 | CLIHandler._get_usage_examples | `
        functi...`, `severity-` |
| `
JSON report saved to: ` | cli.py:140 | OutputHandler._save_json_ou... | `
        functi...`, `severity-` |
| `
Shutting down development environmen...` | dev_launcher_core.py:105 | DevLauncher._cleanup_handler | `
        functi...`, `severity-` |
| `
✅ No test splitting suggestions need...` | cli.py:119 | OutputHandler._print_test_s... | `
        functi...`, `severity-` |
| ` critical violations \- Build failing` | boundary_enforcer_cli_handler.py:163 | FailureHandler.check_critic... | `
        functi...`, `severity-` |
| `"event":` | websocket_coherence_review.py:94 | check_event_structure | `
        functi...`, `severity-` |
| `\#\#\# 2\. ✅ Missing Unified Events \...` | websocket_coherence_review.py:199 | _build_events_fix_section | `
        functi...`, `severity-` |
| `'event':` | websocket_coherence_review.py:94 | check_event_structure | `
        functi...`, `severity-` |
| `\- \`` | websocket_coherence_review.py:275 | _format_event_list | `
        functi...`, `severity-` |
| `\-\-check\-test\-limits` | cli.py:63 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `\-\-fail\-on\-violation` | cli.py:46 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `\-\-focus` | cli.py:40 | CLIHandler._add_focus_argum... | `
        functi...`, `severity-` |
| `\-\-ignore\-folders` | cli.py:54 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `\-\-json\-only` | cli.py:86 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `\-\-json\-output` | cli.py:85 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `\-\-max\-file\-lines` | cli.py:48 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `\-\-max\-function\-lines` | cli.py:50 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `\-\-mode` | cli.py:30 | CLIHandler._add_mode_arguments | `
        functi...`, `severity-` |
| `\-\-no\-emoji` | cli.py:79 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `\-\-no\-smart\-limits` | cli.py:77 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `\-\-no\-test\-limits` | cli.py:65 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `\-\-output` | verify_workflow_status.py:197 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-path` | cli.py:45 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `\-\-poll\-interval` | verify_workflow_status.py:193 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-recent\-commits` | cli.py:49 | CLIHandler._add_other_argum... | `
        functi...`, `severity-` |
| `\-\-repo` | verify_workflow_status.py:169 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-report` | cli.py:53 | CLIHandler._add_other_argum... | `
        functi...`, `severity-` |
| `\-\-run\-id` | verify_workflow_status.py:177 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-show\-all` | cli.py:73 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `\-\-target\-folders` | cli.py:52 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `\-\-test\-suggestions` | cli.py:67 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `\-\-threshold` | cli.py:88 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `\-\-timeout` | verify_workflow_status.py:189 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-token` | verify_workflow_status.py:181 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-violation\-limit` | cli.py:75 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `\-\-wait\-for\-completion` | verify_workflow_status.py:185 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\-\-wait\-for\-completion requires \-...` | verify_workflow_status.py:226 | CLIHandler.validate_args | `
        functi...`, `severity-` |
| `\-\-workflow\-name` | verify_workflow_status.py:173 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `\.\.\.` | ssot_checker.py:109 | SSOTChecker._check_duplicat... | `
        functi...`, `severity-` |
| `Add arguments to parser` | cli.py:44 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Add display\-related arguments` | cli.py:72 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `Add focus\-related arguments` | cli.py:38 | CLIHandler._add_focus_argum... | `
        functi...`, `severity-` |
| `Add mode\-related arguments` | cli.py:28 | CLIHandler._add_mode_arguments | `
        functi...`, `severity-` |
| `Add other arguments` | cli.py:47 | CLIHandler._add_other_argum... | `
        functi...`, `severity-` |
| `Add output\-related arguments` | cli.py:84 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `Add test\-specific arguments` | cli.py:62 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `ai\-focus` | cli.py:31 | CLIHandler._add_mode_arguments | `
        functi...`, `severity-` |
| `ai\-issues` | cli.py:41 | CLIHandler._add_focus_argum... | `
        functi...`, `severity-` |
| `Build the current event inventory sec...` | websocket_coherence_review.py:260 | _build_event_inventory | `
        functi...`, `severity-` |
| `Build the missing events fix section` | websocket_coherence_review.py:198 | _build_events_fix_section | `
        functi...`, `severity-` |
| `Check architecture compliance with en...` | cli.py:23 | CLIHandler.create_argument_... | `
        functi...`, `severity-` |
| `Check for consistent event structure` | websocket_coherence_review.py:82 | check_event_structure | `
        functi...`, `severity-` |
| `Check for duplicate handler/manager p...` | ssot_checker.py:80 | SSOTChecker._check_duplicat... | `
        functi...`, `severity-` |
| `Check test file limits \(300 lines\) ...` | cli.py:64 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `Command\-line interface handler\.` | verify_workflow_status.py:155 | CLIHandler | `
        functi...`, `severity-` |
| `Consider consolidating into single ha...` | ssot_checker.py:113 | SSOTChecker._check_duplicat... | `
        functi...`, `severity-` |
| `Create and configure argument parser` | cli.py:21 | CLIHandler.create_argument_... | `
        functi...`, `severity-` |
| `Create and configure argument parser` | cli.py:19 | CLIHandler.create_argument_... | `
        functi...`, `severity-` |
| `Determine if should exit with failure...` | cli.py:150 | OutputHandler._should_exit_... | `
        functi...`, `severity-` |
| `Disable emoji severity markers` | cli.py:80 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `Disable smart limit detection` | cli.py:78 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `Either \-\-run\-id or \-\-workflow\-n...` | verify_workflow_status.py:223 | CLIHandler.validate_args | `
        functi...`, `severity-` |
| `Exit with non\-zero code on violations` | cli.py:47 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Extract error handling information` | ultra_thinking_analyzer.py:152 | UltraThinkingAnalyzer._extr... | `
        functi...`, `severity-` |
| `Find all WebSocket event handlers in ...` | websocket_coherence_review.py:52 | find_frontend_handlers | `
        functi...`, `severity-` |
| `Find all WebSocket events sent by the...` | websocket_coherence_review.py:14 | find_backend_events | `
        functi...`, `severity-` |
| `Focus area for targeted review` | cli.py:42 | CLIHandler._add_focus_argum... | `
        functi...`, `severity-` |
| `Folders to check \(default: app front...` | cli.py:53 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Folders to ignore \(default: scripts ...` | cli.py:55 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Format events dictionary into a list` | websocket_coherence_review.py:272 | _format_event_list | `
        functi...`, `severity-` |
| `Generate automated splitting suggesti...` | cli.py:68 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `Generate detailed report \(automatic ...` | cli.py:54 | CLIHandler._add_other_argum... | `
        functi...`, `severity-` |
| `Get GitHub token from args or environ...` | verify_workflow_status.py:229 | CLIHandler.get_github_token | `
        functi...`, `severity-` |
| `Get usage examples for help text` | cli.py:32 | CLIHandler._get_usage_examples | `
        functi...`, `severity-` |
| `Get usage examples for help text\.` | verify_workflow_status.py:204 | CLIHandler._get_usage_examples | `
        functi...`, `severity-` |
| `GitHub token \(defaults to GITHUB\_TO...` | verify_workflow_status.py:182 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Handle cleanup on exit\.` | dev_launcher_core.py:104 | DevLauncher._cleanup_handler | `
        functi...`, `severity-` |
| `Handle critical failure conditions` | boundary_enforcer_cli_handler.py:160 | FailureHandler.check_critic... | `
        functi...`, `severity-` |
| `Handle emergency failure conditions` | boundary_enforcer_cli_handler.py:153 | FailureHandler.check_emerge... | `
        functi...`, `severity-` |
| `Handle exit code based on results` | cli.py:144 | OutputHandler.handle_exit_code | `
        functi...`, `severity-` |
| `Handles command line interface operat...` | cli.py:17 | CLIHandler | `
        functi...`, `severity-` |
| `Handles command line interface operat...` | cli.py:15 | CLIHandler | `
        functi...`, `severity-` |
| `Handles failure condition checking an...` | boundary_enforcer_cli_handler.py:149 | FailureHandler | `
        functi...`, `severity-` |
| `Handles JSON output operations` | boundary_enforcer_cli_handler.py:139 | JSONOutputHandler | `
        functi...`, `severity-` |
| `Handles output processing and formatting` | cli.py:93 | OutputHandler | `
        functi...`, `severity-` |
| `Max violations to display per categor...` | cli.py:76 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `Maximum lines per file \(default: 500...` | cli.py:49 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Maximum lines per function \(default:...` | cli.py:51 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Minimum compliance score \(0\-100\) t...` | cli.py:89 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `Multiple ` | ssot_checker.py:112 | SSOTChecker._check_duplicat... | `
        functi...`, `severity-` |
| `Number of recent commits to analyze` | cli.py:50 | CLIHandler._add_other_argum... | `
        functi...`, `severity-` |
| `Output format \(default: table\)` | verify_workflow_status.py:198 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Output JSON report to file` | cli.py:85 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `Output only JSON, no human\-readable ...` | cli.py:87 | CLIHandler._add_output_argu... | `
        functi...`, `severity-` |
| `Parse command\-line arguments\.` | verify_workflow_status.py:161 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Polling interval in seconds \(default...` | verify_workflow_status.py:194 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Print JSON output to stdout` | cli.py:111 | OutputHandler._print_json_o... | `
        functi...`, `severity-` |
| `Print test splitting suggestions` | cli.py:116 | OutputHandler._print_test_s... | `
        functi...`, `severity-` |
| `Process and output results` | cli.py:97 | OutputHandler.process_output | `
        functi...`, `severity-` |
| `Repository in format 'owner/repo'` | verify_workflow_status.py:170 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Review mode \(quick=5min, standard=10...` | cli.py:33 | CLIHandler._add_mode_arguments | `
        functi...`, `severity-` |
| `Root path to check` | cli.py:45 | CLIHandler._add_parser_argu... | `
        functi...`, `severity-` |
| `Run comprehensive code review` | cli.py:20 | CLIHandler.create_argument_... | `
        functi...`, `severity-` |
| `s for similar functionality` | ssot_checker.py:112 | SSOTChecker._check_duplicat... | `
        functi...`, `severity-` |
| `Save JSON output if requested` | cli.py:136 | OutputHandler._save_json_ou... | `
        functi...`, `severity-` |
| `Save JSON report to file` | boundary_enforcer_cli_handler.py:143 | JSONOutputHandler.save_json... | `
        functi...`, `severity-` |
| `Setup signal handlers for cleanup\.` | dev_launcher_core.py:91 | DevLauncher._setup_signal_h... | `
        functi...`, `severity-` |
| `Show all violations instead of top ones` | cli.py:74 | CLIHandler._add_display_arg... | `
        functi...`, `severity-` |
| `Skip test limits checking` | cli.py:66 | CLIHandler._add_test_arguments | `
        functi...`, `severity-` |
| `spec\-alignment` | cli.py:41 | CLIHandler._add_focus_argum... | `
        functi...`, `severity-` |
| `Specific workflow run ID to check` | verify_workflow_status.py:178 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Still using old "event" field instead...` | websocket_coherence_review.py:99 | check_event_structure | `
        functi...`, `severity-` |
| `Timeout in seconds for waiting \(defa...` | verify_workflow_status.py:190 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `utf\-8` | websocket_coherence_review.py:27 | find_backend_events | `
        functi...`, `severity-` |
| `utf\-8` | websocket_coherence_review.py:65 | find_frontend_handlers | `
        functi...`, `severity-` |
| `utf\-8` | websocket_coherence_review.py:90 | check_event_structure | `
        functi...`, `severity-` |
| `Validate command\-line arguments\.` | verify_workflow_status.py:221 | CLIHandler.validate_args | `
        functi...`, `severity-` |
| `Verify GitHub workflow status` | verify_workflow_status.py:163 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `Wait for workflow to complete` | verify_workflow_status.py:186 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `win32` | dev_launcher_core.py:96 | DevLauncher._setup_signal_h... | `
        functi...`, `severity-` |
| `Workflow name \(file name without \.y...` | verify_workflow_status.py:174 | CLIHandler.parse_args | `
        functi...`, `severity-` |
| `🔧 TEST SPLITTING SUGGESTIONS` | cli.py:123 | OutputHandler._print_test_s... | `
        functi...`, `severity-` |

### 🔴 Low (<0.5) (243 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `
            <tr>
                <td>` | architecture_dashboard_tables.py:30 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `
            <tr>
                <td>` | architecture_dashboard_tables.py:56 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `
        function showTab\(tabName\) ...` | architecture_dashboard.py:196 | ArchitectureDashboard._gene... | `severity-`, `
            <t...` |
| `
  Total: ` | reporter.py:141 | ComplianceReporter._print_f... | `
        functi...`, `severity-` |
| `
\#\# Integration Health

` | status_section_renderers.py:133 | IntegrationRenderer.build_i... | `
        functi...`, `severity-` |
| `
\#\#\#\# \`` | function_complexity_analyzer.py:267 | FunctionComplexityAnalyzer.... | `
        functi...`, `severity-` |
| `
=== Enhanced Categorization Report ===` | categorizer_enhanced.py:554 | print_categorization_report | `
        functi...`, `severity-` |
| `
=== Improvement Analysis ===` | demo_enhanced_categorizer.py:91 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `
=== Sample Enhanced Categorizations ===` | demo_enhanced_categorizer.py:70 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `
Confidence Distribution:` | categorizer_enhanced.py:559 | print_categorization_report | `
        functi...`, `severity-` |
| `
File splitting complete\!
Remember to:` | split_large_files.py:260 | _print_completion_message | `
        functi...`, `severity-` |
| `
JSON report saved to: ` | create_enforcement_tools.py:464 | save_json_report | `
        functi...`, `severity-` |
| `
Operation complete\!` | reset_clickhouse.py:254 | print_operation_summary | `
        functi...`, `severity-` |
| `
Top Categories:` | categorizer_enhanced.py:564 | print_categorization_report | `
        functi...`, `severity-` |
| `
VIOLATION BREAKDOWN:` | architecture_reporter.py:98 | ArchitectureReporter._print... | `
        functi...`, `severity-` |
| `    Context: ` | demo_enhanced_categorizer.py:85 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `    Error processing ` | merge_results.py:43 | read_json_file | `
        functi...`, `severity-` |
| `    Expected lines: ` | auto_decompose_functions.py:432 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `    Fix: ` | create_enforcement_tools.py:435 | print_violation_details | `
        functi...`, `severity-` |
| `    Parameters: ` | auto_decompose_functions.py:431 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `   1\. Update any imports in other fi...` | split_large_files.py:261 | _print_completion_message | `
        functi...`, `severity-` |
| `   3\. Update test discovery patterns...` | split_large_files.py:262 | _print_completion_message | `
        functi...`, `severity-` |
| `   ⚠️ ` | schema_sync.py:106 | print_validation_errors | `
        functi...`, `severity-` |
| `  \- Deduplicate ` | reporter.py:310 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| `  \- Refactor ` | reporter.py:308 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| `  \- Remove ` | reporter.py:312 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| `  \- Split ` | reporter.py:306 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| `  \.\.\. and ` | reporter.py:84 | ComplianceReporter._print_t... | `
        functi...`, `severity-` |
| `  \.\.\. and ` | categorizer_enhanced.py:571 | print_categorization_report | `
        functi...`, `severity-` |
| `  \.\.\. and ` | validate_type_deduplication.py:284 | TypeDeduplicationValidator.... | `
        functi...`, `severity-` |
| `  Categorized: ` | demo_enhanced_categorizer.py:42 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `  Created ` | seed_staging_data.py:278 | StagingDataSeeder.seed_opti... | `
        functi...`, `severity-` |
| `  Database: ` | reset_clickhouse.py:80 | _print_connection_info | `
        functi...`, `severity-` |
| `  Database: ` | reset_clickhouse_auto.py:81 | _display_connection_info | `
        functi...`, `severity-` |
| `  Git Hooks: ` | status_manager.py:101 | StatusManager._format_insta... | `
        functi...`, `severity-` |
| `  Host: ` | reset_clickhouse.py:78 | _print_connection_info | `
        functi...`, `severity-` |
| `  Host: ` | reset_clickhouse_auto.py:79 | _display_connection_info | `
        functi...`, `severity-` |
| `  Port: ` | reset_clickhouse.py:79 | _print_connection_info | `
        functi...`, `severity-` |
| `  Port: ` | reset_clickhouse_auto.py:80 | _display_connection_info | `
        functi...`, `severity-` |
| `  Scanning ` | demo_enhanced_categorizer.py:56 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `  Total literals: ` | demo_enhanced_categorizer.py:41 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `  Uncategorized: ` | demo_enhanced_categorizer.py:43 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `  User: ` | reset_clickhouse.py:81 | _print_connection_info | `
        functi...`, `severity-` |
| `  User: ` | reset_clickhouse_auto.py:82 | _display_connection_info | `
        functi...`, `severity-` |
| ` boundary violations` | boundary_enforcer_cli_handler.py:174 | ViolationDisplayer.display_... | `
        functi...`, `severity-` |
| ` complex functions` | reporter.py:308 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| ` complex functions into smaller units` | architecture_metrics.py:192 | ArchitectureMetrics._get_fu... | `
        functi...`, `severity-` |
| ` found` | env_checker.py:107 | check_python_version | `
        functi...`, `severity-` |
| ` Function '` | core.py:123 | ViolationBuilder.function_v... | `
        functi...`, `severity-` |
| ` functions` | boundary_enforcer_function_checks.py:85 | FunctionBoundaryChecker._bu... | `
        functi...`, `severity-` |
| ` functions` | ai_detector.py:99 | AIDetector._check_missing_p... | `
        functi...`, `severity-` |
| ` functions without return type hints` | ai_detector.py:98 | AIDetector._check_missing_p... | `
        functi...`, `severity-` |
| ` Health Checks: ` | validate_staging_health.py:260 | print_validation_summary | `
        functi...`, `severity-` |
| ` in ` | boundary_enforcer_cli_handler.py:176 | ViolationDisplayer.display_... | `
        functi...`, `severity-` |
| ` into ` | core.py:124 | ViolationBuilder.function_v... | `
        functi...`, `severity-` |
| ` line HARD LIMIT` | boundary_enforcer_file_checks.py:71 | FileBoundaryChecker._build_... | `
        functi...`, `severity-` |
| ` line HARD LIMIT` | boundary_enforcer_function_checks.py:84 | FunctionBoundaryChecker._bu... | `
        functi...`, `severity-` |
| ` line limit` | create_enforcement_tools.py:178 | EnforcementEngine.analyze_f... | `
        functi...`, `severity-` |
| ` lines` | architecture_metrics.py:163 | ArchitectureMetrics._get_fu... | `
        functi...`, `severity-` |
| ` lines` | enforce_limits.py:109 | FunctionLineChecker._check_... | `
        functi...`, `severity-` |
| ` lines: ` | reporter.py:114 | ComplianceReporter._print_f... | `
        functi...`, `severity-` |
| ` lines: ` | reporter.py:129 | ComplianceReporter._print_f... | `
        functi...`, `severity-` |
| ` literals in sample
` | demo_enhanced_categorizer.py:60 | compare_categorization_appr... | `
        functi...`, `severity-` |
| ` modules` | boundary_enforcer_file_checks.py:72 | FileBoundaryChecker._build_... | `
        functi...`, `severity-` |
| ` more` | code_review_reporter.py:116 | CodeReviewReporter._add_med... | `
        functi...`, `severity-` |
| ` more` | report_generator.py:149 | ReportGenerator._add_medium... | `
        functi...`, `severity-` |
| ` more` | validate_type_deduplication.py:284 | TypeDeduplicationValidator.... | `
        functi...`, `severity-` |
| ` more categories` | categorizer_enhanced.py:571 | print_categorization_report | `
        functi...`, `severity-` |
| ` optimization requests` | seed_staging_data.py:278 | StagingDataSeeder.seed_opti... | `
        functi...`, `severity-` |
| ` oversized files` | reporter.py:306 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| ` Performance: ` | validate_staging_health.py:264 | print_validation_summary | `
        functi...`, `severity-` |
| ` Security: ` | validate_staging_health.py:268 | print_validation_summary | `
        functi...`, `severity-` |
| ` smaller functions` | core.py:124 | ViolationBuilder.function_v... | `
        functi...`, `severity-` |
| ` smaller functions with single respon...` | create_enforcement_tools.py:179 | EnforcementEngine.analyze_f... | `
        functi...`, `severity-` |
| ` test stubs from production` | reporter.py:312 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| ` type definitions` | reporter.py:310 | ComplianceReporter._print_a... | `
        functi...`, `severity-` |
| ` unique literals` | scan_string_literals_enhanced.py:220 | EnhancedStringLiteralIndexe... | `
        functi...`, `severity-` |
| ` violations, ` | reporter.py:141 | ComplianceReporter._print_f... | `
        functi...`, `severity-` |
| ` \| Risk: ` | metadata_header_generator.py:142 | MetadataHeaderGenerator.for... | `
        functi...`, `severity-` |
| ` \| Scope: ` | metadata_header_generator.py:142 | MetadataHeaderGenerator.for... | `
        functi...`, `severity-` |
| ` \| Score: ` | metadata_header_generator.py:144 | MetadataHeaderGenerator.for... | `
        functi...`, `severity-` |
| ` \| Seq: ` | metadata_header_generator.py:143 | MetadataHeaderGenerator.for... | `
        functi...`, `severity-` |
| `">` | architecture_dashboard_tables.py:35 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `">` | architecture_dashboard_tables.py:62 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `% to ` | demo_enhanced_categorizer.py:95 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `' exceeds ` | create_enforcement_tools.py:178 | EnforcementEngine.analyze_f... | `
        functi...`, `severity-` |
| `' has ` | core.py:123 | ViolationBuilder.function_v... | `
        functi...`, `severity-` |
| `' has ` | enforce_limits.py:109 | FunctionLineChecker._check_... | `
        functi...`, `severity-` |
| `\- No urgent action items` | team_updates_formatter.py:212 | HumanFormatter.format_actio... | `
        functi...`, `severity-` |
| `\-\-action` | build_staging.py:256 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-auto` | main.py:49 | _add_execution_arguments | `
        functi...`, `severity-` |
| `\-\-check` | function_complexity_cli.py:35 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-continuous` | main.py:53 | _add_execution_arguments | `
        functi...`, `severity-` |
| `\-\-fail\-on\-violation` | function_complexity_cli.py:37 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-fix\-suggestions` | function_complexity_cli.py:39 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-format=json` | dependency_scanner.py:90 | get_installed_python_packages | `
        functi...`, `severity-` |
| `\-\-format=json` | environment_validator_dependencies.py:99 | DependencyValidator._count_... | `
        functi...`, `severity-` |
| `\-\-full\-analysis` | main.py:51 | _add_execution_arguments | `
        functi...`, `severity-` |
| `\-\-install\-hook` | function_complexity_cli.py:41 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-project` | create_staging_secrets.py:94 | get_production_secret | `
        functi...`, `severity-` |
| `\-\-quick` | main.py:50 | _add_execution_arguments | `
        functi...`, `severity-` |
| `\-\-secret` | create_staging_secrets.py:94 | get_production_secret | `
        functi...`, `severity-` |
| `\-\-service` | build_staging.py:258 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-skip\-build` | build_staging.py:259 | _add_action_arguments | `
        functi...`, `severity-` |
| `\-\-smart\-generate` | main.py:52 | _add_execution_arguments | `
        functi...`, `severity-` |
| `\-\-ultra\-think` | main.py:54 | _add_execution_arguments | `
        functi...`, `severity-` |
| `\-> ` | ai_detector.py:96 | AIDetector._check_missing_p... | `
        functi...`, `severity-` |
| `\-c` | environment_validator_dependencies.py:214 | DependencyValidator._is_pyt... | `
        functi...`, `severity-` |
| `\-m` | environment_validator_dependencies.py:99 | DependencyValidator._count_... | `
        functi...`, `severity-` |
| `\-r` | dependency_scanner.py:245 | fix_python_dependencies | `
        functi...`, `severity-` |
| `\-staging` | create_staging_secrets.py:90 | get_production_secret | `
        functi...`, `severity-` |
| `\.\.\.` | demo_enhanced_categorizer.py:56 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.\.\.` | reset_clickhouse.py:77 | _print_connection_info | `
        functi...`, `severity-` |
| `\.\.\.` | reset_clickhouse_auto.py:78 | _display_connection_info | `
        functi...`, `severity-` |
| `\.\.\. and ` | code_review_reporter.py:116 | CodeReviewReporter._add_med... | `
        functi...`, `severity-` |
| `\.\.\. and ` | report_generator.py:149 | ReportGenerator._add_medium... | `
        functi...`, `severity-` |
| `\.1%` | auto_decompose_functions.py:426 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `\.1f` | demo_enhanced_categorizer.py:42 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.1f` | demo_enhanced_categorizer.py:43 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.1f` | demo_enhanced_categorizer.py:95 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.1f` | demo_enhanced_categorizer.py:95 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.1f` | demo_enhanced_categorizer.py:95 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.1f` | demo_enhanced_categorizer.py:98 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.1f` | categorizer_enhanced.py:557 | print_categorization_report | `
        functi...`, `severity-` |
| `\.1f` | categorizer_enhanced.py:560 | print_categorization_report | `
        functi...`, `severity-` |
| `\.1f` | categorizer_enhanced.py:561 | print_categorization_report | `
        functi...`, `severity-` |
| `\.1f` | categorizer_enhanced.py:562 | print_categorization_report | `
        functi...`, `severity-` |
| `\.1f` | categorizer_enhanced.py:568 | print_categorization_report | `
        functi...`, `severity-` |
| `\.2f` | demo_enhanced_categorizer.py:83 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.2f` | function_complexity_analyzer.py:271 | FunctionComplexityAnalyzer.... | `
        functi...`, `severity-` |
| `\.3f` | demo_enhanced_categorizer.py:97 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `\.3f` | categorizer_enhanced.py:556 | print_categorization_report | `
        functi...`, `severity-` |
| `\.git` | demo_enhanced_categorizer.py:57 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `/tests/` | validate_type_deduplication.py:114 | TypeDeduplicationValidator.... | `
        functi...`, `severity-` |
| `/version/` | generate_openapi_spec.py:158 | check_version_exists | `
        functi...`, `severity-` |
| `127\.0\.0\.1` | environment_validator_ports.py:145 | PortValidator._check_port_l... | `
        functi...`, `severity-` |
| `13\.0` | installer_types.py:68 | create_version_requirements | `
        functi...`, `severity-` |
| `18\.0\.0` | installer_types.py:84 | create_version_requirements | `
        functi...`, `severity-` |
| `2\. Extract error handling into separ...` | auto_decompose_functions.py:439 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `21\.0` | installer_types.py:78 | create_version_requirements | `
        functi...`, `severity-` |
| `3\. Break logical blocks into focused...` | auto_decompose_functions.py:440 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `3d` | reporter.py:114 | ComplianceReporter._print_f... | `
        functi...`, `severity-` |
| `3d` | reporter.py:129 | ComplianceReporter._print_f... | `
        functi...`, `severity-` |
| `4\. Test each decomposed function ind...` | auto_decompose_functions.py:441 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `4d` | reporter.py:73 | ComplianceReporter._print_v... | `
        functi...`, `severity-` |
| `4d` | reporter.py:77 | ComplianceReporter._print_v... | `
        functi...`, `severity-` |
| `6\.0` | installer_types.py:73 | create_version_requirements | `
        functi...`, `severity-` |
| `: ConnectionManager` | fix_e2e_connection_manager_imports.py:82 | fix_connection_manager_imports | `
        functi...`, `severity-` |
| `:def ` | ai_detector.py:60 | AIDetector._parse_function_... | `
        functi...`, `severity-` |
| `:def ` | ai_detector.py:61 | AIDetector._parse_function_... | `
        functi...`, `severity-` |
| `</td>
                <td class="` | architecture_dashboard_tables.py:34 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td class="` | architecture_dashboard_tables.py:61 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:32 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:33 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:35 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:58 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:59 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:60 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
                <td>` | architecture_dashboard_tables.py:62 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
            </tr>` | architecture_dashboard_tables.py:36 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `</td>
            </tr>` | architecture_dashboard_tables.py:63 | DashboardTableRenderers._ge... | `
        functi...`, `severity-` |
| `<p>🎉 No function complexity violation...` | architecture_dashboard_tables.py:45 | DashboardTableRenderers.ren... | `
        functi...`, `severity-` |
| `==` | dependency_scanner.py:189 | is_version_compatible | `
        functi...`, `severity-` |
| `==` | dependency_scanner.py:190 | is_version_compatible | `
        functi...`, `severity-` |
| `=== Enhanced String Literal Categoriz...` | demo_enhanced_categorizer.py:30 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `>=` | dependency_scanner.py:186 | is_version_compatible | `
        functi...`, `severity-` |
| `>=` | dependency_scanner.py:187 | is_version_compatible | `
        functi...`, `severity-` |
| `@mock\_justified` | mock_justification_checker.py:154 | MockJustificationChecker._h... | `
        functi...`, `severity-` |
| `Action to perform` | build_staging.py:257 | _add_action_arguments | `
        functi...`, `severity-` |
| `Architectural Debt` | architecture_reporter.py:107 | ArchitectureReporter._print... | `
        functi...`, `severity-` |
| `Average confidence: ` | demo_enhanced_categorizer.py:97 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `Average confidence: ` | categorizer_enhanced.py:556 | print_categorization_report | `
        functi...`, `severity-` |
| `Backward Compatible` | scan_string_literals_enhanced.py:215 | EnhancedStringLiteralIndexe... | `
        functi...`, `severity-` |
| `clickhouse\-connect` | environment_validator_dependencies.py:202 | DependencyValidator._check_... | `
        functi...`, `severity-` |
| `Code Quality Issues` | architecture_reporter.py:108 | ArchitectureReporter._print... | `
        functi...`, `severity-` |
| `CONFIDENCE: ` | auto_decompose_functions.py:426 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `Consider splitting` | core.py:118 | ViolationBuilder.function_v... | `
        functi...`, `severity-` |
| `CURRENT LINES: ` | auto_decompose_functions.py:424 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `Duplicate Types` | architecture_reporter.py:104 | ArchitectureReporter._print... | `
        functi...`, `severity-` |
| `Excess Lines` | architecture_dashboard_tables.py:48 | DashboardTableRenderers.ren... | `
        functi...`, `severity-` |
| `File exceeds ` | boundary_enforcer_file_checks.py:71 | FileBoundaryChecker._build_... | `
        functi...`, `severity-` |
| `final result` | auto_decompose_functions.py:288 | FunctionDecomposer._suggest... | `
        functi...`, `severity-` |
| `Found ` | demo_enhanced_categorizer.py:60 | compare_categorization_appr... | `
        functi...`, `severity-` |
| `Found ` | ai_detector.py:98 | AIDetector._check_missing_p... | `
        functi...`, `severity-` |
| `from ` | check_e2e_imports.py:168 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from \.` | check_e2e_imports.py:135 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from \.\.` | check_e2e_imports.py:134 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from app\.` | check_e2e_imports.py:138 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from auth\_core\.` | check_e2e_imports.py:146 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from frontend\.` | check_e2e_imports.py:149 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from netra\_backend\.` | check_e2e_imports.py:134 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from netra\_backend\.` | check_e2e_imports.py:135 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `from test\_utils` | check_e2e_imports.py:143 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `Function '` | create_enforcement_tools.py:178 | EnforcementEngine.analyze_f... | `
        functi...`, `severity-` |
| `Function '` | enforce_limits.py:109 | FunctionLineChecker._check_... | `
        functi...`, `severity-` |
| `Function Complexity` | architecture_metrics.py:162 | ArchitectureMetrics._get_fu... | `
        functi...`, `severity-` |
| `Function exceeds ` | boundary_enforcer_function_checks.py:84 | FunctionBoundaryChecker._bu... | `
        functi...`, `severity-` |
| `Function group: ` | auto_split_files.py:183 | FileSplitter._suggest_funct... | `
        functi...`, `severity-` |
| `FUNCTION: ` | auto_decompose_functions.py:423 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `import ` | check_e2e_imports.py:168 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `import ` | environment_validator_dependencies.py:214 | DependencyValidator._is_pyt... | `
        functi...`, `severity-` |
| `import app\.` | check_e2e_imports.py:139 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `Missing type hints: ` | ai_detector.py:99 | AIDetector._check_missing_p... | `
        functi...`, `severity-` |
| `NOT READY` | validate_staging_health.py:271 | print_validation_summary | `
        functi...`, `severity-` |
| `Overall: ` | validate_staging_health.py:271 | print_validation_summary | `
        functi...`, `severity-` |
| `postgresql://` | environment_validator_database.py:137 | DatabaseValidator._build_po... | `
        functi...`, `severity-` |
| `processed result` | auto_decompose_functions.py:281 | FunctionDecomposer._suggest... | `
        functi...`, `severity-` |
| `Python ` | environment_validator_dependencies.py:93 | DependencyValidator._check_... | `
        functi...`, `severity-` |
| `Python ` | env_checker.py:107 | check_python_version | `
        functi...`, `severity-` |
| `Python ` | env_checker.py:110 | check_python_version | `
        functi...`, `severity-` |
| `Python fix failed: ` | dependency_scanner.py:248 | fix_python_dependencies | `
        functi...`, `severity-` |
| `python\-deps` | dependency_scanner.py:246 | fix_python_dependencies | `
        functi...`, `severity-` |
| `python\-deps` | dependency_scanner.py:248 | fix_python_dependencies | `
        functi...`, `severity-` |
| `python\-dotenv` | environment_validator_dependencies.py:203 | DependencyValidator._check_... | `
        functi...`, `severity-` |
| `READY FOR DEPLOYMENT` | validate_staging_health.py:271 | print_validation_summary | `
        functi...`, `severity-` |
| `RECOMMENDATIONS:` | auto_decompose_functions.py:437 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `Refactor ` | architecture_metrics.py:192 | ArchitectureMetrics._get_fu... | `
        functi...`, `severity-` |
| `Service name for logs` | build_staging.py:258 | _add_action_arguments | `
        functi...`, `severity-` |
| `severity\-` | architecture_dashboard_tables.py:29 | DashboardTableRenderers._ge... | `
        functi...`, `
            <... |
| `severity\-` | architecture_dashboard_tables.py:55 | DashboardTableRenderers._ge... | `
        functi...`, `
            <... |
| `Split function into ` | create_enforcement_tools.py:179 | EnforcementEngine.analyze_f... | `
        functi...`, `severity-` |
| `STRATEGY: ` | auto_decompose_functions.py:425 | FunctionDecomposer.generate... | `
        functi...`, `severity-` |
| `sys\.path` | check_e2e_imports.py:158 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `Test Stubs` | architecture_reporter.py:105 | ArchitectureReporter._print... | `
        functi...`, `severity-` |
| `Uncategorized: ` | categorizer_enhanced.py:557 | print_categorization_report | `
        functi...`, `severity-` |
| `unknown:0` | generate_string_literals_docs.py:30 | load_from_json_index | `
        functi...`, `severity-` |
| `utf\-8` | architecture_reporter.py:55 | ArchitectureReporter._write... | `
        functi...`, `severity-` |
| `utf\-8` | architecture_scanner.py:125 | ArchitectureScanner._extrac... | `
        functi...`, `severity-` |
| `utf\-8` | check_e2e_imports.py:125 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `utf\-8` | check_e2e_imports.py:178 | E2EImportChecker.fix_common... | `
        functi...`, `severity-` |
| `utf\-8` | create_enforcement_tools.py:162 | EnforcementEngine.analyze_f... | `
        functi...`, `severity-` |
| `utf\-8` | deduplicate_types.py:144 | TypeDeduplicator.find_pytho... | `
        functi...`, `severity-` |
| `utf\-8` | fix_e2e_connection_manager_imports.py:42 | find_files_with_connection_... | `
        functi...`, `severity-` |
| `utf\-8` | fix_e2e_connection_manager_imports.py:56 | fix_connection_manager_imports | `
        functi...`, `severity-` |
| `utf\-8` | fix_e2e_connection_manager_imports.py:95 | fix_connection_manager_imports | `
        functi...`, `severity-` |
| `utf\-8` | fix_import_issues.py:92 | fix_connection_manager_specs | `
        functi...`, `severity-` |
| `utf\-8` | fix_import_issues.py:112 | fix_connection_manager_specs | `
        functi...`, `severity-` |
| `utf\-8` | generate_string_literals_docs.py:21 | load_from_json_index | `
        functi...`, `severity-` |
| `utf\-8` | scan_string_literals_enhanced.py:211 | EnhancedStringLiteralIndexe... | `
        functi...`, `severity-` |
| `utf\-8` | validate_type_deduplication.py:96 | TypeDeduplicationValidator.... | `
        functi...`, `severity-` |
| `validated data` | auto_decompose_functions.py:274 | FunctionDecomposer._suggest... | `
        functi...`, `severity-` |
| `\| Percentile \| Duration \|` | generate_performance_report.py:103 | add_duration_metrics | `
        functi...`, `severity-` |
| `\|\-\-\-\-\-\-\-\-\-\-\-\-\|\-\-\-\-\...` | generate_performance_report.py:104 | add_duration_metrics | `
        functi...`, `severity-` |

### Usage Examples

- **scripts\websocket_coherence_review.py:267** - `_build_event_inventory`
- **scripts\boundary_enforcer_cli_handler.py:155** - `FailureHandler.check_emergency_failures`
- **scripts\boundary_enforcer_cli_handler.py:146** - `JSONOutputHandler.save_json_report`

---

## Subcategory: handler {subcategory-handler}

**Count**: 6 literals

### 🟢 High (≥0.8) (6 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `handle\_` | ssot_checker.py:171 | SSOTChecker._are_likely_dup... | `on_message_rece...`, `on_` |
| `on\_` | categorizer_enhanced.py:235 | EnhancedStringLiteralCatego... | `handle_`, `on_message_rece...` |
| `emit\_event` | categorizer_enhanced.py:587 | module | `handle_`, `on_message_rece...` |
| `emit\_event` | markdown_reporter.py:666 | module | `handle_`, `on_message_rece...` |
| `handle\_error` | markdown_reporter.py:668 | module | `handle_`, `on_message_rece...` |
| `on\_message\_received` | demo_enhanced_categorizer.py:113 | categorize_specific_examples | `handle_`, `on_` |

### Usage Examples

- **scripts\compliance\ssot_checker.py:171** - `SSOTChecker._are_likely_duplicates`
- **scripts\string_literals\categorizer_enhanced.py:235** - `EnhancedStringLiteralCategorizer._setup_context_hints`
- **scripts\string_literals\categorizer_enhanced.py:587** - `module`

---

## Subcategory: lifecycle {subcategory-lifecycle}

**Count**: 7 literals

### 🟢 High (≥0.8) (7 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `auto\_cleanup` | workflow_presets.py:29 | WorkflowPresets.get_minimal... | `SCHEDULE_CLEANU...`, `SCHEDULE_CLEAN... |
| `auto\_cleanup` | workflow_presets.py:44 | WorkflowPresets.get_standar... | `SCHEDULE_CLEANU...`, `SCHEDULE_CLEAN... |
| `auto\_cleanup` | workflow_presets.py:59 | WorkflowPresets.get_full_pr... | `SCHEDULE_CLEANU...`, `SCHEDULE_CLEAN... |
| `auto\_cleanup` | workflow_presets.py:74 | WorkflowPresets.get_cost_op... | `SCHEDULE_CLEANU...`, `SCHEDULE_CLEAN... |
| `SCHEDULE\_CLEANUP` | emergency_boundary_actions.py:270 | EmergencyActionSystem._crea... | `SKIP_APP_INIT`, `auto_cleanup` |
| `SCHEDULE\_CLEANUP` | emergency_boundary_actions.py:299 | EmergencyActionSystem._exec... | `SKIP_APP_INIT`, `auto_cleanup` |
| `SKIP\_APP\_INIT` | simple_perf_runner.py:21 | _setup_environment | `SCHEDULE_CLEANU...`, `SCHEDULE_CLEAN... |

### Usage Examples

- **scripts\workflow_presets.py:29** - `WorkflowPresets.get_minimal_preset`
- **scripts\workflow_presets.py:44** - `WorkflowPresets.get_standard_preset`
- **scripts\workflow_presets.py:59** - `WorkflowPresets.get_full_preset`

---

## Subcategory: type {subcategory-type}

**Count**: 24 literals

### 🟢 High (≥0.8) (24 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `files\_created` | auto_fix_test_sizes.py:694 | TestSizeFixer.fix_specific_... | `new_files_creat...`, `new_files_crea... |
| `files\_created` | auto_fix_test_sizes.py:701 | TestSizeFixer.fix_specific_... | `new_files_creat...`, `new_files_crea... |
| `files\_deleted` | cleanup_generated_files.py:296 | main | `new_files_creat...`, `new_files_crea... |
| `last\_updated` | split_learnings.py:71 | create_category_file | `new_files_creat...`, `new_files_crea... |
| `last\_updated` | split_learnings.py:95 | create_index | `new_files_creat...`, `new_files_crea... |
| `lines\_deleted` | metadata_header_generator.py:120 | MetadataHeaderGenerator.gen... | `new_files_creat...`, `new_files_crea... |
| `new\_files\_created` | auto_fix_test_sizes.py:620 | TestSizeFixer.fix_all_viola... | `files_created`, `files_created` |
| `new\_files\_created` | auto_fix_test_sizes.py:663 | TestSizeFixer.fix_all_viola... | `files_created`, `files_created` |
| `new\_files\_created` | auto_fix_test_sizes.py:751 | main | `files_created`, `files_created` |
| `thread\_created` | categorizer_enhanced.py:587 | module | `new_files_creat...`, `new_files_crea... |
| `thread\_created` | markdown_reporter.py:666 | module | `new_files_creat...`, `new_files_crea... |
| `websocket\_` | categorizer_enhanced.py:81 | EnhancedStringLiteralCatego... | `new_files_creat...`, `new_files_crea... |
| `websocket\_config` | test_websocket_dev_mode.py:96 | WebSocketDevModeTest.test_c... | `new_files_creat...`, `new_files_crea... |
| `websocket\_config` | test_websocket_dev_mode.py:98 | WebSocketDevModeTest.test_c... | `new_files_creat...`, `new_files_crea... |
| `websocket\_connection` | test_websocket_dev_mode.py:43 | WebSocketDevModeTest.__init__ | `new_files_creat...`, `new_files_crea... |
| `websocket\_connection` | test_websocket_dev_mode.py:192 | WebSocketDevModeTest.test_w... | `new_files_creat...`, `new_files_crea... |
| `websocket\_connection` | test_websocket_dev_mode.py:222 | WebSocketDevModeTest.test_w... | `new_files_creat...`, `new_files_crea... |
| `websocket\_connection` | test_websocket_dev_mode.py:231 | WebSocketDevModeTest.test_w... | `new_files_creat...`, `new_files_crea... |
| `websocket\_endpoint` | e2e_import_fixer_comprehensive.py:104 | E2EImportFixer.__init__ | `new_files_creat...`, `new_files_crea... |
| `websocket\_endpoint` | e2e_import_fixer_comprehensive.py:104 | E2EImportFixer.__init__ | `new_files_creat...`, `new_files_crea... |
| `websocket\_endpoint` | scan_string_literals.py:60 | StringLiteralCategorizer | `new_files_creat...`, `new_files_crea... |
| `websocket\_endpoint: ` | fix_import_issues.py:163 | main | `new_files_creat...`, `new_files_crea... |
| `websocket\_endpoint: ` | unified_import_manager.py:413 | UnifiedImportManager._fix_s... | `new_files_creat...`, `new_files_crea... |
| `websocket\_event` | scan_string_literals.py:78 | StringLiteralCategorizer | `new_files_creat...`, `new_files_crea... |

### Usage Examples

- **scripts\auto_fix_test_sizes.py:694** - `TestSizeFixer.fix_specific_file`
- **scripts\auto_fix_test_sizes.py:701** - `TestSizeFixer.fix_specific_file`
- **scripts\cleanup_generated_files.py:296** - `main`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

### Related Categories

- 🏷️ [Identifiers](identifiers.md) - Events often use identifier patterns

---

*This is the detailed documentation for the `events` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*