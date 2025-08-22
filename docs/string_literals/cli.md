# 💻 Cli Literals

Command line arguments and CLI-related strings

*Generated on 2025-08-21 22:03:48*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 522 |
| Subcategories | 1 |
| Average Confidence | 0.800 |

## Subcategory: argument {subcategory-argument}

**Count**: 522 literals

### 🟢 High (≥0.8) (522 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `      \-> Should be: ` | check_netra_backend_imports.py:257 | ImportAnalyzer.generate_report | `--version`, `-W` |
| `   \- @pytest\.mark\.mock\_only for t...` | categorize_tests.py:363 | main | `--version`, `-W` |
| `   \- @pytest\.mark\.real\_database f...` | categorize_tests.py:362 | main | `--version`, `-W` |
| `   \- @pytest\.mark\.real\_llm for te...` | categorize_tests.py:361 | main | `--version`, `-W` |
| `   \- app/tests/mock\_tests/` | categorize_tests.py:372 | main | `--version`, `-W` |
| `   \- app/tests/real\_services/` | categorize_tests.py:371 | main | `--version`, `-W` |
| `   \- CI/CD: pytest \-m 'not real\_se...` | categorize_tests.py:366 | main | `--version`, `-W` |
| `   \- Complexity: ` | decompose_functions.py:146 | generate_report | `--version`, `-W` |
| `   \- Data integrity verification` | demo_real_llm_testing.py:140 | demo_seed_data_management | `--version`, `-W` |
| `   \- Dependency resolution` | demo_real_llm_testing.py:141 | demo_seed_data_management | `--version`, `-W` |
| `   \- From ` | dev_launcher_secrets.py:189 | EnhancedSecretLoader._print... | `--version`, `-W` |
| `   \- Lines: ` | decompose_functions.py:145 | generate_report | `--version`, `-W` |
| `   \- Local: pytest \-m mock\_only` | categorize_tests.py:367 | main | `--version`, `-W` |
| `   \- Parallel dataset loading` | demo_real_llm_testing.py:139 | demo_seed_data_management | `--version`, `-W` |
| `   \- Staging: pytest \-m real\_servi...` | categorize_tests.py:368 | main | `--version`, `-W` |
| `   \- Transaction\-based isolation` | demo_real_llm_testing.py:142 | demo_seed_data_management | `--version`, `-W` |
| `  \- Added ` | fetch_secrets_to_env.py:123 | _print_summary | `--version`, `-W` |
| `  \- Current time: ` | cleanup_generated_files.py:227 | main | `--version`, `-W` |
| `  \- Fetched ` | fetch_secrets_to_env.py:122 | _print_summary | `--version`, `-W` |
| `  \- Files deleted: ` | cleanup_generated_files.py:286 | main | `--version`, `-W` |
| `  \- import testcontainers\.postgres ...` | fix_testcontainers_imports.py:136 | main | `--version`, `-W` |
| `  \- import testcontainers\.redis as ...` | fix_testcontainers_imports.py:135 | main | `--version`, `-W` |
| `  \- JSON: ` | check_e2e_imports.py:261 | E2EImportChecker.generate_r... | `--version`, `-W` |
| `  \- JSON: ` | import_management.py:251 | ImportManagementSystem.gene... | `--version`, `-W` |
| `  \- Markdown: ` | check_e2e_imports.py:262 | E2EImportChecker.generate_r... | `--version`, `-W` |
| `  \- Markdown: ` | import_management.py:252 | ImportManagementSystem.gene... | `--version`, `-W` |
| `  \- Max file age: ` | cleanup_generated_files.py:226 | main | `--version`, `-W` |
| `  \- postgres\_container\.PostgresCon...` | fix_testcontainers_imports.py:138 | main | `--version`, `-W` |
| `  \- redis\_container\.RedisContainer...` | fix_testcontainers_imports.py:137 | main | `--version`, `-W` |
| `  \- Replaced: ` | fix_supervisor_imports.py:42 | fix_supervisor_imports | `--version`, `-W` |
| `  \- Run from project root directory` | verify_staging_tests.py:172 | print_usage_instructions | `--version`, `-W` |
| `  \- Some tests may be skipped if res...` | verify_staging_tests.py:171 | print_usage_instructions | `--version`, `-W` |
| `  \- Space freed: ` | cleanup_generated_files.py:287 | main | `--version`, `-W` |
| `  \- Tests require access to real GCP...` | verify_staging_tests.py:170 | print_usage_instructions | `--version`, `-W` |
| `  \- With Justification: ` | analyze_mocks.py:247 | MockAnalyzer.print_summary | `--version`, `-W` |
| `  \- Without Justification: ` | analyze_mocks.py:248 | MockAnalyzer.print_summary | `--version`, `-W` |
| `  \-\-dry\-run  : Show what would be ...` | cleanup_generated_files.py:342 | module | `--version`, `-W` |
| `  \-\-force     Force synchronization...` | schema_sync.py:180 | print_usage | `--version`, `-W` |
| `  \-\-help      Show this help message` | schema_sync.py:183 | print_usage | `--version`, `-W` |
| `  \-\-help, \-h : Show this help message` | cleanup_generated_files.py:344 | module | `--version`, `-W` |
| `  \-> ` | validate_frontend_tests.py:246 | main | `--version`, `-W` |
| `  \-> Fixed` | fix_remaining_syntax_errors.py:217 | main | `--version`, `-W` |
| `  \-> No changes made` | fix_remaining_syntax_errors.py:219 | main | `--version`, `-W` |
| ` \- has justification` | find_top_mocks.py:138 | main | `--version`, `-W` |
| ` \- mocked ` | find_top_mocks.py:129 | main | `--version`, `-W` |
| ` \- NO JUSTIFICATION` | find_top_mocks.py:136 | main | `--version`, `-W` |
| ` \- Set CLICKHOUSE\_PASSWORD env var` | reset_clickhouse_auto.py:72 | _check_password_requirements | `--version`, `-W` |
| ` \- syntax already valid` | fix_embedded_setup_imports.py:143 | EmbeddedSetupImportFixer.pr... | `--version`, `-W` |
| ` \- syntax already valid` | fix_malformed_imports.py:185 | MalformedImportFixer.proces... | `--version`, `-W` |
| ` \- Test ` | seed_staging_data.py:174 | StagingDataSeeder.seed_thre... | `--version`, `-W` |
| ` \- Unexpected error: ` | fast_import_checker.py:416 | verify_fixes | `--version`, `-W` |
| ` \-\-action stop' to shut down` | build_staging.py:380 | _print_success_message | `--version`, `-W` |
| ` \-\-fix` | fix_e2e_tests_comprehensive.py:387 | main | `--version`, `-W` |
| ` \-\-include='` | command_runner.py:66 | CommandRunner.grep_search | `--version`, `-W` |
| ` \-> ` | check_imports.py:302 | ImportAnalyzer.generate_report | `--version`, `-W` |
| ` \-> ` | code_review_analysis.py:130 | CodeReviewAnalysis._check_k... | `--version`, `-W` |
| ` \-> ` | comprehensive_import_scanner.py:119 | ComprehensiveScanReport.pri... | `--version`, `-W` |
| ` \-> ` | e2e_import_fixer_comprehensive.py:389 | E2EImportFixer.fix_file | `--version`, `-W` |
| ` \-> ` | fix_schema_imports.py:109 | SchemaImportFixer._move_sch... | `--version`, `-W` |
| `\- \`` | markdown_reporter.py:355 | MarkdownReporter._generate_... | `--version`, `-W` |
| `\- \`` | markdown_reporter.py:376 | MarkdownReporter._generate_... | `--version`, `-W` |
| `\- \`` | websocket_coherence_review.py:306 | _build_backend_only_section | `--version`, `-W` |
| `\- \`` | websocket_coherence_review.py:316 | _build_frontend_only_section | `--version`, `-W` |
| `\- Active SPECs: ` | update_spec_timestamps.py:280 | main | `--version`, `-W` |
| `\- All modules have test coverage` | report_generator.py:57 | ReportGenerator._generate_m... | `--version`, `-W` |
| `\- Business Goal:` | aggressive_syntax_fix.py:98 | aggressive_fix | `--version`, `-W` |
| `\- Comprehensive validation` | demo_real_llm_testing.py:261 | main | `--version`, `-W` |
| `\- Conduct thorough security audit im...` | code_review_reporter.py:132 | CodeReviewReporter._add_rec... | `--version`, `-W` |
| `\- Conduct thorough security audit im...` | report_generator.py:170 | ReportGenerator._add_genera... | `--version`, `-W` |
| `\- Consider manual review of recent A...` | code_review_reporter.py:128 | CodeReviewReporter._add_rec... | `--version`, `-W` |
| `\- Consider manual review of recent A...` | report_generator.py:166 | ReportGenerator._add_genera... | `--version`, `-W` |
| `\- Cost tracking and safety monitoring` | demo_real_llm_testing.py:264 | main | `--version`, `-W` |
| `\- Critical Issues Found: ` | code_review_reporter.py:29 | CodeReviewReporter._add_exe... | `--version`, `-W` |
| `\- Critical Issues Found: ` | report_generator.py:53 | ReportGenerator._add_issue_... | `--version`, `-W` |
| `\- Enhanced seed data management` | demo_real_llm_testing.py:262 | main | `--version`, `-W` |
| `\- Failed: ` | check_e2e_imports.py:251 | E2EImportChecker.generate_r... | `--version`, `-W` |
| `\- Files fixed: ` | fix_e2e_tests_comprehensive.py:376 | main | `--version`, `-W` |
| `\- Files with issues: ` | fix_e2e_tests_comprehensive.py:375 | main | `--version`, `-W` |
| `\- Fixed: ` | check_e2e_imports.py:252 | E2EImportChecker.generate_r... | `--version`, `-W` |
| `\- Focus Area: ` | code_review_reporter.py:28 | CodeReviewReporter._add_exe... | `--version`, `-W` |
| `\- Focus Area: ` | report_generator.py:46 | ReportGenerator._add_execut... | `--version`, `-W` |
| `\- High Priority Issues: ` | code_review_reporter.py:30 | CodeReviewReporter._add_exe... | `--version`, `-W` |
| `\- High Priority Issues: ` | report_generator.py:54 | ReportGenerator._add_issue_... | `--version`, `-W` |
| `\- Isolated test environments` | demo_real_llm_testing.py:260 | main | `--version`, `-W` |
| `\- Legacy SPECs: ` | update_spec_timestamps.py:279 | main | `--version`, `-W` |
| `\- Low Priority Issues: ` | code_review_reporter.py:32 | CodeReviewReporter._add_exe... | `--version`, `-W` |
| `\- Low Priority Issues: ` | report_generator.py:56 | ReportGenerator._add_issue_... | `--version`, `-W` |
| `\- Medium Priority Issues: ` | code_review_reporter.py:31 | CodeReviewReporter._add_exe... | `--version`, `-W` |
| `\- Medium Priority Issues: ` | report_generator.py:55 | ReportGenerator._add_issue_... | `--version`, `-W` |
| `\- No critical gaps found` | report_generator.py:53 | ReportGenerator._generate_m... | `--version`, `-W` |
| `\- No flaky tests detected` | report_generator.py:64 | ReportGenerator._generate_m... | `--version`, `-W` |
| `\- No legacy tests found` | report_generator.py:61 | ReportGenerator._generate_m... | `--version`, `-W` |
| `\- No recommendations at this time` | report_generator.py:70 | ReportGenerator._generate_m... | `--version`, `-W` |
| `\- No slow tests detected` | report_generator.py:67 | ReportGenerator._generate_m... | `--version`, `-W` |
| `\- Parallel test coordination` | demo_real_llm_testing.py:263 | main | `--version`, `-W` |
| `\- Profile application performance an...` | code_review_reporter.py:134 | CodeReviewReporter._add_rec... | `--version`, `-W` |
| `\- Profile application performance an...` | report_generator.py:172 | ReportGenerator._add_genera... | `--version`, `-W` |
| `\- Remaining issues: ` | fix_e2e_tests_comprehensive.py:377 | main | `--version`, `-W` |
| `\- Revenue Impact:` | aggressive_syntax_fix.py:100 | aggressive_fix | `--version`, `-W` |
| `\- Review Type: ` | code_review_reporter.py:26 | CodeReviewReporter._add_exe... | `--version`, `-W` |
| `\- Review Type: ` | report_generator.py:44 | ReportGenerator._add_execut... | `--version`, `-W` |
| `\- Segment:` | aggressive_syntax_fix.py:97 | aggressive_fix | `--version`, `-W` |
| `\- Successful: ` | check_e2e_imports.py:250 | E2EImportChecker.generate_r... | `--version`, `-W` |
| `\- Total files modified: ` | fix_all_import_issues.py:240 | ComprehensiveImportFixer.ge... | `--version`, `-W` |
| `\- Total Files: ` | check_e2e_imports.py:249 | E2EImportChecker.generate_r... | `--version`, `-W` |
| `\- Total files: ` | fix_e2e_tests_comprehensive.py:374 | main | `--version`, `-W` |
| `\- Total fixes applied: ` | fix_all_import_issues.py:241 | ComprehensiveImportFixer.ge... | `--version`, `-W` |
| `\- Total SPEC files: ` | update_spec_timestamps.py:278 | main | `--version`, `-W` |
| `\- Unknown status: ` | update_spec_timestamps.py:281 | main | `--version`, `-W` |
| `\- Update specifications to match cur...` | code_review_reporter.py:130 | CodeReviewReporter._add_rec... | `--version`, `-W` |
| `\- Update specifications to match cur...` | report_generator.py:168 | ReportGenerator._add_genera... | `--version`, `-W` |
| `\- Value Impact:` | aggressive_syntax_fix.py:99 | aggressive_fix | `--version`, `-W` |
| `\- ⏱️ Average test duration is high, ...` | generate_performance_report.py:127 | add_recommendations | `--version`, `-W` |
| `\- ⚠️ Investigate security test failures` | generate_security_report.py:211 | _generate_security_recommen... | `--version`, `-W` |
| `\- ⚡ Consider parallelizing long\-run...` | generate_performance_report.py:122 | add_recommendations | `--version`, `-W` |
| `\- ✅ No critical security issues found` | generate_security_report.py:220 | _generate_security_recommen... | `--version`, `-W` |
| `\- ✅ Performance is within acceptable...` | generate_performance_report.py:125 | add_recommendations | `--version`, `-W` |
| `\- ❌ Fix failing security tests befor...` | generate_security_report.py:216 | _generate_security_recommen... | `--version`, `-W` |
| `\- 📊 Profile tests with duration > 10s` | generate_performance_report.py:123 | add_recommendations | `--version`, `-W` |
| `\- 📚 Keep security dependencies up to...` | generate_security_report.py:222 | _generate_security_recommen... | `--version`, `-W` |
| `\- 📝 Update security tests to cover i...` | generate_security_report.py:206 | _generate_security_recommen... | `--version`, `-W` |
| `\- 🔄 Continue regular security testing` | generate_security_report.py:221 | _generate_security_recommen... | `--version`, `-W` |
| `\- 🔍 Investigate timeout issues in sl...` | generate_performance_report.py:121 | add_recommendations | `--version`, `-W` |
| `\- 🔍 Review and fix static analysis f...` | generate_security_report.py:205 | _generate_security_recommen... | `--version`, `-W` |
| `\- 🛡️ Strengthen security controls in...` | generate_security_report.py:212 | _generate_security_recommen... | `--version`, `-W` |
| `\-\-` | generate_fix.py:370 | load_context | `--version`, `-W` |
| `\-\-\-` | code_review_reporter.py:139 | CodeReviewReporter._add_rep... | `--version`, `-W` |
| `\-\-\-` | report_generator.py:177 | ReportGenerator._add_report... | `--version`, `-W` |
| `\-\-\-` | markdown_reporter.py:383 | MarkdownReporter._generate_... | `--version`, `-W` |
| `\-\-\-` | markdown_reporter.py:394 | MarkdownReporter._generate_... | `--version`, `-W` |
| `\-\-\-` | markdown_reporter.py:517 | MarkdownReporter._generate_... | `--version`, `-W` |
| `\-\-\-` | markdown_reporter.py:537 | MarkdownReporter._generate_... | `--version`, `-W` |
| `\-\-\-` | team_updates_sync.py:149 | generate_simple_report | `--version`, `-W` |
| `\-\-activate` | enable_metadata_tracking.py:17 | _get_argument_parser | `--version`, `-W` |
| `\-\-add\-cloudsql\-instances` | deploy_to_gcp.py:488 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-add\-cloudsql\-instances` | deploy_to_gcp.py:494 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-agent` | agent_tracking_helper.py:371 | _add_required_arguments | `--version`, `-W` |
| `\-\-allow\-unauthenticated` | deploy_to_gcp.py:472 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-assess` | emergency_boundary_actions.py:436 | main | `--version`, `-W` |
| `\-\-auto\-fix` | fix_e2e_tests_comprehensive.py:369 | main | `--version`, `-W` |
| `\-\-auto\-restart` | dev_launcher_improved.py:73 | _add_feature_arguments | `--version`, `-W` |
| `\-\-backend\-port` | dev_launcher_improved.py:57 | _add_port_arguments | `--version`, `-W` |
| `\-\-batch` | metadata_header_generator.py:357 | main | `--version`, `-W` |
| `\-\-build\-arg` | build_staging.py:61 | StagingBuilder.build_backend | `--version`, `-W` |
| `\-\-build\-arg` | build_staging.py:112 | StagingBuilder.build_frontend | `--version`, `-W` |
| `\-\-build\-arg` | build_staging.py:113 | StagingBuilder.build_frontend | `--version`, `-W` |
| `\-\-build\-local` | deploy_to_gcp.py:785 | main | `--version`, `-W` |
| `\-\-category` | benchmark_optimization.py:403 | main | `--version`, `-W` |
| `\-\-category` | query_string_literals.py:138 | main | `--version`, `-W` |
| `\-\-change\-type` | metadata_header_generator.py:359 | main | `--version`, `-W` |
| `\-\-changes` | agent_tracking_helper.py:375 | _add_required_arguments | `--version`, `-W` |
| `\-\-check` | auth_constants_migration.py:338 | main | `--version`, `-W` |
| `\-\-check` | generate_fix.py:309 | FixValidator._apply_patch | `--version`, `-W` |
| `\-\-check\-all` | fix_malformed_imports.py:293 | main | `--version`, `-W` |
| `\-\-check\-files\-only` | enforce_limits.py:234 | create_argument_parser | `--version`, `-W` |
| `\-\-check\-functions\-only` | enforce_limits.py:236 | create_argument_parser | `--version`, `-W` |
| `\-\-check\-stubs` | enforce_limits.py:240 | create_argument_parser | `--version`, `-W` |
| `\-\-check\-types` | enforce_limits.py:238 | create_argument_parser | `--version`, `-W` |
| `\-\-ci` | validate_type_deduplication.py:344 | main | `--version`, `-W` |
| `\-\-clean` | deduplicate_types.py:424 | main | `--version`, `-W` |
| `\-\-cleanup` | deploy_to_gcp.py:789 | main | `--version`, `-W` |
| `\-\-cli\-only` | architecture_health.py:69 | main | `--version`, `-W` |
| `\-\-config` | deploy_to_gcp.py:422 | GCPDeployer.build_image_cloud | `--version`, `-W` |
| `\-\-config\-file` | seed_staging_data.py:384 | _add_basic_arguments | `--version`, `-W` |
| `\-\-coverage` | generate_report.py:176 | main | `--version`, `-W` |
| `\-\-cpu` | deploy_to_gcp.py:468 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-create\-db` | enable_metadata_tracking.py:23 | _get_argument_parser | `--version`, `-W` |
| `\-\-daily` | manage_workflows.py:189 | _setup_budget_parser | `--version`, `-W` |
| `\-\-data\-file=\-` | create_staging_secrets.py:71 | create_secret | `--version`, `-W` |
| `\-\-data\-file=\-` | deploy_to_gcp.py:589 | GCPDeployer.setup_secrets | `--version`, `-W` |
| `\-\-date=iso` | team_updates_git_analyzer.py:42 | GitAnalyzer.get_commits | `--version`, `-W` |
| `\-\-days` | cleanup_generated_files.py:333 | module | `--version`, `-W` |
| `\-\-days` | cleanup_generated_files.py:335 | module | `--version`, `-W` |
| `\-\-days` | cleanup_workflow_runs.py:180 | parse_args | `--version`, `-W` |
| `\-\-deployment\-time` | staging_error_monitor.py:257 | parse_deployment_time | `--version`, `-W` |
| `\-\-depth=0` | dependency_scanner.py:133 | get_installed_node_packages | `--version`, `-W` |
| `\-\-diagnose` | startup_diagnostics.py:211 | main | `--version`, `-W` |
| `\-\-dirs` | enhanced_string_literals_docs.py:81 | main | `--version`, `-W` |
| `\-\-dirs` | scan_string_literals_enhanced.py:374 | main | `--version`, `-W` |
| `\-\-disable` | manage_workflows.py:183 | _setup_feature_parser | `--version`, `-W` |
| `\-\-dry\-run` | agent_tracking_helper.py:379 | _add_optional_arguments | `--version`, `-W` |
| `\-\-dry\-run` | auth_constants_migration.py:340 | main | `--version`, `-W` |
| `\-\-dry\-run` | cleanup_duplicate_tests.py:285 | main | `--version`, `-W` |
| `\-\-dry\-run` | cleanup_generated_files.py:331 | module | `--version`, `-W` |
| `\-\-dry\-run` | cleanup_staging_environments.py:406 | _add_basic_arguments | `--version`, `-W` |
| `\-\-dry\-run` | cleanup_workflow_runs.py:190 | parse_args | `--version`, `-W` |
| `\-\-dry\-run` | clean_slate_executor.py:224 | main | `--version`, `-W` |
| `\-\-dry\-run` | comprehensive_import_scanner.py:751 | main | `--version`, `-W` |
| `\-\-dry\-run` | deduplicate_types.py:394 | main | `--version`, `-W` |
| `\-\-dry\-run` | e2e_import_fixer_comprehensive.py:558 | main | `--version`, `-W` |
| `\-\-dry\-run` | fix_all_import_issues.py:266 | main | `--version`, `-W` |
| `\-\-dry\-run` | fix_comprehensive_imports.py:304 | main | `--version`, `-W` |
| `\-\-dry\-run` | fix_embedded_setup_imports.py:241 | main | `--version`, `-W` |
| `\-\-dry\-run` | fix_imports.py:314 | main | `--version`, `-W` |
| `\-\-dry\-run` | fix_malformed_imports.py:283 | main | `--version`, `-W` |
| `\-\-dry\-run` | fix_netra_backend_imports.py:233 | main | `--version`, `-W` |
| `\-\-dry\-run` | import_management.py:128 | ImportManagementSystem.fix_... | `--version`, `-W` |
| `\-\-dry\-run` | import_management.py:319 | main | `--version`, `-W` |
| `\-\-dry\-run` | unified_import_manager.py:607 | main | `--version`, `-W` |
| `\-\-dry\-run` | validate_agent_tests.py:331 | main | `--version`, `-W` |
| `\-\-dynamic` | dev_launcher_improved.py:59 | _add_port_arguments | `--version`, `-W` |
| `\-\-emergency\-only` | boundary_enforcer_cli_handler.py:43 | CLIArgumentParser._add_rema... | `--version`, `-W` |
| `\-\-enable` | manage_workflows.py:182 | _setup_feature_parser | `--version`, `-W` |
| `\-\-enforce` | emergency_boundary_actions.py:78 | EmergencyActionSystem._get_... | `--version`, `-W` |
| `\-\-enhanced` | generate_string_literals_docs.py:79 | main | `--version`, `-W` |
| `\-\-enhanced\-mode` | scan_string_literals.py:278 | main | `--version`, `-W` |
| `\-\-env` | act_wrapper.py:227 | add_staging_command | `--version`, `-W` |
| `\-\-env\-file` | act_wrapper.py:101 | ACTWrapper._build_act_command | `--version`, `-W` |
| `\-\-environment` | validate_network_constants.py:209 | main | `--version`, `-W` |
| `\-\-error` | generate_fix.py:386 | main | `--version`, `-W` |
| `\-\-exclude\-pattern` | create_enforcement_tools.py:390 | add_advanced_arguments | `--version`, `-W` |
| `\-\-execute` | emergency_boundary_actions.py:437 | main | `--version`, `-W` |
| `\-\-fail\-fast` | enforce_limits.py:230 | create_argument_parser | `--version`, `-W` |
| `\-\-fail\-on\-stubs` | enforce_limits.py:244 | create_argument_parser | `--version`, `-W` |
| `\-\-fail\-on\-violation` | create_enforcement_tools.py:387 | add_advanced_arguments | `--version`, `-W` |
| `\-\-fail\-on\-violations` | architecture_health.py:70 | main | `--version`, `-W` |
| `\-\-fast\-fail` | clean_slate_executor.py:177 | CleanSlateExecutor.phase4_v... | `--version`, `-W` |
| `\-\-fast\-fail` | deploy_to_gcp.py:168 | GCPDeployer.run_pre_deploym... | `--version`, `-W` |
| `\-\-file` | auto_decompose_functions.py:456 | main | `--version`, `-W` |
| `\-\-file` | auto_split_files.py:364 | main | `--version`, `-W` |
| `\-\-file` | metadata_header_generator.py:356 | main | `--version`, `-W` |
| `\-\-fix` | check_e2e_imports.py:270 | main | `--version`, `-W` |
| `\-\-fix` | check_imports.py:345 | main | `--version`, `-W` |
| `\-\-fix` | comprehensive_import_scanner.py:750 | main | `--version`, `-W` |
| `\-\-fix` | dependency_scanner.py:265 | main | `--version`, `-W` |
| `\-\-fix` | fix_e2e_tests_comprehensive.py:369 | main | `--version`, `-W` |
| `\-\-fix` | startup_diagnostics.py:212 | main | `--version`, `-W` |
| `\-\-fix` | validate_service_independence.py:260 | main | `--version`, `-W` |
| `\-\-focus` | check_imports.py:349 | main | `--version`, `-W` |
| `\-\-focus` | comprehensive_import_scanner.py:754 | main | `--version`, `-W` |
| `\-\-focus` | fix_imports.py:318 | main | `--version`, `-W` |
| `\-\-force` | schema_sync.py:50 | parse_command_line_args | `--version`, `-W` |
| `\-\-format` | generate_performance_report.py:155 | parse_arguments | `--version`, `-W` |
| `\-\-format` | generate_report.py:177 | main | `--version`, `-W` |
| `\-\-format` | generate_security_report.py:259 | main | `--version`, `-W` |
| `\-\-format` | process_results.py:210 | main | `--version`, `-W` |
| `\-\-format` | deploy_to_gcp.py:543 | GCPDeployer.get_service_url | `--version`, `-W` |
| `\-\-format` | function_complexity_analyzer.py:355 | main | `--version`, `-W` |
| `\-\-format` | scan_string_literals_enhanced.py:366 | main | `--version`, `-W` |
| `\-\-format` | team_updates.py:49 | main | `--version`, `-W` |
| `\-\-frontend\-port` | dev_launcher_improved.py:58 | _add_port_arguments | `--version`, `-W` |
| `\-\-help` | cleanup_generated_files.py:340 | module | `--version`, `-W` |
| `\-\-help` | schema_sync.py:192 | module | `--version`, `-W` |
| `\-\-host` | start_auth_service.py:58 | AuthServiceManager.start_au... | `--version`, `-W` |
| `\-\-image` | deploy_to_gcp.py:463 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-import\-only` | fix_comprehensive_imports.py:330 | main | `--version`, `-W` |
| `\-\-import\-only` | import_management.py:70 | ImportManagementSystem.chec... | `--version`, `-W` |
| `\-\-inactive\-hours` | cleanup_staging_environments.py:412 | _add_cleanup_arguments | `--version`, `-W` |
| `\-\-include\-confidence` | scan_string_literals_enhanced.py:368 | main | `--version`, `-W` |
| `\-\-include\-pattern` | create_enforcement_tools.py:389 | add_advanced_arguments | `--version`, `-W` |
| `\-\-include\-tests` | enhanced_string_literals_docs.py:82 | main | `--version`, `-W` |
| `\-\-include\-tests` | scan_string_literals.py:276 | main | `--version`, `-W` |
| `\-\-include\-tests` | scan_string_literals_enhanced.py:370 | main | `--version`, `-W` |
| `\-\-index` | query_string_literals.py:139 | main | `--version`, `-W` |
| `\-\-input` | generate_performance_report.py:154 | parse_arguments | `--version`, `-W` |
| `\-\-input` | generate_report.py:175 | main | `--version`, `-W` |
| `\-\-input` | generate_security_report.py:258 | main | `--version`, `-W` |
| `\-\-input` | process_results.py:209 | main | `--version`, `-W` |
| `\-\-input` | generate_string_literals_docs.py:75 | main | `--version`, `-W` |
| `\-\-input\-dir` | merge_results.py:137 | create_argument_parser | `--version`, `-W` |
| `\-\-install\-hooks` | boundary_enforcer_cli_handler.py:44 | CLIArgumentParser._add_rema... | `--version`, `-W` |
| `\-\-install\-hooks` | enable_metadata_tracking.py:21 | _get_argument_parser | `--version`, `-W` |
| `\-\-job` | act_wrapper.py:221 | add_run_command | `--version`, `-W` |
| `\-\-json` | check_imports.py:347 | main | `--version`, `-W` |
| `\-\-json` | comprehensive_import_scanner.py:752 | main | `--version`, `-W` |
| `\-\-json` | dependency_scanner.py:133 | get_installed_node_packages | `--version`, `-W` |
| `\-\-json` | enforce_limits.py:254 | create_argument_parser | `--version`, `-W` |
| `\-\-json` | function_complexity_cli.py:30 | _add_basic_arguments | `--version`, `-W` |
| `\-\-json` | generate_wip_report.py:69 | WIPReportGenerator.run_comp... | `--version`, `-W` |
| `\-\-json` | team_updates_compliance_analyzer.py:75 | ComplianceAnalyzer.get_comp... | `--version`, `-W` |
| `\-\-json` | validate_type_deduplication.py:345 | main | `--version`, `-W` |
| `\-\-json` | workflow_introspection.py:110 | WorkflowIntrospector.get_re... | `--version`, `-W` |
| `\-\-json` | workflow_introspection.py:138 | WorkflowIntrospector.get_ru... | `--version`, `-W` |
| `\-\-json\-only` | create_enforcement_tools.py:391 | add_advanced_arguments | `--version`, `-W` |
| `\-\-json\-output` | boundary_enforcer_cli_handler.py:42 | CLIArgumentParser._add_rema... | `--version`, `-W` |
| `\-\-json\-output` | emergency_boundary_actions.py:78 | EmergencyActionSystem._get_... | `--version`, `-W` |
| `\-\-keep\-failed` | cleanup_workflow_runs.py:205 | parse_args | `--version`, `-W` |
| `\-\-lenient` | schema_sync.py:52 | parse_command_line_args | `--version`, `-W` |
| `\-\-level` | clean_slate_executor.py:165 | CleanSlateExecutor.phase4_v... | `--version`, `-W` |
| `\-\-level` | clean_slate_executor.py:176 | CleanSlateExecutor.phase4_v... | `--version`, `-W` |
| `\-\-level` | deploy_to_gcp.py:168 | GCPDeployer.run_pre_deploym... | `--version`, `-W` |
| `\-\-limit` | workflow_introspection.py:91 | WorkflowIntrospector.list_w... | `--version`, `-W` |
| `\-\-limit` | workflow_introspection.py:110 | WorkflowIntrospector.get_re... | `--version`, `-W` |
| `\-\-limit` | workflow_introspection.py:345 | main | `--version`, `-W` |
| `\-\-limit` | workflow_introspection.py:349 | main | `--version`, `-W` |
| `\-\-load\-secrets` | dev_launcher_improved.py:70 | _add_feature_arguments | `--version`, `-W` |
| `\-\-local\-only` | cleanup_workflow_runs.py:195 | parse_args | `--version`, `-W` |
| `\-\-logs` | workflow_introspection.py:355 | main | `--version`, `-W` |
| `\-\-machine\-type` | deploy_to_gcp.py:424 | GCPDeployer.build_image_cloud | `--version`, `-W` |
| `\-\-max\-age\-days` | cleanup_staging_environments.py:411 | _add_cleanup_arguments | `--version`, `-W` |
| `\-\-max\-cost\-per\-pr` | cleanup_staging_environments.py:413 | _add_cleanup_arguments | `--version`, `-W` |
| `\-\-max\-file\-lines` | create_enforcement_tools.py:381 | add_basic_arguments | `--version`, `-W` |
| `\-\-max\-function\-lines` | create_enforcement_tools.py:382 | add_basic_arguments | `--version`, `-W` |
| `\-\-max\-function\-lines` | enforce_limits.py:250 | create_argument_parser | `--version`, `-W` |
| `\-\-max\-instances` | deploy_to_gcp.py:470 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-max\-lines` | enforce_limits.py:248 | create_argument_parser | `--version`, `-W` |
| `\-\-max\-lines` | function_complexity_cli.py:26 | _add_basic_arguments | `--version`, `-W` |
| `\-\-memory` | deploy_to_gcp.py:467 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-messages\-per\-thread` | seed_staging_data.py:390 | _add_data_count_arguments | `--version`, `-W` |
| `\-\-metrics` | seed_staging_data.py:392 | _add_data_count_arguments | `--version`, `-W` |
| `\-\-migrate` | auth_constants_migration.py:339 | main | `--version`, `-W` |
| `\-\-migrate` | deduplicate_types.py:397 | main | `--version`, `-W` |
| `\-\-migration\-mode` | scan_string_literals_enhanced.py:384 | main | `--version`, `-W` |
| `\-\-min\-instances` | deploy_to_gcp.py:469 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-mode` | main.py:40 | _add_mode_arguments | `--version`, `-W` |
| `\-\-mode` | enforce_limits.py:228 | create_argument_parser | `--version`, `-W` |
| `\-\-model` | agent_tracking_helper.py:372 | _add_required_arguments | `--version`, `-W` |
| `\-\-monitor` | monitor_oauth_flow.py:206 | main | `--version`, `-W` |
| `\-\-monthly` | manage_workflows.py:190 | _setup_budget_parser | `--version`, `-W` |
| `\-\-no\-backend\-reload` | dev_launcher_improved.py:64 | _add_control_arguments | `--version`, `-W` |
| `\-\-no\-browser` | dev_launcher_improved.py:72 | _add_feature_arguments | `--version`, `-W` |
| `\-\-no\-coverage` | clean_slate_executor.py:177 | CleanSlateExecutor.phase4_v... | `--version`, `-W` |
| `\-\-no\-coverage` | deploy_to_gcp.py:168 | GCPDeployer.run_pre_deploym... | `--version`, `-W` |
| `\-\-no\-cpu\-throttling` | deploy_to_gcp.py:473 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-no\-duplicates` | fix_imports.py:316 | main | `--version`, `-W` |
| `\-\-no\-frontend\-reload` | dev_launcher_improved.py:65 | _add_control_arguments | `--version`, `-W` |
| `\-\-no\-reload` | dev_launcher_improved.py:66 | _add_control_arguments | `--version`, `-W` |
| `\-\-no\-reload` | dev_launcher_service.py:88 | ServiceManager._build_backe... | `--version`, `-W` |
| `\-\-no\-turbopack` | dev_launcher_improved.py:74 | _add_feature_arguments | `--version`, `-W` |
| `\-\-oneline` | team_updates_sync.py:59 | generate_simple_report | `--version`, `-W` |
| `\-\-optimizations` | seed_staging_data.py:391 | _add_data_count_arguments | `--version`, `-W` |
| `\-\-output` | generate_fix.py:390 | main | `--version`, `-W` |
| `\-\-output` | generate_performance_report.py:156 | parse_arguments | `--version`, `-W` |
| `\-\-output` | generate_report.py:178 | main | `--version`, `-W` |
| `\-\-output` | generate_security_report.py:260 | main | `--version`, `-W` |
| `\-\-output` | process_results.py:212 | main | `--version`, `-W` |
| `\-\-output` | create_enforcement_tools.py:380 | add_basic_arguments | `--version`, `-W` |
| `\-\-output` | e2e_import_fixer_comprehensive.py:561 | main | `--version`, `-W` |
| `\-\-output` | enhanced_string_literals_docs.py:80 | main | `--version`, `-W` |
| `\-\-output` | function_complexity_analyzer.py:354 | main | `--version`, `-W` |
| `\-\-output` | generate_openapi_spec.py:286 | _add_output_args | `--version`, `-W` |
| `\-\-output` | generate_string_literals_docs.py:77 | main | `--version`, `-W` |
| `\-\-output` | scan_string_literals.py:274 | main | `--version`, `-W` |
| `\-\-output` | scan_string_literals_enhanced.py:362 | main | `--version`, `-W` |
| `\-\-output` | seed_staging_data.py:396 | _add_output_arguments | `--version`, `-W` |
| `\-\-output` | team_updates.py:44 | main | `--version`, `-W` |
| `\-\-output` | team_updates_orchestrator.py:105 | main | `--version`, `-W` |
| `\-\-output` | unified_import_manager.py:617 | main | `--version`, `-W` |
| `\-\-output\-coverage` | merge_results.py:139 | create_argument_parser | `--version`, `-W` |
| `\-\-output\-dir` | benchmark_optimization.py:405 | main | `--version`, `-W` |
| `\-\-output\-html` | architecture_health.py:67 | main | `--version`, `-W` |
| `\-\-output\-json` | architecture_health.py:68 | main | `--version`, `-W` |
| `\-\-output\-json` | analyze_failures.py:210 | main | `--version`, `-W` |
| `\-\-output\-json` | merge_results.py:138 | create_argument_parser | `--version`, `-W` |
| `\-\-outputs` | workflow_introspection.py:356 | main | `--version`, `-W` |
| `\-\-path` | architecture_health.py:66 | main | `--version`, `-W` |
| `\-\-path` | create_enforcement_tools.py:379 | add_basic_arguments | `--version`, `-W` |
| `\-\-path` | function_complexity_cli.py:28 | _add_basic_arguments | `--version`, `-W` |
| `\-\-platform` | deploy_to_gcp.py:356 | GCPDeployer.build_image_local | `--version`, `-W` |
| `\-\-platform` | deploy_to_gcp.py:464 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-platform` | deploy_to_gcp.py:541 | GCPDeployer.get_service_url | `--version`, `-W` |
| `\-\-platform` | deploy_to_gcp.py:723 | GCPDeployer.cleanup | `--version`, `-W` |
| `\-\-porcelain` | clean_slate_executor.py:61 | CleanSlateExecutor.phase1_a... | `--version`, `-W` |
| `\-\-port` | deploy_to_gcp.py:466 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-port` | dev_launcher_service.py:84 | ServiceManager._build_backe... | `--version`, `-W` |
| `\-\-port` | start_auth_service.py:59 | AuthServiceManager.start_au... | `--version`, `-W` |
| `\-\-pr\-comment` | boundary_enforcer_cli_handler.py:45 | CLIArgumentParser._add_rema... | `--version`, `-W` |
| `\-\-pr\-number` | seed_staging_data.py:383 | _add_basic_arguments | `--version`, `-W` |
| `\-\-prevent\-duplicates` | enforce_limits.py:242 | create_argument_parser | `--version`, `-W` |
| `\-\-progress` | build_staging.py:62 | StagingBuilder.build_backend | `--version`, `-W` |
| `\-\-progress` | build_staging.py:114 | StagingBuilder.build_frontend | `--version`, `-W` |
| `\-\-project` | create_staging_secrets.py:42 | check_secret_exists | `--version`, `-W` |
| `\-\-project` | create_staging_secrets.py:58 | create_secret | `--version`, `-W` |
| `\-\-project` | create_staging_secrets.py:71 | create_secret | `--version`, `-W` |
| `\-\-project` | deploy_to_gcp.py:781 | main | `--version`, `-W` |
| `\-\-project\-id` | cleanup_staging_environments.py:404 | _add_basic_arguments | `--version`, `-W` |
| `\-\-project\-id` | dev_launcher_improved.py:71 | _add_feature_arguments | `--version`, `-W` |
| `\-\-project\-root` | auth_constants_migration.py:341 | main | `--version`, `-W` |
| `\-\-project\-root` | function_complexity_analyzer.py:353 | main | `--version`, `-W` |
| `\-\-prompt` | agent_tracking_helper.py:374 | _add_required_arguments | `--version`, `-W` |
| `\-\-provider` | generate_fix.py:387 | main | `--version`, `-W` |
| `\-\-quiet` | deploy_to_gcp.py:376 | GCPDeployer.build_image_local | `--version`, `-W` |
| `\-\-quiet` | deploy_to_gcp.py:725 | GCPDeployer.cleanup | `--version`, `-W` |
| `\-\-quiet` | validate_type_deduplication.py:346 | main | `--version`, `-W` |
| `\-\-readme\-api\-key` | generate_openapi_spec.py:302 | _add_readme_args | `--version`, `-W` |
| `\-\-readme\-url` | generate_openapi_spec.py:310 | _add_readme_args | `--version`, `-W` |
| `\-\-readme\-version` | generate_openapi_spec.py:306 | _add_readme_args | `--version`, `-W` |
| `\-\-reason` | manage_precommit.py:113 | main | `--version`, `-W` |
| `\-\-reason` | manage_precommit.py:117 | main | `--version`, `-W` |
| `\-\-region` | cleanup_staging_environments.py:405 | _add_basic_arguments | `--version`, `-W` |
| `\-\-region` | deploy_to_gcp.py:465 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-region` | deploy_to_gcp.py:542 | GCPDeployer.get_service_url | `--version`, `-W` |
| `\-\-region` | deploy_to_gcp.py:724 | GCPDeployer.cleanup | `--version`, `-W` |
| `\-\-region` | deploy_to_gcp.py:782 | main | `--version`, `-W` |
| `\-\-reload` | start_auth_service.py:60 | AuthServiceManager.start_au... | `--version`, `-W` |
| `\-\-remote\-only` | cleanup_workflow_runs.py:200 | parse_args | `--version`, `-W` |
| `\-\-repo` | cleanup_workflow_runs.py:176 | parse_args | `--version`, `-W` |
| `\-\-repo` | workflow_introspection.py:72 | WorkflowIntrospector._run_g... | `--version`, `-W` |
| `\-\-repo` | workflow_introspection.py:339 | main | `--version`, `-W` |
| `\-\-report` | auto_decompose_functions.py:455 | main | `--version`, `-W` |
| `\-\-report` | auto_split_files.py:363 | main | `--version`, `-W` |
| `\-\-report` | check_e2e_imports.py:271 | main | `--version`, `-W` |
| `\-\-report` | comprehensive_e2e_import_fixer.py:326 | main | `--version`, `-W` |
| `\-\-report` | emergency_boundary_actions.py:438 | main | `--version`, `-W` |
| `\-\-report` | fix_all_import_issues.py:268 | main | `--version`, `-W` |
| `\-\-results\-dir` | analyze_failures.py:209 | main | `--version`, `-W` |
| `\-\-risk` | metadata_header_generator.py:361 | main | `--version`, `-W` |
| `\-\-root` | enhanced_string_literals_docs.py:79 | main | `--version`, `-W` |
| `\-\-root` | scan_string_literals.py:273 | main | `--version`, `-W` |
| `\-\-root` | scan_string_literals_enhanced.py:360 | main | `--version`, `-W` |
| `\-\-run\-checks` | deploy_to_gcp.py:787 | main | `--version`, `-W` |
| `\-\-scan` | auto_decompose_functions.py:454 | main | `--version`, `-W` |
| `\-\-scan` | auto_split_files.py:362 | main | `--version`, `-W` |
| `\-\-scan` | dependency_scanner.py:262 | main | `--version`, `-W` |
| `\-\-scan` | emergency_boundary_actions.py:355 | EmergencyActionSystem._exec... | `--version`, `-W` |
| `\-\-scope` | metadata_header_generator.py:360 | main | `--version`, `-W` |
| `\-\-secret\-file` | act_wrapper.py:99 | ACTWrapper._build_act_command | `--version`, `-W` |
| `\-\-service` | service_discovery.py:127 | module | `--version`, `-W` |
| `\-\-set\-env\-vars` | deploy_to_gcp.py:482 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-set\-secrets` | deploy_to_gcp.py:489 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-set\-secrets` | deploy_to_gcp.py:495 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-since=` | team_updates_git_analyzer.py:41 | GitAnalyzer.get_commits | `--version`, `-W` |
| `\-\-since=` | team_updates_sync.py:59 | generate_simple_report | `--version`, `-W` |
| `\-\-skip\-backup` | clean_slate_executor.py:225 | main | `--version`, `-W` |
| `\-\-skip\-build` | deploy_to_gcp.py:783 | main | `--version`, `-W` |
| `\-\-skip\-database` | clean_slate_executor.py:226 | main | `--version`, `-W` |
| `\-\-skip\-validation` | clean_slate_executor.py:227 | main | `--version`, `-W` |
| `\-\-stat` | team_updates_sync.py:14 | get_top_changed_files | `--version`, `-W` |
| `\-\-status` | enable_metadata_tracking.py:19 | _get_argument_parser | `--version`, `-W` |
| `\-\-strict` | schema_sync.py:51 | parse_command_line_args | `--version`, `-W` |
| `\-\-strict` | validate_type_deduplication.py:343 | main | `--version`, `-W` |
| `\-\-sync\-readme` | generate_openapi_spec.py:298 | _add_readme_args | `--version`, `-W` |
| `\-\-task` | metadata_header_generator.py:358 | main | `--version`, `-W` |
| `\-\-task\-id` | agent_tracking_helper.py:373 | _add_required_arguments | `--version`, `-W` |
| `\-\-test` | generate_fix.py:385 | main | `--version`, `-W` |
| `\-\-threads\-per\-user` | seed_staging_data.py:389 | _add_data_count_arguments | `--version`, `-W` |
| `\-\-threshold` | create_enforcement_tools.py:388 | add_advanced_arguments | `--version`, `-W` |
| `\-\-time\-frame` | team_updates.py:37 | main | `--version`, `-W` |
| `\-\-time\-frame` | team_updates_orchestrator.py:102 | main | `--version`, `-W` |
| `\-\-timeout` | deploy_to_gcp.py:423 | GCPDeployer.build_image_cloud | `--version`, `-W` |
| `\-\-timeout` | deploy_to_gcp.py:471 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-until=` | team_updates_git_analyzer.py:41 | GitAnalyzer.get_commits | `--version`, `-W` |
| `\-\-update\-env\-vars` | deploy_to_gcp.py:504 | GCPDeployer.deploy_service | `--version`, `-W` |
| `\-\-upgrade` | dependency_installer.py:66 | upgrade_pip | `--version`, `-W` |
| `\-\-user` | manage_precommit.py:119 | main | `--version`, `-W` |
| `\-\-users` | seed_staging_data.py:388 | _add_data_count_arguments | `--version`, `-W` |
| `\-\-validate` | generate_fix.py:391 | main | `--version`, `-W` |
| `\-\-validate` | deduplicate_types.py:432 | main | `--version`, `-W` |
| `\-\-validate` | e2e_import_fixer_comprehensive.py:560 | main | `--version`, `-W` |
| `\-\-validate` | scan_string_literals_enhanced.py:378 | main | `--version`, `-W` |
| `\-\-validate\-only` | generate_openapi_spec.py:290 | _add_output_args | `--version`, `-W` |
| `\-\-value` | local_secrets_manager.py:218 | main | `--version`, `-W` |
| `\-\-verbose` | check_imports.py:351 | main | `--version`, `-W` |
| `\-\-verbose` | cleanup_duplicate_tests.py:290 | main | `--version`, `-W` |
| `\-\-verbose` | comprehensive_import_scanner.py:753 | main | `--version`, `-W` |
| `\-\-verbose` | demo_enhanced_categorizer.py:111 | categorize_specific_examples | `--version`, `-W` |
| `\-\-verbose` | dev_launcher_improved.py:63 | _add_control_arguments | `--version`, `-W` |
| `\-\-verbose` | dev_launcher_service.py:95 | ServiceManager._build_backe... | `--version`, `-W` |
| `\-\-verbose` | e2e_import_fixer_comprehensive.py:559 | main | `--version`, `-W` |
| `\-\-verbose` | enforce_limits.py:256 | create_argument_parser | `--version`, `-W` |
| `\-\-verbose` | fix_embedded_setup_imports.py:246 | main | `--version`, `-W` |
| `\-\-verbose` | fix_malformed_imports.py:288 | main | `--version`, `-W` |
| `\-\-verbose` | fix_netra_backend_imports.py:238 | main | `--version`, `-W` |
| `\-\-verbose` | import_management.py:325 | main | `--version`, `-W` |
| `\-\-verbose` | scan_string_literals_enhanced.py:380 | main | `--version`, `-W` |
| `\-\-verbose` | unified_import_manager.py:612 | main | `--version`, `-W` |
| `\-\-verbose` | validate_network_constants.py:215 | main | `--version`, `-W` |
| `\-\-verify` | comprehensive_e2e_import_fixer.py:325 | main | `--version`, `-W` |
| `\-\-verify` | fix_all_import_issues.py:267 | main | `--version`, `-W` |
| `\-\-verify` | fix_comprehensive_imports.py:305 | main | `--version`, `-W` |
| `\-\-verify` | startup_diagnostics.py:213 | main | `--version`, `-W` |
| `\-\-version` | act_wrapper.py:30 | ACTWrapper._validate_prereq... | `-W`, `-j` |
| `\-\-version` | dependency_scanner.py:155 | scan_system_dependencies | `-W`, `-j` |
| `\-\-version` | dependency_scanner.py:156 | scan_system_dependencies | `-W`, `-j` |
| `\-\-version` | dependency_scanner.py:157 | scan_system_dependencies | `-W`, `-j` |
| `\-\-version` | dependency_scanner.py:158 | scan_system_dependencies | `-W`, `-j` |
| `\-\-version` | dependency_services.py:77 | check_redis_installation | `-W`, `-j` |
| `\-\-version` | deploy_to_gcp.py:115 | GCPDeployer.check_gcloud | `-W`, `-j` |
| `\-\-version` | environment_validator_dependencies.py:132 | DependencyValidator._check_... | `-W`, `-j` |
| `\-\-version` | environment_validator_dependencies.py:155 | DependencyValidator._check_... | `-W`, `-j` |
| `\-\-version` | env_checker.py:151 | get_git_version | `-W`, `-j` |
| `\-\-version` | setup_act.py:29 | check_act | `-W`, `-j` |
| `\-\-version` | startup_environment.py:101 | DependencyChecker._check_no... | `-W`, `-j` |
| `\-\-version` | startup_environment.py:113 | DependencyChecker._check_npm | `-W`, `-j` |
| `\-\-watch\-boundaries` | enhance_dev_launcher_boundaries.py:70 | enhance_launcher_args | `--version`, `-W` |
| `\-\-workflow` | workflow_introspection.py:114 | WorkflowIntrospector.get_re... | `--version`, `-W` |
| `\-\-workflow` | workflow_introspection.py:350 | main | `--version`, `-W` |
| `\-\-workflow\-id` | cleanup_workflow_runs.py:186 | parse_args | `--version`, `-W` |
| `\-> ` | code_review_ai_detector.py:94 | CodeReviewAIDetector._check... | `--version`, `-W` |
| `\-c` | benchmark_optimization.py:403 | main | `--version`, `-W` |
| `\-c` | clean_slate_executor.py:108 | CleanSlateExecutor.phase2_d... | `--version`, `-W` |
| `\-c` | config_setup_scripts.py:157 | verify_module_imports | `--version`, `-W` |
| `\-c` | query_string_literals.py:138 | main | `--version`, `-W` |
| `\-c` | setup_act.py:46 | install_act | `--version`, `-W` |
| `\-c` | startup_diagnostics.py:77 | check_database_connection | `--version`, `-W` |
| `\-c` | validate_service_independence.py:184 | ServiceIndependenceValidato... | `--version`, `-W` |
| `\-d` | start_auth_service.py:29 | AuthServiceManager.start_de... | `--version`, `-W` |
| `\-f` | build_staging.py:60 | StagingBuilder.build_backend | `--version`, `-W` |
| `\-f` | build_staging.py:111 | StagingBuilder.build_frontend | `--version`, `-W` |
| `\-f` | deploy_to_gcp.py:355 | GCPDeployer.build_image_local | `--version`, `-W` |
| `\-f` | deploy_to_gcp.py:411 | GCPDeployer.build_image_cloud | `--version`, `-W` |
| `\-f` | start_auth_service.py:28 | AuthServiceManager.start_de... | `--version`, `-W` |
| `\-f` | start_auth_service.py:88 | AuthServiceManager.stop_all | `--version`, `-W` |
| `\-h` | cleanup_generated_files.py:340 | module | `--version`, `-W` |
| `\-i` | generate_fix.py:321 | FixValidator._apply_patch | `--version`, `-W` |
| `\-j` | act_wrapper.py:97 | ACTWrapper._build_act_command | `--version`, `-W` |
| `\-l` | act_wrapper.py:115 | ACTWrapper._validate_single... | `--version`, `-W` |
| `\-m` | dependency_installer.py:66 | upgrade_pip | `--version`, `-W` |
| `\-m` | fix_comprehensive_imports.py:330 | main | `--version`, `-W` |
| `\-m` | import_management.py:70 | ImportManagementSystem.chec... | `--version`, `-W` |
| `\-m` | setup_act.py:128 | install_dependencies | `--version`, `-W` |
| `\-m` | startup_diagnostics.py:91 | check_dependencies | `--version`, `-W` |
| `\-m` | start_auth_service.py:56 | AuthServiceManager.start_au... | `--version`, `-W` |
| `\-o` | create_enforcement_tools.py:380 | add_basic_arguments | `--version`, `-W` |
| `\-o` | generate_openapi_spec.py:286 | _add_output_args | `--version`, `-W` |
| `\-p1` | generate_fix.py:321 | FixValidator._apply_patch | `--version`, `-W` |
| `\-r` | dependency_installer.py:89 | install_from_requirements | `--version`, `-W` |
| `\-r` | startup_diagnostics.py:161 | fix_dependencies | `--version`, `-W` |
| `\-rf` | dependency_installer.py:165 | clean_node_modules | `--version`, `-W` |
| `\-t` | build_staging.py:59 | StagingBuilder.build_backend | `--version`, `-W` |
| `\-t` | build_staging.py:110 | StagingBuilder.build_frontend | `--version`, `-W` |
| `\-t` | deploy_to_gcp.py:354 | GCPDeployer.build_image_local | `--version`, `-W` |
| `\-t` | deploy_to_gcp.py:411 | GCPDeployer.build_image_cloud | `--version`, `-W` |
| `\-v` | enforce_limits.py:256 | create_argument_parser | `--version`, `-W` |
| `\-v` | env_checker.py:125 | check_node_version | `--version`, `-W` |
| `\-v` | validate_network_constants.py:215 | main | `--version`, `-W` |
| `\-W` | act_wrapper.py:95 | ACTWrapper._build_act_command | `--version`, `-j` |
| `\-W` | act_wrapper.py:115 | ACTWrapper._validate_single... | `--version`, `-j` |
| `\-X` | cleanup_workflow_runs.py:60 | get_workflow_runs | `--version`, `-W` |
| `\-X` | cleanup_workflow_runs.py:85 | delete_workflow_run | `--version`, `-W` |
| `\-X` | cleanup_workflow_runs.py:99 | get_artifacts | `--version`, `-W` |
| `\-X` | cleanup_workflow_runs.py:124 | delete_artifact | `--version`, `-W` |

### Usage Examples

- **scripts\check_netra_backend_imports.py:257** - `ImportAnalyzer.generate_report`
- **scripts\categorize_tests.py:363** - `main`
- **scripts\categorize_tests.py:362** - `main`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

---

*This is the detailed documentation for the `cli` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*