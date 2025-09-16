"""
Factory Pattern Audit Test - Comprehensive Baseline Analysis

This test performs a comprehensive audit of all factory patterns in the codebase
to establish baseline metrics before cleanup. It categorizes factories into
essential vs unnecessary patterns based on Issue #1116 criteria.

Business Value: Platform/Internal - Architecture optimization and technical debt reduction
Eliminates over-engineering and unnecessary factory abstractions while preserving
legitimate multi-user isolation and dependency injection patterns.

Test Strategy:
1. Scan entire codebase for factory patterns
2. Categorize based on business justification and multi-user needs
3. Measure performance impact and complexity overhead
4. Generate detailed recommendations for cleanup

SSOT Compliance:
- Uses SSotBaseTestCase for consistent test infrastructure
- Integrates with IsolatedEnvironment for environment access
- Records comprehensive metrics for baseline analysis
"""

import ast
import os
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class FactoryPattern:
    """Represents a discovered factory pattern."""
    file_path: str
    class_name: str
    method_name: str
    pattern_type: str  # 'factory_class', 'factory_method', 'singleton', 'builder'
    lines_of_code: int
    dependencies: List[str] = field(default_factory=list)
    consumers: List[str] = field(default_factory=list)
    complexity_score: int = 0
    business_justification: str = ""
    recommendation: str = ""
    essential: bool = False


@dataclass
class FactoryAuditReport:
    """Complete factory audit report."""
    total_factories: int = 0
    essential_factories: int = 0
    unnecessary_factories: int = 0
    patterns_by_type: Dict[str, int] = field(default_factory=dict)
    complexity_overhead: int = 0
    files_analyzed: int = 0
    recommendations: List[str] = field(default_factory=list)
    detailed_findings: List[FactoryPattern] = field(default_factory=list)


class TestFactoryPatternAudit(SSotBaseTestCase):
    """
    Comprehensive factory pattern audit test.

    This test scans the entire codebase to identify all factory patterns,
    categorize them by necessity, and provide detailed recommendations
    for cleanup and optimization.
    """

    def setup_method(self, method=None):
        """Setup test environment."""
        super().setup_method(method)

        # Initialize audit metrics
        self.record_metric("audit_start_time", time.time())
        self.record_metric("factories_analyzed", 0)
        self.record_metric("files_scanned", 0)
        self.record_metric("complexity_overhead", 0)

        # Directory patterns to scan
        self.scan_directories = [
            "netra_backend",
            "auth_service",
            "frontend",
            "shared",
            "test_framework"
        ]

        # Factory pattern indicators
        self.factory_indicators = {
            'factory_class': [
                r'class.*Factory[^a-zA-Z]',
                r'class.*Builder[^a-zA-Z]',
                r'class.*Creator[^a-zA-Z]',
                r'class.*Generator[^a-zA-Z]'
            ],
            'factory_method': [
                r'def create_',
                r'def make_',
                r'def build_',
                r'def get_instance',
                r'def get_factory',
                r'@.*factory',
                r'@staticmethod.*def.*factory'
            ],
            'singleton': [
                r'_instance.*=.*None',
                r'def __new__',
                r'if not.*instance',
                r'@singleton',
                r'class.*Singleton'
            ],
            'builder': [
                r'def with_',
                r'return self',
                r'class.*Builder',
                r'def add_.*return self'
            ]
        }

        # Issue #1116 criteria for essential factories
        self.essential_criteria = {
            'multi_user_isolation': [
                'UserExecutionContext',
                'WebSocket',
                'Agent',
                'Session',
                'Context',
                'Isolation'
            ],
            'dependency_injection': [
                'Config',
                'Database',
                'Service',
                'Client'
            ],
            'testing_infrastructure': [
                'Mock',
                'Test',
                'Stub'
            ]
        }

    def test_factory_pattern_audit_complete(self):
        """
        Comprehensive factory pattern audit.

        Scans entire codebase for factory patterns and generates
        detailed baseline report with recommendations.
        """
        audit_report = FactoryAuditReport()

        # Scan all relevant directories
        for directory in self.scan_directories:
            if os.path.exists(directory):
                self._scan_directory(directory, audit_report)

        # Analyze findings and generate recommendations
        self._analyze_findings(audit_report)

        # Record comprehensive metrics
        self._record_audit_metrics(audit_report)

        # Generate detailed report
        report_content = self._generate_audit_report(audit_report)

        # Save report for analysis
        self._save_audit_report(report_content)

        # Validate findings
        self._validate_audit_results(audit_report)

        self.record_metric("audit_completed", True)
        self.record_metric("total_factories_found", audit_report.total_factories)

    def test_factory_complexity_measurement(self):
        """
        Measure complexity overhead of current factory patterns.

        Calculates lines of code, cyclomatic complexity, and
        maintenance burden of factory implementations.
        """
        complexity_metrics = {
            'total_loc': 0,
            'average_complexity': 0,
            'max_complexity': 0,
            'cyclomatic_complexity': 0,
            'maintenance_score': 0
        }

        factory_files = self._find_factory_files()

        for file_path in factory_files:
            file_metrics = self._analyze_file_complexity(file_path)
            complexity_metrics['total_loc'] += file_metrics['loc']
            complexity_metrics['cyclomatic_complexity'] += file_metrics['cyclomatic']
            complexity_metrics['max_complexity'] = max(
                complexity_metrics['max_complexity'],
                file_metrics['cyclomatic']
            )

        # Calculate averages
        if factory_files:
            complexity_metrics['average_complexity'] = (
                complexity_metrics['cyclomatic_complexity'] / len(factory_files)
            )

        # Calculate maintenance score (higher = more maintenance burden)
        complexity_metrics['maintenance_score'] = (
            complexity_metrics['total_loc'] * 0.1 +
            complexity_metrics['cyclomatic_complexity'] * 0.3 +
            len(factory_files) * 0.2
        )

        # Record metrics
        for metric, value in complexity_metrics.items():
            self.record_metric(f"complexity_{metric}", value)

        # Assertions for baseline validation
        self.assertGreater(complexity_metrics['total_loc'], 0,
                          "Should find factory code to analyze")

        self.record_metric("complexity_analysis_completed", True)

    def test_factory_categorization(self):
        """
        Categorize all factories by business necessity and type.

        Applies Issue #1116 criteria to classify factories as
        essential or candidates for removal.
        """
        categories = {
            'essential_multi_user': [],
            'essential_dependency_injection': [],
            'essential_testing': [],
            'unnecessary_over_engineering': [],
            'unnecessary_premature_abstraction': [],
            'legacy_compatibility': []
        }

        factories = self._discover_all_factories()

        for factory in factories:
            category = self._categorize_factory(factory)
            categories[category].append(factory)

        # Record categorization metrics
        for category, factories_in_category in categories.items():
            count = len(factories_in_category)
            self.record_metric(f"category_{category}_count", count)

            # Log detailed findings for review
            if factories_in_category:
                factory_names = [f.class_name for f in factories_in_category]
                self.record_metric(f"category_{category}_factories", factory_names)

        # Calculate essential vs unnecessary ratios
        essential_count = (
            len(categories['essential_multi_user']) +
            len(categories['essential_dependency_injection']) +
            len(categories['essential_testing'])
        )

        unnecessary_count = (
            len(categories['unnecessary_over_engineering']) +
            len(categories['unnecessary_premature_abstraction'])
        )

        total_count = essential_count + unnecessary_count + len(categories['legacy_compatibility'])

        if total_count > 0:
            essential_ratio = essential_count / total_count
            unnecessary_ratio = unnecessary_count / total_count

            self.record_metric("essential_factory_ratio", essential_ratio)
            self.record_metric("unnecessary_factory_ratio", unnecessary_ratio)

        # Validate categorization results
        self.assertGreater(total_count, 0, "Should discover factories to categorize")

        self.record_metric("categorization_completed", True)

    def test_factory_dependency_analysis(self):
        """
        Analyze factory dependencies and consumer relationships.

        Maps dependency graphs to understand impact of factory
        removal and identify tightly coupled patterns.
        """
        dependency_map = defaultdict(list)
        consumer_map = defaultdict(list)
        circular_dependencies = []

        factories = self._discover_all_factories()

        # Build dependency and consumer maps
        for factory in factories:
            for dependency in factory.dependencies:
                dependency_map[factory.class_name].append(dependency)
                consumer_map[dependency].append(factory.class_name)

        # Detect circular dependencies
        for factory_name in dependency_map.keys():
            circular_deps = self._detect_circular_dependencies(
                factory_name, dependency_map, set()
            )
            if circular_deps:
                circular_dependencies.extend(circular_deps)

        # Calculate dependency metrics
        total_dependencies = sum(len(deps) for deps in dependency_map.values())
        max_dependencies = max((len(deps) for deps in dependency_map.values()), default=0)
        highly_coupled_factories = [
            name for name, deps in dependency_map.items()
            if len(deps) > 5
        ]

        # Record dependency analysis metrics
        self.record_metric("total_factory_dependencies", total_dependencies)
        self.record_metric("max_factory_dependencies", max_dependencies)
        self.record_metric("circular_dependency_count", len(circular_dependencies))
        self.record_metric("highly_coupled_factories", highly_coupled_factories)
        self.record_metric("dependency_map_size", len(dependency_map))

        if circular_dependencies:
            self.record_metric("circular_dependencies_found", circular_dependencies)

        # Validate analysis
        self.record_metric("dependency_analysis_completed", True)

    def _scan_directory(self, directory: str, audit_report: FactoryAuditReport):
        """Scan directory for factory patterns."""
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self._analyze_file(file_path, audit_report)
                    audit_report.files_analyzed += 1

    def _analyze_file(self, file_path: str, audit_report: FactoryAuditReport):
        """Analyze single file for factory patterns."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for factory patterns
            factories = self._detect_factory_patterns(file_path, content)
            audit_report.detailed_findings.extend(factories)
            audit_report.total_factories += len(factories)

        except Exception as e:
            self.record_metric("file_analysis_errors",
                             self.get_metric("file_analysis_errors", 0) + 1)

    def _detect_factory_patterns(self, file_path: str, content: str) -> List[FactoryPattern]:
        """Detect factory patterns in file content."""
        factories = []
        lines = content.split('\n')

        for pattern_type, indicators in self.factory_indicators.items():
            for indicator in indicators:
                matches = re.finditer(indicator, content, re.MULTILINE | re.IGNORECASE)

                for match in matches:
                    # Find the line number
                    line_num = content[:match.start()].count('\n') + 1

                    # Extract class/method name context
                    context = self._extract_context(lines, line_num)

                    if context:
                        factory = FactoryPattern(
                            file_path=file_path,
                            class_name=context.get('class_name', 'Unknown'),
                            method_name=context.get('method_name', 'Unknown'),
                            pattern_type=pattern_type,
                            lines_of_code=context.get('loc', 0)
                        )

                        # Apply business justification analysis
                        factory = self._analyze_business_justification(factory)

                        factories.append(factory)

        return factories

    def _extract_context(self, lines: List[str], line_num: int) -> Dict[str, Any]:
        """Extract context around a pattern match."""
        context = {}

        # Look backwards for class definition
        for i in range(max(0, line_num - 20), line_num):
            line = lines[i] if i < len(lines) else ""
            if line.strip().startswith('class '):
                class_match = re.match(r'\s*class\s+(\w+)', line)
                if class_match:
                    context['class_name'] = class_match.group(1)
                break

        # Look backwards for method definition
        for i in range(max(0, line_num - 10), line_num):
            line = lines[i] if i < len(lines) else ""
            if line.strip().startswith('def '):
                method_match = re.match(r'\s*def\s+(\w+)', line)
                if method_match:
                    context['method_name'] = method_match.group(1)
                break

        # Estimate lines of code for this pattern
        context['loc'] = self._estimate_pattern_loc(lines, line_num)

        return context

    def _estimate_pattern_loc(self, lines: List[str], line_num: int) -> int:
        """Estimate lines of code for a pattern."""
        # Simple heuristic: count non-empty lines in surrounding block
        start = max(0, line_num - 10)
        end = min(len(lines), line_num + 20)

        loc = 0
        for i in range(start, end):
            line = lines[i] if i < len(lines) else ""
            if line.strip() and not line.strip().startswith('#'):
                loc += 1

        return min(loc, 50)  # Cap at reasonable estimate

    def _analyze_business_justification(self, factory: FactoryPattern) -> FactoryPattern:
        """Analyze business justification for factory pattern."""
        file_content = factory.file_path.lower()
        class_name = factory.class_name.lower()

        # Check for multi-user isolation needs
        for keyword in self.essential_criteria['multi_user_isolation']:
            if keyword.lower() in class_name or keyword.lower() in file_content:
                factory.essential = True
                factory.business_justification = "Multi-user isolation required"
                factory.recommendation = "KEEP - Essential for user context separation"
                return factory

        # Check for dependency injection needs
        for keyword in self.essential_criteria['dependency_injection']:
            if keyword.lower() in class_name or keyword.lower() in file_content:
                factory.essential = True
                factory.business_justification = "Dependency injection pattern"
                factory.recommendation = "KEEP - Essential for service configuration"
                return factory

        # Check for testing infrastructure
        if 'test' in file_content:
            for keyword in self.essential_criteria['testing_infrastructure']:
                if keyword.lower() in class_name:
                    factory.essential = True
                    factory.business_justification = "Testing infrastructure"
                    factory.recommendation = "KEEP - Required for test consistency"
                    return factory

        # Default to unnecessary if no clear justification
        factory.essential = False
        factory.business_justification = "No clear business justification found"
        factory.recommendation = "REVIEW - Consider removing or simplifying"

        return factory

    def _analyze_findings(self, audit_report: FactoryAuditReport):
        """Analyze audit findings and generate insights."""
        # Count by pattern type
        for factory in audit_report.detailed_findings:
            pattern_type = factory.pattern_type
            audit_report.patterns_by_type[pattern_type] = (
                audit_report.patterns_by_type.get(pattern_type, 0) + 1
            )

            if factory.essential:
                audit_report.essential_factories += 1
            else:
                audit_report.unnecessary_factories += 1

            audit_report.complexity_overhead += factory.lines_of_code

        # Generate high-level recommendations
        if audit_report.unnecessary_factories > audit_report.essential_factories:
            audit_report.recommendations.append(
                "HIGH PRIORITY: Significant factory over-engineering detected. "
                f"{audit_report.unnecessary_factories} unnecessary factories vs "
                f"{audit_report.essential_factories} essential ones."
            )

        if audit_report.complexity_overhead > 5000:
            audit_report.recommendations.append(
                f"COMPLEXITY CONCERN: {audit_report.complexity_overhead} lines of factory code. "
                "Consider consolidation to reduce maintenance burden."
            )

        # Pattern-specific recommendations
        singleton_count = audit_report.patterns_by_type.get('singleton', 0)
        if singleton_count > 10:
            audit_report.recommendations.append(
                f"SINGLETON OVERUSE: {singleton_count} singleton patterns detected. "
                "Review for Issue #1116 compliance and multi-user safety."
            )

    def _record_audit_metrics(self, audit_report: FactoryAuditReport):
        """Record comprehensive audit metrics."""
        self.record_metric("audit_total_factories", audit_report.total_factories)
        self.record_metric("audit_essential_factories", audit_report.essential_factories)
        self.record_metric("audit_unnecessary_factories", audit_report.unnecessary_factories)
        self.record_metric("audit_complexity_overhead", audit_report.complexity_overhead)
        self.record_metric("audit_files_analyzed", audit_report.files_analyzed)
        self.record_metric("audit_recommendations_count", len(audit_report.recommendations))

        # Pattern type breakdown
        for pattern_type, count in audit_report.patterns_by_type.items():
            self.record_metric(f"audit_pattern_{pattern_type}_count", count)

        # Efficiency ratios
        if audit_report.total_factories > 0:
            essential_ratio = audit_report.essential_factories / audit_report.total_factories
            self.record_metric("audit_essential_ratio", essential_ratio)

    def _generate_audit_report(self, audit_report: FactoryAuditReport) -> str:
        """Generate detailed audit report."""
        report_lines = [
            "# Factory Pattern Audit Report",
            f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Files Analyzed:** {audit_report.files_analyzed}",
            "",
            "## Executive Summary",
            f"- **Total Factories:** {audit_report.total_factories}",
            f"- **Essential Factories:** {audit_report.essential_factories}",
            f"- **Unnecessary Factories:** {audit_report.unnecessary_factories}",
            f"- **Complexity Overhead:** {audit_report.complexity_overhead} LOC",
            "",
            "## Pattern Breakdown",
        ]

        for pattern_type, count in audit_report.patterns_by_type.items():
            report_lines.append(f"- **{pattern_type.title()}:** {count}")

        report_lines.extend([
            "",
            "## Recommendations",
        ])

        for i, recommendation in enumerate(audit_report.recommendations, 1):
            report_lines.append(f"{i}. {recommendation}")

        report_lines.extend([
            "",
            "## Detailed Findings",
            "",
            "### Essential Factories (KEEP)",
        ])

        essential_factories = [f for f in audit_report.detailed_findings if f.essential]
        for factory in essential_factories[:10]:  # Top 10 for brevity
            report_lines.append(
                f"- **{factory.class_name}** ({factory.pattern_type}) - {factory.business_justification}"
            )

        report_lines.extend([
            "",
            "### Unnecessary Factories (REVIEW)",
        ])

        unnecessary_factories = [f for f in audit_report.detailed_findings if not f.essential]
        for factory in unnecessary_factories[:10]:  # Top 10 for brevity
            report_lines.append(
                f"- **{factory.class_name}** ({factory.pattern_type}) - {factory.recommendation}"
            )

        return "\n".join(report_lines)

    def _save_audit_report(self, report_content: str):
        """Save audit report to file."""
        try:
            report_path = "FACTORY_PATTERN_AUDIT_BASELINE_REPORT.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            self.record_metric("audit_report_saved", True)
            self.record_metric("audit_report_path", report_path)

        except Exception as e:
            self.record_metric("audit_report_save_error", str(e))

    def _validate_audit_results(self, audit_report: FactoryAuditReport):
        """Validate audit results for consistency."""
        # Basic validation
        self.assertGreaterEqual(audit_report.files_analyzed, 100,
                               "Should analyze substantial number of files")

        self.assertGreater(audit_report.total_factories, 0,
                          "Should discover factory patterns")

        # Consistency checks
        expected_total = audit_report.essential_factories + audit_report.unnecessary_factories
        self.assertLessEqual(expected_total, audit_report.total_factories,
                            "Essential + unnecessary should not exceed total")

        # Pattern type validation
        pattern_type_total = sum(audit_report.patterns_by_type.values())
        self.assertGreaterEqual(pattern_type_total, audit_report.total_factories,
                               "Pattern type counts should cover all factories")

        self.record_metric("audit_validation_passed", True)

    # Helper methods for additional analysis

    def _find_factory_files(self) -> List[str]:
        """Find all files containing factory patterns."""
        factory_files = []

        for directory in self.scan_directories:
            if not os.path.exists(directory):
                continue

            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)

                        # Quick check for factory indicators
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read().lower()

                            for indicators in self.factory_indicators.values():
                                for indicator in indicators:
                                    if re.search(indicator.lower(), content):
                                        factory_files.append(file_path)
                                        break
                                else:
                                    continue
                                break
                        except Exception:
                            continue

        return factory_files

    def _analyze_file_complexity(self, file_path: str) -> Dict[str, int]:
        """Analyze complexity metrics for a file."""
        metrics = {'loc': 0, 'cyclomatic': 0}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Count lines of code (non-empty, non-comment)
            lines = content.split('\n')
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    metrics['loc'] += 1

            # Estimate cyclomatic complexity (simple heuristic)
            complexity_keywords = ['if', 'elif', 'for', 'while', 'try', 'except', 'with']
            for keyword in complexity_keywords:
                metrics['cyclomatic'] += len(re.findall(rf'\b{keyword}\b', content))

        except Exception:
            pass

        return metrics

    def _discover_all_factories(self) -> List[FactoryPattern]:
        """Discover all factory patterns across the codebase."""
        all_factories = []
        audit_report = FactoryAuditReport()

        for directory in self.scan_directories:
            if os.path.exists(directory):
                self._scan_directory(directory, audit_report)

        return audit_report.detailed_findings

    def _categorize_factory(self, factory: FactoryPattern) -> str:
        """Categorize a factory pattern by business necessity."""
        if factory.essential:
            if any(keyword in factory.class_name.lower()
                  for keyword in self.essential_criteria['multi_user_isolation']):
                return 'essential_multi_user'
            elif any(keyword in factory.class_name.lower()
                    for keyword in self.essential_criteria['dependency_injection']):
                return 'essential_dependency_injection'
            else:
                return 'essential_testing'
        else:
            # Classify unnecessary patterns
            if factory.complexity_score > 20 or factory.lines_of_code > 100:
                return 'unnecessary_over_engineering'
            elif 'legacy' in factory.file_path.lower():
                return 'legacy_compatibility'
            else:
                return 'unnecessary_premature_abstraction'

    def _detect_circular_dependencies(self, factory_name: str,
                                    dependency_map: Dict, visited: Set) -> List[str]:
        """Detect circular dependencies in factory relationships."""
        if factory_name in visited:
            return [factory_name]

        visited.add(factory_name)
        circular_deps = []

        for dependency in dependency_map.get(factory_name, []):
            if dependency in visited:
                circular_deps.append(f"{factory_name} -> {dependency}")
            else:
                sub_circular = self._detect_circular_dependencies(
                    dependency, dependency_map, visited.copy()
                )
                circular_deps.extend(sub_circular)

        return circular_deps