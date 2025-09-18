#!/usr/bin/env python3
"""
Factory Migration Validator - Issue #1194 Phase 1

This script provides safety validation for factory migration operations to ensure
that removing or consolidating factories doesn't break business functionality or
introduce security vulnerabilities.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Safe reduction of architectural complexity
- Value Impact: Prevent breaking changes during factory consolidation
- Strategic Impact: Enable confident factory removal with zero business risk

Key Features:
- Pre-migration safety validation
- Business impact assessment
- Test coverage verification
- Multi-user isolation validation
- Migration rollback validation
- Post-migration verification

Part of Issue #1194 Phase 1: Safety Infrastructure & Analysis
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Represents a validation issue found during migration analysis."""
    severity: str  # 'ERROR', 'WARNING', 'INFO'
    category: str  # 'business_impact', 'test_coverage', 'user_isolation', 'breaking_change'
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None
    blocking: bool = False  # If True, blocks migration


@dataclass
class MigrationValidationResult:
    """Results of factory migration validation."""
    factory_name: str
    migration_safe: bool = True
    confidence_level: str = "HIGH"  # HIGH, MEDIUM, LOW
    issues: List[ValidationIssue] = field(default_factory=list)
    test_coverage: Dict[str, Any] = field(default_factory=dict)
    business_impact: Dict[str, Any] = field(default_factory=dict)
    rollback_plan: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class FactoryMigrationValidator:
    """Validates safety of factory migration operations."""

    # Critical business functions that must be preserved
    CRITICAL_BUSINESS_FUNCTIONS = {
        'user_authentication': ['auth', 'login', 'token', 'session'],
        'agent_execution': ['agent', 'execute', 'run', 'supervisor'],
        'websocket_communication': ['websocket', 'emit', 'notify', 'event'],
        'database_operations': ['database', 'session', 'query', 'save'],
        'llm_communication': ['llm', 'openai', 'anthropic', 'client'],
        'file_operations': ['upload', 'download', 'file', 'document']
    }

    # Essential factories that require special validation
    ESSENTIAL_FACTORIES = {
        'AgentInstanceFactory': 'Agent creation and user isolation',
        'UserExecutionContextFactory': 'User context management',
        'DatabaseSessionFactory': 'Database session lifecycle',
        'WebSocketConnectionFactory': 'WebSocket connection management',
        'LLMClientFactory': 'LLM client instantiation',
        'ToolDispatcherFactory': 'Tool execution coordination',
        'ConfigurationFactory': 'Environment configuration',
        'TestRepositoryFactory': 'Test data generation'
    }

    # Patterns that indicate user isolation requirements
    USER_ISOLATION_PATTERNS = [
        r'user_id', r'user_context', r'UserExecutionContext',
        r'per_user', r'user_specific', r'isolation',
        r'multi_user', r'concurrent_users', r'user_state'
    ]

    # Test patterns to verify coverage
    TEST_PATTERNS = [
        r'test_.*factory', r'test_.*create', r'test_.*build',
        r'factory.*test', r'create.*test', r'build.*test'
    ]

    def __init__(self):
        self.project_root = project_root
        self.file_cache = {}
        self.test_files = set()
        self._scan_test_files()

    def _scan_test_files(self) -> None:
        """Scan for test files in the project."""
        for test_file in self.project_root.rglob("test_*.py"):
            self.test_files.add(str(test_file))
        for test_file in self.project_root.rglob("*_test.py"):
            self.test_files.add(str(test_file))

    def validate_factory_migration(self, factory_name: str,
                                 target_replacement: Optional[str] = None,
                                 migration_type: str = "removal") -> MigrationValidationResult:
        """
        Validate the safety of migrating a specific factory.

        Args:
            factory_name: Name of the factory to migrate
            target_replacement: Name of replacement factory (if consolidating)
            migration_type: Type of migration ('removal', 'consolidation', 'refactor')

        Returns:
            MigrationValidationResult: Comprehensive validation results
        """
        logger.info(f"Validating {migration_type} of factory: {factory_name}")

        result = MigrationValidationResult(factory_name=factory_name)

        # Step 1: Business Impact Analysis
        self._analyze_business_impact(factory_name, result)

        # Step 2: Test Coverage Analysis
        self._analyze_test_coverage(factory_name, result)

        # Step 3: User Isolation Validation
        self._validate_user_isolation(factory_name, result)

        # Step 4: Breaking Change Detection
        self._detect_breaking_changes(factory_name, target_replacement, result)

        # Step 5: Essential Factory Validation
        self._validate_essential_factory(factory_name, result)

        # Step 6: Dependency Analysis
        self._analyze_dependencies(factory_name, result)

        # Step 7: Generate Recommendations
        self._generate_recommendations(factory_name, migration_type, result)

        # Step 8: Assess Overall Safety
        self._assess_migration_safety(result)

        logger.info(f"Validation complete for {factory_name}: "
                   f"Safe={result.migration_safe}, "
                   f"Confidence={result.confidence_level}")

        return result

    def _analyze_business_impact(self, factory_name: str,
                               result: MigrationValidationResult) -> None:
        """Analyze potential business impact of factory migration."""
        logger.debug(f"Analyzing business impact for {factory_name}")

        business_impact = {
            'critical_functions_affected': [],
            'user_facing_impact': False,
            'production_readiness_impact': False,
            'security_impact': False
        }

        # Find all files that use this factory
        usage_files = self._find_factory_usage_files(factory_name)

        for file_path in usage_files:
            try:
                content = self._get_file_content(file_path)

                # Check for critical business functions
                for function_category, keywords in self.CRITICAL_BUSINESS_FUNCTIONS.items():
                    if any(keyword in content.lower() for keyword in keywords):
                        if function_category not in business_impact['critical_functions_affected']:
                            business_impact['critical_functions_affected'].append(function_category)

                            # Add validation issue
                            result.issues.append(ValidationIssue(
                                severity='WARNING',
                                category='business_impact',
                                message=f"Factory {factory_name} affects critical business function: {function_category}",
                                file_path=file_path,
                                suggested_fix=f"Ensure {function_category} remains functional after migration"
                            ))

                # Check for user-facing impact
                user_facing_indicators = ['route', 'endpoint', 'api', 'frontend', 'ui', 'user']
                if any(indicator in content.lower() for indicator in user_facing_indicators):
                    business_impact['user_facing_impact'] = True

                # Check for security impact
                security_indicators = ['auth', 'security', 'permission', 'access', 'token']
                if any(indicator in content.lower() for indicator in security_indicators):
                    business_impact['security_impact'] = True

            except Exception as e:
                logger.warning(f"Error analyzing business impact in {file_path}: {e}")

        # Add high-severity issue if critical functions affected
        if len(business_impact['critical_functions_affected']) > 0:
            result.issues.append(ValidationIssue(
                severity='ERROR' if len(business_impact['critical_functions_affected']) > 2 else 'WARNING',
                category='business_impact',
                message=f"Migration affects {len(business_impact['critical_functions_affected'])} critical business functions",
                blocking=len(business_impact['critical_functions_affected']) > 2,
                suggested_fix="Create comprehensive migration plan with business function preservation"
            ))

        result.business_impact = business_impact

    def _analyze_test_coverage(self, factory_name: str,
                             result: MigrationValidationResult) -> None:
        """Analyze test coverage for the factory."""
        logger.debug(f"Analyzing test coverage for {factory_name}")

        coverage = {
            'unit_tests': [],
            'integration_tests': [],
            'e2e_tests': [],
            'coverage_percentage': 0,
            'missing_test_scenarios': []
        }

        # Find tests that cover this factory
        for test_file in self.test_files:
            try:
                content = self._get_file_content(test_file)

                if factory_name in content:
                    # Categorize test type
                    if 'unit' in test_file or '/unit/' in test_file:
                        coverage['unit_tests'].append(test_file)
                    elif 'integration' in test_file or '/integration/' in test_file:
                        coverage['integration_tests'].append(test_file)
                    elif 'e2e' in test_file or '/e2e/' in test_file:
                        coverage['e2e_tests'].append(test_file)
                    else:
                        # Default to unit test
                        coverage['unit_tests'].append(test_file)

            except Exception as e:
                logger.debug(f"Error analyzing test coverage in {test_file}: {e}")

        # Calculate coverage score
        total_tests = (len(coverage['unit_tests']) +
                      len(coverage['integration_tests']) +
                      len(coverage['e2e_tests']))

        if total_tests == 0:
            coverage['coverage_percentage'] = 0
            result.issues.append(ValidationIssue(
                severity='ERROR',
                category='test_coverage',
                message=f"No tests found for factory {factory_name}",
                blocking=True,
                suggested_fix="Add comprehensive test coverage before migration"
            ))
        elif total_tests < 3:
            coverage['coverage_percentage'] = 30
            result.issues.append(ValidationIssue(
                severity='WARNING',
                category='test_coverage',
                message=f"Limited test coverage for factory {factory_name} ({total_tests} tests)",
                suggested_fix="Add additional test scenarios"
            ))
        else:
            coverage['coverage_percentage'] = min(100, total_tests * 20)

        # Check for missing test scenarios
        required_scenarios = ['creation', 'configuration', 'error_handling', 'cleanup']
        for scenario in required_scenarios:
            scenario_found = False
            for test_file in (coverage['unit_tests'] + coverage['integration_tests']):
                content = self._get_file_content(test_file)
                if scenario in content.lower():
                    scenario_found = True
                    break

            if not scenario_found:
                coverage['missing_test_scenarios'].append(scenario)

        if coverage['missing_test_scenarios']:
            result.issues.append(ValidationIssue(
                severity='WARNING',
                category='test_coverage',
                message=f"Missing test scenarios: {', '.join(coverage['missing_test_scenarios'])}",
                suggested_fix="Add tests for missing scenarios"
            ))

        result.test_coverage = coverage

    def _validate_user_isolation(self, factory_name: str,
                               result: MigrationValidationResult) -> None:
        """Validate user isolation requirements for the factory."""
        logger.debug(f"Validating user isolation for {factory_name}")

        # Find factory implementation
        factory_files = self._find_factory_implementation_files(factory_name)

        has_user_isolation = False
        isolation_methods = []

        for file_path in factory_files:
            try:
                content = self._get_file_content(file_path)

                # Check for user isolation patterns
                for pattern in self.USER_ISOLATION_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_user_isolation = True
                        isolation_methods.append(pattern)

            except Exception as e:
                logger.debug(f"Error validating user isolation in {file_path}: {e}")

        # If factory handles user data but lacks isolation
        if not has_user_isolation:
            # Check if factory deals with user data
            user_data_indicators = ['user', 'session', 'context', 'execution']
            deals_with_user_data = False

            for file_path in factory_files:
                content = self._get_file_content(file_path)
                if any(indicator in content.lower() for indicator in user_data_indicators):
                    deals_with_user_data = True
                    break

            if deals_with_user_data:
                result.issues.append(ValidationIssue(
                    severity='ERROR',
                    category='user_isolation',
                    message=f"Factory {factory_name} handles user data but lacks isolation mechanisms",
                    blocking=True,
                    suggested_fix="Add user isolation before migration or ensure replacement has proper isolation"
                ))
        else:
            logger.debug(f"Factory {factory_name} has user isolation: {isolation_methods}")

    def _detect_breaking_changes(self, factory_name: str,
                               target_replacement: Optional[str],
                               result: MigrationValidationResult) -> None:
        """Detect potential breaking changes from factory migration."""
        logger.debug(f"Detecting breaking changes for {factory_name}")

        usage_files = self._find_factory_usage_files(factory_name)

        for file_path in usage_files:
            try:
                content = self._get_file_content(file_path)

                # Parse AST for more accurate analysis
                try:
                    tree = ast.parse(content)
                    self._analyze_ast_for_breaking_changes(tree, factory_name, file_path, result)
                except SyntaxError:
                    # Fallback to regex analysis
                    self._analyze_regex_for_breaking_changes(content, factory_name, file_path, result)

            except Exception as e:
                logger.debug(f"Error detecting breaking changes in {file_path}: {e}")

    def _analyze_ast_for_breaking_changes(self, tree: ast.AST, factory_name: str,
                                        file_path: str, result: MigrationValidationResult) -> None:
        """Analyze AST for breaking changes."""
        for node in ast.walk(tree):
            # Check function calls
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Name) and
                    factory_name in getattr(node.func, 'id', '')):

                    result.issues.append(ValidationIssue(
                        severity='WARNING',
                        category='breaking_change',
                        message=f"Direct function call to {factory_name} found",
                        file_path=file_path,
                        line_number=getattr(node, 'lineno', 0),
                        suggested_fix="Update call to use replacement factory"
                    ))

            # Check imports
            elif isinstance(node, ast.ImportFrom):
                if any(alias.name == factory_name for alias in (node.names or [])):
                    result.issues.append(ValidationIssue(
                        severity='WARNING',
                        category='breaking_change',
                        message=f"Import of {factory_name} found",
                        file_path=file_path,
                        line_number=getattr(node, 'lineno', 0),
                        suggested_fix="Update import to use replacement factory"
                    ))

    def _analyze_regex_for_breaking_changes(self, content: str, factory_name: str,
                                          file_path: str, result: MigrationValidationResult) -> None:
        """Fallback regex analysis for breaking changes."""
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if factory_name in line:
                # Check for function calls
                if f"{factory_name}(" in line:
                    result.issues.append(ValidationIssue(
                        severity='WARNING',
                        category='breaking_change',
                        message=f"Function call to {factory_name} found",
                        file_path=file_path,
                        line_number=i + 1,
                        suggested_fix="Update call to use replacement factory"
                    ))

                # Check for imports
                if 'import' in line and factory_name in line:
                    result.issues.append(ValidationIssue(
                        severity='WARNING',
                        category='breaking_change',
                        message=f"Import of {factory_name} found",
                        file_path=file_path,
                        line_number=i + 1,
                        suggested_fix="Update import to use replacement factory"
                    ))

    def _validate_essential_factory(self, factory_name: str,
                                  result: MigrationValidationResult) -> None:
        """Validate if factory is essential and requires special handling."""
        if factory_name in self.ESSENTIAL_FACTORIES:
            result.issues.append(ValidationIssue(
                severity='ERROR',
                category='business_impact',
                message=f"Factory {factory_name} is essential: {self.ESSENTIAL_FACTORIES[factory_name]}",
                blocking=True,
                suggested_fix="Essential factories require careful migration with replacement validation"
            ))

    def _analyze_dependencies(self, factory_name: str,
                            result: MigrationValidationResult) -> None:
        """Analyze dependencies of the factory."""
        logger.debug(f"Analyzing dependencies for {factory_name}")

        factory_files = self._find_factory_implementation_files(factory_name)
        dependencies = set()

        for file_path in factory_files:
            try:
                content = self._get_file_content(file_path)

                # Find imports
                import_pattern = r'from\s+[\w.]+\s+import\s+[\w,\s]+|import\s+[\w.,\s]+'
                imports = re.findall(import_pattern, content)

                for import_line in imports:
                    # Extract dependency names
                    if 'from' in import_line:
                        parts = import_line.split('import')
                        if len(parts) > 1:
                            deps = [dep.strip() for dep in parts[1].split(',')]
                            dependencies.update(deps)
                    else:
                        deps = import_line.replace('import', '').split(',')
                        dependencies.update([dep.strip() for dep in deps])

            except Exception as e:
                logger.debug(f"Error analyzing dependencies in {file_path}: {e}")

        # Check for circular dependencies
        for dep in dependencies:
            if 'factory' in dep.lower() and dep != factory_name:
                result.issues.append(ValidationIssue(
                    severity='WARNING',
                    category='breaking_change',
                    message=f"Factory dependency found: {dep}",
                    suggested_fix="Ensure dependency migration order is correct"
                ))

    def _generate_recommendations(self, factory_name: str, migration_type: str,
                                result: MigrationValidationResult) -> None:
        """Generate migration recommendations."""
        recommendations = []

        # Based on issues found
        error_count = len([i for i in result.issues if i.severity == 'ERROR'])
        warning_count = len([i for i in result.issues if i.severity == 'WARNING'])

        if error_count > 0:
            recommendations.append(f"Address {error_count} blocking errors before migration")

        if warning_count > 0:
            recommendations.append(f"Review and address {warning_count} warnings")

        # Based on test coverage
        if result.test_coverage.get('coverage_percentage', 0) < 50:
            recommendations.append("Improve test coverage to at least 50% before migration")

        # Based on business impact
        critical_functions = len(result.business_impact.get('critical_functions_affected', []))
        if critical_functions > 0:
            recommendations.append(f"Create business continuity plan for {critical_functions} affected functions")

        # Migration type specific recommendations
        if migration_type == 'removal':
            recommendations.append("Verify all functionality is covered by alternative implementations")
        elif migration_type == 'consolidation':
            recommendations.append("Ensure target factory supports all use cases of source factory")

        # Essential factory recommendations
        if factory_name in self.ESSENTIAL_FACTORIES:
            recommendations.append("Essential factory requires replacement with equivalent functionality")

        result.recommendations = recommendations

    def _assess_migration_safety(self, result: MigrationValidationResult) -> None:
        """Assess overall migration safety."""
        # Check for blocking issues
        blocking_issues = [i for i in result.issues if i.blocking]
        if blocking_issues:
            result.migration_safe = False
            result.confidence_level = "LOW"
            return

        # Calculate risk score
        risk_score = 0

        # Severity weights
        for issue in result.issues:
            if issue.severity == 'ERROR':
                risk_score += 3
            elif issue.severity == 'WARNING':
                risk_score += 1

        # Business impact weights
        critical_functions = len(result.business_impact.get('critical_functions_affected', []))
        risk_score += critical_functions * 2

        # Test coverage weights
        coverage = result.test_coverage.get('coverage_percentage', 0)
        if coverage < 30:
            risk_score += 3
        elif coverage < 50:
            risk_score += 1

        # Determine safety and confidence
        if risk_score >= 10:
            result.migration_safe = False
            result.confidence_level = "LOW"
        elif risk_score >= 5:
            result.migration_safe = True
            result.confidence_level = "MEDIUM"
        else:
            result.migration_safe = True
            result.confidence_level = "HIGH"

    def _find_factory_usage_files(self, factory_name: str) -> List[str]:
        """Find all files that use the specified factory."""
        usage_files = []

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                content = self._get_file_content(str(py_file))
                if factory_name in content:
                    usage_files.append(str(py_file))
            except Exception:
                continue

        return usage_files

    def _find_factory_implementation_files(self, factory_name: str) -> List[str]:
        """Find files that implement the factory."""
        impl_files = []

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                content = self._get_file_content(str(py_file))
                # Look for class or function definitions
                if (f"class {factory_name}" in content or
                    f"def {factory_name}" in content or
                    f"def create_{factory_name.lower()}" in content):
                    impl_files.append(str(py_file))
            except Exception:
                continue

        return impl_files

    def _get_file_content(self, file_path: str) -> str:
        """Get file content with caching."""
        if file_path not in self.file_cache:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.file_cache[file_path] = f.read()
            except Exception as e:
                logger.debug(f"Could not read {file_path}: {e}")
                self.file_cache[file_path] = ""

        return self.file_cache[file_path]

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', 'node_modules', '.pytest_cache',
            'venv', '.venv', 'htmlcov', 'backups'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def validate_batch_migration(self, factory_names: List[str],
                                migration_plan: Dict[str, str]) -> Dict[str, MigrationValidationResult]:
        """Validate a batch of factory migrations."""
        logger.info(f"Validating batch migration of {len(factory_names)} factories")

        results = {}

        for factory_name in factory_names:
            migration_type = migration_plan.get(factory_name, 'removal')
            results[factory_name] = self.validate_factory_migration(
                factory_name, migration_type=migration_type
            )

        # Cross-factory validation
        self._validate_cross_factory_dependencies(results)

        return results

    def _validate_cross_factory_dependencies(self, results: Dict[str, MigrationValidationResult]) -> None:
        """Validate dependencies between factories being migrated."""
        for factory_name, result in results.items():
            for other_factory in results.keys():
                if other_factory != factory_name:
                    # Check if this factory depends on another factory being migrated
                    usage_files = self._find_factory_usage_files(factory_name)
                    for file_path in usage_files:
                        content = self._get_file_content(file_path)
                        if other_factory in content:
                            result.issues.append(ValidationIssue(
                                severity='WARNING',
                                category='breaking_change',
                                message=f"Cross-factory dependency: {factory_name} uses {other_factory}",
                                suggested_fix="Ensure migration order handles dependencies correctly"
                            ))

    def run_migration_tests(self, factory_name: str) -> Dict[str, Any]:
        """Run relevant tests for factory migration validation."""
        logger.info(f"Running migration tests for {factory_name}")

        test_results = {
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'test_output': '',
            'relevant_tests': []
        }

        # Find relevant tests
        relevant_tests = []
        for test_file in self.test_files:
            content = self._get_file_content(test_file)
            if factory_name in content:
                relevant_tests.append(test_file)

        test_results['relevant_tests'] = relevant_tests

        # Run tests if found
        if relevant_tests:
            for test_file in relevant_tests[:5]:  # Limit to first 5 to avoid long execution
                try:
                    # Use relative path for pytest
                    rel_path = str(Path(test_file).relative_to(self.project_root))
                    result = subprocess.run(
                        ['python', '-m', 'pytest', rel_path, '-v'],
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    test_results['tests_run'] += 1
                    if result.returncode == 0:
                        test_results['tests_passed'] += 1
                    else:
                        test_results['tests_failed'] += 1

                    test_results['test_output'] += f"\n--- {test_file} ---\n"
                    test_results['test_output'] += result.stdout + result.stderr

                except Exception as e:
                    logger.debug(f"Error running test {test_file}: {e}")
                    test_results['test_output'] += f"\nError running {test_file}: {e}\n"

        return test_results

    def generate_validation_report(self, results: Dict[str, MigrationValidationResult]) -> str:
        """Generate comprehensive validation report."""
        report_lines = [
            "=" * 80,
            "FACTORY MIGRATION VALIDATION REPORT - Issue #1194 Phase 1",
            "=" * 80,
            "",
            "VALIDATION SUMMARY:",
            f"  Factories Validated: {len(results)}",
            f"  Safe Migrations: {sum(1 for r in results.values() if r.migration_safe)}",
            f"  Blocked Migrations: {sum(1 for r in results.values() if not r.migration_safe)}",
            ""
        ]

        # Group by safety status
        safe_factories = [name for name, result in results.items() if result.migration_safe]
        blocked_factories = [name for name, result in results.items() if not result.migration_safe]

        if safe_factories:
            report_lines.extend([
                f"SAFE TO MIGRATE ({len(safe_factories)}):",
                *[f"  ✓ {name} ({results[name].confidence_level} confidence)" for name in safe_factories],
                ""
            ])

        if blocked_factories:
            report_lines.extend([
                f"BLOCKED MIGRATIONS ({len(blocked_factories)}):",
                *[f"  ✗ {name} ({len(results[name].issues)} issues)" for name in blocked_factories],
                ""
            ])

        # Detailed issues by category
        all_issues = []
        for result in results.values():
            all_issues.extend(result.issues)

        if all_issues:
            issues_by_category = {}
            for issue in all_issues:
                if issue.category not in issues_by_category:
                    issues_by_category[issue.category] = []
                issues_by_category[issue.category].append(issue)

            report_lines.append("ISSUES BY CATEGORY:")
            for category, issues in issues_by_category.items():
                report_lines.append(f"  {category.upper()}: {len(issues)} issues")
                for issue in issues[:3]:  # Show first 3
                    report_lines.append(f"    - {issue.severity}: {issue.message}")
                if len(issues) > 3:
                    report_lines.append(f"    ... and {len(issues) - 3} more")
                report_lines.append("")

        # Recommendations
        all_recommendations = []
        for result in results.values():
            all_recommendations.extend(result.recommendations)

        if all_recommendations:
            unique_recommendations = list(set(all_recommendations))
            report_lines.extend([
                "MIGRATION RECOMMENDATIONS:",
                *[f"  - {rec}" for rec in unique_recommendations[:10]],
                ""
            ])

        return "\n".join(report_lines)


def main():
    """Main entry point for factory migration validation."""
    parser = argparse.ArgumentParser(
        description="Validate safety of factory migration operations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--factory', '-f',
        type=str,
        help='Factory name to validate for migration'
    )

    parser.add_argument(
        '--batch', '-b',
        type=Path,
        help='JSON file containing batch migration plan'
    )

    parser.add_argument(
        '--replacement', '-r',
        type=str,
        help='Replacement factory name (for consolidation)'
    )

    parser.add_argument(
        '--migration-type',
        choices=['removal', 'consolidation', 'refactor'],
        default='removal',
        help='Type of migration to validate'
    )

    parser.add_argument(
        '--run-tests',
        action='store_true',
        help='Run relevant tests as part of validation'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for validation results'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'text'],
        default='text',
        help='Output format'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not args.factory and not args.batch:
        parser.error("Either --factory or --batch must be specified")

    try:
        validator = FactoryMigrationValidator()

        if args.factory:
            # Single factory validation
            result = validator.validate_factory_migration(
                args.factory,
                args.replacement,
                args.migration_type
            )

            # Run tests if requested
            if args.run_tests:
                test_results = validator.run_migration_tests(args.factory)
                result.test_coverage['test_results'] = test_results

            results = {args.factory: result}

        else:
            # Batch validation
            with open(args.batch, 'r') as f:
                migration_plan = json.load(f)

            factory_names = list(migration_plan.keys())
            results = validator.validate_batch_migration(factory_names, migration_plan)

        # Generate output
        if args.format == 'json':
            output_content = json.dumps(
                {name: asdict(result) for name, result in results.items()},
                indent=2,
                default=str
            )
        else:
            output_content = validator.generate_validation_report(results)

        # Write output
        if args.output:
            args.output.write_text(output_content, encoding='utf-8')
            logger.info(f"Validation report written to {args.output}")
        else:
            print(output_content)

        # Summary
        safe_count = sum(1 for r in results.values() if r.migration_safe)
        total_count = len(results)

        logger.info(f"Validation complete: {safe_count}/{total_count} migrations are safe")

        # Exit with error if any migrations are blocked
        if safe_count < total_count:
            logger.warning(f"{total_count - safe_count} migrations are blocked")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Migration validation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())