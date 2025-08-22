# 📋 Formats Literals

Template strings, regex patterns, JSON, and datetime formats

*Generated on 2025-08-21 22:09:50*

## 📊 Category Statistics

| Metric | Value |
|--------|-------|
| Total Literals | 1,903 |
| Subcategories | 5 |
| Average Confidence | 0.614 |

## 📋 Subcategories

- [datetime (58 literals)](#subcategory-datetime)
- [json (110 literals)](#subcategory-json)
- [mime_type (10 literals)](#subcategory-mime-type)
- [regex (1576 literals)](#subcategory-regex)
- [template (149 literals)](#subcategory-template)

## Subcategory: datetime {subcategory-datetime}

**Count**: 58 literals

### 🟢 High (≥0.8) (57 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `2022\-11\-28` | force_cancel_workflow.py:17 | get_workflow_runs | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `2022\-11\-28` | force_cancel_workflow.py:34 | force_cancel_workflow | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `2025\-08\-16` | split_learnings.py:71 | create_category_file | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `2025\-08\-16` | split_learnings.py:95 | create_index | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `        <last\_updated>2025\-08\-16</...` | split_learnings_robust.py:59 | create_category_file | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `        <last\_updated>2025\-08\-16</...` | split_learnings_robust.py:88 | create_index | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y%m%d\_%H%M%S` | architecture_reporter.py:25 | ArchitectureReporter.export... | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | auto_fix_test_violations.py:753 | TestViolationAnalyzer._crea... | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | clean_slate_executor.py:22 | CleanSlateExecutor.__init__ | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | clean_slate_executor.py:24 | CleanSlateExecutor.__init__ | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | code_review_reporter.py:174 | CodeReviewReporter.save_report | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | comprehensive_test_fixer.py:406 | BatchProcessor.generate_report | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | e2e_import_fixer_comprehensive.py:541 | E2EImportFixer.save_report | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | emergency_boundary_actions.py:320 | EmergencyActionSystem._crea... | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | fix_test_batch.py:374 | main | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | report_generator.py:184 | ReportGenerator.save_report | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | startup_reporter.py:69 | JsonReportGenerator._create... | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | startup_reporter.py:153 | MarkdownReportGenerator._cr... | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y%m%d\_%H%M%S` | unified_import_manager.py:494 | UnifiedImportManager.save_r... | `%Y-%m-%d %H:%M:...`, `%Y-%m-%d %H:%M... |
| `%Y\-%m\-%d` | generate_wip_report.py:200 | WIPReportGenerator._generat... | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d` | team_updates_documentation_analyzer.py:40 | DocumentationAnalyzer.find_... | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d` | team_updates_documentation_analyzer.py:57 | DocumentationAnalyzer.find_... | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d` | team_updates_sync.py:56 | generate_simple_report | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M` | team_updates_formatter.py:46 | HumanFormatter.format_header | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M` | team_updates_sync.py:49 | generate_simple_report | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | architecture_dashboard_html.py:45 | DashboardHTMLComponents._ge... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | report_generator.py:42 | ReportGenerator._generate_m... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | test_generator.py:99 | _build_test_header | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | auto_fix_test_violations.py:854 | TestViolationAnalyzer.gener... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | boundary_enforcer_core_types.py:54 | create_timestamp | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | generate_performance_report.py:23 | add_report_header | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | generate_report.py:16 | _format_header | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | generate_security_report.py:36 | _build_security_report_header | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | cleanup_generated_files.py:227 | main | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | clean_slate_executor.py:28 | CleanSlateExecutor.log | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | code_review_reporter.py:20 | CodeReviewReporter._add_rep... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | core.py:158 | create_compliance_results | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | comprehensive_import_scanner.py:102 | ComprehensiveScanReport.pri... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | create_enforcement_tools.py:349 | EnforcementEngine.run_all_c... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | report_generator.py:38 | ReportGenerator._add_report... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | startup_environment.py:37 | StartupEnvironment._print_h... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | startup_reporter.py:101 | MarkdownReportGenerator._bu... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | markdown_reporter.py:230 | MarkdownReporter._generate_... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | markdown_reporter.py:413 | MarkdownReporter._generate_... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | markdown_reporter.py:611 | MarkdownReporter._generate_... | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | team_updates_git_analyzer.py:37 | GitAnalyzer.get_commits | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | team_updates_git_analyzer.py:38 | GitAnalyzer.get_commits | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | team_updates_sync.py:150 | generate_simple_report | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d %H:%M:%S` | websocket_coherence_review.py:150 | _build_report_header | `%Y%m%d_%H%M%S`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d\_%H\-%M` | team_updates.py:68 | main | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d\_%H\-%M` | team_updates_sync.py:151 | generate_simple_report | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\-%m\-%d\_%H\-%M` | team_updates_sync.py:170 | main | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `%Y\|%m\|%d\|%H\|%M\|%S` | categorizer_enhanced.py:225 | EnhancedStringLiteralCatego... | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `\-\-pretty=format:%H\|%an\|%ae\|%ad\|%s` | team_updates_git_analyzer.py:42 | GitAnalyzer.get_commits | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `\-\-pretty=format:%h\|%s` | team_updates_documentation_analyzer.py:43 | DocumentationAnalyzer.find_... | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `\-\-pretty=format:%h\|%s` | team_updates_documentation_analyzer.py:60 | DocumentationAnalyzer.find_... | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |
| `2024\-01\-15T10:30:00Z` | categorizer_enhanced.py:590 | module | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |

### 🔴 Low (<0.5) (1 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `
Automated File Splitting Tool for Ne...` | split_large_files.py:2 | module | `%Y-%m-%d %H:%M:...`, `%Y%m%d_%H%M%S` |

### Usage Examples

- **scripts\force_cancel_workflow.py:17** - `get_workflow_runs`
- **scripts\force_cancel_workflow.py:34** - `force_cancel_workflow`
- **scripts\split_learnings.py:71** - `create_category_file`

---

## Subcategory: json {subcategory-json}

**Count**: 110 literals

### 🟢 High (≥0.8) (83 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `\[ \]` | reporter.py:76 | ComplianceReporter._print_v... | `[red]ACT not in...`, `[red]Docker no... |
| `\[ \]` | reporter_utils.py:47 | ReporterUtils.get_severity_... | `[red]ACT not in...`, `[red]Docker no... |
| `\["\\'\]type\["\\'\]\\s\*:\\s\*\["\\'...` | websocket_coherence_review.py:31 | find_backend_events | `[red]ACT not in...`, `[red]Docker no... |
| `\['\\"\]\(\[^'\\"\]\+\)\['\\"\]` | find_top_mocks.py:64 | analyze_mock_targets | `[red]ACT not in...`, `[red]Docker no... |
| `\[/cyan\]` | act_wrapper.py:90 | ACTWrapper._execute_act | `[red]ACT not in...`, `[red]Docker no... |
| `\[/red\]` | setup_act.py:51 | install_act | `[red]ACT not in...`, `[red]Docker no... |
| `\[/red\]` | setup_act.py:149 | run_validation | `[red]ACT not in...`, `[red]Docker no... |
| `\[/red\]` | verify_workflow_status.py:370 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[/red\]` | workflow_introspection.py:83 | WorkflowIntrospector._run_g... | `[red]ACT not in...`, `[red]Docker no... |
| `\[/red\]` | workflow_introspection.py:400 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[/yellow\]` | verify_workflow_status.py:143 | WorkflowStatusVerifier.wait... | `[red]ACT not in...`, `[red]Docker no... |
| `\[^0\-9\.\]` | env_checker.py:63 | normalize_version | `[red]ACT not in...`, `[red]Docker no... |
| `\[^a\-z0\-9\_\]` | split_learnings.py:53 | sanitize_filename | `[red]ACT not in...`, `[red]Docker no... |
| `\[^a\-z0\-9\_\]` | split_learnings_robust.py:34 | sanitize_filename | `[red]ACT not in...`, `[red]Docker no... |
| `\[a\-zA\-Z\_\]\\\.\\\.\[a\-zA\-Z\_\]` | comprehensive_import_scanner.py:173 | ComprehensiveImportScanner.... | `[red]ACT not in...`, `[red]Docker no... |
| `\[CRITICAL\]` | real_test_validator.py:301 | RealTestValidator.generate_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[cyan\]Installing ACT\.\.\.\[/cyan\]` | setup_act.py:39 | install_act | `[red]ACT not in...`, `[red]Docker no... |
| `\[cyan\]Validating workflows\.\.\.\[/...` | act_wrapper.py:106 | ACTWrapper.validate_workflows | `[red]ACT not in...`, `[red]Docker no... |
| `\[cyan\]Validating workflows\.\.\.\[/...` | setup_act.py:133 | run_validation | `[red]ACT not in...`, `[red]Docker no... |
| `\[DISABLED\]` | workflow_config_utils.py:38 | WorkflowConfigUtils._show_w... | `[red]ACT not in...`, `[red]Docker no... |
| `\[ENABLED\]` | workflow_config_utils.py:38 | WorkflowConfigUtils._show_w... | `[red]ACT not in...`, `[red]Docker no... |
| `\[ERR\]` | unified_import_manager.py:528 | UnifiedImportManager.print_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[EXISTS\]` | status_manager.py:95 | StatusManager._format_compo... | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAIL\]` | startup_environment.py:155 | DependencyChecker._display_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAIL\]` | startup_reporter.py:190 | StartupReporter._print_indi... | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAIL\]` | test_verify_workflow_status.py:178 | WorkflowStatusTester.genera... | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAIL\]` | validate_staging_config.py:425 | print_validation_results | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAILED/SKIPPED\]` | reset_clickhouse.py:252 | print_operation_summary | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAILED/SKIPPED\]` | reset_clickhouse_auto.py:180 | display_auto_summary | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAILED/SKIPPED\]` | reset_clickhouse_final.py:141 | display_final_summary | `[red]ACT not in...`, `[red]Docker no... |
| `\[FAILED\]` | test_async_postgres.py:185 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]Updated \.gitignore\[/green\]` | setup_act.py:115 | create_config_files | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]Valid\[/green\]` | workflow_validator.py:193 | WorkflowValidator._display_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[H\]` | reporter.py:76 | ComplianceReporter._print_v... | `[red]ACT not in...`, `[red]Docker no... |
| `\[H\]` | reporter_utils.py:46 | ReporterUtils.get_severity_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[INSTALLED\]` | status_manager.py:100 | StatusManager._format_insta... | `[red]ACT not in...`, `[red]Docker no... |
| `\[L\]` | reporter.py:76 | ComplianceReporter._print_v... | `[red]ACT not in...`, `[red]Docker no... |
| `\[L\]` | reporter_utils.py:46 | ReporterUtils.get_severity_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[LAUNCH\]` | dev_launcher_core.py:150 | DevLauncher.run | `[red]ACT not in...`, `[red]Docker no... |
| `\[M\]` | reporter.py:76 | ComplianceReporter._print_v... | `[red]ACT not in...`, `[red]Docker no... |
| `\[M\]` | reporter_utils.py:46 | ReporterUtils.get_severity_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[MAJOR\]` | real_test_validator.py:301 | RealTestValidator.generate_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[MINOR\]` | real_test_validator.py:301 | RealTestValidator.generate_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[MISSING\]` | test_backend.py:348 | _display_dependency_statuses | `[red]ACT not in...`, `[red]Docker no... |
| `\[MISSING\]` | test_frontend.py:452 | handle_dependency_check | `[red]ACT not in...`, `[red]Docker no... |
| `\[NO\]` | status_manager.py:90 | StatusManager._format_statu... | `[red]ACT not in...`, `[red]Docker no... |
| `\[NOT FOUND\]` | status_manager.py:95 | StatusManager._format_compo... | `[red]ACT not in...`, `[red]Docker no... |
| `\[NOT INSTALLED\]` | status_manager.py:100 | StatusManager._format_insta... | `[red]ACT not in...`, `[red]Docker no... |
| `\[o\]` | workflow_introspection.py:294 | OutputFormatter.display_run... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OFF\]` | manage_workflows.py:224 | _display_workflow_list | `[red]ACT not in...`, `[red]Docker no... |
| `\[OFF\]` | workflow_config_utils.py:29 | WorkflowConfigUtils._show_f... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | dev_launcher_config.py:93 | check_emoji_support | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | dev_launcher_core.py:123 | DevLauncher.cleanup | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | dev_launcher_core.py:136 | DevLauncher.check_dependencies | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | dev_launcher_service.py:133 | ServiceManager._finalize_ba... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | dev_launcher_service.py:239 | ServiceManager._finalize_fr... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | import_management.py:81 | ImportManagementSystem.chec... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | startup_environment.py:155 | DependencyChecker._display_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | startup_reporter.py:190 | StartupReporter._print_indi... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | test_backend.py:348 | _display_dependency_statuses | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | test_frontend.py:452 | handle_dependency_check | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | unified_import_manager.py:528 | UnifiedImportManager.print_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[OK\]` | workflow_introspection.py:294 | OutputFormatter.display_run... | `[red]ACT not in...`, `[red]Docker no... |
| `\[ON\]` | manage_workflows.py:224 | _display_workflow_list | `[red]ACT not in...`, `[red]Docker no... |
| `\[ON\]` | workflow_config_utils.py:29 | WorkflowConfigUtils._show_f... | `[red]ACT not in...`, `[red]Docker no... |
| `\[PASS\]` | test_verify_workflow_status.py:178 | WorkflowStatusTester.genera... | `[red]ACT not in...`, `[red]Docker no... |
| `\[PASS\]` | validate_staging_config.py:425 | print_validation_results | `[red]ACT not in...`, `[red]Docker no... |
| `\[PASSED\]` | test_async_postgres.py:185 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]Invalid\[/red\]` | workflow_validator.py:194 | WorkflowValidator._display_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[SKIPPED\]` | test_async_postgres.py:185 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[STOP\]` | dev_launcher_core.py:105 | DevLauncher._cleanup_handler | `[red]ACT not in...`, `[red]Docker no... |
| `\[SUCCESS\]` | reset_clickhouse.py:252 | print_operation_summary | `[red]ACT not in...`, `[red]Docker no... |
| `\[SUCCESS\]` | reset_clickhouse_auto.py:180 | display_auto_summary | `[red]ACT not in...`, `[red]Docker no... |
| `\[SUCCESS\]` | reset_clickhouse_final.py:141 | display_final_summary | `[red]ACT not in...`, `[red]Docker no... |
| `\[VIOLATION\]` | function_checker.py:93 | FunctionChecker._get_violat... | `[red]ACT not in...`, `[red]Docker no... |
| `\[WARN\]` | unified_import_manager.py:528 | UnifiedImportManager.print_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[X\]` | fix_comprehensive_imports.py:337 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[X\]` | fix_comprehensive_imports.py:346 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[X\]` | import_management.py:80 | ImportManagementSystem.chec... | `[red]ACT not in...`, `[red]Docker no... |
| `\[X\]` | workflow_introspection.py:294 | OutputFormatter.display_run... | `[red]ACT not in...`, `[red]Docker no... |
| `\[YES\]` | status_manager.py:90 | StatusManager._format_statu... | `[red]ACT not in...`, `[red]Docker no... |
| `\{owner\}/\{repo\}` | workflow_introspection.py:197 | WorkflowIntrospector.get_wo... | `[red]ACT not in...`, `[red]Docker no... |
| `\{\{\.Names\}\}` | reset_clickhouse_final.py:18 | _check_docker_container | `[red]ACT not in...`, `[red]Docker no... |

### 🟡 Medium (0.5-0.8) (27 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `\[bold\]Jobs and Steps\[/bold\]` | workflow_introspection.py:286 | OutputFormatter.display_run... | `[red]ACT not in...`, `[red]Docker no... |
| `\[cyan\]Installing Python dependencie...` | setup_act.py:122 | install_dependencies | `[red]ACT not in...`, `[red]Docker no... |
| `\[cyan\]Secrets storage already initi...` | local_secrets_manager.py:56 | LocalSecretsManager.initialize | `[red]ACT not in...`, `[red]Docker no... |
| `\[cyan\]Validating GitHub Actions wor...` | workflow_validator.py:40 | WorkflowValidator.validate_all | `[red]ACT not in...`, `[red]Docker no... |
| `\[DRY RUN MODE \- No files were actua...` | fix_netra_backend_imports.py:154 | ImportFixer.generate_report | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]All required secrets configu...` | workflow_validator.py:228 | SecretValidator.validate | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]Created \.act\.env template\...` | setup_act.py:92 | create_config_files | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]Created \.act\.secrets templ...` | setup_act.py:78 | create_config_files | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]Secrets storage initialized\...` | local_secrets_manager.py:54 | LocalSecretsManager.initialize | `[red]ACT not in...`, `[red]Docker no... |
| `\[green\]Workflow validation passed\[...` | setup_act.py:142 | run_validation | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]ACT not installed\. Install fr...` | act_wrapper.py:31 | ACTWrapper._validate_prereq... | `[red]Docker not...`, `[/cyan]` |
| `\[red\]Docker is not running\. Please...` | setup_act.py:170 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]Docker not running\. Please st...` | act_wrapper.py:34 | ACTWrapper._validate_prereq... | `[red]ACT not in...`, `[/cyan]` |
| `\[red\]ERROR: No workflow runs found\...` | verify_workflow_status.py:345 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]Failed to install ACT\[/red\]` | setup_act.py:180 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]Missing required secrets:\[/red\]` | workflow_validator.py:243 | SecretValidator._report_mis... | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]No encryption key found\[/red\]` | local_secrets_manager.py:110 | LocalSecretsManager._save_s... | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]Not initialized\. Run 'init' f...` | local_secrets_manager.py:122 | LocalSecretsManager._get_key | `[red]ACT not in...`, `[red]Docker no... |
| `\[red\]Passwords do not match\[/red\]` | local_secrets_manager.py:64 | LocalSecretsManager._genera... | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]ACT not found\. Installing\...` | setup_act.py:178 | main | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]No \.act\.secrets file foun...` | workflow_validator.py:218 | SecretValidator.validate | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]No command specified\. Use ...` | act_wrapper.py:243 | execute_command | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]No GitHub secrets found in ...` | local_secrets_manager.py:174 | LocalSecretsManager.import_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]No secrets stored\[/yellow\]` | local_secrets_manager.py:130 | LocalSecretsManager.list_se... | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]No secrets to export\[/yell...` | local_secrets_manager.py:146 | LocalSecretsManager.export_... | `[red]ACT not in...`, `[red]Docker no... |
| `\[yellow\]Some workflows have issues\...` | setup_act.py:145 | run_validation | `[red]ACT not in...`, `[red]Docker no... |
| `\{timestamp\}: \{level\} \- \{message\}` | demo_enhanced_categorizer.py:120 | categorize_specific_examples | `[red]ACT not in...`, `[red]Docker no... |

### Usage Examples

- **scripts\compliance\reporter.py:76** - `ComplianceReporter._print_violation_list`
- **scripts\compliance\reporter_utils.py:47** - `ReporterUtils.get_severity_marker`
- **scripts\websocket_coherence_review.py:31** - `find_backend_events`

---

## Subcategory: mime_type {subcategory-mime-type}

**Count**: 10 literals

### 🟢 High (≥0.8) (10 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| ` lines/function` | create_enforcement_tools.py:322 | EnforcementEngine.run_all_c... | `interface/type`, `audit/example` |
| `actions/cache` | workflow_validator.py:33 | WorkflowValidator._load_kno... | `interface/type`, `audit/example` |
| `actions/checkout` | workflow_validator.py:30 | WorkflowValidator._load_kno... | `interface/type`, `audit/example` |
| `agents/supervisor` | extract_function_violations.py:48 | FunctionViolationExtractor.... | `interface/type`, `audit/example` |
| `application/json` | demo_enhanced_categorizer.py:108 | categorize_specific_examples | `interface/type`, `audit/example` |
| `application/json` | generate_openapi_spec.py:152 | create_readme_headers | `interface/type`, `audit/example` |
| `application/json` | generate_openapi_spec.py:183 | upload_spec_to_readme | `interface/type`, `audit/example` |
| `audit/example` | function_checker.py:76 | FunctionChecker._is_example... | `interface/type`, ` lines/function` |
| `interface/type` | architecture_scanner.py:158 | ArchitectureScanner._extrac... | `audit/example`, ` lines/function` |
| `services/websocket` | extract_function_violations.py:53 | FunctionViolationExtractor.... | `interface/type`, `audit/example` |

### Usage Examples

- **scripts\create_enforcement_tools.py:322** - `EnforcementEngine.run_all_checks`
- **scripts\workflow_validator.py:33** - `WorkflowValidator._load_known_actions`
- **scripts\workflow_validator.py:30** - `WorkflowValidator._load_known_actions`

---

## Subcategory: regex {subcategory-regex}

**Count**: 1576 literals

### 🟡 Medium (0.5-0.8) (1027 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `

\*\*Decomposition Priority\*\*: ` | function_complexity_analyzer.py:272 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `

\[INTERRUPT\]` | dev_launcher_core.py:263 | DevLauncher._wait_for_proce... | `[red]Workflow '`, `[cyan]Running: ` |
| `
        self\.boundary\_monitor\.cle...` | enhance_dev_launcher_boundaries.py:153 | enhance_launcher_main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Compliance Score:\*\* ` | boundary_enforcer_report_generator.py:210 | PRCommentGenerator._build_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Confidence:\*\* ` | generate_security_report.py:125 | _format_vulnerability_list | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Date:\*\* ` | startup_reporter.py:101 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Description\*\*: ` | test_verify_workflow_status.py:180 | WorkflowStatusTester.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Description:\*\* ` | generate_security_report.py:126 | _format_vulnerability_list | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Exit Code\*\*: ` | test_verify_workflow_status.py:181 | WorkflowStatusTester.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Generated:\*\* ` | real_service_test_metrics.py:124 | RealServiceTestMetrics._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Timestamp:\*\* ` | cleanup_staging_environments.py:286 | StagingEnvironmentCleaner.p... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\.\.\. and ` | generate_security_report.py:135 | _get_overflow_text | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\.\.\. and ` | process_results.py:100 | TestResultProcessor._genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*Plus ` | team_updates_formatter.py:100 | HumanFormatter.format_features | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*Plus ` | team_updates_formatter.py:117 | HumanFormatter.format_bugs | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Commit\*\*: ` | team_updates_formatter.py:96 | HumanFormatter.format_features | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Failed\*\*: ` | status_section_renderers.py:201 | TestingSectionRenderer._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Failed\*\*: ` | test_verify_workflow_status.py:169 | WorkflowStatusTester.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Issues\*\*: ` | function_complexity_analyzer.py:271 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Passed\*\*: ` | status_section_renderers.py:200 | TestingSectionRenderer._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Passed\*\*: ` | test_verify_workflow_status.py:168 | WorkflowStatusTester.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*What\*\*: ` | team_updates_formatter.py:94 | HumanFormatter.format_features | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Who\*\*: ` | team_updates_formatter.py:95 | HumanFormatter.format_features | `[red]Workflow '`, `[cyan]Running: ` |
| `
/\*\*
` | agent_tracking_helper.py:234 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[BACKEND\]` | dev_launcher_monitoring.py:122 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[bold\]Artifacts URL:\[/bold\] ` | workflow_introspection.py:308 | OutputFormatter.display_out... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[bold\]Logs:\[/bold\]` | workflow_introspection.py:387 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[bold\]Workflow Outputs:\[/bold\]` | workflow_introspection.py:302 | OutputFormatter.display_out... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[BOUNDARY VIOLATIONS\]:` | boundary_enforcer_report_generator.py:132 | ConsoleReportPrinter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[COMMANDS\]:` | dev_launcher_monitoring.py:135 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[CONFIG\] Configuration:` | dev_launcher_monitoring.py:145 | print_configuration_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[COST CONTROL\]:` | workflow_config_utils.py:44 | WorkflowConfigUtils._show_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DIR\] ` | test_discovery_report.py:145 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Missing ` | verify_staging_tests.py:67 | verify_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FAIL\] ` | boundary_enforcer_cli_handler.py:163 | FailureHandler.check_critic... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FAIL\] Found ` | boundary_enforcer_cli_handler.py:174 | ViolationDisplayer.display_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FEATURES\]:` | workflow_config_utils.py:26 | WorkflowConfigUtils._show_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FRONTEND\]` | dev_launcher_monitoring.py:127 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[IMPORTANT\]:` | verify_staging_tests.py:169 | print_usage_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[OK\] All ` | verify_staging_tests.py:70 | verify_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PREREQUISITES\]:` | verify_staging_tests.py:164 | print_usage_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PREVIEW\]
` | team_updates_sync.py:176 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[REMEDIATION PLAN\]:` | boundary_enforcer_report_generator.py:148 | ConsoleReportPrinter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[START\]` | dev_launcher_service.py:42 | ServiceManager.start_backend | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[START\]` | dev_launcher_service.py:141 | ServiceManager.start_frontend | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[STATUS\] Coverage: ` | main.py:110 | _print_continuous_status | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] Applied ` | test_reviewer.py:299 | AutonomousTestReviewer._app... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SYSTEM METRICS\]:` | boundary_enforcer_report_generator.py:121 | ConsoleReportPrinter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[TEST HIERARCHY\]:` | workflow_config_utils.py:52 | WorkflowConfigUtils._show_t... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[TEST\] ` | test_verify_workflow_status_corrected.py:23 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[UNJUSTIFIED MOCKS\]` | reporter.py:207 | ComplianceReporter._report_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[WARN\] Found ` | validate_workflow_config.py:213 | _exit_with_status | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[WORKFLOWS\] Status` | manage_workflows.py:221 | _display_workflow_list | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[WORKFLOWS\]:` | workflow_config_utils.py:35 | WorkflowConfigUtils._show_w... | `[red]Workflow '`, `[cyan]Running: ` |
| `
Continue? \(yes/no\): ` | clean_slate_executor.py:39 | CleanSlateExecutor.confirm_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
Status: \[` | workflow_introspection.py:273 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m` | dev_launcher_processes.py:28 | LogStreamer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m` | install_dev_env.py:36 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m` | test_discovery_report.py:73 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m` | test_discovery_report.py:128 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m` | test_discovery_report.py:129 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m` | test_discovery_report.py:130 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[0m \- ` | test_discovery_report.py:95 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[1m` | install_dev_env.py:37 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `\[35m` | dev_launcher_core.py:216 | DevLauncher._start_frontend... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[35m` | dev_launcher_service.py:228 | ServiceManager._finalize_fr... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[36m` | dev_launcher_core.py:195 | DevLauncher._start_backend_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[36m` | dev_launcher_service.py:110 | ServiceManager._start_backe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | install_dev_env.py:35 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | test_discovery_report.py:73 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | test_discovery_report.py:95 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | test_discovery_report.py:108 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | test_discovery_report.py:128 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | test_discovery_report.py:129 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[91m` | test_discovery_report.py:130 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[92m` | install_dev_env.py:33 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `\[93m` | install_dev_env.py:34 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `\[95m` | install_dev_env.py:31 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `\[96m` | install_dev_env.py:32 | Colors | `[red]Workflow '`, `[cyan]Running: ` |
| `            project\_root=find\_proje...` | enhance_dev_launcher_boundaries.py:35 | enhance_launcher_config | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[DELETED\] ` | cleanup_generated_files.py:124 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] ` | test_discovery_report.py:148 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] ` | test_staging_startup.py:53 | StagingStartupTester.test_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] ` | test_staging_startup.py:91 | StagingStartupTester.test_d... | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] ` | test_staging_startup.py:121 | StagingStartupTester.test_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] ` | test_staging_startup.py:151 | StagingStartupTester.test_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] ` | test_staging_startup.py:188 | StagingStartupTester.test_h... | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[OK\] Dropped: ` | reset_clickhouse_final.py:51 | _drop_table_from_db | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[REMOVED DIR\] ` | cleanup_generated_files.py:139 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `    sys\.path\.insert\(0, str\(PROJEC...` | align_test_imports.py:183 | TestImportAligner.fix_sys_path | `[red]Workflow '`, `[cyan]Running: ` |
| `   \(similarity: ` | analyze_test_overlap.py:593 | TestOverlapAnalyzer._save_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `   \* Turbopack: ` | dev_launcher_monitoring.py:151 | print_configuration_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[ERROR\] ` | test_verify_workflow_status_corrected.py:55 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[ERROR\] Error: ` | test_verify_workflow_status.py:60 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[FAIL\] ` | dev_launcher_secrets.py:97 | EnhancedSecretLoader._fetch... | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[OK\] ` | dev_launcher_secrets.py:55 | EnhancedSecretLoader._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[OK\] ` | dev_launcher_secrets.py:148 | EnhancedSecretLoader._final... | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[OUTPUT\] ` | test_verify_workflow_status_corrected.py:52 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[OUTPUT\] Output: ` | test_verify_workflow_status.py:58 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `   \[STATUS\] ` | test_verify_workflow_status_corrected.py:57 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `   localStorage\.getItem\('jwt\_token'\)` | monitor_oauth_flow.py:193 | OAuthMonitor.run_full_diagn... | `[red]Workflow '`, `[cyan]Running: ` |
| `   💡 \*` | boundary_enforcer_report_generator.py:261 | PRCommentGenerator._build_v... | `[red]Workflow '`, `[cyan]Running: ` |
| `   💡 \*` | real_test_requirements_enforcer.py:528 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \(similarity: ` | analyze_test_overlap.py:608 | TestOverlapAnalyzer._save_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[DIR\] Processing ` | markdown_reporter.py:585 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[ERROR\] Scanning ` | test_failure_scanner.py:95 | _execute_pytest_and_parse_r... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[FAIL\] ` | code_review_smoke_tests.py:65 | CodeReviewSmokeTests._run_b... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[FAIL\] ` | smoke_tester.py:86 | SmokeTester._print_test_result | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[FAIL\] ` | test_failure_scanner.py:179 | _print_category_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[FAIL\] Error: ` | validate_frontend_tests.py:191 | FrontendTestValidator._test... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[MISSING\] ` | verify_staging_tests.py:63 | verify_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] ` | test_discovery_report.py:79 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] ` | verify_staging_tests.py:61 | verify_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Deleted ` | cleanup_generated_files.py:274 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Discovered ` | verify_staging_tests.py:129 | verify_test_discovery | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Found ` | scan_string_literals_enhanced.py:97 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Found ` | validate_frontend_tests.py:77 | FrontendTestValidator._disc... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Generated: ` | markdown_reporter.py:590 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Generated: ` | markdown_reporter.py:641 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] ` | code_review_smoke_tests.py:63 | CodeReviewSmokeTests._run_b... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] ` | code_review_smoke_tests.py:86 | CodeReviewSmokeTests._run_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] ` | smoke_tester.py:84 | SmokeTester._print_test_result | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] ` | smoke_tester.py:93 | SmokeTester._print_frontend... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] All ` | test_failure_scanner.py:182 | _print_category_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[red\]ERROR:\[/red\] ` | workflow_validator.py:173 | WorkflowValidator._report_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[SCAN\] ` | scan_string_literals_enhanced.py:93 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] ` | code_review_smoke_tests.py:88 | CodeReviewSmokeTests._run_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] ` | smoke_tester.py:95 | SmokeTester._print_frontend... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] Found ` | code_review_analysis.py:70 | CodeReviewAnalysis._analyze... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] Found ` | code_review_analysis.py:95 | CodeReviewAnalysis._check_u... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] Found ` | git_analyzer.py:59 | GitAnalyzer._report_hotspots | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] Found ` | git_analyzer.py:89 | GitAnalyzer._check_unstaged... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] Found ` | validate_frontend_tests.py:148 | FrontendTestValidator._chec... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[yellow\]WARN:\[/yellow\] ` | workflow_validator.py:177 | WorkflowValidator._report_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  High \(>=0\.8\): ` | categorizer_enhanced.py:560 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `  Low \(<0\.5\): ` | categorizer_enhanced.py:562 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `  Medium \(0\.5\-0\.8\): ` | categorizer_enhanced.py:561 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` \($` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(\+` | architecture_dashboard_tables.py:99 | DashboardTableRenderers._fo... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(age: ` | cleanup_generated_files.py:119 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(age: ` | cleanup_generated_files.py:124 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(age: ` | cleanup_generated_files.py:203 | print_scan_summary | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(attempt ` | dev_launcher_processes.py:181 | ProcessMonitor._attempt_res... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(by ` | team_updates_formatter.py:114 | HumanFormatter.format_bugs | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(confidence: ` | demo_enhanced_categorizer.py:133 | categorize_specific_examples | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(confidence: ` | categorizer_enhanced.py:599 | module | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(currently ` | test_fixer.py:357 | TestFixer.generate_fix_plan | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(end\-to\-end tests\)` | test_size_validator.py:374 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(exception\)` | test_staging_startup.py:258 | StagingStartupTester.run_al... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(excluding dependencies\)` | generate_test_audit.py:277 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(expected: ` | test_verify_workflow_status_corrected.py:46 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(failure ` | dev_launcher_processes.py:199 | ProcessMonitor._perform_res... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(from ` | dev_launcher_secrets.py:55 | EnhancedSecretLoader._print... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(ID: ` | force_cancel_workflow.py:84 | _print_run_info | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(ID: ` | force_cancel_workflow.py:94 | _display_stuck_runs_summary | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(ID: ` | verify_workflow_status.py:142 | WorkflowStatusVerifier.wait... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(integration tests\)` | test_limits_checker.py:201 | TestLimitsChecker._suggest_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(integration tests\)` | test_size_validator.py:373 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(JS/TS\)` | generate_test_audit.py:56 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(length: ` | environment_validator.py:127 | EnvironmentValidator._valid... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(line ` | boundary_enforcer_file_checks.py:103 | ASTAnalyzer.extract_ast_nodes | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(line ` | boundary_enforcer_file_checks.py:105 | ASTAnalyzer.extract_ast_nodes | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(line ` | check_function_lengths.py:62 | module | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(line ` | reporter.py:195 | ComplianceReporter._print_t... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(line ` | find_long_functions.py:53 | scan_directory | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(Line ` | fix_netra_backend_imports.py:194 | ImportFixer.generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(line ` | status_section_renderers.py:84 | ComponentDetailsRenderer._f... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(matched: ` | test_exclusion_check.py:42 | check_test_file_locations | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(must pass\)` | demo_feature_flag_system.py:157 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(Score: ` | business_value_test_index.py:724 | BusinessValueTestIndexer.pr... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(shared utilities\)` | test_limits_checker.py:202 | TestLimitsChecker._suggest_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(start: ` | decompose_functions.py:145 | generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(static config\)` | dev_launcher_secrets.py:148 | EnhancedSecretLoader._final... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(too large\)` | real_test_linter.py:172 | RealTestLinter._attempt_fixes | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(unit tests\)` | test_limits_checker.py:200 | TestLimitsChecker._suggest_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(unit tests\)` | test_size_validator.py:372 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(~` | demo_test_size_enforcement.py:103 | demo_test_refactor_helper | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(~` | test_refactor_helper.py:727 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* ================================` | metadata_header_generator.py:155 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* ================================` | metadata_header_generator.py:163 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Agent: ` | metadata_header_generator.py:157 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Change: ` | metadata_header_generator.py:160 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Context: ` | metadata_header_generator.py:158 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Entry ` | agent_tracking_helper.py:238 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Git: ` | metadata_header_generator.py:159 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Review: ` | metadata_header_generator.py:162 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Session: ` | metadata_header_generator.py:161 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Timestamp: ` | metadata_header_generator.py:156 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*\*` | real_test_requirements_enforcer.py:524 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*\*` | real_test_requirements_enforcer.py:550 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*\*` | real_test_validator.py:302 | RealTestValidator.generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*\*` | markdown_reporter.py:629 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*/` | metadata_header_generator.py:164 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*/
` | agent_tracking_helper.py:152 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \*/
` | agent_tracking_helper.py:240 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \[FAIL\]` | startup_reporter.py:112 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \[FAIL\]` | startup_reporter.py:182 | StartupReporter._print_summary | `[red]Workflow '`, `[cyan]Running: ` |
| ` \[OK\]` | startup_reporter.py:111 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \[OK\]` | startup_reporter.py:181 | StartupReporter._print_summary | `[red]Workflow '`, `[cyan]Running: ` |
| ` attempts\)` | dev_launcher_monitoring.py:43 | _handle_service_check_failure | `[red]Workflow '`, `[cyan]Running: ` |
| ` bytes\)` | cleanup_generated_files.py:120 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| ` bytes\)` | cleanup_generated_files.py:125 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| ` bytes\)` | verify_staging_tests.py:61 | verify_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| ` completed successfully\[/green\]` | verify_workflow_status.py:297 | OutputFormatter.display_suc... | `[red]Workflow '`, `[cyan]Running: ` |
| ` day\(s\)` | cleanup_generated_files.py:226 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` definitions\)` | validate_type_deduplication.py:268 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| ` definitions\)` | validate_type_deduplication.py:282 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| ` definitions\)` | validate_type_deduplication.py:294 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| ` deployment\.\.\.\[/cyan\]` | act_wrapper.py:154 | StagingDeployer.deploy | `[red]Workflow '`, `[cyan]Running: ` |
| ` documentation\]\(` | markdown_reporter.py:381 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` failed\)
Coverage: ` | validate_agent_tests.py:260 | AgentTestValidator.generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` failed\[/red\]` | verify_workflow_status.py:303 | OutputFormatter.display_fai... | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\)` | code_review_analysis.py:97 | CodeReviewAnalysis._check_u... | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\)` | real_test_requirements_enforcer.py:519 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\)` | reporter.py:246 | ComplianceReporter._print_c... | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\)` | test_violations_reporter.py:76 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\)` | fix_all_import_issues.py:290 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\)` | git_analyzer.py:91 | GitAnalyzer._check_unstaged... | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\):` | check_test_compliance.py:165 | print_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\):` | check_test_compliance.py:173 | print_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` files\):` | check_test_compliance.py:183 | print_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` fixes\)` | fix_embedded_setup_imports.py:214 | EmbeddedSetupImportFixer.ge... | `[red]Workflow '`, `[cyan]Running: ` |
| ` fixes\)` | fix_malformed_imports.py:256 | MalformedImportFixer.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| ` functions\)` | test_violations_reporter.py:95 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` helpers\)` | test_size_validator.py:385 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` import \(` | fix_all_import_syntax.py:55 | fix_import_syntax_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| ` import \(` | fix_all_import_syntax.py:63 | fix_import_syntax_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| ` import \(` | fix_simple_import_errors.py:44 | fix_simple_import_error | `[red]Workflow '`, `[cyan]Running: ` |
| ` import \*` | fix_imports.py:138 | ImportFixer.fix_file | `[red]Workflow '`, `[cyan]Running: ` |
| ` import \*
` | fix_all_test_issues.py:198 | split_large_test_file | `[red]Workflow '`, `[cyan]Running: ` |
| ` import \*

` | test_generator.py:114 | _build_test_header | `[red]Workflow '`, `[cyan]Running: ` |
| ` instances reset\)` | reset_clickhouse_auto.py:182 | display_auto_summary | `[red]Workflow '`, `[cyan]Running: ` |
| ` issues\)` | comprehensive_import_scanner.py:108 | ComprehensiveScanReport.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` issues\)` | comprehensive_import_scanner.py:109 | ComprehensiveScanReport.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` issues\)
` | generate_security_report.py:114 | _format_severity_group | `[red]Workflow '`, `[cyan]Running: ` |
| ` items\)` | test_violations_reporter.py:143 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` learnings\)` | split_learnings_robust.py:162 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` learnings\)\.\.\.` | split_learnings.py:131 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` learnings\)\.\.\.` | split_learnings_robust.py:151 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` line limit:\*\* ` | test_size_validator.py:462 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` line limit:\*\* ` | test_size_validator.py:463 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(\+` | test_violations_reporter.py:84 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(\+` | test_violations_reporter.py:124 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(limit: ` | test_limits_checker.py:193 | TestLimitsChecker._suggest_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(limit: ` | test_limits_checker.py:209 | TestLimitsChecker._suggest_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(limit: ` | test_size_validator.py:366 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(max: ` | core.py:123 | ViolationBuilder.function_v... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(max: ` | test_limits_checker.py:156 | TestLimitsChecker._check_te... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(max: ` | enforce_limits.py:50 | FileLineChecker.check_file | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines \(max: ` | function_complexity_linter.py:117 | FunctionComplexityLinter._c... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | analyze_coverage.py:34 | module | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | architecture_reporter.py:121 | ArchitectureReporter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | auto_fix_test_sizes.py:256 | TestFileSplitter.split_over... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | auto_fix_test_sizes.py:259 | TestFileSplitter.split_over... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | auto_fix_test_sizes.py:445 | TestFunctionOptimizer.optim... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | auto_fix_test_sizes.py:653 | TestSizeFixer.fix_all_viola... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | demo_test_size_enforcement.py:103 | demo_test_refactor_helper | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | reporter.py:48 | ComplianceReporter._report_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | reporter.py:88 | ComplianceReporter._report_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | test_fixer.py:357 | TestFixer.generate_fix_plan | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | test_refactor_helper.py:727 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | split_large_files.py:172 | TestFileSplitter.split_file | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | team_updates_formatter.py:164 | HumanFormatter.format_code_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)` | team_updates_formatter.py:170 | HumanFormatter.format_code_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\) manually` | auto_fix_test_violations.py:622 | FunctionRefactor.refactor_l... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\):` | decompose_functions.py:186 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\): ` | fix_all_test_issues.py:261 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` literals \(` | markdown_reporter.py:253 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` literals\)` | query_string_literals.py:187 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` literals\)` | markdown_reporter.py:436 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` literals\)` | markdown_reporter.py:472 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` more errors\*` | generate_report.py:121 | _format_errors | `[red]Workflow '`, `[cyan]Running: ` |
| ` more failures\*` | generate_report.py:98 | _format_failures | `[red]Workflow '`, `[cyan]Running: ` |
| ` more failures\*` | process_results.py:100 | TestResultProcessor._genera... | `[red]Workflow '`, `[cyan]Running: ` |
| ` more features\.\.\.\*` | team_updates_formatter.py:100 | HumanFormatter.format_features | `[red]Workflow '`, `[cyan]Running: ` |
| ` more fixes\.\.\.\*` | team_updates_formatter.py:117 | HumanFormatter.format_bugs | `[red]Workflow '`, `[cyan]Running: ` |
| ` more\)` | architecture_dashboard_tables.py:99 | DashboardTableRenderers._fo... | `[red]Workflow '`, `[cyan]Running: ` |
| ` pattern\(s\) corrected` | fix_embedded_setup_imports.py:163 | EmbeddedSetupImportFixer.pr... | `[red]Workflow '`, `[cyan]Running: ` |
| ` pattern\(s\) corrected` | fix_malformed_imports.py:205 | MalformedImportFixer.proces... | `[red]Workflow '`, `[cyan]Running: ` |
| ` process\(es\)\.` | cleanup_test_processes.py:126 | cleanup_test_processes | `[red]Workflow '`, `[cyan]Running: ` |
| ` seconds \(` | benchmark_optimization.py:352 | TestExecutionBenchmark._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` Severity \(` | generate_security_report.py:114 | _format_severity_group | `[red]Workflow '`, `[cyan]Running: ` |
| ` severity issues\*
` | generate_security_report.py:135 | _get_overflow_text | `[red]Workflow '`, `[cyan]Running: ` |
| ` table\(s\):` | reset_clickhouse.py:97 | _fetch_and_display_tables | `[red]Workflow '`, `[cyan]Running: ` |
| ` table\(s\):` | reset_clickhouse.py:132 | fetch_and_display_tables | `[red]Workflow '`, `[cyan]Running: ` |
| ` table\(s\):` | reset_clickhouse_auto.py:98 | _process_existing_tables | `[red]Workflow '`, `[cyan]Running: ` |
| ` table\(s\):` | reset_clickhouse_final.py:42 | _display_tables_info | `[red]Workflow '`, `[cyan]Running: ` |
| ` test\(s\) failed\!` | validate_jwt_consistency.py:209 | validate_jwt_secret_consist... | `[red]Workflow '`, `[cyan]Running: ` |
| ` test\(s\) failed\*\*` | process_results.py:46 | TestResultProcessor._genera... | `[red]Workflow '`, `[cyan]Running: ` |
| ` test\-related process\(es\):` | cleanup_test_processes.py:106 | cleanup_test_processes | `[red]Workflow '`, `[cyan]Running: ` |
| ` tests\[0m` | test_discovery_report.py:120 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| ` tests\)` | business_value_test_index.py:680 | BusinessValueTestIndexer._g... | `[red]Workflow '`, `[cyan]Running: ` |
| ` tests\)` | fix_test_batch.py:242 | BatchTestProcessor.process_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` tests\)\[0m \- ` | test_discovery_report.py:108 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| ` tests\) \- ` | test_discovery_report.py:110 | EnhancedTestDiscoveryReport... | `[red]Workflow '`, `[cyan]Running: ` |
| ` total \(` | validate_agent_tests.py:260 | AgentTestValidator.generate... | `[red]Workflow '`, `[cyan]Running: ` |
| ` uncommitted\)` | metadata_header_generator.py:56 | MetadataHeaderGenerator._ge... | `[red]Workflow '`, `[cyan]Running: ` |
| ` Violations \(` | project_test_validator.py:344 | ProjectTestValidator.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| ` VIOLATIONS \(` | enforce_limits.py:174 | EnforcementReporter.generat... | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations \(dry\_run=` | auto_fix_test_violations.py:796 | TestViolationAnalyzer.analy... | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations\)` | real_test_requirements_enforcer.py:550 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations\)` | real_test_validator.py:318 | RealTestValidator.generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations\)` | test_violations_reporter.py:117 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations\)` | decompose_functions.py:158 | generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations\):` | check_test_stubs.py:71 | CITestStubChecker._print_de... | `[red]Workflow '`, `[cyan]Running: ` |
| ` violations\):` | check_test_stubs.py:79 | CITestStubChecker._print_de... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \| $` | real_service_test_metrics.py:150 | RealServiceTestMetrics._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| ` → \*` | markdown_reporter.py:325 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` ❌ \(FAILING\)` | auto_fix_test_violations.py:883 | TestViolationAnalyzer.gener... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\(\.\*?\)"""` | ultra_thinking_analyzer.py:185 | UltraThinkingAnalyzer._extr... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*\[Jj\]ustification\.\*"""` | analyze_mocks.py:53 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*\[Jj\]ustification\.\*"""` | mock_justification_checker.py:39 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*for testing\.\*"""` | architecture_scanner_helpers.py:115 | ScannerHelpers.get_stub_pat... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*for testing\.\*"""` | create_enforcement_tools.py:258 | EnforcementEngine.detect_te... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*for testing\.\*"""` | remove_test_stubs.py:50 | TestStubDetector.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*mock implementation\.\*"""` | remove_test_stubs.py:48 | TestStubDetector.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*placeholder\.\*"""` | create_enforcement_tools.py:259 | EnforcementEngine.detect_te... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*test implementation\.\*"""` | architecture_scanner_helpers.py:114 | ScannerHelpers.get_stub_pat... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*test implementation\.\*"""` | create_enforcement_tools.py:257 | EnforcementEngine.detect_te... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""\.\*test implementation\.\*"""` | remove_test_stubs.py:49 | TestStubDetector.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*\[Jj\]ustification:` | find_top_mocks.py:82 | check_for_justification | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Justification:` | analyze_mocks.py:51 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*JUSTIFICATION:` | analyze_mocks.py:52 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Justification:` | mock_justification_checker.py:37 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*JUSTIFICATION:` | mock_justification_checker.py:38 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Mock justification:` | analyze_mocks.py:50 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Mock justification:` | find_top_mocks.py:83 | check_for_justification | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Mock justification:` | mock_justification_checker.py:36 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Mock needed` | analyze_mocks.py:56 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Necessary because` | analyze_mocks.py:55 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Necessary because` | find_top_mocks.py:85 | check_for_justification | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Required for` | find_top_mocks.py:84 | check_for_justification | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\\s\*Required for\.\*test` | analyze_mocks.py:54 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `$\{\{ env\.ACT` | fix_workflow_env_issues.py:72 | process_workflow_file | `[red]Workflow '`, `[cyan]Running: ` |
| `$\{\{ env\.ACT` | fix_workflow_env_issues.py:72 | process_workflow_file | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(` | analyze_coverage.py:34 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(` | architecture_reporter.py:78 | ArchitectureReporter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(` | process_results.py:55 | TestResultProcessor._genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(` | team_updates_formatter.py:138 | HumanFormatter.format_test_... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(` | team_updates_formatter.py:139 | HumanFormatter.format_test_... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(from ` | demo_enhanced_categorizer.py:95 | compare_categorization_appr... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(Target: ` | main.py:128 | _print_coverage_metrics | `[red]Workflow '`, `[cyan]Running: ` |
| `% covered\)` | analyze_coverage.py:26 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `%\) \- ` | create_enforcement_tools.py:69 | ProgressTracker.update | `[red]Workflow '`, `[cyan]Running: ` |
| `%\*\* \(` | generate_wip_report.py:225 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `%\[sd\]\|%\\\(\[^\)\]\+\\\)` | categorizer_enhanced.py:214 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `&\(?\!\(?:amp\|lt\|gt\|quot\|apos\);\)` | split_learnings.py:14 | fix_xml_content | `[red]Workflow '`, `[cyan]Running: ` |
| `' \(current: ` | business_value_test_index.py:680 | BusinessValueTestIndexer._g... | `[red]Workflow '`, `[cyan]Running: ` |
| `' removed\[/green\]` | local_secrets_manager.py:168 | LocalSecretsManager.remove_... | `[red]Workflow '`, `[cyan]Running: ` |
| `' saved\[/green\]` | local_secrets_manager.py:90 | LocalSecretsManager.add_secret | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\)
` | test_fixer.py:286 | TestFixer._split_function_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) \(` | decompose_functions.py:186 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) \- ` | architecture_metrics.py:163 | ArchitectureMetrics._get_fu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) \- ` | auto_decompose_functions.py:430 | FunctionDecomposer.generate... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) \- ` | test_violations_reporter.py:124 | TestViolationsReporter._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) \- ` | decompose_functions.py:180 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) \- ` | function_complexity_linter.py:215 | FunctionComplexityLinter._p... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) in ` | reporter.py:114 | ComplianceReporter._print_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) in ` | reporter.py:129 | ComplianceReporter._print_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) in ` | extract_function_violations.py:108 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\):` | auto_fix_test_sizes.py:570 | TestFunctionOptimizer._manu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\):` | auto_fix_test_sizes.py:572 | TestFunctionOptimizer._manu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\): ` | decompose_functions.py:160 | generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\)\` \- ` | function_complexity_analyzer.py:268 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\.\*?\)` | fix_all_import_issues.py:73 | ComprehensiveImportFixer._b... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(?:interface\|type\)\\s\+\(\\w\+\)` | architecture_scanner.py:153 | ArchitectureScanner._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(?:interface\|type\)\\s\+\(\\w\+\)` | boundary_enforcer_type_checks.py:91 | TypeBoundaryChecker._find_t... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(?:interface\|type\)\\s\+\(\\w\+\)` | create_enforcement_tools.py:228 | EnforcementEngine.find_dupl... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(?:test\|it\|describe\)\\s\*\\\(\\s\...` | business_value_test_index.py:287 | BusinessValueTestIndexer._s... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\[\\w/\\\\\\\.\]\+::\\S\+\)` | test_failure_scanner.py:145 | _extract_test_name_if_failed | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\) deletions?\\\(\-\\\)` | boundary_enforcer_system_checks.py:138 | SystemMetricsCalculator._ex... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\) insertions?\\\(\\\+\\\)` | boundary_enforcer_system_checks.py:136 | SystemMetricsCalculator._ex... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\)\\s\+` | status_collector.py:286 | TestResultsCollector._extra... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\)\\s\+passed\.\*?\(\\d\+\)\\s...` | team_updates_test_analyzer.py:107 | TestReportAnalyzer._parse_r... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\\\.\\d\+\(?:\\\.\\d\+\)?\)` | dependency_scanner.py:172 | check_system_dependency | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\\\.\\d\+\)` | dependency_services.py:24 | check_postgresql_installation | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\\\.\\d\+\\\.\\d\+\)` | dependency_services.py:77 | check_redis_installation | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\d\+\\\.\\d\+\\\.\\d\+\)` | env_checker.py:152 | get_git_version | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\w\+\)\\s\*=\\s\*Mock\\\(\\\)` | find_top_mocks.py:71 | analyze_mock_targets | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\\w\+\)\\s\*\\\(` | test_refactor_helper.py:222 | TestRefactorHelper._extract... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(^\|\\n\)\(async def ` | add_test_markers.py:103 | TestMarkerAdder.add_markers... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(^\|\\n\)\(class ` | add_test_markers.py:66 | TestMarkerAdder.add_markers... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(const\|function\) ` | auto_split_files.py:109 | FileSplitter._analyze_types... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(from\\s\+\[\\w\\\.\]\+\\s\+import\\...` | fix_import_indents.py:18 | fix_import_indents | `[red]Workflow '`, `[cyan]Running: ` |
| `\(from\\s\+\[\\w\\\.\]\+\\s\+import\\...` | fix_remaining_imports.py:13 | fix_import_indents | `[red]Workflow '`, `[cyan]Running: ` |
| `\(import datetime\\n\)` | enhanced_fix_datetime_deprecation.py:61 | _add_separate_utc_import | `[red]Workflow '`, `[cyan]Running: ` |
| `\(import datetime\\n\)` | fix_datetime_deprecation.py:40 | fix_datetime_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `\(import\[^;\]\+;\[\\s\]\*\)\+` | fix_frontend_tests.py:24 | _add_test_providers_import | `[red]Workflow '`, `[cyan]Running: ` |
| `\(self\):
` | test_fixer.py:280 | TestFixer._split_function_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(self\):
        """Test ` | test_generator.py:216 | _generate_method_tests | `[red]Workflow '`, `[cyan]Running: ` |
| `\(self, ` | fix_e2e_tests_comprehensive.py:252 | E2ETestFixer._add_basic_tests | `[red]Workflow '`, `[cyan]Running: ` |
| `\) \- ` | team_updates_sync.py:121 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\) \- ` | test_verify_workflow_status_corrected.py:46 | WorkflowStatusTester.run_test | `[red]Workflow '`, `[cyan]Running: ` |
| `\) available` | env_checker.py:237 | get_service_ports_status | `[red]Workflow '`, `[cyan]Running: ` |
| `\)\*\*` | markdown_reporter.py:381 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\)\.\.\.` | auto_fix_test_violations.py:796 | TestViolationAnalyzer.analy... | `[red]Workflow '`, `[cyan]Running: ` |
| `\)\.\.\.` | generate_openapi_spec.py:182 | upload_spec_to_readme | `[red]Workflow '`, `[cyan]Running: ` |
| `\)\.\.\.` | validate_network_constants.py:165 | validate_network_environmen... | `[red]Workflow '`, `[cyan]Running: ` |
| `\):
        """Test ` | fix_e2e_tests_comprehensive.py:252 | E2ETestFixer._add_basic_tests | `[red]Workflow '`, `[cyan]Running: ` |
| `\): ` | check_function_lengths.py:62 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\): ` | demo_feature_flag_system.py:46 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `\): ` | demo_feature_flag_system.py:47 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `\): ` | demo_feature_flag_system.py:48 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `\): ` | demo_feature_flag_system.py:49 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `\): ` | find_long_functions.py:53 | scan_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `\)\\S\+\\s\+import\\s\+\.\*` | validate_type_deduplication.py:198 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\)\\S\+\\s\+import\\s\+\.\*` | validate_type_deduplication.py:199 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.\.\. and ` | generate_report.py:98 | _format_failures | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.\.\. and ` | generate_report.py:121 | _format_errors | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.bin` | agent_tracking_helper.py:58 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.csv` | agent_tracking_helper.py:62 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.csv` | cleanup_generated_files.py:23 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.dll` | agent_tracking_helper.py:57 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.doc` | agent_tracking_helper.py:60 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.docx` | agent_tracking_helper.py:60 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.dylib` | agent_tracking_helper.py:57 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.egg\-info` | core.py:88 | ComplianceConfig._get_skip_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.exe` | agent_tracking_helper.py:58 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.gif` | agent_tracking_helper.py:59 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.gz` | agent_tracking_helper.py:61 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.html` | cleanup_generated_files.py:23 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.html` | cleanup_generated_files.py:65 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.ico` | agent_tracking_helper.py:59 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.jpeg` | agent_tracking_helper.py:59 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.jpg` | agent_tracking_helper.py:59 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.min\.css` | agent_tracking_helper.py:55 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.min\.js` | agent_tracking_helper.py:55 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.pdf` | agent_tracking_helper.py:60 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.png` | agent_tracking_helper.py:59 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.pyc` | agent_tracking_helper.py:56 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.pyd` | agent_tracking_helper.py:56 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.pyo` | agent_tracking_helper.py:56 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.so` | agent_tracking_helper.py:57 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.spec\.ts` | check_test_compliance.py:96 | scan_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.spec\.ts` | generate_test_audit.py:52 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.spec\.tsx` | check_test_compliance.py:96 | scan_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.spec\.tsx` | generate_test_audit.py:52 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.svg` | agent_tracking_helper.py:59 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.tar` | agent_tracking_helper.py:61 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.js` | generate_test_audit.py:52 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.jsx` | generate_test_audit.py:52 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.ts` | check_test_compliance.py:96 | scan_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.ts` | generate_test_audit.py:52 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.ts\*` | test_reviewer.py:141 | AutonomousTestReviewer._ass... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.tsx` | check_test_compliance.py:96 | scan_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.test\.tsx` | generate_test_audit.py:52 | count_test_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.ts` | deduplicate_types.py:180 | TypeDeduplicator.find_types... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.ts` | enforce_limits.py:273 | collect_target_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.ts` | websocket_coherence_review.py:61 | find_frontend_handlers | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.ts,\*\.tsx` | ai_detector.py:84 | AIDetector._check_typescrip... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.ts,\*\.tsx` | ai_detector.py:140 | AIDetector._check_console_logs | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.tsx` | test_reviewer.py:188 | AutonomousTestReviewer._ide... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.tsx` | enforce_limits.py:273 | collect_target_files | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.xml'` | spec_checker.py:100 | SpecChecker._find_matching_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.y\*ml` | act_wrapper.py:108 | ACTWrapper.validate_workflows | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\.zip` | agent_tracking_helper.py:61 | AgentTrackingHelper | `[red]Workflow '`, `[cyan]Running: ` |
| `\*/\}
` | agent_tracking_helper.py:163 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\_backup\.\*` | clean_slate_executor.py:84 | CleanSlateExecutor.phase1_a... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\_deprecated\.\*` | clean_slate_executor.py:84 | CleanSlateExecutor.phase1_a... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\_old\.\*` | clean_slate_executor.py:84 | CleanSlateExecutor.phase1_a... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*\_temp\.\*` | clean_slate_executor.py:84 | CleanSlateExecutor.phase1_a... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Generated on ` | markdown_reporter.py:230 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Generated on ` | markdown_reporter.py:413 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Generated on ` | markdown_reporter.py:611 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Generated: ` | team_updates_sync.py:150 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\+\.1f` | benchmark_optimization.py:357 | TestExecutionBenchmark._pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\+00:00` | cleanup_staging_environments.py:113 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\+00:00` | cleanup_staging_environments.py:123 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\+00:00` | cleanup_workflow_runs.py:68 | get_workflow_runs | `[red]Workflow '`, `[cyan]Running: ` |
| `\+00:00` | cleanup_workflow_runs.py:107 | get_artifacts | `[red]Workflow '`, `[cyan]Running: ` |
| `\+00:00` | staging_error_monitor.py:212 | StagingErrorMonitor._parse_... | `[red]Workflow '`, `[cyan]Running: ` |
| `, error\["error\_message"\]\[:500\], ` | generate_report.py:131 | _format_single_error | `[red]Workflow '`, `[cyan]Running: ` |
| `, failure\["error\_message"\]\[:500\], ` | generate_report.py:108 | _format_single_failure | `[red]Workflow '`, `[cyan]Running: ` |
| `, SPEC/testing\.xml\)` | test_limits_checker.py:156 | TestLimitsChecker._check_te... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | boundary_enforcer_report_generator.py:234 | PRCommentGenerator._build_b... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | project_test_validator.py:358 | ProjectTestValidator.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | real_test_validator.py:318 | RealTestValidator.generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | function_complexity_analyzer.py:236 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | generate_test_audit.py:165 | generate_audit_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | import_management.py:233 | ImportManagementSystem.gene... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | status_renderer.py:109 | StatusReportRenderer._extra... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | status_section_renderers.py:84 | ComponentDetailsRenderer._f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | markdown_reporter.py:325 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | team_updates_formatter.py:57 | HumanFormatter.format_criti... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | team_updates_formatter.py:188 | HumanFormatter.format_docum... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | team_updates_formatter.py:193 | HumanFormatter.format_docum... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | websocket_coherence_review.py:332 | _build_structure_issues_sec... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*` | websocket_coherence_review.py:345 | _build_payload_issues_section | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Commits\*\*: ` | team_updates_sync.py:64 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Critical:\*\* ` | real_test_requirements_enforcer.py:492 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Documentation\*\*: ` | team_updates_sync.py:103 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Duration:\*\* ` | startup_reporter.py:114 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Errors\*\*: ` | status_section_renderers.py:197 | TestingSectionRenderer._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Failed:\*\* ` | real_service_test_metrics.py:138 | RealServiceTestMetrics._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Failed:\*\* ` | startup_reporter.py:112 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Fixed\*\*: ` | team_updates_formatter.py:114 | HumanFormatter.format_bugs | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Hits:\*\* ` | real_service_test_metrics.py:173 | RealServiceTestMetrics._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Major:\*\* ` | real_test_requirements_enforcer.py:493 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Memory:\*\* ` | startup_reporter.py:136 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Minor:\*\* ` | real_test_requirements_enforcer.py:494 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Misses:\*\* ` | real_service_test_metrics.py:174 | RealServiceTestMetrics._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Passed:\*\* ` | real_service_test_metrics.py:137 | RealServiceTestMetrics._bui... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Passed:\*\* ` | startup_reporter.py:111 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Platform:\*\* ` | startup_reporter.py:134 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Python:\*\* ` | startup_reporter.py:133 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Related\*\*: ` | analyze_test_overlap.py:532 | TestOverlapAnalyzer._save_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Similar\*\*: ` | analyze_test_overlap.py:531 | TestOverlapAnalyzer._save_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Sub\-Agents\*\*: ` | status_section_renderers.py:111 | ComponentDetailsRenderer._f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \[` | markdown_reporter.py:99 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \[CRITICAL\]: ` | project_test_validator.py:332 | ProjectTestValidator.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \[MAJOR\]: ` | project_test_validator.py:333 | ProjectTestValidator.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \[MINOR\]: ` | project_test_validator.py:334 | ProjectTestValidator.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\-filter=name:staging\-\*` | cleanup_staging_environments.py:48 | StagingEnvironmentCleaner.g... | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\-filter=resource\.labels\.service\...` | cleanup_staging_environments.py:144 | StagingEnvironmentCleaner.g... | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\-format=value\(name\)` | cleanup_staging_environments.py:249 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\-format=value\(timestamp,textPaylo...` | monitor_oauth_flow.py:110 | OAuthMonitor.monitor_logs | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\-testPathPattern=\_\_tests\_\_/\(c...` | fix_common_test_issues.py:58 | run_simple_unit_tests | `[red]Workflow '`, `[cyan]Running: ` |
| `\. \*\*` | boundary_enforcer_report_generator.py:259 | PRCommentGenerator._build_v... | `[red]Workflow '`, `[cyan]Running: ` |
| `\. \*\*` | decompose_functions.py:144 | generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\. \[` | test_failure_scanner.py:242 | _print_priority_failures | `[red]Workflow '`, `[cyan]Running: ` |
| `\. \[\`` | team_updates_sync.py:121 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*$` | fix_comprehensive_imports.py:104 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*?\(?=\\ndef\|\\Z\)` | audit_permissions.py:27 | analyze_route_file | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*\\\.apps\\\.googleusercontent\\\.com` | environment_validator_core.py:67 | EnvironmentValidatorCore._d... | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*\\\.git\.\*` | auth_constants_migration.py:90 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*\\\.pyc$` | auth_constants_migration.py:88 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*\\\.pyo$` | auth_constants_migration.py:89 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*\\\.venv\.\*` | auth_constants_migration.py:93 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*\_\_pycache\_\_\.\*` | auth_constants_migration.py:87 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*auth\_constants\\\.py$` | auth_constants_migration.py:94 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*node\_modules\.\*` | auth_constants_migration.py:91 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*test\.\*constants\.\*` | auth_constants_migration.py:95 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\*venv\.\*` | auth_constants_migration.py:92 | AuthConstantsMigrator.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\.\.\.' \(confidence: ` | demo_enhanced_categorizer.py:83 | compare_categorization_appr... | `[red]Workflow '`, `[cyan]Running: ` |
| `\.env\.test\*` | generate_test_audit.py:89 | analyze_test_structure | `[red]Workflow '`, `[cyan]Running: ` |
| `\.md\)` | markdown_reporter.py:628 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\.md\) \- ` | markdown_reporter.py:534 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\.md\*` | team_updates_sync.py:151 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\.md\]\(` | markdown_reporter.py:628 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*` | metadata_header_generator.py:153 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*
` | agent_tracking_helper.py:146 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*/\*\.test\.\[jt\]s?\(x\)` | test_frontend.py:179 | _build_test_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*/\*\.test\.\[jt\]s?\(x\)` | test_frontend.py:181 | _build_test_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*/\*\.ts` | core.py:56 | ComplianceConfig.get_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*/\*\.ts` | core.py:68 | ComplianceConfig.get_typesc... | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*/\*\.tsx` | core.py:56 | ComplianceConfig.get_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `/\*\*/\*\.tsx` | core.py:68 | ComplianceConfig.get_typesc... | `[red]Workflow '`, `[cyan]Running: ` |
| `/1k tokens\)` | demo_real_llm_testing.py:118 | demo_real_llm_configuration | `[red]Workflow '`, `[cyan]Running: ` |
| `/day, $` | validate_workflow_config.py:201 | _print_config_details | `[red]Workflow '`, `[cyan]Running: ` |
| `:\*\* ` | boundary_enforcer_report_generator.py:234 | PRCommentGenerator._build_b... | `[red]Workflow '`, `[cyan]Running: ` |
| `:\*\* ` | import_management.py:233 | ImportManagementSystem.gene... | `[red]Workflow '`, `[cyan]Running: ` |
| `://\*\*\*@` | test_config_loading.py:122 | _mask_database_url | `[red]Workflow '`, `[cyan]Running: ` |
| `:\\s\*ConnectionManager\\b` | fix_e2e_connection_manager_imports.py:82 | fix_connection_manager_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `<category>\(\[^<\]\+\)</category>` | split_learnings_robust.py:20 | extract_learnings | `[red]Workflow '`, `[cyan]Running: ` |
| `<learning id="\(\[^"\]\+\)">\(\.\*?\)...` | split_learnings_robust.py:15 | extract_learnings | `[red]Workflow '`, `[cyan]Running: ` |
| `=\\s\*\["'\]\[^"'\]\+\["'\]` | code_review_analysis.py:192 | CodeReviewAnalysis._check_h... | `[red]Workflow '`, `[cyan]Running: ` |
| `=\\s\*\["'\]\[^"'\]\+\["'\]` | security_checker.py:38 | SecurityChecker._get_secret... | `[red]Workflow '`, `[cyan]Running: ` |
| `=\\s\*ConnectionManager\\b` | fix_e2e_connection_manager_imports.py:92 | fix_connection_manager_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `? \(y/n\): ` | force_cancel_workflow.py:105 | _handle_single_workflow_choice | `[red]Workflow '`, `[cyan]Running: ` |
| `? \(y/N\): ` | split_large_files.py:241 | _get_user_confirmations | `[red]Workflow '`, `[cyan]Running: ` |
| `? \(yes/no\): ` | reset_clickhouse.py:143 | confirm_table_deletion | `[red]Workflow '`, `[cyan]Running: ` |
| `?host=/cloudsql/` | validate_staging_config.py:95 | parse_database_url | `[red]Workflow '`, `[cyan]Running: ` |
| `?host=/cloudsql/` | validate_staging_config.py:102 | split_cloudsql_url_parts | `[red]Workflow '`, `[cyan]Running: ` |
| `?host=/cloudsql/` | validate_staging_config_partial.py:84 | _parse_cloud_sql_url | `[red]Workflow '`, `[cyan]Running: ` |
| `?host=/cloudsql/` | validate_staging_config_partial.py:144 | check_database_connection | `[red]Workflow '`, `[cyan]Running: ` |
| `?per\_page=100&page=` | cleanup_workflow_runs.py:60 | get_workflow_runs | `[red]Workflow '`, `[cyan]Running: ` |
| `?per\_page=100&page=` | cleanup_workflow_runs.py:99 | get_artifacts | `[red]Workflow '`, `[cyan]Running: ` |
| `@\\w\+\\\.\(get\|post\|put\|delete\|p...` | status_integration_analyzer.py:109 | IntegrationAnalyzer._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| `@experimental\_test\(\)` | demo_feature_flag_system.py:173 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@feature\_flag\('feature\_name'\)` | demo_feature_flag_system.py:170 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@flaky\_test\(max\_retries=3\)` | demo_feature_flag_system.py:178 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@integration\_only\(\)` | demo_feature_flag_system.py:175 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@mock\\\.patch\\\(` | analyze_mocks.py:37 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `@mock\\\.patch\\\(` | mock_justification_checker.py:24 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `@mock\_justified\\\(` | analyze_mocks.py:49 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `@mock\_justified\\\(` | mock_justification_checker.py:35 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `@patch\\\(` | analyze_mocks.py:36 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `@patch\\\(` | find_top_mocks.py:23 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `@patch\\\(` | mock_justification_checker.py:23 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `@performance\_test\(threshold\_ms=100\)` | demo_feature_flag_system.py:174 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@pytest\\\.fixture` | fix_e2e_tests_comprehensive.py:92 | E2ETestFixer.analyze_test_file | `[red]Workflow '`, `[cyan]Running: ` |
| `@pytest\\\.fixture\.\*?\\ndef\\s\+\(\...` | test_refactor_helper.py:230 | TestRefactorHelper._extract... | `[red]Workflow '`, `[cyan]Running: ` |
| `@pytest\\\.fixture\[^\\n\]\*\\ndef \(...` | fix_e2e_tests_comprehensive.py:234 | E2ETestFixer._add_basic_tests | `[red]Workflow '`, `[cyan]Running: ` |
| `@pytest\\\.mark\\\.skip` | categorize_tests.py:122 | TestCategorizer._check_e2e_... | `[red]Workflow '`, `[cyan]Running: ` |
| `@requires\_env\('VAR1', 'VAR2'\)` | demo_feature_flag_system.py:177 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@requires\_feature\('f1', 'f2'\)` | demo_feature_flag_system.py:172 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@router\\\.\(get\|post\|put\|delete\|...` | audit_permissions.py:20 | analyze_route_file | `[red]Workflow '`, `[cyan]Running: ` |
| `@tdd\_test\('feature\_name'\)` | demo_feature_flag_system.py:171 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `@unit\_only\(\)` | demo_feature_flag_system.py:176 | demonstrate_decorator_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `\[\!\] ` | install_dev_env.py:65 | DevEnvironmentInstaller.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[\+\] ` | install_dev_env.py:61 | DevEnvironmentInstaller.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[^:\]\*:\)` | add_test_markers.py:66 | TestMarkerAdder.add_markers... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[A\-Za\-z0\-9\+/\]\+=\*` | environment_validator_core.py:82 | EnvironmentValidatorCore._d... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[a\-zA\-Z\_\]\\\.\\\.` | comprehensive_import_scanner.py:217 | ComprehensiveImportScanner.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[bold\]Logs URL:\[/bold\] ` | workflow_introspection.py:311 | OutputFormatter.display_out... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[CRITICAL\] Issues: ` | code_review_reporter.py:195 | CodeReviewReporter._display... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[CRITICAL\] Issues: ` | cli.py:95 | DisplayFormatter._display_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[cyan\]Running: ` | act_wrapper.py:90 | ACTWrapper._execute_act | `[red]Workflow '`, `*.y*ml` |
| `\[DISABLED\] Workflow: ` | manage_workflows.py:116 | WorkflowManager.disable_wor... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[DONE\] Updated ` | fix_warp_runners.py:41 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ENABLED\] Workflow: ` | manage_workflows.py:101 | WorkflowManager.enable_work... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] ` | fix_import_syntax_errors.py:132 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Found ` | validate_service_independence.py:79 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Processing ` | fix_netra_domain.py:40 | fix_domain_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] ` | test_staging_startup.py:254 | StagingStartupTester.run_al... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] ` | test_staging_startup.py:258 | StagingStartupTester.run_al... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] ` | validate_staging_config.py:74 | print_secret_status | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] ` | validate_staging_config.py:336 | check_environment_variables | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] Fail` | startup_reporter.py:125 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAILED\] ` | verify_startup_fix.py:94 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FIXED\] ` | fix_import_syntax_errors.py:129 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FIXED\] ` | fix_netra_domain.py:33 | fix_domain_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]Exported ` | local_secrets_manager.py:150 | LocalSecretsManager.export_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]Imported ` | local_secrets_manager.py:201 | LocalSecretsManager._import... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]Secret '` | local_secrets_manager.py:90 | LocalSecretsManager.add_secret | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]Secret '` | local_secrets_manager.py:168 | LocalSecretsManager.remove_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]SUCCESS: Workflow ` | verify_workflow_status.py:297 | OutputFormatter.display_suc... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]✓\[/green\] ` | act_wrapper.py:118 | ACTWrapper._validate_single... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[green\]✓\[/green\] ` | workflow_validator.py:179 | WorkflowValidator._report_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[JSON\]   ` | scan_string_literals_enhanced.py:220 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[JSON\] Format: ` | scan_string_literals_enhanced.py:215 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] ` | dev_launcher_processes.py:196 | ProcessMonitor._perform_res... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] ` | validate_staging_config.py:70 | print_secret_status | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] ` | validate_staging_config.py:334 | check_environment_variables | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Generated: ` | markdown_reporter.py:577 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Pass` | startup_reporter.py:125 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Updated: ` | fix_warp_runners.py:30 | update_runners | `[red]Workflow '`, `[cyan]Running: ` |
| `\[PASS\] ` | test_staging_startup.py:251 | StagingStartupTester.run_al... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]ERROR: ` | verify_workflow_status.py:370 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]Error: ` | workflow_introspection.py:400 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]FAILED: Workflow ` | verify_workflow_status.py:303 | OutputFormatter.display_fai... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]Run ` | workflow_introspection.py:391 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]Unsupported platform: ` | setup_act.py:51 | install_act | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]Validation failed: ` | setup_act.py:149 | run_validation | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]Workflow '` | act_wrapper.py:73 | ACTWrapper.run_workflow | `[cyan]Running: `, `*.y*ml` |
| `\[red\]✗\[/red\] ` | act_wrapper.py:120 | ACTWrapper._validate_single... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]✗\[/red\] ` | workflow_validator.py:171 | WorkflowValidator._report_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[STATS\] Created ` | markdown_reporter.py:599 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Fixed ` | fix_embedded_setup_imports.py:222 | EmbeddedSetupImportFixer.ge... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Fixed ` | fix_malformed_imports.py:264 | MalformedImportFixer.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[WARN\] ` | validate_staging_config.py:72 | print_secret_status | `[red]Workflow '`, `[cyan]Running: ` |
| `\[WARN\] ` | validate_staging_config.py:332 | check_environment_variables | `[red]Workflow '`, `[cyan]Running: ` |
| `\[X\] ` | test_size_validator.py:442 | TestSizeValidator._generate... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[x\] ` | install_dev_env.py:69 | DevEnvironmentInstaller.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[yellow\]Secret '` | local_secrets_manager.py:163 | LocalSecretsManager.remove_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[yellow\]⚠\[/yellow\] ` | workflow_validator.py:175 | WorkflowValidator._report_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.\(py\|json\|xml\|yaml\|yml\|env\)$` | scan_string_literals.py:61 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.\(py\|json\|xml\|yaml\|yml\|env\|...` | categorizer_enhanced.py:84 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.\\\.\[a\-zA\-Z\_\]` | comprehensive_import_scanner.py:217 | ComprehensiveImportScanner.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.\\s\+\(import\|as\|$\)` | comprehensive_import_scanner.py:187 | ComprehensiveImportScanner.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.agents\\\.\[^\.\]\+\\\.schemas` | check_schema_imports.py:81 | SchemaImportAnalyzer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.handlers\\\.\[^\.\]\+\\\.schemas` | check_schema_imports.py:83 | SchemaImportAnalyzer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.return\_value\\s\*=` | project_test_validator.py:275 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.return\_value\\s\*=` | real_test_validator.py:236 | RealTestValidator._check_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.routes\\\.\[^\.\]\+\\\.schemas` | check_schema_imports.py:80 | SchemaImportAnalyzer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.services\\\.\[^\.\]\+\\\.schemas` | check_schema_imports.py:82 | SchemaImportAnalyzer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.side\_effect\\s\*=` | project_test_validator.py:275 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.strip\\\(\\\)\\\.split\\\(\\\)` | architecture_scanner_helpers.py:143 | ScannerHelpers.get_quality_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.tests\\\.\[^\.\]\+\\\.schemas` | check_schema_imports.py:85 | SchemaImportAnalyzer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\\.utils\\\.\[^\.\]\+\\\.schemas` | check_schema_imports.py:84 | SchemaImportAnalyzer | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1from netra\_backend\.app\.` | fix_netra_backend_imports.py:46 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1from netra\_backend\.tests\.` | fix_netra_backend_imports.py:47 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1import netra\_backend\.app\.` | fix_netra_backend_imports.py:50 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1import netra\_backend\.app\\2` | fix_netra_backend_imports.py:58 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1import netra\_backend\.tests\.` | fix_netra_backend_imports.py:51 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1import netra\_backend\.tests\\2` | fix_netra_backend_imports.py:59 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\^\|\\$\|\\\[\|\\\]\|\\\(\|\\\)\|\\\...` | categorizer_enhanced.py:217 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\b\(\\w\+\)\\b` | fix_e2e_tests_comprehensive.py:150 | E2ETestFixer._find_missing_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bConnectionManager\\\(\\\)` | fix_e2e_connection_manager_imports.py:86 | fix_connection_manager_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bis\\s\+False\\b` | fix_boolean_comparisons.py:19 | fix_boolean_comparisons | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bis\\s\+None\\b` | fix_boolean_comparisons.py:20 | fix_boolean_comparisons | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bis\\s\+not\\s\+False\\b` | fix_boolean_comparisons.py:24 | fix_boolean_comparisons | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bis\\s\+not\\s\+None\\b` | fix_boolean_comparisons.py:25 | fix_boolean_comparisons | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bis\\s\+not\\s\+True\\b` | fix_boolean_comparisons.py:23 | fix_boolean_comparisons | `[red]Workflow '`, `[cyan]Running: ` |
| `\\bis\\s\+True\\b` | fix_boolean_comparisons.py:18 | fix_boolean_comparisons | `[red]Workflow '`, `[cyan]Running: ` |
| `\\d\+` | generate_fix.py:268 | AIFixGenerator._parse_fix_r... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\n\\n\\n\+` | aggressive_syntax_fix.py:168 | aggressive_fix | `[red]Workflow '`, `[cyan]Running: ` |
| `\\n\\n\\n\+` | cleanup_duplicate_tests.py:168 | TestModuleImportCleaner.rem... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\n\\n\\n\+` | fix_e2e_imports.py:207 | E2EImportFixer.cleanup_content | `[red]Workflow '`, `[cyan]Running: ` |
| `\\n\\n\\n\+` | fix_frontend_tests.py:106 | _cleanup_and_write_file | `[red]Workflow '`, `[cyan]Running: ` |
| `\]
Conclusion: ` | workflow_introspection.py:274 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\] \(` | workflow_introspection.py:290 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\] \[` | clean_slate_executor.py:29 | CleanSlateExecutor.log | `[red]Workflow '`, `[cyan]Running: ` |
| `\] PID ` | cleanup_test_processes.py:108 | cleanup_test_processes | `[red]Workflow '`, `[cyan]Running: ` |
| `\] PID ` | cleanup_test_processes.py:166 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\] Processing: ` | comprehensive_test_fixer.py:306 | BatchProcessor.process_all_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\]\(\#` | markdown_reporter.py:99 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\#\\s` | categorizer_enhanced.py:202 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(?:export\\s\+\)?\(?:const\|functio...` | auto_split_files.py:91 | FileSplitter._analyze_types... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\[a\-zA\-Z0\-9\\\-\_\.\\\[,\\\]\]\...` | dependency_scanner.py:81 | extract_package_info | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)\(\.\*\)BaseExecutionEngine` | fix_comprehensive_imports.py:145 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)\(\.\*\)DataSubAgentClickHo...` | fix_comprehensive_imports.py:69 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)\(\.\*\)SupplyResearcherAgent` | fix_comprehensive_imports.py:216 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)from app\\\.` | fix_netra_backend_imports.py:46 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)from tests\\\.` | fix_netra_backend_imports.py:47 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)import app\(\\s\|$\)` | fix_netra_backend_imports.py:58 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)import app\\\.` | fix_netra_backend_imports.py:50 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)import tests\(\\s\|$\)` | fix_netra_backend_imports.py:59 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)import tests\\\.` | fix_netra_backend_imports.py:51 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(app\|frontend\|scripts\|tests\|SPE...` | scan_string_literals.py:62 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(app\|frontend\|scripts\|tests\|SPE...` | categorizer_enhanced.py:88 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(auth\|main\|frontend\)\_service$` | scan_string_literals.py:67 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(auth\|main\|frontend\)\_service$` | categorizer_enhanced.py:100 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(before\|after\)\_` | categorizer_enhanced.py:146 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(created\|updated\|deleted\|archive...` | categorizer_enhanced.py:175 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(DEBUG\|INFO\|WARN\|ERROR\|FATAL\):` | categorizer_enhanced.py:182 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(debug\|verbose\|quiet\|strict\)$` | categorizer_enhanced.py:65 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(development\|staging\|production\|...` | scan_string_literals.py:86 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(enabled\|disabled\|true\|false\)$` | scan_string_literals.py:91 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(enabled\|disabled\|true\|false\|ye...` | categorizer_enhanced.py:172 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(enable\|disable\|allow\|deny\)\_` | categorizer_enhanced.py:63 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(Error\|Failed\|Exception\|Invalid\)` | categorizer_enhanced.py:189 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(error\|success\|failure\|timeout\)\_` | scan_string_literals.py:82 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(error\|success\|failure\|timeout\)\_` | categorizer_enhanced.py:157 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(feat\|feature\)\[:\\\(\\\)\]?\\s\*` | team_updates_git_analyzer.py:105 | GitAnalyzer._extract_featur... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(feat\|fix\|docs\|chore\|refactor\)...` | team_updates_documentation_analyzer.py:183 | DocumentationAnalyzer._simp... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(fix\|bug\)\[:\\\(\\\)\]?\\s\*` | team_updates_git_analyzer.py:118 | GitAnalyzer._extract_bug_de... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(healthy\|degraded\|offline\|online\)$` | scan_string_literals.py:90 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(healthy\|degraded\|offline\|online...` | categorizer_enhanced.py:169 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(id\|name\|email\|password\|token\)$` | categorizer_enhanced.py:122 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(max\|min\|default\|timeout\|retry\)\_` | scan_string_literals.py:55 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(max\|min\|default\|timeout\|retry\...` | categorizer_enhanced.py:58 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(NETRA\|APP\|DB\|REDIS\|LOG\|ENV\)\_` | scan_string_literals.py:85 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(NETRA\|APP\|DB\|REDIS\|LOG\|ENV\)\_` | categorizer_enhanced.py:54 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(on\|emit\|handle\)\_` | scan_string_literals.py:76 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(on\|emit\|handle\)\_` | categorizer_enhanced.py:137 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(pending\|active\|completed\|failed...` | scan_string_literals.py:89 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(pending\|active\|completed\|failed...` | categorizer_enhanced.py:168 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(redis\|postgres\|clickhouse\|jwt\)\_` | categorizer_enhanced.py:60 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(request\|response\|error\|success\)\_` | categorizer_enhanced.py:154 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(SELECT\|INSERT\|UPDATE\|DELETE\|FR...` | scan_string_literals.py:73 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(SELECT\|INSERT\|UPDATE\|DELETE\|FR...` | categorizer_enhanced.py:125 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(started\|stopped\|paused\|resumed\)$` | categorizer_enhanced.py:176 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(Success\|Completed\|Created\|Updat...` | categorizer_enhanced.py:193 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(threads\|messages\|users\|agents\|...` | scan_string_literals.py:71 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(threads\|messages\|users\|agents\|...` | categorizer_enhanced.py:117 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(thread\|message\|user\|agent\)\_` | categorizer_enhanced.py:143 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(user\|thread\|message\|agent\)\_` | categorizer_enhanced.py:105 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^/\(auth\|users\|threads\|messages\|a...` | categorizer_enhanced.py:77 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^/api/` | scan_string_literals.py:59 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^/api/` | categorizer_enhanced.py:76 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^/api/v\\d\+` | categorizer_enhanced.py:75 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^/ws\|^/websocket` | scan_string_literals.py:60 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^/ws\|^/websocket` | categorizer_enhanced.py:80 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^58` | validate_staging_config.py:384 | print_validator_header | `[red]Workflow '`, `[cyan]Running: ` |
| `^60` | validate_staging_config.py:29 | print_section | `[red]Workflow '`, `[cyan]Running: ` |
| `^60` | validate_staging_config_partial.py:29 | print_section | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[a\-z\]\+/\[a\-z\]\+$` | categorizer_enhanced.py:399 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[A\-Z\]\[A\-Z\_\]\+\[A\-Z\]$` | categorizer_enhanced.py:53 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[A\-Z\]\[a\-zA\-Z\]\*\[A\-Z\]\[a\-z...` | categorizer_enhanced.py:108 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[A\-Z\_\]\+$` | scan_string_literals.py:53 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[a\-z\_\]\+$` | categorizer_enhanced.py:111 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[a\-z\_\]\+/$` | categorizer_enhanced.py:89 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[a\-z\_\]\+s$` | categorizer_enhanced.py:118 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\[a\-zA\-Z0\-9\-\_\]\+/\[a\-zA\-Z0\-...` | workflow_validator.py:142 | WorkflowValidator._is_valid... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\\*\\\*\|^\_\_` | categorizer_enhanced.py:207 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\\./` | categorizer_enhanced.py:85 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\\[\.\*\\\]$` | categorizer_enhanced.py:221 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\d\+\\\.\\d\+\\\.\\d\+` | categorizer_enhanced.py:392 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(?:const\|let\|var\)\\s\+\(\\w...` | check_test_compliance.py:32 | check_function_lengths | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(?:export\\s\+\)?\(?:async\\s\...` | check_test_compliance.py:31 | check_function_lengths | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(?:export\\s\+\)?interface\\s\...` | type_checker.py:90 | TypeChecker._find_typescrip... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(?:export\\s\+\)?type\\s\+\(\\...` | type_checker.py:91 | TypeChecker._find_typescrip... | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(?:it\|test\|describe\)\\s\*\\...` | check_test_compliance.py:34 | check_function_lengths | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(\\w\+\)\\s\*:\\s\*\(?:async\\...` | check_test_compliance.py:33 | check_function_lengths | `[red]Workflow '`, `[cyan]Running: ` |
| `^\\s\*\(async\\s\+\)?def\\s\+\\w\+` | auto_fix_test_violations.py:264 | TestFileAnalyzer._check_fun... | `[red]Workflow '`, `[cyan]Running: ` |
| `^class\\s\+\(\\w\+\)` | boundary_enforcer_type_checks.py:68 | TypeBoundaryChecker._find_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `^class\\s\+\(\\w\+\)` | create_enforcement_tools.py:222 | EnforcementEngine.find_dupl... | `[red]Workflow '`, `[cyan]Running: ` |
| `^class\\s\+\(\\w\+\)` | validate_type_deduplication.py:100 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^class\\s\+\(\\w\+\)\\s\*\[\\\(:\]` | type_checker.py:59 | TypeChecker._find_python_cl... | `[red]Workflow '`, `[cyan]Running: ` |
| `^def ` | ai_detector.py:50 | AIDetector._check_pattern_d... | `[red]Workflow '`, `[cyan]Running: ` |
| `^def \.\*\):$` | ai_detector.py:93 | AIDetector._check_missing_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `^def test\_module\_import\\\(\\\):` | cleanup_duplicate_tests.py:114 | TestModuleImportCleaner.rem... | `[red]Workflow '`, `[cyan]Running: ` |
| `^enum\\s\+\(\\w\+\)` | validate_type_deduplication.py:148 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^export\\s\+enum\\s\+\(\\w\+\)` | validate_type_deduplication.py:147 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^export\\s\+interface\\s\+\(\\w\+\)` | validate_type_deduplication.py:143 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^export\\s\+type\\s\+\(\\w\+\)` | validate_type_deduplication.py:145 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from \\\.` | fix_e2e_imports.py:86 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from \\\.\\\.` | fix_e2e_imports.py:85 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from app\\\.` | e2e_import_fixer_comprehensive.py:77 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from e2e\\\.` | e2e_import_fixer_comprehensive.py:89 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from helpers\\\.` | fix_e2e_test_imports.py:75 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from integration\\\.` | e2e_import_fixer_comprehensive.py:93 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from test\_framework\\\.` | e2e_import_fixer_comprehensive.py:97 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from tests\\\.` | e2e_import_fixer_comprehensive.py:81 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from unified\\\.` | e2e_import_fixer_comprehensive.py:85 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^ftp://` | categorizer_enhanced.py:93 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^https?://` | scan_string_literals.py:63 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `^https?://` | categorizer_enhanced.py:92 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^import app\\\.` | e2e_import_fixer_comprehensive.py:78 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import e2e\\\.` | e2e_import_fixer_comprehensive.py:90 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import integration\\\.` | e2e_import_fixer_comprehensive.py:94 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import schemas$` | comprehensive_e2e_import_fixer.py:66 | ComprehensiveE2EImportFixer... | `[red]Workflow '`, `[cyan]Running: ` |
| `^import schemas\\b` | fix_e2e_imports.py:44 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import test\_framework\\\.` | e2e_import_fixer_comprehensive.py:98 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import tests\\\.` | e2e_import_fixer_comprehensive.py:82 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import unified\\\.` | e2e_import_fixer_comprehensive.py:86 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^import ws\_manager\\b` | fix_e2e_imports.py:48 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^interface\\s\+\(\\w\+\)` | auto_split_files.py:89 | FileSplitter._analyze_types... | `[red]Workflow '`, `[cyan]Running: ` |
| `^interface\\s\+\(\\w\+\)` | validate_type_deduplication.py:144 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^type\\s\+\(\\w\+\)` | auto_split_files.py:90 | FileSplitter._analyze_types... | `[red]Workflow '`, `[cyan]Running: ` |
| `^type\\s\+\(\\w\+\)` | validate_type_deduplication.py:146 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^~>=<` | dependency_scanner.py:144 | validate_node_dependency | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(agent\|manager\|executor\|service\)$` | scan_string_literals.py:66 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(agent\|manager\|executor\|service...` | categorizer_enhanced.py:99 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(at\|by\|id\|name\|type\|status\)$` | scan_string_literals.py:72 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(at\|by\|id\|name\|type\|status\|c...` | categorizer_enhanced.py:121 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(core\|utilities\|helpers\|fixture...` | prevent_numbered_files.py:106 | suggest_better_name | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(count\|total\|rate\|duration\|lat...` | scan_string_literals.py:81 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(count\|total\|rate\|duration\|lat...` | categorizer_enhanced.py:153 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(cpu\|memory\|disk\|network\)\_` | categorizer_enhanced.py:162 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(enabled\|disabled\|allowed\|denie...` | categorizer_enhanced.py:64 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(errors\|successes\|failures\|time...` | categorizer_enhanced.py:158 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(handler\|listener\)$` | categorizer_enhanced.py:138 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(init\|cleanup\|shutdown\)$` | categorizer_enhanced.py:147 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(name\|type\|status\|state\)$` | categorizer_enhanced.py:104 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(seconds\|milliseconds\|microsecon...` | categorizer_enhanced.py:161 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(url\|uri\|host\|port\|key\|token\...` | scan_string_literals.py:54 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\(url\|uri\|host\|port\|key\|token\...` | categorizer_enhanced.py:57 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\\d\+\\\.py$` | prevent_numbered_files.py:26 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\\d\+\\\.py$` | prevent_numbered_files.py:101 | suggest_better_name | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\\d\+\\\.py$` | prevent_numbered_files.py:102 | suggest_better_name | `[red]Workflow '`, `[cyan]Running: ` |
| `\_\\d\+\_\\d\+\\\.py$` | prevent_numbered_files.py:27 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_backup\\\.py$` | prevent_numbered_files.py:39 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_backup\\\.xml$` | update_spec_timestamps.py:17 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_batch\_\\d\+\\\.py$` | prevent_numbered_files.py:35 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_batch\_\\d\+\\\.py$` | prevent_numbered_files.py:110 | suggest_better_name | `[red]Workflow '`, `[cyan]Running: ` |
| `\_config$` | scan_string_literals.py:56 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\_config$` | categorizer_enhanced.py:59 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_core\_\\d\+\\\.py$` | prevent_numbered_files.py:29 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_deprecated\\\.xml$` | update_spec_timestamps.py:18 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_enhanced\\\.py$` | prevent_numbered_files.py:37 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_fixed\\\.py$` | prevent_numbered_files.py:38 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_fixtures\_\\d\+\\\.py$` | prevent_numbered_files.py:32 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_helpers\_\\d\+\\\.py$` | prevent_numbered_files.py:31 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_id$` | scan_string_literals.py:68 | StringLiteralCategorizer | `[red]Workflow '`, `[cyan]Running: ` |
| `\_id$` | categorizer_enhanced.py:103 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `\_legacy\\\.xml$` | update_spec_timestamps.py:19 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_managers\_\\d\+\\\.py$` | prevent_numbered_files.py:34 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_new\\\.py$` | prevent_numbered_files.py:41 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_old\\\.py$` | prevent_numbered_files.py:40 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_old\\\.xml$` | update_spec_timestamps.py:16 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_services\_\\d\+\\\.py$` | prevent_numbered_files.py:33 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_temp\\\.py$` | prevent_numbered_files.py:42 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_tmp\\\.py$` | prevent_numbered_files.py:43 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_utilities\_\\d\+\\\.py$` | prevent_numbered_files.py:30 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\_v\\d\+\\\.py$` | prevent_numbered_files.py:50 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\`
\*\*Line:\*\* ` | generate_security_report.py:124 | _format_vulnerability_list | `[red]Workflow '`, `[cyan]Running: ` |
| `\` \(` | websocket_coherence_review.py:275 | _format_event_list | `[red]Workflow '`, `[cyan]Running: ` |
| `\` \(similarity: ` | analyze_test_overlap.py:578 | TestOverlapAnalyzer._save_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\` category\.\*` | markdown_reporter.py:539 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\`\]\(\./\.\./` | team_updates_sync.py:121 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `A\+ \(Simulated\)` | benchmark_optimization.py:224 | TestExecutionBenchmark._sim... | `[red]Workflow '`, `[cyan]Running: ` |
| `actual\.\*clickhouse` | categorize_tests.py:64 | TestCategorizer._get_clickh... | `[red]Workflow '`, `[cyan]Running: ` |
| `actual\.\*llm` | categorize_tests.py:49 | TestCategorizer._get_llm_pa... | `[red]Workflow '`, `[cyan]Running: ` |
| `actual\.\*postgres` | categorize_tests.py:54 | TestCategorizer._get_databa... | `[red]Workflow '`, `[cyan]Running: ` |
| `actual\.\*redis` | categorize_tests.py:59 | TestCategorizer._get_redis_... | `[red]Workflow '`, `[cyan]Running: ` |
| `AgentStarted\(` | websocket_coherence_review.py:119 | check_payload_completeness | `[red]Workflow '`, `[cyan]Running: ` |
| `api/v\\d\+` | prevent_numbered_files.py:49 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `assert \\\\1` | test_generator.py:251 | _get_modernization_replacem... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\(\)` | find_top_mocks.py:21 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\(\)` | mock_justification_checker.py:119 | MockJustificationChecker._c... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\(\)` | real_test_requirements_enforcer.py:355 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(` | categorize_tests.py:68 | TestCategorizer._get_mock_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(` | project_test_validator.py:273 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(\\\)` | analyze_mocks.py:43 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(\\\)` | find_top_mocks.py:21 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(\\\)` | mock_justification_checker.py:27 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(\\\)` | real_test_validator.py:235 | RealTestValidator._check_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `AsyncMock\\\(\\\)` | test_fixer.py:317 | TestFixer.reduce_mocking_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `asyncpg\\\.connect` | categorize_tests.py:53 | TestCategorizer._get_databa... | `[red]Workflow '`, `[cyan]Running: ` |
| `Backend \(FastAPI\)` | environment_validator_ports.py:44 | PortValidator._define_requi... | `[red]Workflow '`, `[cyan]Running: ` |
| `C:\\Users\\antho\\miniconda3\\Lib\\si...` | generate_frontend_types.py:16 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `C:\\Users\\antho\\OneDrive\\Desktop\\...` | split_learnings.py:120 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `C:\\Users\\antho\\OneDrive\\Desktop\\...` | split_learnings_robust.py:129 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `class \(Test\\w\+\)\[^:\]\*:` | add_test_markers.py:156 | TestMarkerAdder.process_file | `[red]Workflow '`, `[cyan]Running: ` |
| `class \\\\g<0>:` | test_generator.py:248 | _get_modernization_replacem... | `[red]Workflow '`, `[cyan]Running: ` |
| `class\\s\+\(\\w\+\)\\s\*\[\\\(:\]` | fix_test_batch.py:138 | TestFixer._find_similar_names | `[red]Workflow '`, `[cyan]Running: ` |
| `class\\s\+\\w\*Mock\\w\*:` | real_test_requirements_enforcer.py:53 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `class\\s\+Mock\\w\*:` | real_test_requirements_enforcer.py:52 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `ConnectionManager\\\(\\\)` | fix_import_issues.py:106 | fix_connection_manager_specs | `[red]Workflow '`, `[cyan]Running: ` |
| `const\\s\+Mock\\w\*\\s\*=` | real_test_requirements_enforcer.py:61 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `const\\s\+mock\\w\*\\s\*=` | real_test_requirements_enforcer.py:62 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `create\_autospec\\\(` | analyze_mocks.py:45 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `create\_autospec\\\(` | find_top_mocks.py:25 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `create\_autospec\\\(` | mock_justification_checker.py:29 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `datetime\.now\(UTC\)` | enhanced_fix_datetime_deprecation.py:73 | _replace_datetime_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `datetime\.now\(UTC\)` | fix_datetime_deprecation.py:48 | fix_datetime_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `datetime\.utcnow\(\)` | enhanced_fix_datetime_deprecation.py:73 | _replace_datetime_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `datetime\.utcnow\(\)` | fix_datetime_deprecation.py:27 | fix_datetime_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `datetime\.utcnow\(\)` | fix_datetime_deprecation.py:48 | fix_datetime_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `datetime\\\.utcnow` | enhanced_fix_datetime_deprecation.py:34 | _fix_utc_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `def\\s\+` | audit_permissions.py:27 | analyze_route_file | `[red]Workflow '`, `[cyan]Running: ` |
| `def\\s\+\(\\w\+\)` | auto_fix_test_violations.py:278 | TestFileAnalyzer._check_fun... | `[red]Workflow '`, `[cyan]Running: ` |
| `def\\s\+\(\\w\+\)\\s\*\\\(` | fix_test_batch.py:137 | TestFixer._find_similar_names | `[red]Workflow '`, `[cyan]Running: ` |
| `def\\s\+\\w\*\_mock\\w\*` | real_test_requirements_enforcer.py:60 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `def\\s\+mock\_\\w\+` | real_test_requirements_enforcer.py:59 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `describe\(` | real_test_requirements_enforcer.py:156 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `Dict\[` | fix_missing_functions.py:68 | add_missing_functions | `[red]Workflow '`, `[cyan]Running: ` |
| `dirty \(` | metadata_header_generator.py:56 | MetadataHeaderGenerator._ge... | `[red]Workflow '`, `[cyan]Running: ` |
| `Dockerfile\*` | validate_service_independence.py:152 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `expect\(` | real_test_requirements_enforcer.py:156 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `fake\_\.\*=` | categorize_tests.py:69 | TestCategorizer._get_mock_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `from app\\\.` | align_test_imports.py:199 | TestImportAligner.fix_modul... | `[red]Workflow '`, `[cyan]Running: ` |
| `from app\\\.` | fix_netra_backend_imports.py:110 | ImportFixer._determine_fix_... | `[red]Workflow '`, `[cyan]Running: ` |
| `from tests\\\.` | fix_netra_backend_imports.py:112 | ImportFixer._determine_fix_... | `[red]Workflow '`, `[cyan]Running: ` |
| `from tests\\\.config` | fix_e2e_test_imports.py:55 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `from tests\\\.fixtures` | align_test_imports.py:203 | TestImportAligner.fix_modul... | `[red]Workflow '`, `[cyan]Running: ` |
| `from tests\\\.helpers` | align_test_imports.py:202 | TestImportAligner.fix_modul... | `[red]Workflow '`, `[cyan]Running: ` |
| `from tests\\\.unified\\\.` | fix_e2e_imports.py:72 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `from unified\\\.` | fix_e2e_imports.py:81 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `from\\s\+\(?\!` | validate_type_deduplication.py:199 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `from\\s\+app\\\.\(?\!` | validate_type_deduplication.py:198 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `Frontend \(Next\.js\)` | environment_validator_ports.py:38 | PortValidator._define_requi... | `[red]Workflow '`, `[cyan]Running: ` |
| `GOCSPX\-\.\*` | environment_validator_core.py:72 | EnvironmentValidatorCore._d... | `[red]Workflow '`, `[cyan]Running: ` |
| `if\.\*and\.\*and\.\*and` | architecture_scanner_helpers.py:144 | ScannerHelpers.get_quality_... | `[red]Workflow '`, `[cyan]Running: ` |
| `import \(` | fix_test_syntax_errors.py:163 | fix_invalid_syntax | `[red]Workflow '`, `[cyan]Running: ` |
| `import \(
    ` | fix_import_indents.py:36 | fix_import | `[red]Workflow '`, `[cyan]Running: ` |
| `import \(
    ` | fix_remaining_imports.py:28 | fix_import | `[red]Workflow '`, `[cyan]Running: ` |
| `import \(\.\+\)$` | fix_schema_imports.py:212 | SchemaImportFixer.update_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `import \\\*` | architecture_scanner_helpers.py:132 | ScannerHelpers.get_debt_pat... | `[red]Workflow '`, `[cyan]Running: ` |
| `import app\\\.` | align_test_imports.py:200 | TestImportAligner.fix_modul... | `[red]Workflow '`, `[cyan]Running: ` |
| `import pytest\\n` | test_generator.py:247 | _get_modernization_replacem... | `[red]Workflow '`, `[cyan]Running: ` |
| `import tests\\\.config` | fix_e2e_test_imports.py:87 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `import unified\\\.` | fix_e2e_imports.py:82 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `import unittest\\\\n` | test_generator.py:247 | _get_modernization_replacem... | `[red]Workflow '`, `[cyan]Running: ` |
| `it\(` | real_test_requirements_enforcer.py:156 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `jest\.config\.\*` | generate_test_audit.py:89 | analyze_test_structure | `[red]Workflow '`, `[cyan]Running: ` |
| `jest\.fn\(\)` | real_test_requirements_enforcer.py:391 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `jest\.mock\(` | real_test_requirements_enforcer.py:392 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `jest\\\.fn\\\(\\\)` | real_test_requirements_enforcer.py:69 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `jest\\\.mock\\\(` | real_test_requirements_enforcer.py:70 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `lambda\.\*lambda` | architecture_scanner_helpers.py:145 | ScannerHelpers.get_quality_... | `[red]Workflow '`, `[cyan]Running: ` |
| `LLMManager\(\)` | test_fixer.py:315 | TestFixer.reduce_mocking_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `Local \(Fast\)` | deploy_to_gcp.py:647 | GCPDeployer.deploy_all | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\(\)` | find_top_mocks.py:20 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\(\)` | mock_justification_checker.py:119 | MockJustificationChecker._c... | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\(\)` | real_test_requirements_enforcer.py:355 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\\\(` | categorize_tests.py:68 | TestCategorizer._get_mock_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\\\(` | project_test_validator.py:273 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\\\(\\\)` | analyze_mocks.py:42 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\\\(\\\)` | find_top_mocks.py:20 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\\\(\\\)` | mock_justification_checker.py:26 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `MagicMock\\\(\\\)` | real_test_validator.py:235 | RealTestValidator._check_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\(\)` | find_top_mocks.py:19 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\(\)` | find_top_mocks.py:69 | analyze_mock_targets | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\(\)` | mock_justification_checker.py:119 | MockJustificationChecker._c... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\(\)` | real_test_requirements_enforcer.py:355 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\(\)` | test_fixer.py:43 | TestFixer.fix_mock_componen... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\\\(` | categorize_tests.py:68 | TestCategorizer._get_mock_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\\\(` | project_test_validator.py:273 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\\\(\\\)` | analyze_mocks.py:41 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\\\(\\\)` | find_top_mocks.py:19 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\\\(\\\)` | mock_justification_checker.py:25 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `Mock\\\(\\\)` | real_test_validator.py:235 | RealTestValidator._check_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `mock\\w\*Context\\s\*=` | real_test_requirements_enforcer.py:73 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `mock\_\.\*=` | categorize_tests.py:69 | TestCategorizer._get_mock_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `mock\_\\w\+\\s\*=` | project_test_validator.py:274 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `mock\_\\w\+\\s\*=` | real_test_validator.py:236 | RealTestValidator._check_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `MockComponent\\s\*=` | real_test_requirements_enforcer.py:72 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `NO \(webpack\)` | dev_launcher_monitoring.py:151 | print_configuration_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `pass\\s\*\#\.\*stub` | create_enforcement_tools.py:265 | EnforcementEngine.detect_te... | `[red]Workflow '`, `[cyan]Running: ` |
| `pass\\s\*\#\.\*TODO` | architecture_scanner_helpers.py:120 | ScannerHelpers.get_stub_pat... | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\(` | real_test_requirements_enforcer.py:356 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\(` | project_test_validator.py:274 | ProjectTestValidator._check... | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\(` | real_test_validator.py:236 | RealTestValidator._check_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.dict\\\(` | analyze_mocks.py:39 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.dict\\\(` | mock_justification_checker.py:31 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.multiple\\\(` | analyze_mocks.py:40 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.multiple\\\(` | mock_justification_checker.py:32 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.object\\\(` | analyze_mocks.py:38 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.object\\\(` | find_top_mocks.py:24 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `patch\\\.object\\\(` | mock_justification_checker.py:30 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `pk\-lf\-\.\*` | environment_validator_core.py:91 | EnvironmentValidatorCore._d... | `[red]Workflow '`, `[cyan]Running: ` |
| `postgresql\+asyncpg://` | environment_validator_database.py:51 | DatabaseValidator._parse_po... | `[red]Workflow '`, `[cyan]Running: ` |
| `postgresql\+asyncpg://` | environment_validator_database.py:116 | DatabaseValidator._attempt_... | `[red]Workflow '`, `[cyan]Running: ` |
| `print\\\(` | architecture_scanner_helpers.py:142 | ScannerHelpers.get_quality_... | `[red]Workflow '`, `[cyan]Running: ` |
| `PropertyMock\(\)` | find_top_mocks.py:22 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `PropertyMock\(\)` | mock_justification_checker.py:119 | MockJustificationChecker._c... | `[red]Workflow '`, `[cyan]Running: ` |
| `PropertyMock\\\(\\\)` | analyze_mocks.py:44 | MockAnalyzer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `PropertyMock\\\(\\\)` | find_top_mocks.py:22 | find_mock_patterns | `[red]Workflow '`, `[cyan]Running: ` |
| `PropertyMock\\\(\\\)` | mock_justification_checker.py:28 | MockJustificationChecker.__... | `[red]Workflow '`, `[cyan]Running: ` |
| `Python 3\.8\+` | startup_environment.py:95 | DependencyChecker._check_py... | `[red]Workflow '`, `[cyan]Running: ` |
| `README\*` | team_updates_documentation_analyzer.py:44 | DocumentationAnalyzer.find_... | `[red]Workflow '`, `[cyan]Running: ` |
| `real\.\*clickhouse` | categorize_tests.py:64 | TestCategorizer._get_clickh... | `[red]Workflow '`, `[cyan]Running: ` |
| `real\.\*database` | categorize_tests.py:54 | TestCategorizer._get_databa... | `[red]Workflow '`, `[cyan]Running: ` |
| `real\.\*llm` | categorize_tests.py:49 | TestCategorizer._get_llm_pa... | `[red]Workflow '`, `[cyan]Running: ` |
| `real\.\*redis` | categorize_tests.py:59 | TestCategorizer._get_redis_... | `[red]Workflow '`, `[cyan]Running: ` |
| `redis\\\.Redis\\\(` | categorize_tests.py:58 | TestCategorizer._get_redis_... | `[red]Workflow '`, `[cyan]Running: ` |
| `return cls\(` | enhance_dev_launcher_boundaries.py:22 | enhance_launcher_config | `[red]Workflow '`, `[cyan]Running: ` |
| `s \(limit: ` | test_staging_startup.py:207 | StagingStartupTester.test_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | environment_validator.py:161 | EnvironmentValidator.test_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | environment_validator.py:218 | EnvironmentValidator.test_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | environment_validator_database.py:120 | DatabaseValidator._attempt_... | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | environment_validator_database.py:181 | DatabaseValidator._test_cli... | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | test_async_postgres.py:50 | test_backend_connection | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | validate_staging_config.py:138 | test_db_connection | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | validate_staging_config.py:287 | check_clickhouse_connection | `[red]Workflow '`, `[cyan]Running: ` |
| `SELECT version\(\)` | validate_staging_config_partial.py:109 | _test_db_version | `[red]Workflow '`, `[cyan]Running: ` |
| `self\.boundary\_monitor\.setup\_monit...` | enhance_dev_launcher_boundaries.py:144 | enhance_launcher_main | `[red]Workflow '`, `[cyan]Running: ` |
| `self\\\.\(\\w\+\)` | test_refactor_helper.py:226 | TestRefactorHelper._extract... | `[red]Workflow '`, `[cyan]Running: ` |
| `setup\_test\_path\(\)` | fix_embedded_setup_imports.py:82 | EmbeddedSetupImportFixer.fi... | `[red]Workflow '`, `[cyan]Running: ` |
| `setup\_test\_path\(\)` | fix_malformed_imports.py:95 | MalformedImportFixer.find_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `setup\_test\_path\(\)` | fix_malformed_imports.py:135 | MalformedImportFixer.fix_ma... | `[red]Workflow '`, `[cyan]Running: ` |
| `setup\_test\_path\(\)` | fix_test_import_order.py:27 | fix_import_order | `[red]Workflow '`, `[cyan]Running: ` |
| `sleep\(` | test_generator.py:282 | _check_hardcoded_waits | `[red]Workflow '`, `[cyan]Running: ` |
| `test\(` | real_test_requirements_enforcer.py:156 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\*` | generate_test_audit.py:72 | analyze_test_structure | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*component` | categorize_tests.py:78 | TestCategorizer._get_unit_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*e2e` | categorize_tests.py:73 | TestCategorizer._get_integr... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*integration` | categorize_tests.py:73 | TestCategorizer._get_integr... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*isolated` | categorize_tests.py:78 | TestCategorizer._get_unit_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*orchestration` | categorize_tests.py:74 | TestCategorizer._get_integr... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*unit` | categorize_tests.py:78 | TestCategorizer._get_unit_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\.\*workflow` | categorize_tests.py:73 | TestCategorizer._get_integr... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\_\(\\w\+\)\_` | test_refactor_helper.py:529 | TestRefactorHelper._identif... | `[red]Workflow '`, `[cyan]Running: ` |
| `test\_\.\*?\(\\w\+\)\_\\w\+$` | test_refactor_helper.py:530 | TestRefactorHelper._identif... | `[red]Workflow '`, `[cyan]Running: ` |
| `tests\\\.unified\\\.e2e\\\.` | fix_e2e_test_imports.py:78 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `v?\(\\d\+\\\.\\d\+\\\.\\d\+\)` | env_checker.py:126 | check_node_version | `[red]Workflow '`, `[cyan]Running: ` |
| `v\\d\+` | prevent_numbered_files.py:48 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `validate\_token\\\(` | fix_import_issues.py:34 | fix_validate_token_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `validate\_token\_jwt\(` | fix_import_issues.py:35 | fix_validate_token_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `value\(status\.url\)` | deploy_to_gcp.py:543 | GCPDeployer.get_service_url | `[red]Workflow '`, `[cyan]Running: ` |
| `YES \(experimental\)` | dev_launcher_monitoring.py:151 | print_configuration_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `\{/\* 
` | agent_tracking_helper.py:157 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| `❌ \*\*` | process_results.py:46 | TestResultProcessor._genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `🔥 \*\*` | real_test_requirements_enforcer.py:503 | RealTestRequirementsEnforce... | `[red]Workflow '`, `[cyan]Running: ` |

### 🔴 Low (<0.5) (549 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `%\)` | main.py:128 | _print_coverage_metrics | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | demo_enhanced_categorizer.py:42 | compare_categorization_appr... | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | demo_enhanced_categorizer.py:43 | compare_categorization_appr... | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | demo_enhanced_categorizer.py:95 | compare_categorization_appr... | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | categorizer_enhanced.py:557 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | categorizer_enhanced.py:560 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | categorizer_enhanced.py:561 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | categorizer_enhanced.py:562 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | categorizer_enhanced.py:568 | print_categorization_report | `[red]Workflow '`, `[cyan]Running: ` |
| `%\)` | markdown_reporter.py:253 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\)` | mock_justification_checker.py:164 | MockJustificationChecker._c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\[` | aggressive_syntax_fix.py:152 | aggressive_fix | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | audit_permissions.py:70 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | audit_permissions.py:75 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | audit_permissions.py:83 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | e2e_import_fixer_comprehensive.py:524 | E2EImportFixer.print_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | enforce_limits.py:174 | EnforcementReporter.generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | fix_netra_backend_imports.py:194 | ImportFixer.generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | validate_service_independence.py:236 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | validate_service_independence.py:241 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | validate_type_deduplication.py:279 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | validate_type_deduplication.py:291 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\):` | validate_type_deduplication.py:303 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\*` | cleanup_staging_environments.py:225 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\-\*` | cleanup_staging_environments.py:233 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | verify_workflow_status.py:261 | OutputFormatter.display_table | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | verify_workflow_status.py:262 | OutputFormatter.display_table | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | workflow_introspection.py:230 | OutputFormatter.display_wor... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | workflow_introspection.py:256 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | workflow_introspection.py:257 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | workflow_introspection.py:274 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | workflow_introspection.py:290 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[/` | workflow_introspection.py:295 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `\]\(` | markdown_reporter.py:534 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `s\)` | startup_reporter.py:191 | StartupReporter._print_indi... | `[red]Workflow '`, `[cyan]Running: ` |
| `

\_\_all\_\_ = \[
` | fix_schema_imports.py:206 | SchemaImportFixer.update_in... | `[red]Workflow '`, `[cyan]Running: ` |
| `

Top 20 Files by Lowest Coverage Per...` | analyze_coverage.py:28 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
        self\.boundary\_monitor = Bo...` | enhance_dev_launcher_boundaries.py:135 | enhance_launcher_main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\#\# VIOLATION SUMMARY
\- \*\*Total ...` | function_complexity_analyzer.py:227 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\#\#\# Components Marked as Work\-In...` | status_renderer.py:117 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Files exceeding 300 lines\*\*: ` | team_updates_formatter.py:161 | HumanFormatter.format_code_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\*\*Functions exceeding 8 lines\*\*: ` | team_updates_formatter.py:167 | HumanFormatter.format_code_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Backend Only:\*\* ` | websocket_coherence_review.py:297 | _build_alignment_stats | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Critical Areas Affected\*\*: ` | function_complexity_analyzer.py:229 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Estimated Coverage:\*\* ` | generate_wip_report.py:263 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Frontend Only:\*\* ` | websocket_coherence_review.py:298 | _build_alignment_stats | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Growth Velocity:\*\* ` | boundary_enforcer_report_generator.py:222 | PRCommentGenerator._build_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*High Priority\*\*: ` | status_renderer.py:119 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Low Priority\*\*: ` | status_renderer.py:121 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Medium Priority\*\*: ` | status_renderer.py:120 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Module Count:\*\* ` | boundary_enforcer_report_generator.py:221 | PRCommentGenerator._build_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\- \*\*Total Lines:\*\* ` | boundary_enforcer_report_generator.py:220 | PRCommentGenerator._build_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[1/5\] Creating configuration\.\.\.` | metadata_enabler.py:38 | MetadataTrackingEnabler.ena... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[1\] Quick staging validation \(2\-...` | verify_staging_tests.py:155 | print_usage_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[2/5\] Setting up database\.\.\.` | metadata_enabler.py:43 | MetadataTrackingEnabler.ena... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[2\] Full staging configuration tes...` | verify_staging_tests.py:158 | print_usage_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[3/5\] Creating validator script\.\.\.` | metadata_enabler.py:48 | MetadataTrackingEnabler.ena... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[3\] Run with explicit GCP staging ...` | verify_staging_tests.py:161 | print_usage_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[4/5\] Creating archiver script\.\.\.` | metadata_enabler.py:53 | MetadataTrackingEnabler.ena... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[5/5\] Installing git hooks\.\.\.` | metadata_enabler.py:58 | MetadataTrackingEnabler.ena... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ADMIN\] ADMIN\-ONLY ROUTES \(` | audit_permissions.py:70 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[AI\] Detecting AI Coding Issues\.\.\.` | code_review_ai_detector.py:36 | CodeReviewAIDetector.detect... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[AI\] Detecting AI Coding Issues\.\.\.` | ai_detector.py:22 | AIDetector.detect_ai_coding... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[AUTH\] AUTHENTICATED ROUTES \(` | audit_permissions.py:75 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[AUTO\] Auto\-Restart: Enabled` | dev_launcher_monitoring.py:132 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[bold\]Workflow Run Details\[/bold\...` | workflow_introspection.py:268 | OutputFormatter.display_run... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[CANCELLED\] Cleanup cancelled by u...` | cleanup_generated_files.py:252 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[CANCELLED\] Scanning cancelled by ...` | scan_string_literals_enhanced.py:412 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[COMPLETE\] AI Agent Metadata Track...` | enabler.py:81 | MetadataTrackingEnabler._pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[COMPLETED\] Cleanup script complet...` | cleanup_generated_files.py:324 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[COMPLIANCE BY CATEGORY\]` | reporter.py:238 | ComplianceReporter._print_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[CONFIG\] Adding static configuration:` | dev_launcher_secrets.py:143 | EnhancedSecretLoader._final... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[CREATE\] Creating initial \.env fi...` | dev_launcher_secrets.py:209 | EnhancedSecretLoader._write... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[CRITICAL\] POTENTIALLY SENSITIVE P...` | audit_permissions.py:103 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DATABASE\] Validating Database Con...` | validate_network_constants.py:77 | validate_database_constants | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[dim\]No workflow outputs available...` | workflow_introspection.py:305 | OutputFormatter.display_out... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DONE\] Documentation generation co...` | markdown_reporter.py:597 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DONE\] Enhanced string literals sc...` | scan_string_literals_enhanced.py:331 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DRY RUN MODE\] No files will be de...` | cleanup_generated_files.py:248 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DRY RUN\] No files were actually m...` | fix_all_import_issues.py:308 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DRY RUN\] No files were actually m...` | fix_comprehensive_imports.py:353 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[DUPLICATE TYPE DEFINITIONS\]` | reporter.py:147 | ComplianceReporter._report_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[EMERGENCY ACTIONS REQUIRED\]:` | boundary_enforcer_report_generator.py:140 | ConsoleReportPrinter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ENDPOINTS\] Validating Service End...` | validate_network_constants.py:146 | validate_service_endpoints | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ENV\] Setting environment variable...` | dev_launcher_secrets.py:172 | EnhancedSecretLoader._set_e... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ENVIRONMENT\] Validating Network E...` | validate_network_constants.py:165 | validate_network_environmen... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Connection failed: ` | reset_clickhouse.py:190 | reset_clickhouse_instance | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Connection failed: ` | reset_clickhouse_auto.py:134 | reset_clickhouse_instance | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] ERRORS \(` | validate_service_independence.py:236 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Failed to generate documen...` | enhanced_string_literals_docs.py:105 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] PRE\-COMMIT: Import compli...` | unified_import_manager.py:576 | run_precommit_check | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Unexpected error: ` | reset_clickhouse.py:193 | reset_clickhouse_instance | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Unexpected error: ` | reset_clickhouse_auto.py:138 | reset_clickhouse_instance | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[ERROR\] Validation failed: ` | validate_network_constants.py:249 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FAILED\] Review FAILED \- Critical...` | code_review_reporter.py:218 | CodeReviewReporter.determin... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FAILED\] Review FAILED \- Critical...` | cli.py:123 | DisplayFormatter.determine_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FILE SIZE VIOLATIONS\] \(>` | reporter.py:48 | ComplianceReporter._report_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[FUNCTION COMPLEXITY VIOLATIONS\] \(>` | reporter.py:88 | ComplianceReporter._report_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[GIT\] Analyzing Recent Changes\.\.\.` | code_review_analysis.py:39 | CodeReviewAnalysis.analyze_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[GIT\] Analyzing Recent Changes\.\.\.` | git_analyzer.py:22 | GitAnalyzer.analyze_recent_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[green\]✓ All validations passed\[/...` | workflow_validator.py:257 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[HOSTS\] Validating Host Constants\...` | validate_network_constants.py:62 | validate_host_constants | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[JSON\] Import issues exported to: ` | check_netra_backend_imports.py:346 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[OK\] All dependencies satisfied` | startup_environment.py:169 | DependencyChecker._handle_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[OK\] No files found older than \{\...` | cleanup_generated_files.py:240 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[OK\] No sensitive public routes found` | audit_permissions.py:107 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PASSED\] Review PASSED` | code_review_reporter.py:224 | CodeReviewReporter.determin... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PASSED\] Review PASSED` | cli.py:129 | DisplayFormatter.determine_... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PERF\] Checking Performance Issues...` | code_review_analysis.py:153 | CodeReviewAnalysis.check_pe... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PERF\] Checking Performance Issues...` | performance_checker.py:20 | PerformanceChecker.check_pe... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PORTS\] Validating Service Ports\....` | validate_network_constants.py:40 | validate_service_ports | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[PRESERVE\] Keeping existing \.env ...` | dev_launcher_secrets.py:205 | EnhancedSecretLoader._write... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[red\]✗ Validation failed\[/red\]` | workflow_validator.py:260 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[REPORT\] Detailed report saved to: ` | report_generator.py:29 | ReportGenerator.generate_re... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[REPORT\] Report saved to: ` | code_review_reporter.py:180 | CodeReviewReporter.save_report | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[REPORT\] Report saved to: ` | report_generator.py:188 | ReportGenerator.save_report | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SECRETS\] Loading Process Started` | dev_launcher_secrets.py:124 | EnhancedSecretLoader.load_a... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SECRETS\] Loading secrets from Goo...` | dev_launcher_secrets.py:59 | EnhancedSecretLoader.load_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SECURITY\] Checking Security Issue...` | code_review_analysis.py:182 | CodeReviewAnalysis.check_se... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SECURITY\] Checking Security Issue...` | security_checker.py:22 | SecurityChecker.check_secur... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SPEC\] Checking Spec\-Code Alignme...` | code_review_analysis.py:101 | CodeReviewAnalysis.check_sp... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SPEC\] Checking Spec\-Code Alignme...` | spec_checker.py:22 | SpecChecker.check_spec_code... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[STOPPED\] Continuous review stopped` | main.py:105 | _run_continuous_review | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] All components are prope...` | status_manager.py:128 | StatusManager.print_status | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] All imports follow the c...` | check_netra_backend_imports.py:277 | ImportAnalyzer.generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] All startup issues resol...` | verify_startup_fix.py:100 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] All tables dropped in ` | reset_clickhouse.py:162 | verify_table_cleanup | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] All tables dropped in ` | reset_clickhouse_auto.py:115 | _handle_verification_results | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] Enhanced documentation g...` | enhanced_string_literals_docs.py:99 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] Markdown documentation g...` | generate_string_literals_docs.py:108 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUCCESS\] No schema import violati...` | check_schema_imports.py:438 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[SUMMARY\] Summary of validated com...` | validate_network_constants.py:238 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[TOP CRITICAL VIOLATIONS\]:` | boundary_enforcer_report_generator.py:155 | ConsoleReportPrinter._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[TOTAL\] Issues Found: ` | code_review_reporter.py:209 | CodeReviewReporter._display... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[TOTAL\] Issues Found: ` | cli.py:113 | DisplayFormatter._display_t... | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[URLS\] Validating URL Constants\.\.\.` | validate_network_constants.py:114 | validate_url_constants | `[red]Workflow '`, `[cyan]Running: ` |
| `
\[VALIDATING\] Service independence ...` | validate_service_independence.py:25 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `
CRITICAL ISSUES \(showing first 5\):` | comprehensive_import_scanner.py:127 | ComprehensiveScanReport.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `
Enter choice \(1\-4\): ` | reset_clickhouse.py:209 | show_menu_and_get_choice | `[red]Workflow '`, `[cyan]Running: ` |
| `
Enter the number of the workflow to ...` | force_cancel_workflow.py:111 | _handle_multiple_workflow_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `
Files that cannot be imported \(` | e2e_import_fixer_comprehensive.py:524 | E2EImportFixer.print_report | `[red]Workflow '`, `[cyan]Running: ` |
| `
High violation files \(10\+\): ` | extract_violations.py:71 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Operation complete\! \(` | reset_clickhouse_auto.py:182 | display_auto_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `
Proceed with ALL selected instances?...` | reset_clickhouse.py:232 | get_batch_confirmation | `[red]Workflow '`, `[cyan]Running: ` |
| `
Review Mode: Ultra\-Thinking Powered...` | report_generator.py:42 | ReportGenerator._generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `
SEVERE VIOLATIONS \(>20 lines\): ` | identify_violations.py:75 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
TOP HIGH SEVERITY VIOLATIONS \(showi...` | create_enforcement_tools.py:443 | print_high_severity_violations | `[red]Workflow '`, `[cyan]Running: ` |
| `
Use Ctrl\+Shift\+P \-> 'Tasks: Run T...` | simple_enhance_boundaries.py:67 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
Which ClickHouse instance\(s\) to re...` | reset_clickhouse.py:204 | show_menu_and_get_choice | `[red]Workflow '`, `[cyan]Running: ` |
| `
⚠️  This is NOT a dry run\. Continue...` | clean_slate_executor.py:238 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
✅ ENABLED FEATURES \(` | demo_feature_flag_system.py:136 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `
❌ DISABLED \(` | demo_feature_flag_system.py:148 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `
🚧 IN DEVELOPMENT \(` | demo_feature_flag_system.py:142 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `
🧪 Simulating OAuth Callback \(test o...` | monitor_oauth_flow.py:129 | OAuthMonitor.simulate_oauth... | `[red]Workflow '`, `[cyan]Running: ` |
| `            "clickhouse\_host": os\.e...` | fix_remaining_syntax_errors.py:133 | fix_file_structure_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `            "clickhouse\_port": os\.e...` | fix_remaining_syntax_errors.py:134 | fix_file_structure_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `            "postgres\_port": os\.env...` | fix_remaining_syntax_errors.py:132 | fix_file_structure_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `     Tests: Expected to fail \(xfail\...` | demo_feature_flag_system.py:86 | demonstrate_tdd_workflow | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[DRY RUN\] Would delete: ` | cleanup_generated_files.py:119 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `    \[ERROR\] Error deleting ` | cleanup_generated_files.py:130 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `   \# Set test database \(recommended\)` | demo_real_llm_testing.py:228 | demo_cli_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `   \# Set test\-specific API keys \(r...` | demo_real_llm_testing.py:224 | demo_cli_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `   \- Archived \(moved to archived fo...` | update_spec_timestamps.py:295 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `   \- Deleted \(if truly obsolete\)
` | update_spec_timestamps.py:296 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `   \- Updated \(if still relevant but...` | update_spec_timestamps.py:297 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `   1\. Write test BEFORE implementati...` | demo_feature_flag_system.py:68 | demonstrate_tdd_workflow | `[red]Workflow '`, `[cyan]Running: ` |
| `   3\. CI/CD maintains 100% pass rate...` | demo_feature_flag_system.py:70 | demonstrate_tdd_workflow | `[red]Workflow '`, `[cyan]Running: ` |
| `   API keys: FAILED \(` | demo_real_llm_testing.py:70 | demo_environment_validation | `[red]Workflow '`, `[cyan]Running: ` |
| `   Database connection: FAILED \(` | demo_real_llm_testing.py:51 | demo_environment_validation | `[red]Workflow '`, `[cyan]Running: ` |
| `   Fix issues and try again, or use \...` | deploy_to_gcp.py:654 | GCPDeployer.deploy_all | `[red]Workflow '`, `[cyan]Running: ` |
| `   Logs: Real\-time streaming \(cyan\)` | dev_launcher_monitoring.py:125 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `   Logs: Real\-time streaming \(magen...` | dev_launcher_monitoring.py:129 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `   Press Ctrl\+C to stop all services` | dev_launcher_monitoring.py:136 | print_service_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `   Seed data management: FAILED \(` | demo_real_llm_testing.py:170 | demo_seed_data_management | `[red]Workflow '`, `[cyan]Running: ` |
| `   Seed data: FAILED \(` | demo_real_llm_testing.py:88 | demo_environment_validation | `[red]Workflow '`, `[cyan]Running: ` |
| `   Still waiting\.\.\. \(` | dev_launcher_monitoring.py:43 | _handle_service_check_failure | `[red]Workflow '`, `[cyan]Running: ` |
| `   Using Turbopack \(experimental\)` | dev_launcher_service.py:186 | ServiceManager._build_front... | `[red]Workflow '`, `[cyan]Running: ` |
| `   • Result: 100% pass rate maintaine...` | demo_feature_flag_system.py:160 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `   ✅ Enabled Features \(` | demo_feature_flag_system.py:46 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `   ❌ Disabled Features \(` | demo_feature_flag_system.py:48 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `   🚧 In Development \(` | demo_feature_flag_system.py:47 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `   🧪 Experimental \(` | demo_feature_flag_system.py:49 | demonstrate_feature_flag_ba... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \(showing first 20 of ` | fix_all_import_issues.py:290 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `  \+ Added CostOptimizer class` | fast_import_checker.py:198 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `  \+ Added get\_async\_db function` | fast_import_checker.py:253 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `  \+ Added StartupCheckResult class` | fast_import_checker.py:148 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `  \+ Added thread\_service export` | fast_import_checker.py:104 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `  \+ Created WebSocket manager module` | fast_import_checker.py:321 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `  \-\-days N   : Set max age in days ...` | cleanup_generated_files.py:343 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `  \-\-lenient   Use lenient validatio...` | schema_sync.py:182 | print_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `  \-\-strict    Use strict validation...` | schema_sync.py:181 | print_usage | `[red]Workflow '`, `[cyan]Running: ` |
| `  2\. Set GCP\_PROJECT\_ID \(defaults...` | verify_staging_tests.py:166 | print_usage_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[DRY RUN\] Would destroy environme...` | cleanup_staging_environments.py:166 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[ERROR\] Failed to list tables: ` | reset_clickhouse_final.py:32 | _get_database_tables | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[ERROR\] Failed to scan ` | scan_string_literals_enhanced.py:99 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[FAIL\] Failed to fetch ` | fetch_secrets_to_env.py:76 | _fetch_all_secrets | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Archiver script for audit lo...` | enabler.py:87 | MetadataTrackingEnabler._pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Configuration file with trac...` | enabler.py:85 | MetadataTrackingEnabler._pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Dropped table: ` | reset_clickhouse.py:59 | drop_table | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Dropped table: ` | reset_clickhouse_auto.py:60 | drop_table | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Git hooks for automatic vali...` | enabler.py:83 | MetadataTrackingEnabler._pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] No tables found in ` | reset_clickhouse_final.py:40 | _display_tables_info | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] SQLite database for metadata...` | enabler.py:84 | MetadataTrackingEnabler._pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Successfully fetched ` | fetch_secrets_to_env.py:74 | _fetch_all_secrets | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[OK\] Validator script for metadat...` | enabler.py:86 | MetadataTrackingEnabler._pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] All mocks are justified` | reporter.py:218 | ComplianceReporter._print_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] No duplicates found` | reporter.py:158 | ComplianceReporter._print_d... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] No violations found` | reporter.py:65 | ComplianceReporter._print_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[PASS\] No violations found` | reporter.py:143 | ComplianceReporter._print_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[SUCCESS\] All tables dropped from ` | reset_clickhouse_final.py:64 | _verify_tables_dropped | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] No specification found for: ` | code_review_analysis.py:148 | CodeReviewAnalysis._check_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `  \[WARN\] No specification found for: ` | spec_checker.py:91 | SpecChecker._check_module_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `  Expected error \(invalid code\): ` | monitor_oauth_flow.py:147 | OAuthMonitor.simulate_oauth... | `[red]Workflow '`, `[cyan]Running: ` |
| `  Replace with import checking hook? ...` | setup_import_hooks.py:35 | setup_pre_commit_hook | `[red]Workflow '`, `[cyan]Running: ` |
| `  VIOLATIONS \(must fix\):` | reporter.py:110 | ComplianceReporter._print_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `  • Database URL builders \(PostgreSQ...` | validate_network_constants.py:241 | main | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(has other syntax errors\)` | fix_embedded_setup_imports.py:173 | EmbeddedSetupImportFixer.pr... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(has other syntax errors\)` | fix_malformed_imports.py:215 | MalformedImportFixer.proces... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(skipped \- don't count\)` | demo_feature_flag_system.py:159 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| ` \(xfail \- don't count against pass ...` | demo_feature_flag_system.py:158 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Agent Modification History
` | agent_tracking_helper.py:235 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* Agent Modification Tracking
` | agent_tracking_helper.py:147 | AgentTrackingHelper._format... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \* AI AGENT MODIFICATION METADATA` | metadata_header_generator.py:154 | MetadataHeaderGenerator.for... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \\\* Agent Modification History\\n \...` | agent_tracking_helper.py:204 | AgentTrackingHelper._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| ` Boundary Enforcement Report

\*\*Sta...` | boundary_enforcer_report_generator.py:207 | PRCommentGenerator._build_p... | `[red]Workflow '`, `[cyan]Running: ` |
| ` enabled features pass\)` | demo_feature_flag_system.py:160 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| ` exceeded maximum restart attempts \(` | dev_launcher_processes.py:151 | ProcessMonitor._handle_proc... | `[red]Workflow '`, `[cyan]Running: ` |
| ` failed \(will retry on first run\)` | config_setup_core.py:97 | execute_database_script | `[red]Workflow '`, `[cyan]Running: ` |
| ` frequently changed files \(potential...` | code_review_analysis.py:70 | CodeReviewAnalysis._analyze... | `[red]Workflow '`, `[cyan]Running: ` |
| ` frequently changed files \(potential...` | git_analyzer.py:59 | GitAnalyzer._report_hotspots | `[red]Workflow '`, `[cyan]Running: ` |
| ` issues found
\- \*\*API Endpoints\*\*: ` | status_renderer.py:78 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| ` issues found
\- \*\*Frontend Compone...` | status_renderer.py:77 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| ` issues found
\- \*\*Test Results\*\*: ` | status_renderer.py:79 | StatusReportRenderer._build... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines
\- \*\*File\*\*: \`` | function_complexity_analyzer.py:268 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| ` lines\)
\- \*\*Complexity Score\*\*: ` | function_complexity_analyzer.py:270 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| ` monitoring stopped \(exceeded max re...` | dev_launcher_monitoring.py:75 | check_monitor_health | `[red]Workflow '`, `[cyan]Running: ` |
| ` more \(use \-\-show\-all to see all\)` | reporter.py:84 | ComplianceReporter._print_t... | `[red]Workflow '`, `[cyan]Running: ` |
| ` not available in error\_types\\n\# \...` | fix_comprehensive_imports.py:107 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| ` not supported, requires 3\.8\+` | environment_validator_dependencies.py:93 | DependencyValidator._check_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` occurrences in file\)` | relaxed_violation_counter.py:148 | RelaxedViolationCounter.get... | `[red]Workflow '`, `[cyan]Running: ` |
| ` occurrences in file\)` | relaxed_violation_counter.py:161 | RelaxedViolationCounter.get... | `[red]Workflow '`, `[cyan]Running: ` |
| ` port conflicts \(non\-critical\)` | environment_validator_ports.py:185 | PortValidator._update_port_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` potentially stuck workflow\(s\):` | force_cancel_workflow.py:92 | _display_stuck_runs_summary | `[red]Workflow '`, `[cyan]Running: ` |
| ` secrets from environment\[/green\]` | local_secrets_manager.py:201 | LocalSecretsManager._import... | `[red]Workflow '`, `[cyan]Running: ` |
| ` secrets to \.act\.secrets\[/green\]` | local_secrets_manager.py:150 | LocalSecretsManager.export_... | `[red]Workflow '`, `[cyan]Running: ` |
| ` staging environment \(Reason: ` | cleanup_staging_environments.py:163 | StagingEnvironmentCleaner.c... | `[red]Workflow '`, `[cyan]Running: ` |
| ` table\(s\) still exist:` | reset_clickhouse.py:165 | verify_table_cleanup | `[red]Workflow '`, `[cyan]Running: ` |
| ` table\(s\) still exist:` | reset_clickhouse_auto.py:117 | _handle_verification_results | `[red]Workflow '`, `[cyan]Running: ` |
| ` \|

\#\#\# Coverage Metrics
\- \*\*T...` | generate_wip_report.py:260 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \|
\| \*\*Total\*\* \| \*\*` | generate_wip_report.py:241 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \|
\| Integration \(L2\-L3\) \| ` | generate_wip_report.py:258 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \|
\| Unit Tests \(L1\) \| ` | generate_wip_report.py:259 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `"postgres\_host": os\.environ\.get\("...` | fix_remaining_syntax_errors.py:115 | fix_file_structure_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `%
\*\*Total Violations:\*\* ` | boundary_enforcer_report_generator.py:211 | PRCommentGenerator._build_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `%
\- \*\*Coverage Gap\*\*: ` | report_generator.py:47 | ReportGenerator._generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `%
\- \*\*Target Coverage\*\*: ` | report_generator.py:46 | ReportGenerator._generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `%
\- \*\*Target Coverage:\*\* 97%
\- ...` | generate_wip_report.py:264 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `%
\- \*\*Test Quality Score\*\*: ` | report_generator.py:48 | ReportGenerator._generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(Based on pyramid distribution\)
\...` | generate_wip_report.py:231 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(E2E tests: ` | generate_wip_report.py:195 | WIPReportGenerator.generate... | `[red]Workflow '`, `[cyan]Running: ` |
| `% \(Production code only\)
\- \*\*Tes...` | generate_wip_report.py:230 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `% compliant \(` | reporter.py:246 | ComplianceReporter._print_c... | `[red]Workflow '`, `[cyan]Running: ` |
| `%\*\* passing
\- Code is \*\*` | team_updates_formatter.py:79 | HumanFormatter.format_execu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\# Agent Modification Tracking\\n\#...` | agent_tracking_helper.py:180 | AgentTrackingHelper._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\# Agent Modification Tracking\\n\#...` | agent_tracking_helper.py:186 | AgentTrackingHelper._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\) at line ` | analyze_critical_paths.py:76 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\(\)\*\* in \`` | decompose_functions.py:144 | generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\(/\\\*\\\*\\n \\\* Agent Modificatio...` | agent_tracking_helper.py:182 | AgentTrackingHelper._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| `\(from datetime import\[^\\n\]\+\)` | enhanced_fix_datetime_deprecation.py:43 | _add_utc_import | `[red]Workflow '`, `[cyan]Running: ` |
| `\(from datetime import\[^\\n\]\+\)` | fix_datetime_deprecation.py:31 | fix_datetime_in_file | `[red]Workflow '`, `[cyan]Running: ` |
| `\) \- MUST PASS:` | demo_feature_flag_system.py:136 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `\) \- SKIPPED:` | demo_feature_flag_system.py:148 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `\) \- Status: ` | verify_workflow_status.py:143 | WorkflowStatusVerifier.wait... | `[red]Workflow '`, `[cyan]Running: ` |
| `\) \- XFAIL \(TDD\):` | demo_feature_flag_system.py:142 | demonstrate_ci_cd_integration | `[red]Workflow '`, `[cyan]Running: ` |
| `\) in use` | environment_validator_ports.py:203 | PortValidator._add_port_rec... | `[red]Workflow '`, `[cyan]Running: ` |
| `\) in use` | env_checker.py:239 | get_service_ports_status | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Generated by run\_review\.py implem...` | code_review_reporter.py:140 | CodeReviewReporter._add_rep... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Generated by run\_review\.py implem...` | report_generator.py:178 | ReportGenerator._add_report... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Most changed files in this period:\*` | team_updates_sync.py:109 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\*No file changes detected\*` | team_updates_sync.py:126 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\*Report saved to: team\_updates/` | team_updates_sync.py:151 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\*This documentation is automatically...` | markdown_reporter.py:396 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*This is the detailed documentation ...` | markdown_reporter.py:539 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\+ All working` | fast_import_checker.py:441 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\+ required, found ` | env_checker.py:110 | check_python_version | `[red]Workflow '`, `[cyan]Running: ` |
| `\+ required, found ` | env_checker.py:136 | check_node_version | `[red]Workflow '`, `[cyan]Running: ` |
| `, the team:
\- Completed \*\*` | team_updates_formatter.py:76 | HumanFormatter.format_execu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Add tests\*\* to restore cover...` | team_updates_formatter.py:209 | HumanFormatter.format_actio... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Apex Optimizer Agent\*\*: ` | status_section_renderers.py:119 | ComponentDetailsRenderer._f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Commits\*\*: Unable to fetch \...` | team_updates_sync.py:66 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Compliance\*\*: Unable to check` | team_updates_sync.py:94 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Compliance\*\*: ⚠️ Some violat...` | team_updates_sync.py:92 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Compliance\*\*: ✅ Architecture...` | team_updates_sync.py:90 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*CPU Cores:\*\* ` | startup_reporter.py:135 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Fix failing tests\*\* before n...` | team_updates_formatter.py:203 | HumanFormatter.format_actio... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Matched Events:\*\* ` | websocket_coherence_review.py:297 | _build_alignment_stats | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Refactor large files\*\* to me...` | team_updates_formatter.py:206 | HumanFormatter.format_actio... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Success Rate:\*\* ` | startup_reporter.py:113 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Supervisor Status\*\*: ` | status_section_renderers.py:101 | ComponentDetailsRenderer._f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Test Reports\*\*: ` | team_updates_sync.py:72 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Test Status\*\*: ✅ Tests passing` | team_updates_sync.py:79 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Test Status\*\*: ❌ Some tests ...` | team_updates_sync.py:81 | generate_simple_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*Total Tests:\*\* ` | startup_reporter.py:110 | MarkdownReportGenerator._bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*URGENT\*\*: Address critical i...` | code_review_reporter.py:126 | CodeReviewReporter._add_rec... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- \*\*URGENT\*\*: Address critical i...` | report_generator.py:161 | ReportGenerator._add_critic... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- ⚙️ \[Scan for New Literals\]\(\.\....` | markdown_reporter.py:392 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 🏠 \[Back to Main Index\]\(\.\./str...` | markdown_reporter.py:523 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 🏠 \[Back to Main Index\]\(\.\./str...` | markdown_reporter.py:634 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 🏠 \[Back to Top\]\(\#string\-liter...` | markdown_reporter.py:389 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 📂 \[Browse Categories by File\]\(s...` | markdown_reporter.py:390 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 📂 \[Browse Other Categories\]\(\./\)` | markdown_reporter.py:524 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 🔍 \[Query String Literals\]\(\.\./...` | markdown_reporter.py:391 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 🔍 \[Query String Literals\]\(\.\./...` | markdown_reporter.py:635 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\- 🔴 \*\*CRITICAL:\*\* Address ` | generate_security_report.py:203 | _generate_security_recommen... | `[red]Workflow '`, `[cyan]Running: ` |
| `/100
\- \*\*Technical Debt\*\*: ` | report_generator.py:49 | ReportGenerator._generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `/bin/bash \-c "$\(curl \-fsSL https:/...` | dependency_services.py:68 | get_mac_pg_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `1\. Start with high\-confidence sugge...` | auto_split_files.py:346 | FileSplitter.generate_split... | `[red]Workflow '`, `[cyan]Running: ` |
| `1\. Start with validation\_processing...` | auto_decompose_functions.py:438 | FunctionDecomposer.generate... | `[red]Workflow '`, `[cyan]Running: ` |
| `2\. Fix critical duplicates first \(m...` | validate_type_deduplication.py:317 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `2\. Review class\-based splits first ...` | auto_split_files.py:347 | FileSplitter.generate_split... | `[red]Workflow '`, `[cyan]Running: ` |
| `: ERROR reading file \(` | demo_real_llm_testing.py:165 | demo_seed_data_management | `[red]Workflow '`, `[cyan]Running: ` |
| `: Generate with: python \-c "import s...` | create_staging_secrets.py:158 | _provide_manual_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `: Not set \(optional\)` | validate_staging_config_partial.py:62 | check_github_secrets | `[red]Workflow '`, `[cyan]Running: ` |
| `</span>
\*\*Growth Risk:\*\* ` | boundary_enforcer_report_generator.py:209 | PRCommentGenerator._build_p... | `[red]Workflow '`, `[cyan]Running: ` |
| `<?xml version="1\.0" encoding="UTF\-8"?>` | split_learnings_robust.py:52 | create_category_file | `[red]Workflow '`, `[cyan]Running: ` |
| `<?xml version="1\.0" encoding="UTF\-8"?>` | split_learnings_robust.py:82 | create_index | `[red]Workflow '`, `[cyan]Running: ` |
| `\[\!\] Drop ALL tables in ` | reset_clickhouse.py:143 | confirm_table_deletion | `[red]Workflow '`, `[cyan]Running: ` |
| `\[\!\] Installation completed with is...` | install_dev_env.py:159 | DevEnvironmentInstaller.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[\+\] Installation completed\!` | install_dev_env.py:156 | DevEnvironmentInstaller.pri... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[BUDGET\] Set daily budget: $` | manage_workflows.py:135 | WorkflowManager.set_cost_bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[BUDGET\] Set monthly budget: $` | manage_workflows.py:139 | WorkflowManager.set_cost_bu... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[CATEGORIZE\] Active literals: ` | scan_string_literals_enhanced.py:110 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[CATEGORIZE\] Ignored literals: ` | scan_string_literals_enhanced.py:111 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[CATEGORIZE\] Processing literals wi...` | scan_string_literals_enhanced.py:105 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[DRY RUN MODE\] Would have deleted:` | cleanup_generated_files.py:282 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[DRY RUN\] No files were actually mo...` | fix_embedded_setup_imports.py:220 | EmbeddedSetupImportFixer.ge... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[DRY RUN\] No files were actually mo...` | fix_malformed_imports.py:262 | MalformedImportFixer.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ENV\] Loading from existing \.env f...` | dev_launcher_secrets.py:34 | EnhancedSecretLoader.load_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Error fixing ` | fix_supervisor_imports.py:50 | fix_supervisor_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Errors encountered during i...` | unified_import_manager.py:564 | UnifiedImportManager.print_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to create metadata d...` | database_manager.py:116 | DatabaseManager.create_data... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to create script ` | script_generator.py:54 | ScriptGeneratorBase._create... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to import network co...` | validate_network_constants.py:34 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to install git hooks: ` | git_hooks_manager.py:30 | GitHooksManager.install_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to install git hooks: ` | hooks_manager.py:100 | GitHooksManager.install_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to install some git ...` | hooks_manager.py:96 | GitHooksManager.install_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Failed to write script file ` | script_generator.py:50 | ScriptGeneratorBase._create... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] No literals found to process` | scan_string_literals_enhanced.py:309 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] No requirements\.txt found` | validate_service_independence.py:117 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Please specify \-\-enable o...` | manage_workflows.py:235 | _handle_feature_command | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Service cannot be imported ...` | validate_service_independence.py:194 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Service has 'app' directory...` | validate_service_independence.py:46 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Service path does not exist: ` | validate_service_independence.py:268 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Step failed: ` | enabler.py:64 | MetadataTrackingEnabler._ex... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Unexpected error: ` | reset_clickhouse_final.py:93 | reset_local_clickhouse | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Unexpected error: ` | scan_string_literals_enhanced.py:415 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[ERROR\] Unknown preset: ` | workflow_presets.py:88 | WorkflowPresets.validate_pr... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] Frontend test setup has issues:` | validate_frontend_tests.py:239 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAIL\] VIOLATIONS FOUND: ` | reporter.py:292 | ComplianceReporter._print_f... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FAILED\] VERIFICATION FAILED` | verify_staging_tests.py:197 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[FIXED\] Import issues have been aut...` | unified_import_manager.py:559 | UnifiedImportManager.print_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[HIGH\] Priority Issues: ` | code_review_reporter.py:202 | CodeReviewReporter._display... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[HIGH\] Priority Issues: ` | cli.py:104 | DisplayFormatter._display_h... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] Category files: ` | markdown_reporter.py:601 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] Cloud reset requires clickho...` | reset_clickhouse_final.py:109 | reset_cloud_clickhouse | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] Main index: ` | markdown_reporter.py:600 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] No embedded setup patterns f...` | fix_embedded_setup_imports.py:224 | EmbeddedSetupImportFixer.ge... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] No malformed import patterns...` | fix_malformed_imports.py:266 | MalformedImportFixer.genera... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] Switching from Warp runners ...` | fix_warp_runners.py:35 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[INFO\] Use \.env\.development for l...` | dev_launcher_secrets.py:206 | EnhancedSecretLoader._write... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[JSON\] Saved enhanced index to ` | scan_string_literals_enhanced.py:214 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[JSON\] Total categories: ` | scan_string_literals_enhanced.py:216 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[MARKDOWN\] Documentation generated in ` | scan_string_literals_enhanced.py:236 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[MARKDOWN\] Generating enhanced docu...` | scan_string_literals_enhanced.py:224 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[MARKDOWN\] No active literals to do...` | scan_string_literals_enhanced.py:230 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] All checks passed\! Service is...` | validate_service_independence.py:233 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Backend is ready` | dev_launcher_monitoring.py:90 | validate_backend_health | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Boundary enforcement hooks and...` | boundary_enforcer_cli_handler.py:58 | HookInstaller.install_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Database constants validation ...` | validate_network_constants.py:109 | validate_database_constants | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Dockerfile copies entire servi...` | validate_service_independence.py:105 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Fixed imports in ` | fix_supervisor_imports.py:46 | fix_supervisor_imports | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Found Docker container: netra\...` | reset_clickhouse_final.py:24 | _check_docker_container | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Frontend is ready` | dev_launcher_monitoring.py:107 | validate_frontend_health | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Frontend tests are properly co...` | validate_frontend_tests.py:235 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Generated test ` | generate_startup_integration_tests.py:399 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Host constants validation passed` | validate_network_constants.py:72 | validate_host_constants | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Network constants module is wo...` | validate_network_constants.py:235 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Network environment helper val...` | validate_network_constants.py:195 | validate_network_environmen... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] No 'app' directory found \(good\)` | validate_service_independence.py:49 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] No imports from main app found...` | validate_service_independence.py:82 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] No tables found\. Database is ...` | reset_clickhouse.py:95 | _fetch_and_display_tables | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] No tables found\. Database is ...` | reset_clickhouse.py:129 | fetch_and_display_tables | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] No tables found\. Database is ...` | reset_clickhouse_auto.py:96 | _process_existing_tables | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Requirements appear complete` | validate_service_independence.py:143 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Service can be imported indepe...` | validate_service_independence.py:191 | ServiceIndependenceValidato... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Service endpoints validation p...` | validate_network_constants.py:160 | validate_service_endpoints | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Service ports validation passed` | validate_network_constants.py:57 | validate_service_ports | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] Successfully imported network ...` | validate_network_constants.py:32 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `\[OK\] URL constants validation passed` | validate_network_constants.py:141 | validate_url_constants | `[red]Workflow '`, `[cyan]Running: ` |
| `\[PASS\] FULL COMPLIANCE \- All archi...` | reporter.py:278 | ComplianceReporter._handle_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[PASS\] No boundary violations found` | boundary_enforcer_cli_handler.py:179 | ViolationDisplayer.display_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[red\]Error executing gh command: ` | workflow_introspection.py:83 | WorkflowIntrospector._run_g... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[REPORT\] JSON report saved to: ` | report_generator.py:37 | ReportGenerator.generate_re... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[RESTART\] Attempting to restart ` | dev_launcher_processes.py:181 | ProcessMonitor._attempt_res... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SCAN\] Total raw literals found: ` | scan_string_literals_enhanced.py:102 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[STATS\] Average confidence: ` | scan_string_literals_enhanced.py:116 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[STATS\] Categorization rate: ` | scan_string_literals_enhanced.py:117 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[STATS\] Generated documentation for ` | markdown_reporter.py:598 | MarkdownReporter.generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] All import issues have be...` | fix_netra_backend_imports.py:214 | ImportFixer.generate_report | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] All imports are compliant...` | unified_import_manager.py:557 | UnifiedImportManager.print_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] All validations passed su...` | validate_network_constants.py:234 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Created \.env with ` | fetch_secrets_to_env.py:119 | _print_summary | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Git hooks installed succe...` | git_hooks_manager.py:26 | GitHooksManager.install_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Git hooks installed succe...` | hooks_manager.py:93 | GitHooksManager.install_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Metadata database created...` | database_manager.py:105 | DatabaseManager._finalize_s... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Pre\-commit hooks DISABLED` | manage_precommit.py:70 | disable_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Pre\-commit hooks ENABLED` | manage_precommit.py:49 | enable_hooks | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] PRE\-COMMIT: All imports ...` | unified_import_manager.py:582 | run_precommit_check | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Script created at ` | script_generator.py:47 | ScriptGeneratorBase._create... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] Team update report saved ...` | team_updates_sync.py:175 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUCCESS\] VERIFICATION SUCCESSFUL` | verify_staging_tests.py:193 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[SUMMARY\] Secret Loading Summary:` | dev_launcher_secrets.py:180 | EnhancedSecretLoader._print... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[TEST\] Network Constants Validation...` | validate_network_constants.py:222 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] Comparing enhanced outpu...` | scan_string_literals_enhanced.py:245 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] Enhanced literals: ` | scan_string_literals_enhanced.py:263 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] Error loading original d...` | scan_string_literals_enhanced.py:252 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] Original literals: ` | scan_string_literals_enhanced.py:262 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] Run the original scanner...` | scan_string_literals_enhanced.py:242 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] This may indicate a regr...` | scan_string_literals_enhanced.py:268 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ⚠️  Enhanced scanner val...` | scan_string_literals_enhanced.py:294 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ⚠️  Significant differen...` | scan_string_literals_enhanced.py:267 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ✅ Category structure is ...` | scan_string_literals_enhanced.py:286 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ✅ Enhanced scanner valid...` | scan_string_literals_enhanced.py:292 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ✅ Literal counts are con...` | scan_string_literals_enhanced.py:270 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ➕ New categories: ` | scan_string_literals_enhanced.py:280 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[VALIDATE\] ➖ Missing categories: ` | scan_string_literals_enhanced.py:283 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `\[WAIT\] Waiting for backend to be re...` | dev_launcher_monitoring.py:86 | validate_backend_health | `[red]Workflow '`, `[cyan]Running: ` |
| `\[WAIT\] Waiting for frontend to be r...` | dev_launcher_monitoring.py:99 | validate_frontend_health | `[red]Workflow '`, `[cyan]Running: ` |
| `\[WAITING\] Next review in 1 hour\.\.\.` | main.py:102 | _run_continuous_review | `[red]Workflow '`, `[cyan]Running: ` |
| `\[WEB\] Opening browser at ` | dev_launcher_monitoring.py:57 | open_browser | `[red]Workflow '`, `[cyan]Running: ` |
| `\[yellow\]Waiting for workflow ` | verify_workflow_status.py:142 | WorkflowStatusVerifier.wait... | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1from netra\_backend\.app import` | fix_netra_backend_imports.py:54 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\\1from netra\_backend\.tests import` | fix_netra_backend_imports.py:55 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\] Feature '` | manage_workflows.py:126 | WorkflowManager.set_feature | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)from app import` | fix_netra_backend_imports.py:54 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(\\s\*\)from tests import` | fix_netra_backend_imports.py:55 | ImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^\(ORDER BY\|GROUP BY\|HAVING\|LIMIT\...` | categorizer_enhanced.py:126 | EnhancedStringLiteralCatego... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from \.\+ import \\\($` | fix_embedded_setup_imports.py:66 | EmbeddedSetupImportFixer.fi... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from \.\+ import \\\($` | fix_malformed_imports.py:72 | MalformedImportFixer.find_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from conftest import` | fix_remaining_e2e_imports.py:51 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.agents...` | fix_comprehensive_imports.py:138 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.agents...` | fix_comprehensive_imports.py:209 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.agents...` | fix_comprehensive_imports.py:177 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.core\\...` | fix_comprehensive_imports.py:104 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.monito...` | fix_comprehensive_imports.py:89 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from schemas import` | comprehensive_e2e_import_fixer.py:65 | ComprehensiveE2EImportFixer... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from schemas import` | fix_e2e_imports.py:43 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `^from value\_corpus\_to\_xml import` | fix_all_import_issues.py:122 | ComprehensiveImportFixer._b... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from value\_corpus\_validation import` | fix_all_import_issues.py:128 | ComprehensiveImportFixer._b... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from ws\_manager import` | fix_e2e_imports.py:47 | E2EImportFixer.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `\`
\- \*\*Lines\*\*: ` | function_complexity_analyzer.py:269 | FunctionComplexityAnalyzer.... | `[red]Workflow '`, `[cyan]Running: ` |
| `\` \- \*` | markdown_reporter.py:376 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `C:\\Program Files \(x86\)\\GitHub CLI...` | cleanup_workflow_runs.py:23 | run_gh_command | `[red]Workflow '`, `[cyan]Running: ` |
| `C:\\Program Files\\GitHub CLI\\gh\.exe` | cleanup_workflow_runs.py:22 | run_gh_command | `[red]Workflow '`, `[cyan]Running: ` |
| `ENGINE = MergeTree\(` | aggressive_syntax_fix.py:147 | aggressive_fix | `[red]Workflow '`, `[cyan]Running: ` |
| `ENGINE = MergeTree\(` | aggressive_syntax_fix.py:149 | aggressive_fix | `[red]Workflow '`, `[cyan]Running: ` |
| `ENGINE = MergeTree\(\)` | aggressive_syntax_fix.py:149 | aggressive_fix | `[red]Workflow '`, `[cyan]Running: ` |
| `Entry \\d\+: \(\.\+\)` | agent_tracking_helper.py:212 | AgentTrackingHelper._extrac... | `[red]Workflow '`, `[cyan]Running: ` |
| `find SPEC \-name '\*` | spec_checker.py:100 | SpecChecker._find_matching_... | `[red]Workflow '`, `[cyan]Running: ` |
| `from \.\* import \\\*` | architecture_scanner_helpers.py:133 | ScannerHelpers.get_debt_pat... | `[red]Workflow '`, `[cyan]Running: ` |
| `from netra\_backend\.app\.websocket\....` | fix_all_e2e_imports.py:36 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `from netra\_backend\.app\.websocket\....` | fix_all_e2e_imports.py:42 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `import sys
from pathlib import Path
s...` | check_e2e_imports.py:159 | E2EImportChecker.fix_common... | `[red]Workflow '`, `[cyan]Running: ` |
| `NOT SET \(optional\)` | validate_staging_config_partial.py:41 | check_env_var | `[red]Workflow '`, `[cyan]Running: ` |
| `Press Ctrl\+C to stop` | start_auth_service.py:116 | AuthServiceManager.run | `[red]Workflow '`, `[cyan]Running: ` |
| `return \\\[\{"id": "1"` | architecture_scanner_helpers.py:116 | ScannerHelpers.get_stub_pat... | `[red]Workflow '`, `[cyan]Running: ` |
| `runs\-on: $\{\{ env\.ACT` | fix_workflow_env_issues.py:76 | process_workflow_file | `[red]Workflow '`, `[cyan]Running: ` |
| `runs\-on: $\{\{ env\.ACT` | fix_workflow_env_issues.py:76 | process_workflow_file | `[red]Workflow '`, `[cyan]Running: ` |
| `⚠️  IMPORT VIOLATIONS \(` | validate_type_deduplication.py:303 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `✅ DEPLOYMENT HEALTHY \(Score: ` | staging_error_monitor.py:111 | ConsoleFormatter.format_rec... | `[red]Workflow '`, `[cyan]Running: ` |
| `❌ DEPLOYMENT FAILURE RECOMMENDED \(Sc...` | staging_error_monitor.py:110 | ConsoleFormatter.format_rec... | `[red]Workflow '`, `[cyan]Running: ` |
| `🐍 PYTHON DUPLICATES \(` | validate_type_deduplication.py:279 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `📄 \*\*\[View detailed ` | markdown_reporter.py:381 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `🔴 CRITICAL DUPLICATES \(Must Fix Imme...` | validate_type_deduplication.py:265 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `🔴 Low \(<0\.5\)` | markdown_reporter.py:28 | MarkdownReporter.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `🔷 TYPESCRIPT DUPLICATES \(` | validate_type_deduplication.py:291 | TypeDeduplicationValidator.... | `[red]Workflow '`, `[cyan]Running: ` |
| `🟡 Medium \(0\.5\-0\.8\)` | markdown_reporter.py:27 | MarkdownReporter.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `🟢 High \(≥0\.8\)` | markdown_reporter.py:26 | MarkdownReporter.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `
                <div class="tabs">
 ...` | architecture_dashboard.py:79 | ArchitectureDashboard._gene... | `[red]Workflow '`, `[cyan]Running: ` |
| `
            CREATE TABLE IF NOT EXIS...` | database_manager.py:65 | DatabaseManager._get_rollba... | `[red]Workflow '`, `[cyan]Running: ` |
| `
        Decorator to document mock j...` | mock_justification_checker.py:183 | mock_justified | `[red]Workflow '`, `[cyan]Running: ` |
| `
    Check if a file has a problemati...` | prevent_numbered_files.py:55 | check_file_naming | `[red]Workflow '`, `[cyan]Running: ` |
| `
    Clean up files in a directory ba...` | cleanup_generated_files.py:93 | cleanup_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `
    Determine if a SPEC file is lega...` | update_spec_timestamps.py:79 | is_legacy_spec | `[red]Workflow '`, `[cyan]Running: ` |
| `
    Main function to check files\.
 ...` | prevent_numbered_files.py:117 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
    Scan directory for files that wo...` | cleanup_generated_files.py:154 | scan_for_cleanup | `[red]Workflow '`, `[cyan]Running: ` |
| `
    Sync OpenAPI specification to Re...` | generate_openapi_spec.py:215 | sync_to_readme | `[red]Workflow '`, `[cyan]Running: ` |
| `
Advanced E2E Test Import Fixer

Busi...` | fix_e2e_imports.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
async def generate\_stream\(message:...` | fix_missing_functions.py:30 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
async def get\_async\_db\(\):
    ""...` | fast_import_checker.py:218 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `
class StartupCheckResult:
    """Res...` | fast_import_checker.py:125 | fix_known_import_issues | `[red]Workflow '`, `[cyan]Running: ` |
| `
Comprehensive E2E Import Fixer
Fixes...` | comprehensive_e2e_import_fixer.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Comprehensive E2E Test Fixer Script
...` | fix_e2e_tests_comprehensive.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Comprehensive Import Scanner and Fix...` | comprehensive_import_scanner.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Demo script for Real LLM Testing Con...` | demo_real_llm_testing.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
E2E Test Import Verification and Fix...` | check_e2e_imports.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Elite Enforcement Script for Netra A...` | enforce_limits.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Examples:
  python scripts/team\_upd...` | team_updates.py:21 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
Examples:
  Recommended deployment:
...` | deploy_to_gcp.py:767 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `
File size and naming compliance chec...` | file_checker.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Fix E2E Test ConnectionManager Impor...` | fix_e2e_connection_manager_imports.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Function complexity compliance check...` | function_checker.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
GCP Deployment Script for Netra Apex...` | deploy_to_gcp.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Generate OpenAPI/Swagger specificati...` | generate_openapi_spec.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Pre\-commit hook script to prevent n...` | prevent_numbered_files.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Simple script to fix the specific im...` | fix_simple_import_errors.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Single Source of Truth \(SSOT\) comp...` | ssot_checker.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
Unified Import Management System for...` | import_management.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `
🔴 BOUNDARY ENFORCER 🔴
Modular Ultra ...` | boundary_enforcer.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `  
\*\*Status:\*\* Post\-Fix Review
\...` | websocket_coherence_review.py:152 | _build_report_header | `[red]Workflow '`, `[cyan]Running: ` |
| `    def get\_current\_commit\(self\) ...` | archiver_generator.py:44 | ArchiverGenerator._get_comm... | `[red]Workflow '`, `[cyan]Running: ` |
| `    def get\_modified\_files\(self\) ...` | validator_generator.py:50 | ValidatorGenerator._get_mod... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \- Production stability improving
\-...` | generate_wip_report.py:247 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| ` tests
\- \*\*Overall Trajectory:\*\*...` | generate_wip_report.py:232 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| ` \| \*\*Methodology:\*\* \[SPEC/maste...` | generate_wip_report.py:217 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""General test fixtures\."""

import...` | fix_e2e_imports.py:347 | E2EImportFixer.create_missi... | `[red]Workflow '`, `[cyan]Running: ` |
| `"""Test factories for unit tests\."""...` | fix_remaining_e2e_imports.py:157 | create_missing_helpers | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\!/bin/bash
\# AI Agent Metadata Va...` | git_hooks_manager.py:59 | GitHooksManager._get_pre_co... | `[red]Workflow '`, `[cyan]Running: ` |
| `\#\!/bin/bash
\# AI Agent Metadata Va...` | hooks_manager.py:28 | GitHooksManager._get_pre_co... | `[red]Workflow '`, `[cyan]Running: ` |
| `% goal

\#\# Configuration
To enable ...` | report_generator.py:82 | ReportGenerator._generate_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `\)

The Netra Apex AI Optimization Pl...` | generate_wip_report.py:225 | WIPReportGenerator._generat... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*For questions or improvements, see ...` | markdown_reporter.py:397 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `\*For the complete system overview, s...` | markdown_reporter.py:540 | MarkdownReporter._generate_... | `[red]Workflow '`, `[cyan]Running: ` |
| `: Generate with: python \-c "from cry...` | create_staging_secrets.py:160 | _provide_manual_instructions | `[red]Workflow '`, `[cyan]Running: ` |
| `\[bold cyan\]ACT Local Testing Setup\...` | setup_act.py:156 | main | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.servic...` | fix_comprehensive_imports.py:62 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `^from netra\_backend\\\.app\\\.servic...` | fix_comprehensive_imports.py:79 | ComprehensiveImportFixerV2.... | `[red]Workflow '`, `[cyan]Running: ` |
| `class MetadataArchiver:
    """Archiv...` | archiver_generator.py:36 | ArchiverGenerator._get_clas... | `[red]Workflow '`, `[cyan]Running: ` |
| `def \_create\_email\_config\(\) \-> N...` | fix_monitoring_violations.py:81 | fix_alert_notifications | `[red]Workflow '`, `[cyan]Running: ` |
| `Deploy all services to GCP\.
        ...` | deploy_to_gcp.py:637 | GCPDeployer.deploy_all | `[red]Workflow '`, `[cyan]Running: ` |
| `Find malformed import patterns in con...` | fix_malformed_imports.py:60 | MalformedImportFixer.find_m... | `[red]Workflow '`, `[cyan]Running: ` |
| `Fix embedded setup\_test\_path patter...` | fix_embedded_setup_imports.py:54 | EmbeddedSetupImportFixer.fi... | `[red]Workflow '`, `[cyan]Running: ` |
| `Fix malformed import patterns in cont...` | fix_malformed_imports.py:114 | MalformedImportFixer.fix_ma... | `[red]Workflow '`, `[cyan]Running: ` |
| `Fix supervisor agent import issues\.
...` | fix_supervisor_imports.py:2 | module | `[red]Workflow '`, `[cyan]Running: ` |
| `import sys
import os
from pathlib imp...` | fix_e2e_imports.py:193 | E2EImportFixer.get_path_setup | `[red]Workflow '`, `[cyan]Running: ` |
| `Initialize scanner for a specific fil...` | scanner_core.py:37 | StringLiteralScanner.__init__ | `[red]Workflow '`, `[cyan]Running: ` |
| `Initialize the enhanced indexer\.
   ...` | scan_string_literals_enhanced.py:62 | EnhancedStringLiteralIndexe... | `[red]Workflow '`, `[cyan]Running: ` |
| `Recursively scan directory for string...` | scanner_core.py:137 | scan_directory | `[red]Workflow '`, `[cyan]Running: ` |
| `Scan a single Python file for string ...` | scanner_core.py:86 | scan_file | `[red]Workflow '`, `[cyan]Running: ` |

### Usage Examples

- **scripts\function_complexity_analyzer.py:272** - `FunctionComplexityAnalyzer._format_function_analysis`
- **scripts\dev_launcher_core.py:263** - `DevLauncher._wait_for_processes`
- **scripts\enhance_dev_launcher_boundaries.py:153** - `enhance_launcher_main`

---

## Subcategory: template {subcategory-template}

**Count**: 149 literals

### 🟢 High (≥0.8) (27 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| ` \-\- \{file\_path\}` | metadata_header_generator.py:127 | MetadataHeaderGenerator.gen... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(levelname\)s: %\(message\)s` | cleanup_duplicate_tests.py:28 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `:\\d\{1,5\}$` | categorizer_enhanced.py:406 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `<TestProviders>\{children\}</TestProv...` | fix_frontend_tests.py:78 | _fix_wrapper_pattern_4 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `<WebSocketProvider>\\\{children\\\}</...` | fix_frontend_tests.py:77 | _fix_wrapper_pattern_4 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `=\\s\*\["'\]\[A\-Za\-z0\-9\]\{20,\}\[...` | code_review_analysis.py:190 | CodeReviewAnalysis._check_h... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `=\\s\*\["'\]\[A\-Za\-z0\-9\]\{20,\}\[...` | code_review_analysis.py:191 | CodeReviewAnalysis._check_h... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `=\\s\*\["'\]\[A\-Za\-z0\-9\]\{20,\}\[...` | security_checker.py:36 | SecurityChecker._get_secret... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `=\\s\*\["'\]\[A\-Za\-z0\-9\]\{20,\}\[...` | security_checker.py:37 | SecurityChecker._get_secret... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\[progress\.description\]\{task\.desc...` | setup_act.py:163 | main | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\\d\{4\}\-\\d\{2\}\-\\d\{2\}` | categorizer_enhanced.py:224 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\\\{\[^\}\]\+\\\}` | categorizer_enhanced.py:213 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^\#\{1,6\}\\s` | categorizer_enhanced.py:206 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^\[a\-f0\-9\]\{8,\}$` | categorizer_enhanced.py:395 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^\[A\-Z\]\[a\-z\]\.\{20,\}$` | categorizer_enhanced.py:186 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^\\d\{1,3\}\\\.\\d\{1,3\}\\\.\\d\{1,3...` | categorizer_enhanced.py:403 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^\\s\*\[A\-Z\]\[a\-z\]\.\{30,\}\\\.$` | categorizer_enhanced.py:199 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^\\\{\.\*\\\}$` | categorizer_enhanced.py:220 | EnhancedStringLiteralCatego... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^from\\s\+\\\.\{1,3\}\[a\-zA\-Z\_\]` | comprehensive_import_scanner.py:215 | ComprehensiveImportScanner.... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `^from\\s\+\\\.\{4,\}` | comprehensive_import_scanner.py:201 | ComprehensiveImportScanner.... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `AIza\[0\-9A\-Za\-z\-\_\]\{35\}` | environment_validator_core.py:62 | EnvironmentValidatorCore._d... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `COMPONENT\_MAPPINGS\\s\*=\\s\*\\\{\[^...` | align_test_imports.py:281 | TestImportAligner.update_co... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `fetch\\s\*\\\(\[^,\]\+,\\s\*\\\{\[^\}...` | status_integration_analyzer.py:131 | IntegrationAnalyzer._extrac... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `import\\s\*\\\{\\s\*\(\[^\}\]\+\)\\s\...` | deduplicate_types.py:175 | TypeDeduplicator.find_types... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `return\\s\*\\\{\\s\*\["\\'\]status\["...` | remove_test_stubs.py:58 | TestStubDetector.__init__ | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `return\\s\*\\\{\\s\*\["\\'\]test\["\\...` | remove_test_stubs.py:57 | TestStubDetector.__init__ | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `TEST\_DIRECTORIES\\s\*=\\s\*\\\{\[^\}...` | align_test_imports.py:247 | TestImportAligner.update_te... | `(\{/\* \n  Agen...`, `COMPONENT_MAPP... |

### 🔴 Low (<0.5) (122 literals)

| Literal | Files | Context | Related |
|---------|-------|---------|---------|
| `
        print\(f"  • Boundary monito...` | enhance_dev_launcher_boundaries.py:162 | enhance_launcher_main | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | check_e2e_imports.py:29 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | comprehensive_e2e_import_fixer.py:30 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | fix_all_import_issues.py:20 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | fix_comprehensive_imports.py:19 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | fix_e2e_imports.py:27 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | fix_netra_backend_imports.py:20 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(levelname\)s \- %...` | import_management.py:30 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `%\(asctime\)s \- %\(name\)s \- %\(lev...` | unified_import_manager.py:79 | UnifiedImportManager.__init__ | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\(\\\{/\\\* \\n  Agent Modification T...` | agent_tracking_helper.py:184 | AgentTrackingHelper._extrac... | `TEST_DIRECTORIE...`, `COMPONENT_MAPP... |
| `ACT: \\$\\\{\\\{ env\\\.ACT \\\|\\\| ...` | fix_workflow_env_issues.py:13 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `ACT\_DETECTED: \\$\\\{\\\{ env\\\.ACT...` | fix_workflow_env_issues.py:15 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `ACT\_DRY\_RUN: \\$\\\{\\\{ env\\\.ACT...` | fix_workflow_env_issues.py:16 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `ACT\_MOCK\_GCP: \\$\\\{\\\{ env\\\.AC...` | fix_workflow_env_issues.py:17 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `ACT\_RUNNER\_NAME: \\$\\\{\\\{ env\\\...` | fix_workflow_env_issues.py:18 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `ACT\_TEST\_MODE: \\$\\\{\\\{ env\\\.A...` | fix_workflow_env_issues.py:19 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `Fix Pattern 1: wrapper = \(\{ childre...` | fix_frontend_tests.py:50 | _fix_wrapper_pattern_1 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `import \\\{ WebSocketProvider \\\} fr...` | fix_frontend_tests.py:36 | _replace_websocket_imports | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `IS\_ACT: \\$\\\{\\\{ env\\\.ACT \\\|\...` | fix_workflow_env_issues.py:14 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `LOCAL\_DEPLOY: \\$\\\{\\\{ env\\\.LOC...` | fix_workflow_env_issues.py:20 | fix_env_self_reference | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `print\(f"  • Turbopack: \{'YES' if se...` | enhance_dev_launcher_boundaries.py:158 | enhance_launcher_main | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `return \{"status": "ok"\}` | architecture_scanner_helpers.py:118 | ScannerHelpers.get_stub_pat... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `return \{"test": "data"\}` | architecture_scanner_helpers.py:117 | ScannerHelpers.get_stub_pat... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `runs\-on: \\$\\\{\\\{ env\\\.ACT && \...` | fix_workflow_env_issues.py:31 | fix_runs_on_conditionals | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `timeout\-minutes: \\$\\\{\\\{ env\\\....` | fix_workflow_env_issues.py:43 | fix_timeout_conditionals | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `timeout\-minutes: \\$\\\{\\\{ env\\\....` | fix_workflow_env_issues.py:42 | fix_timeout_conditionals | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `wrapper = \\\(\\\{ children \\\}\[^\)...` | fix_frontend_tests.py:52 | _fix_wrapper_pattern_1 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
            <div class="recommendati...` | architecture_dashboard.py:102 | ArchitectureDashboard._rend... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
  \- Consolidated exists: ` | status_section_renderers.py:102 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
  \- Sample Tools: ` | status_section_renderers.py:120 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
  \- Tool Count: ` | status_section_renderers.py:119 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\#\# Appendix

\#\#\# Files Analyzed...` | status_section_renderers.py:259 | RecommendationsRenderer.bui... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\#\#\# ` | team_updates_formatter.py:93 | HumanFormatter.format_features | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Authentication Enabled: ` | status_section_renderers.py:146 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Callback Configured: ` | status_section_renderers.py:158 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Consider refactoring components w...` | status_section_renderers.py:229 | RecommendationsRenderer.bui... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Frontend Configured: ` | status_section_renderers.py:144 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Frontend Login: ` | status_section_renderers.py:159 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Heartbeat Enabled: ` | status_section_renderers.py:145 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\- Next Scheduled Report: Weekly

\-...` | status_section_renderers.py:269 | RecommendationsRenderer.bui... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
\`\`\`` | markdown_reporter.py:94 | MarkdownReporter._format_co... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
Branch: ` | workflow_introspection.py:275 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
Event: ` | workflow_introspection.py:277 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
Name: ` | workflow_introspection.py:271 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
Report ID: ` | team_updates_formatter.py:47 | HumanFormatter.format_header | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
SHA: ` | workflow_introspection.py:276 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
Time Frame: ` | team_updates_formatter.py:46 | HumanFormatter.format_header | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
URL: ` | workflow_introspection.py:278 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
Workflow: ` | workflow_introspection.py:272 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   Critical: ` | cli.py:114 | DisplayFormatter._display_t... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   Focus: ` | cli.py:77 | DisplayFormatter.print_header | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   High: ` | cli.py:115 | DisplayFormatter._display_t... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   Low: ` | cli.py:117 | DisplayFormatter._display_t... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   Medium: ` | cli.py:116 | DisplayFormatter._display_t... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   Mode: ` | cli.py:75 | DisplayFormatter.print_header | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   Run ID: ` | verify_workflow_status.py:298 | OutputFormatter.display_suc... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `   URL: ` | verify_workflow_status.py:299 | OutputFormatter.display_suc... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  ================================` | metadata_header_generator.py:194 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  ================================` | metadata_header_generator.py:202 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Agent: ` | metadata_header_generator.py:196 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  AI AGENT MODIFICATION METADATA` | metadata_header_generator.py:193 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Change: ` | metadata_header_generator.py:199 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Context: ` | metadata_header_generator.py:197 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Git: ` | metadata_header_generator.py:198 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Review: ` | metadata_header_generator.py:201 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Session: ` | metadata_header_generator.py:200 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `  Timestamp: ` | metadata_header_generator.py:195 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` agents found
` | status_section_renderers.py:111 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` critical issues found in the codebas...` | status_section_renderers.py:236 | RecommendationsRenderer.bui... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` files
\- Frontend: Check frontend/co...` | status_section_renderers.py:263 | RecommendationsRenderer.bui... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` TB` | cleanup_generated_files.py:151 | format_bytes | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` test files

\#\#\# Report Metadata
\...` | status_section_renderers.py:265 | RecommendationsRenderer.bui... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` version active
  \- Legacy exists: ` | status_section_renderers.py:101 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Risk: ` | metadata_header_generator.py:160 | MetadataHeaderGenerator.for... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Risk: ` | metadata_header_generator.py:199 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Scope: ` | metadata_header_generator.py:160 | MetadataHeaderGenerator.for... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Scope: ` | metadata_header_generator.py:199 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Score: ` | metadata_header_generator.py:162 | MetadataHeaderGenerator.for... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Score: ` | metadata_header_generator.py:201 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Seq: ` | metadata_header_generator.py:161 | MetadataHeaderGenerator.for... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| ` \| Seq: ` | metadata_header_generator.py:200 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `, Error Handling=` | status_section_renderers.py:109 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\- Worst offender: ` | team_updates_formatter.py:164 | HumanFormatter.format_code_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\- Worst offender: ` | team_updates_formatter.py:170 | HumanFormatter.format_code_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\-\->` | metadata_header_generator.py:203 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.2f` | generate_report.py:86 | _format_shard_row | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.2f` | cleanup_generated_files.py:149 | format_bytes | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.2f` | cleanup_generated_files.py:151 | format_bytes | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `: Tools=` | status_section_renderers.py:109 | ComponentDetailsRenderer._f... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `<\!\-\-` | metadata_header_generator.py:192 | MetadataHeaderGenerator._fo... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `</li>` | architecture_dashboard.py:111 | ArchitectureDashboard._rend... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `</ul>
            </div>` | architecture_dashboard.py:105 | ArchitectureDashboard._rend... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `<li>` | architecture_dashboard.py:111 | ArchitectureDashboard._rend... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\`\`\`` | generate_fix.py:224 | AIFixGenerator._add_respons... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\`\`\`` | markdown_reporter.py:94 | MarkdownReporter._format_co... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\`\`\`diff` | generate_fix.py:224 | AIFixGenerator._add_respons... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `Build OAuth info` | status_section_renderers.py:156 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `Build WebSocket info` | status_section_renderers.py:142 | IntegrationRenderer._build_... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `Format report header\.` | team_updates_formatter.py:43 | HumanFormatter.format_header | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `Generated: ` | generate_report.py:16 | _format_header | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `N/A` | workflow_introspection.py:275 | OutputFormatter.display_run... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `No commits in period` | team_updates_formatter.py:82 | HumanFormatter.format_execu... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `No description` | generate_security_report.py:127 | _format_vulnerability_list | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `REVIEW SUMMARY` | cli.py:84 | DisplayFormatter.display_su... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `s \|` | generate_report.py:86 | _format_shard_row | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\| Shard \| Tests \| Passed \| Failed...` | generate_report.py:71 | _format_shard_results | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\|\-\-\-\-\-\-\-\|\-\-\-\-\-\-\-\|\-\...` | generate_report.py:71 | _format_shard_results | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `⚠️` | team_updates_formatter.py:14 | HumanFormatter.__init__ | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `⚠️` | team_updates_formatter.py:18 | HumanFormatter.__init__ | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
    // Mock fetch for config
    glo...` | fix_frontend_tests.py:94 | _insert_fetch_mock | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `
async def process\_message\(message:...` | fix_missing_functions.py:17 | module | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `"""Agent test fixtures\."""

import p...` | fix_e2e_imports.py:324 | E2EImportFixer.create_missi... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\* \{ margin: 0; padding: 0; box\-siz...` | architecture_dashboard_html.py:140 | DashboardHTMLComponents._ge... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.charts\-section \{ margin: 30px 0; ...` | architecture_dashboard_html.py:155 | DashboardHTMLComponents._ge... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.dashboard \{ max\-width: 1400px; ma...` | architecture_dashboard_html.py:145 | DashboardHTMLComponents._ge... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.recommendations \{ background: \#e7...` | architecture_dashboard_html.py:165 | DashboardHTMLComponents._ge... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\.tab\-container \{ margin: 20px 0; \...` | architecture_dashboard_html.py:170 | DashboardHTMLComponents._ge... | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `const wrapper = \\\(\\\{ children \\\...` | fix_frontend_tests.py:60 | _fix_wrapper_pattern_2 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `def \_create\_email\_config\(\) \-> N...` | fix_monitoring_violations.py:91 | fix_alert_notifications | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `Fix Pattern 2: const wrapper = \(\{ c...` | fix_frontend_tests.py:58 | _fix_wrapper_pattern_2 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `wrapper = \\\(\\\{ children \\\}\\\) ...` | fix_frontend_tests.py:68 | _fix_wrapper_pattern_3 | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |
| `\{
    "python\.linting\.enabled": tr...` | simple_enhance_boundaries.py:21 | main | `(\{/\* \n  Agen...`, `TEST_DIRECTORI... |

### Usage Examples

- **scripts\metadata_header_generator.py:127** - `MetadataHeaderGenerator.generate_metadata`
- **scripts\cleanup_duplicate_tests.py:28** - `module`
- **scripts\string_literals\categorizer_enhanced.py:406** - `EnhancedStringLiteralCategorizer._smart_fallback_categorization`

---

## 🔗 Navigation

- 🏠 [Back to Main Index](../string_literals_index.md)
- 📂 [Browse Other Categories](./)

---

*This is the detailed documentation for the `formats` category.*
*For the complete system overview, see the [Main String Literals Index](../string_literals_index.md).*