# Netra Apex Tooling Index
## Violation Detection, Code Quality, and Import Management Tools

Last Updated: 2025-08-21

This index provides a comprehensive overview of all quality checking, violation detection, and import management tools in the Netra Apex codebase.

---

## 🚨 Primary Enforcement Tools

### Architecture Compliance Checker
- **Script**: `scripts/check_architecture_compliance.py`
- **Purpose**: Main entry point for enforcing CLAUDE.md architectural rules
- **Key Features**:
  - 450-line file limit enforcement
  - 25-line function limit enforcement
  - Type safety validation
  - Test stub detection
  - Smart violation limiting
- **Usage**: `python scripts/check_architecture_compliance.py [--path PATH] [--show-all]`
- **Module Components**:
  - `scripts/compliance/` - Modular compliance checking components
  - `scripts/compliance/orchestrator.py` - Orchestrates all compliance checks
  - `scripts/compliance/core.py` - Core types and interfaces

### Boundary Enforcer
- **Script**: `scripts/boundary_enforcer.py`
- **Purpose**: Comprehensive system boundary enforcement with modular design
- **Components**:
  - `boundary_enforcer_file_checks.py` - File size boundary validation
  - `boundary_enforcer_function_checks.py` - Function complexity validation
  - `boundary_enforcer_system_checks.py` - System-wide metrics
  - `boundary_enforcer_type_checks.py` - Type safety and duplication checks
  - `boundary_enforcer_report_generator.py` - Report generation
- **Usage**: `python scripts/boundary_enforcer.py [--strict] [--output FILE]`

### Unified Test Runner
- **Script**: `test_framework/test_runner.py`
- **Purpose**: Primary test execution framework with multi-environment support
- **Key Features**:
  - Integration, unit, and E2E test support
  - Real LLM vs mock testing modes
  - Multi-environment validation (local, dev, staging)
  - Coverage reporting
  - Bad test detection
- **Usage**: `python unified_test_runner.py --level integration --no-coverage --fast-fail`

---

## 📦 Import Management Tools

### Unified Import Manager
- **Script**: `scripts/unified_import_manager.py`
- **Purpose**: Centralized interface for all import-related operations
- **Modes**:
  - `check` - Check import compliance only
  - `fix` - Fix issues automatically
  - `report` - Generate detailed report
  - `all` - Check, fix, and report
  - `precommit` - Pre-commit hook mode
- **Usage**: `python scripts/unified_import_manager.py [check|fix|report|all|precommit]`

### Import Checking Scripts
- **`scripts/check_netra_backend_imports.py`** - Validates netra_backend import patterns
- **`scripts/check_schema_imports.py`** - Checks schema import compliance
- **`scripts/check_test_import_order.py`** - Validates test file import ordering
- **`scripts/align_test_imports.py`** - Aligns test imports with standards
- **`scripts/fix_all_import_issues.py`** - Comprehensive import issue fixer
- **`scripts/fix_schema_imports.py`** - Fixes schema-specific import issues
- **`scripts/fix_netra_backend_imports.py`** - Fixes backend import violations
- **`scripts/fix_e2e_connection_manager_imports.py`** - Fixes E2E test imports

### Circular Import Detection
- **Script**: `test_framework/circular_import_detector.py`
- **Purpose**: Detects and reports circular import dependencies
- **Usage**: Automatically run during test framework execution

---

## 🔍 Violation Detection Tools

### Function Complexity Analysis
- **Script**: `scripts/function_complexity_analyzer.py`
- **Purpose**: Analyzes function complexity and cyclomatic complexity
- **Components**:
  - `function_complexity_cli.py` - CLI interface
  - `function_complexity_linter.py` - Linting integration
  - `function_complexity_types.py` - Type definitions
- **Usage**: `python scripts/function_complexity_analyzer.py --path PATH`

### Violation Identification
- **Script**: `scripts/identify_violations.py`
- **Purpose**: Scans codebase for function length violations
- **Categories**:
  - Severe violations (>20 lines)
  - Moderate violations (9-20 lines)
- **Usage**: `python scripts/identify_violations.py`

### Extract Violations Scripts
- **`scripts/extract_violations.py`** - Extracts all violations from codebase
- **`scripts/extract_function_violations.py`** - Focuses on function-level violations

### Auto-Fix Violation Scripts
- **`scripts/auto_fix_test_violations.py`** - Automatically fixes test violations
- **`scripts/fix_monitoring_violations.py`** - Fixes monitoring-related violations
- **`scripts/fix_all_test_issues.py`** - Comprehensive test issue fixer
- **`scripts/auto_fix_test_sizes.py`** - Automatically splits large test files

---

## 🧪 Test Quality Tools

### Test Compliance Checking
- **Script**: `scripts/check_test_compliance.py`
- **Purpose**: Validates test files against compliance standards
- **Checks**:
  - Test file size limits
  - Test function complexity
  - Mock usage justification
  - Real test requirements

### Test Validation Framework
- **Directory**: `scripts/compliance/`
- **Key Components**:
  - `test_size_validator.py` - Enforces test file size limits
  - `test_limits_checker.py` - Checks test complexity limits
  - `real_test_validator.py` - Validates real vs mock test balance
  - `fake_test_scanner.py` - Detects fake/stub tests
  - `stub_checker.py` - Identifies test stubs
  - `mock_justification_checker.py` - Validates mock usage

### Test Stub Management
- **`scripts/remove_test_stubs.py`** - Removes test stubs from production
- **`scripts/ci/check_test_stubs.py`** - CI/CD stub detection

### Test Discovery and Reporting
- **`test_framework/test_discovery.py`** - Discovers and categorizes tests
- **`test_framework/bad_test_detector.py`** - Identifies problematic tests
- **`test_framework/fake_test_detector.py`** - Detects fake test implementations
- **`test_framework/bad_test_reporter.py`** - Reports on bad test patterns

---

## 📊 Code Quality Analysis

### Architecture Health Monitoring
- **Script**: `scripts/architecture_health.py`
- **Purpose**: Comprehensive architecture health assessment
- **Components**:
  - `architecture_scanner.py` - Scans codebase structure
  - `architecture_metrics.py` - Calculates architecture metrics
  - `architecture_reporter.py` - Generates health reports
  - `architecture_dashboard.py` - Creates visual dashboard
- **Usage**: `python scripts/architecture_health.py --generate-report`

### Code Review Tools
- **Directory**: `scripts/review/`
- **Components**:
  - `orchestrator.py` - Orchestrates code review processes
  - `spec_checker.py` - Validates against specifications
  - `smoke_tester.py` - Runs smoke tests
- **Related Scripts**:
  - `code_review_analyzer.py` - Analyzes code review patterns
  - `code_review_ai_detector.py` - Detects AI-generated code patterns
  - `code_review_reporter.py` - Generates review reports

### File Size Management
- **`scripts/find_large_app_files.py`** - Finds files exceeding size limits
- **`scripts/split_large_files.py`** - Automatically splits large files
- **`scripts/auto_split_files.py`** - Intelligent file splitting
- **`scripts/find_long_functions.py`** - Identifies overly long functions
- **`scripts/check_function_lengths.py`** - Validates function length compliance

### Function Decomposition
- **`scripts/decompose_functions.py`** - Manual function decomposition
- **`scripts/auto_decompose_functions.py`** - Automatic function decomposition
- **`scripts/enhance_dev_launcher_boundaries.py`** - Enhances launcher boundaries

---

## 🔧 Type Safety and Deduplication

### Type Safety Validation
- **`scripts/validate_type_deduplication.py`** - Validates type deduplication
- **`scripts/deduplicate_types.py`** - Removes duplicate type definitions
- **`scripts/compliance/type_checker.py`** - Core type checking logic
- **`scripts/compliance/ssot_checker.py`** - Single Source of Truth validation

### String Literals Management
- **`scripts/scan_string_literals.py`** - Scans and indexes all string literals
- **`scripts/query_string_literals.py`** - Query and validate string literals
- **Purpose**: Prevents LLM hallucination of platform constants
- **Categories**: configuration, paths, identifiers, database, events, metrics, environment, states

---

## 🔄 Pre-commit Hooks

### Configuration
- **File**: `.pre-commit-config.yaml`
- **Key Hooks**:
  1. `architecture-compliance` - Enforces architecture limits
  2. `file-size-limit` - 300-line file limit
  3. `function-complexity-limit` - 8-line function limit
  4. `type-safety-check` - Type safety and duplicate prevention
  5. `test-stub-prevention` - Prevents production stubs
  6. `test-file-size-enforcement` - Test file size limits
  7. `prevent-numbered-files` - Enforces semantic naming
  8. `unified-import-compliance` - Import standards
  9. `import-path-validation` - Import pattern validation

### Hook Management
- **`scripts/manage_precommit.py`** - Manages pre-commit configuration
- **`scripts/setup_hooks.bat`** - Windows hook setup script

---

## 📈 Reporting and Status Tools

### WIP Status Reporting
- **Script**: `scripts/generate_wip_report.py`
- **Purpose**: Generates work-in-progress status reports
- **Output**: `MASTER_WIP_STATUS.md`
- **Tracks**:
  - Overall compliance score
  - Per-service alignment scores
  - Critical violations
  - Action items by priority

### Compliance Reporting
- **`scripts/compliance/reporter.py`** - Main compliance reporter
- **`scripts/compliance/reporter_stats.py`** - Statistical analysis
- **`scripts/compliance/reporter_utils.py`** - Reporting utilities
- **`scripts/compliance/test_violations_reporter.py`** - Test violation reports

### Team Updates
- **`scripts/team_updates_orchestrator.py`** - Orchestrates team updates
- **`scripts/team_updates_formatter.py`** - Formats team update reports
- **`scripts/team_updates_compliance_analyzer.py`** - Analyzes compliance trends

---

## 🚀 CI/CD Integration

### GitHub Actions Integration
- **Directory**: `scripts/ci/`
- **Components**:
  - `check_test_stubs.py` - Test stub checking for CI
  - `generate_fix.py` - Generates automated fixes
  - `generate_security_report.py` - Security compliance reports

### Workflow Management
- **`scripts/manage_workflows.py`** - Manages GitHub workflows
- **`scripts/workflow_validator.py`** - Validates workflow configuration
- **`scripts/validate_workflow_config.py`** - Configuration validation

---

## 🛠️ Development Environment Tools

### Service Independence
- **`scripts/validate_service_independence.py`** - Validates microservice independence
- **`SPEC/independent_services.xml`** - Service independence specification

### Environment Validation
- **`scripts/environment_validator.py`** - Main environment validator
- **Components**:
  - `environment_validator_core.py` - Core validation logic
  - `environment_validator_database.py` - Database checks
  - `environment_validator_dependencies.py` - Dependency validation
  - `environment_validator_ports.py` - Port availability checks

### Development Launcher
- **`scripts/dev_launcher.py`** - Main development launcher
- **`scripts/simple_launcher.py`** - Simplified launcher
- **Components**:
  - `dev_launcher_config.py` - Configuration management
  - `dev_launcher_core.py` - Core launcher logic
  - `dev_launcher_processes.py` - Process management
  - `dev_launcher_monitoring.py` - Service monitoring

---

## 📝 Quick Reference Commands

### Daily Development
```bash
# Check architecture compliance
python scripts/check_architecture_compliance.py

# Run unified test suite
python unified_test_runner.py --level integration --no-coverage --fast-fail

# Check and fix imports
python scripts/unified_import_manager.py all

# Generate WIP status report
python scripts/generate_wip_report.py
```

### Before Commits
```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Check specific violations
python scripts/identify_violations.py

# Validate test compliance
python scripts/check_test_compliance.py
```

### Code Quality Analysis
```bash
# Full architecture health check
python scripts/architecture_health.py --generate-report

# Function complexity analysis
python scripts/function_complexity_analyzer.py --path app/

# Find large files
python scripts/find_large_app_files.py
```

### String Literal Management
```bash
# Scan and update string literals index
python scripts/scan_string_literals.py

# Validate a string literal
python scripts/query_string_literals.py validate "your_string"
```

---

## 🎯 Key Compliance Targets

| Metric | Limit | Enforcer |
|--------|-------|----------|
| File Lines | 450 (prod), 300 (strict) | `check_architecture_compliance.py` |
| Function Lines | 25 (prod), 8 (strict) | `function_complexity_analyzer.py` |
| Test File Lines | 450 | `test_size_validator.py` |
| Cyclomatic Complexity | 10 | `function_complexity_linter.py` |
| Import Depth | 3 levels | `unified_import_manager.py` |
| Mock Usage | Justified only | `mock_justification_checker.py` |

---

## 📚 Related Specifications

- `SPEC/type_safety.xml` - Type safety requirements
- `SPEC/conventions.xml` - Coding conventions
- `SPEC/testing.xml` - Testing standards
- `SPEC/no_test_stubs.xml` - Test stub prevention
- `SPEC/anti_regression.xml` - Regression prevention
- `SPEC/code_changes.xml` - Code change checklist
- `SPEC/string_literals_index.xml` - String literal management

---

## 🔄 Continuous Improvement

This tooling suite is continuously evolving. Key areas of focus:
1. **Automation** - Increasing auto-fix capabilities
2. **Performance** - Optimizing scan and check times
3. **Integration** - Deeper IDE and CI/CD integration
4. **Intelligence** - Smarter violation detection and resolution
5. **Reporting** - More actionable insights and trends

For tool enhancement requests or issues, consult `SPEC/ai_factory_patterns.xml` for development patterns.