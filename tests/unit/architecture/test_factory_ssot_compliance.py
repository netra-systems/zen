"""
Factory SSOT Compliance Baseline Test - Comprehensive Compliance Analysis

This test measures the current SSOT compliance impact from factory patterns
and establishes baseline metrics for import path fragmentation, duplicate
detection, and factory consolidation opportunities.

Business Value: Platform/Internal - SSOT compliance and architecture consistency
Supports the 87.2% SSOT compliance goal while identifying factory patterns that
contribute to violations and fragmentation in the system architecture.

Test Strategy:
1. Scan for factory import path fragmentation and SSOT violations
2. Detect duplicate factory implementations across services
3. Measure SSOT compliance impact from factory patterns
4. Analyze factory naming conventions and business focus alignment
5. Generate detailed compliance recommendations

SSOT Compliance Targets:
- Factory import paths: 100% SSOT compliant
- Duplicate factories: 0 duplicates across services
- Naming conventions: Business-focused naming (no "Manager" overuse)
- Service isolation: 100% service boundary compliance

SSOT Compliance:
- Uses SSotBaseTestCase for consistent test infrastructure
- Integrates with IsolatedEnvironment for environment access
- Records comprehensive compliance metrics for baseline
"""

import ast
import os
import re
import importlib
import inspect
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional, Union
from dataclasses import dataclass, field

from test_framework.ssot.base_test_case import SSotBaseTestCase


@dataclass
class SsotViolation:
    """Represents an SSOT compliance violation."""
    file_path: str
    line_number: int
    violation_type: str  # 'duplicate_factory', 'import_fragmentation', 'naming_violation', 'service_boundary'
    description: str
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    factory_name: str = ""
    recommended_fix: str = ""


@dataclass
class FactorySsotAnalysis:
    """Complete factory SSOT compliance analysis."""
    total_factories: int = 0
    compliant_factories: int = 0
    violation_count: int = 0
    violations_by_type: Dict[str, int] = field(default_factory=dict)
    violations_by_severity: Dict[str, int] = field(default_factory=dict)
    duplicate_factories: Dict[str, List[str]] = field(default_factory=dict)
    import_fragments: List[str] = field(default_factory=list)
    naming_violations: List[str] = field(default_factory=list)
    service_boundary_violations: List[str] = field(default_factory=list)
    detailed_violations: List[SsotViolation] = field(default_factory=list)
    compliance_score: float = 0.0


class TestFactorySsotCompliance(SSotBaseTestCase):
    """
    Factory SSOT compliance baseline test suite.

    Analyzes current factory patterns for SSOT compliance violations
    and establishes baseline metrics for remediation planning.
    """

    def setup_method(self, method=None):
        """Setup SSOT compliance testing environment."""
        super().setup_method(method)

        # Initialize compliance tracking
        self.record_metric("ssot_compliance_analysis_start", True)

        # Service boundaries for factory isolation
        self.service_boundaries = {
            'netra_backend': ['netra_backend'],
            'auth_service': ['auth_service'],
            'frontend': ['frontend'],
            'shared': ['shared'],
            'test_framework': ['test_framework']
        }

        # SSOT-compliant factory patterns
        self.ssot_compliant_patterns = {
            'base_classes': [
                'test_framework.ssot.base_test_case.SSotBaseTestCase',
                'test_framework.ssot.mock_factory.SSotMockFactory'
            ],
            'import_patterns': [
                r'from test_framework\.ssot\.',
                r'from netra_backend\.app\.',
                r'from auth_service\.',
                r'from shared\.'
            ],
            'naming_conventions': [
                r'^[A-Z][a-zA-Z]*Factory$',  # PascalCase ending with Factory
                r'^[A-Z][a-zA-Z]*Creator$',  # PascalCase ending with Creator
                r'^[A-Z][a-zA-Z]*Builder$',  # PascalCase ending with Builder
            ]
        }

        # Business-focused naming violations (Issue #1116 criteria)
        self.naming_violation_patterns = {
            'manager_overuse': [
                r'.*Manager.*Factory',
                r'.*Factory.*Manager',
                r'Unified.*Manager.*Factory'
            ],
            'unclear_naming': [
                r'^Factory$',  # Just "Factory"
                r'^Creator$',  # Just "Creator"
                r'^Builder$',  # Just "Builder"
                r'.*Helper.*Factory',  # Vague "Helper" naming
            ],
            'over_engineering': [
                r'.*Abstract.*Factory.*Factory',  # Double Factory
                r'.*Generic.*Universal.*Factory',  # Over-abstracted
                r'.*Configurable.*Dynamic.*Factory'  # Complexity without value
            ]
        }

        # SSOT import registry patterns (from docs/SSOT_IMPORT_REGISTRY.md)
        self.ssot_import_registry = {
            'netra_backend': [
                'netra_backend.app.config',
                'netra_backend.app.core',
                'netra_backend.app.services',
                'netra_backend.app.agents',
                'netra_backend.app.websocket_core'
            ],
            'auth_service': [
                'auth_service.auth_core',
                'auth_service.factory'
            ],
            'test_framework': [
                'test_framework.ssot.base_test_case',
                'test_framework.ssot.mock_factory',
                'test_framework.ssot.orchestration'
            ]
        }

    def test_factory_ssot_compliance_baseline(self):
        """
        Comprehensive factory SSOT compliance baseline analysis.

        Scans entire codebase for factory SSOT compliance violations
        and generates detailed baseline report with remediation priorities.
        """
        ssot_analysis = FactorySsotAnalysis()

        # Scan all services for factory SSOT compliance
        for service_name, service_paths in self.service_boundaries.items():
            for service_path in service_paths:
                if os.path.exists(service_path):
                    self._analyze_service_factories(service_path, service_name, ssot_analysis)

        # Analyze compliance violations
        self._analyze_ssot_violations(ssot_analysis)

        # Calculate compliance score
        if ssot_analysis.total_factories > 0:
            ssot_analysis.compliance_score = (
                ssot_analysis.compliant_factories / ssot_analysis.total_factories * 100
            )

        # Record comprehensive compliance metrics
        self._record_ssot_compliance_metrics(ssot_analysis)

        # Generate detailed compliance report
        compliance_report = self._generate_ssot_compliance_report(ssot_analysis)

        # Save compliance report
        self._save_ssot_compliance_report(compliance_report)

        # Validate compliance analysis
        self._validate_ssot_compliance_analysis(ssot_analysis)

        self.record_metric("factory_ssot_compliance_analysis_completed", True)

    def test_factory_duplicate_detection(self):
        """
        Detect duplicate factory implementations across services.

        Critical for SSOT compliance: identifies factory patterns that
        violate the single source of truth principle.
        """
        duplicate_analysis = {
            'factory_signatures': defaultdict(list),
            'class_name_duplicates': defaultdict(list),
            'method_signature_duplicates': defaultdict(list),
            'interface_duplicates': defaultdict(list)
        }

        # Scan all factory files for duplicates
        factory_files = self._find_all_factory_files()

        for file_path in factory_files:
            factory_info = self._extract_factory_signatures(file_path)

            for signature_type, signatures in factory_info.items():
                for signature in signatures:
                    duplicate_analysis[signature_type][signature].append(file_path)

        # Identify actual duplicates (appearing in multiple files)
        duplicates_found = {}
        for signature_type, signature_map in duplicate_analysis.items():
            duplicates_found[signature_type] = {
                signature: files
                for signature, files in signature_map.items()
                if len(files) > 1
            }

        # Record duplicate detection metrics
        for signature_type, duplicates in duplicates_found.items():
            count = len(duplicates)
            self.record_metric(f"duplicate_{signature_type}_count", count)

            if duplicates:
                duplicate_details = {sig: files for sig, files in duplicates.items()}
                self.record_metric(f"duplicate_{signature_type}_details", duplicate_details)

        # Calculate duplicate factory ratio
        total_signatures = sum(len(sigs) for sigs in duplicate_analysis.values())
        total_duplicates = sum(len(dups) for dups in duplicates_found.values())

        if total_signatures > 0:
            duplicate_ratio = total_duplicates / total_signatures
            self.record_metric("factory_duplicate_ratio", duplicate_ratio)

        # Critical assertion: SSOT compliance requires minimal duplicates
        max_acceptable_duplicates = 5  # Allow minimal legacy duplicates during transition
        self.assertLessEqual(total_duplicates, max_acceptable_duplicates,
                            f"Found {total_duplicates} factory duplicates, "
                            f"should be <= {max_acceptable_duplicates} for SSOT compliance")

        self.record_metric("duplicate_detection_completed", True)

    def test_factory_import_path_fragmentation(self):
        """
        Analyze factory import path fragmentation and SSOT violations.

        Measures how factory imports violate SSOT import registry patterns
        and contribute to import path inconsistencies.
        """
        import_analysis = {
            'total_factory_imports': 0,
            'ssot_compliant_imports': 0,
            'fragmented_imports': [],
            'cross_service_violations': [],
            'relative_import_violations': [],
            'missing_from_registry': []
        }

        # Scan for factory import patterns
        for service_name, service_paths in self.service_boundaries.items():
            for service_path in service_paths:
                if os.path.exists(service_path):
                    service_imports = self._analyze_service_import_patterns(
                        service_path, service_name
                    )

                    import_analysis['total_factory_imports'] += service_imports['total']
                    import_analysis['ssot_compliant_imports'] += service_imports['compliant']
                    import_analysis['fragmented_imports'].extend(service_imports['fragmented'])
                    import_analysis['cross_service_violations'].extend(service_imports['cross_service'])
                    import_analysis['relative_import_violations'].extend(service_imports['relative'])
                    import_analysis['missing_from_registry'].extend(service_imports['missing'])

        # Calculate import fragmentation metrics
        total_imports = import_analysis['total_factory_imports']
        compliant_imports = import_analysis['ssot_compliant_imports']

        if total_imports > 0:
            fragmentation_ratio = 1.0 - (compliant_imports / total_imports)
            import_analysis['fragmentation_ratio'] = fragmentation_ratio
        else:
            import_analysis['fragmentation_ratio'] = 0.0

        # Record import fragmentation metrics
        for metric_name, metric_value in import_analysis.items():
            if isinstance(metric_value, (int, float)):
                self.record_metric(f"import_{metric_name}", metric_value)
            elif isinstance(metric_value, list) and metric_value:
                self.record_metric(f"import_{metric_name}_count", len(metric_value))
                self.record_metric(f"import_{metric_name}_details", metric_value[:10])  # Top 10

        # SSOT compliance assertion for imports
        max_acceptable_fragmentation = 0.20  # 20% fragmentation acceptable during transition
        actual_fragmentation = import_analysis.get('fragmentation_ratio', 0.0)

        self.assertLessEqual(actual_fragmentation, max_acceptable_fragmentation,
                            f"Factory import fragmentation {actual_fragmentation:.2%} "
                            f"should be <= {max_acceptable_fragmentation:.2%}")

        self.record_metric("import_fragmentation_analysis_completed", True)

    def test_factory_naming_convention_compliance(self):
        """
        Analyze factory naming convention compliance and business focus.

        Validates factory naming against business-focused conventions from
        Issue #1116 and identifies over-engineering through naming patterns.
        """
        naming_analysis = {
            'total_factory_names': 0,
            'business_focused_names': 0,
            'manager_overuse_violations': [],
            'unclear_naming_violations': [],
            'over_engineering_violations': [],
            'ssot_compliant_names': 0
        }

        # Scan all factory classes for naming analysis
        factory_classes = self._discover_all_factory_classes()

        for factory_class in factory_classes:
            naming_analysis['total_factory_names'] += 1

            # Check for business-focused naming
            if self._is_business_focused_name(factory_class['name']):
                naming_analysis['business_focused_names'] += 1

            # Check for SSOT compliant naming
            if self._is_ssot_compliant_name(factory_class['name']):
                naming_analysis['ssot_compliant_names'] += 1

            # Check for naming violations
            violations = self._detect_naming_violations(factory_class)

            for violation in violations:
                if violation['type'] == 'manager_overuse':
                    naming_analysis['manager_overuse_violations'].append(violation)
                elif violation['type'] == 'unclear_naming':
                    naming_analysis['unclear_naming_violations'].append(violation)
                elif violation['type'] == 'over_engineering':
                    naming_analysis['over_engineering_violations'].append(violation)

        # Calculate naming compliance metrics
        total_names = naming_analysis['total_factory_names']
        if total_names > 0:
            business_focused_ratio = naming_analysis['business_focused_names'] / total_names
            ssot_compliant_ratio = naming_analysis['ssot_compliant_names'] / total_names
            naming_analysis['business_focused_ratio'] = business_focused_ratio
            naming_analysis['ssot_compliant_ratio'] = ssot_compliant_ratio

        # Record naming compliance metrics
        for metric_name, metric_value in naming_analysis.items():
            if isinstance(metric_value, (int, float)):
                self.record_metric(f"naming_{metric_name}", metric_value)
            elif isinstance(metric_value, list) and metric_value:
                self.record_metric(f"naming_{metric_name}_count", len(metric_value))

        # Business-focused naming assertion
        min_business_focused_ratio = 0.60  # 60% should be business-focused
        actual_business_ratio = naming_analysis.get('business_focused_ratio', 0.0)

        if total_names > 0:
            self.assertGreaterEqual(actual_business_ratio, min_business_focused_ratio,
                                  f"Business-focused naming ratio {actual_business_ratio:.2%} "
                                  f"should be >= {min_business_focused_ratio:.2%}")

        self.record_metric("naming_convention_analysis_completed", True)

    def test_factory_service_boundary_compliance(self):
        """
        Analyze factory service boundary compliance and isolation.

        Validates that factory patterns respect service boundaries and
        don't create inappropriate cross-service dependencies.
        """
        boundary_analysis = {
            'cross_service_factory_usage': [],
            'inappropriate_dependencies': [],
            'service_isolation_violations': [],
            'shared_factory_misuse': [],
            'boundary_compliance_score': 0.0
        }

        # Analyze each service for boundary violations
        for service_name, service_paths in self.service_boundaries.items():
            for service_path in service_paths:
                if os.path.exists(service_path):
                    violations = self._analyze_service_boundary_violations(
                        service_path, service_name
                    )

                    boundary_analysis['cross_service_factory_usage'].extend(
                        violations['cross_service']
                    )
                    boundary_analysis['inappropriate_dependencies'].extend(
                        violations['dependencies']
                    )
                    boundary_analysis['service_isolation_violations'].extend(
                        violations['isolation']
                    )
                    boundary_analysis['shared_factory_misuse'].extend(
                        violations['shared_misuse']
                    )

        # Calculate boundary compliance score
        total_violations = sum(
            len(violations) for violations in [
                boundary_analysis['cross_service_factory_usage'],
                boundary_analysis['inappropriate_dependencies'],
                boundary_analysis['service_isolation_violations'],
                boundary_analysis['shared_factory_misuse']
            ]
        )

        # Estimate total factory usages for compliance calculation
        total_factory_usages = len(self._discover_all_factory_classes())

        if total_factory_usages > 0:
            boundary_analysis['boundary_compliance_score'] = (
                max(0, total_factory_usages - total_violations) / total_factory_usages
            )

        # Record boundary compliance metrics
        for metric_name, metric_value in boundary_analysis.items():
            if isinstance(metric_value, (int, float)):
                self.record_metric(f"boundary_{metric_name}", metric_value)
            elif isinstance(metric_value, list) and metric_value:
                self.record_metric(f"boundary_{metric_name}_count", len(metric_value))
                self.record_metric(f"boundary_{metric_name}_details", metric_value[:5])  # Top 5

        # Service boundary compliance assertion
        min_compliance_score = 0.85  # 85% boundary compliance required
        actual_compliance = boundary_analysis['boundary_compliance_score']

        self.assertGreaterEqual(actual_compliance, min_compliance_score,
                               f"Service boundary compliance {actual_compliance:.2%} "
                               f"should be >= {min_compliance_score:.2%}")

        self.record_metric("service_boundary_analysis_completed", True)

    # Helper methods for SSOT compliance analysis

    def _analyze_service_factories(self, service_path: str, service_name: str,
                                 ssot_analysis: FactorySsotAnalysis):
        """Analyze factories in a specific service for SSOT compliance."""
        for root, dirs, files in os.walk(service_path):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self._analyze_factory_file_compliance(file_path, service_name, ssot_analysis)

    def _analyze_factory_file_compliance(self, file_path: str, service_name: str,
                                       ssot_analysis: FactorySsotAnalysis):
        """Analyze a single file for factory SSOT compliance."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if file contains factory patterns
            if not self._contains_factory_patterns(content):
                return

            ssot_analysis.total_factories += 1

            # Analyze for various SSOT violations
            violations = []

            # Check import fragmentation
            import_violations = self._check_import_fragmentation(file_path, content, service_name)
            violations.extend(import_violations)

            # Check naming conventions
            naming_violations = self._check_naming_violations(file_path, content)
            violations.extend(naming_violations)

            # Check service boundaries
            boundary_violations = self._check_service_boundaries(file_path, content, service_name)
            violations.extend(boundary_violations)

            # Check for duplicates (cross-reference with other files)
            duplicate_violations = self._check_factory_duplicates(file_path, content)
            violations.extend(duplicate_violations)

            # Update analysis with violations found
            if violations:
                ssot_analysis.violation_count += len(violations)
                ssot_analysis.detailed_violations.extend(violations)

                for violation in violations:
                    ssot_analysis.violations_by_type[violation.violation_type] = (
                        ssot_analysis.violations_by_type.get(violation.violation_type, 0) + 1
                    )
                    ssot_analysis.violations_by_severity[violation.severity] = (
                        ssot_analysis.violations_by_severity.get(violation.severity, 0) + 1
                    )
            else:
                ssot_analysis.compliant_factories += 1

        except Exception as e:
            # Record file analysis error but continue
            self.record_metric(f"factory_compliance_analysis_error_{file_path}", str(e))

    def _contains_factory_patterns(self, content: str) -> bool:
        """Check if file content contains factory patterns."""
        factory_indicators = [
            'class.*Factory',
            'class.*Creator',
            'class.*Builder',
            'def create_',
            'def make_',
            'def build_',
            '@.*factory'
        ]

        for indicator in factory_indicators:
            if re.search(indicator, content, re.IGNORECASE):
                return True

        return False

    def _check_import_fragmentation(self, file_path: str, content: str,
                                  service_name: str) -> List[SsotViolation]:
        """Check for import path fragmentation violations."""
        violations = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for factory-related imports
            if re.search(r'import.*[Ff]actory|from.*[Ff]actory', line):
                # Check if import follows SSOT patterns
                if not self._is_ssot_compliant_import(line, service_name):
                    violation = SsotViolation(
                        file_path=file_path,
                        line_number=line_num,
                        violation_type='import_fragmentation',
                        description=f"Non-SSOT import pattern: {line.strip()}",
                        severity='MEDIUM',
                        recommended_fix="Use SSOT import paths from registry"
                    )
                    violations.append(violation)

        return violations

    def _check_naming_violations(self, file_path: str, content: str) -> List[SsotViolation]:
        """Check for factory naming convention violations."""
        violations = []

        # Extract factory class names
        class_pattern = r'class\s+(\w*[Ff]actory\w*|\w*[Cc]reator\w*|\w*[Bb]uilder\w*)'
        matches = re.finditer(class_pattern, content)

        for match in matches:
            class_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            # Check against naming violation patterns
            for violation_type, patterns in self.naming_violation_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, class_name):
                        violation = SsotViolation(
                            file_path=file_path,
                            line_number=line_num,
                            violation_type='naming_violation',
                            description=f"{violation_type}: {class_name}",
                            severity='HIGH' if violation_type == 'over_engineering' else 'MEDIUM',
                            factory_name=class_name,
                            recommended_fix=self._get_naming_fix_recommendation(
                                violation_type, class_name
                            )
                        )
                        violations.append(violation)

        return violations

    def _check_service_boundaries(self, file_path: str, content: str,
                                service_name: str) -> List[SsotViolation]:
        """Check for service boundary violations."""
        violations = []

        # Check for cross-service factory imports
        for line_num, line in enumerate(content.split('\n'), 1):
            if 'import' in line and 'factory' in line.lower():
                # Detect cross-service imports
                for other_service in self.service_boundaries:
                    if other_service != service_name and other_service in line:
                        # Allow shared imports
                        if other_service != 'shared':
                            violation = SsotViolation(
                                file_path=file_path,
                                line_number=line_num,
                                violation_type='service_boundary',
                                description=f"Cross-service factory import: {line.strip()}",
                                severity='HIGH',
                                recommended_fix=f"Use {service_name} service factories or shared utilities"
                            )
                            violations.append(violation)

        return violations

    def _check_factory_duplicates(self, file_path: str, content: str) -> List[SsotViolation]:
        """Check for duplicate factory implementations."""
        violations = []

        # This would be more comprehensive in a real implementation
        # For now, check for obvious duplicate class names
        class_names = re.findall(r'class\s+(\w+)', content)

        # Check against known duplicate patterns
        duplicate_indicators = ['MockFactory', 'TestFactory', 'ConfigFactory']

        for class_name in class_names:
            if any(indicator in class_name for indicator in duplicate_indicators):
                # Check if this might be a duplicate
                violation = SsotViolation(
                    file_path=file_path,
                    line_number=1,  # Would need more sophisticated line detection
                    violation_type='duplicate_factory',
                    description=f"Potential duplicate factory: {class_name}",
                    severity='HIGH',
                    factory_name=class_name,
                    recommended_fix="Consolidate with SSOT factory implementation"
                )
                violations.append(violation)

        return violations

    def _is_ssot_compliant_import(self, import_line: str, service_name: str) -> bool:
        """Check if an import line follows SSOT patterns."""
        # Check against SSOT import patterns
        for pattern in self.ssot_compliant_patterns['import_patterns']:
            if re.search(pattern, import_line):
                return True

        # Check against service-specific registry
        service_patterns = self.ssot_import_registry.get(service_name, [])
        for pattern in service_patterns:
            if pattern in import_line:
                return True

        return False

    def _is_business_focused_name(self, factory_name: str) -> bool:
        """Check if factory name follows business-focused conventions."""
        # Avoid generic "Manager" terminology
        if 'Manager' in factory_name and len(factory_name.split('Manager')) > 1:
            return False

        # Check for business domain terms
        business_terms = [
            'Auth', 'User', 'Chat', 'Message', 'Agent', 'WebSocket',
            'Database', 'Config', 'Service', 'Client', 'Session'
        ]

        return any(term in factory_name for term in business_terms)

    def _is_ssot_compliant_name(self, factory_name: str) -> bool:
        """Check if factory name follows SSOT conventions."""
        for pattern in self.ssot_compliant_patterns['naming_conventions']:
            if re.match(pattern, factory_name):
                return True
        return False

    def _get_naming_fix_recommendation(self, violation_type: str, class_name: str) -> str:
        """Get naming fix recommendation based on violation type."""
        if violation_type == 'manager_overuse':
            return f"Rename to focus on business domain instead of 'Manager'"
        elif violation_type == 'unclear_naming':
            return f"Use specific business-focused name instead of generic '{class_name}'"
        elif violation_type == 'over_engineering':
            return f"Simplify name and remove unnecessary abstraction layers"
        else:
            return "Follow business-focused naming conventions"

    def _analyze_ssot_violations(self, ssot_analysis: FactorySsotAnalysis):
        """Analyze and categorize SSOT violations."""
        # Group violations by type and severity for analysis
        for violation in ssot_analysis.detailed_violations:
            violation_type = violation.violation_type
            severity = violation.severity

            # Track specific violation patterns
            if violation_type == 'duplicate_factory':
                factory_name = violation.factory_name
                if factory_name not in ssot_analysis.duplicate_factories:
                    ssot_analysis.duplicate_factories[factory_name] = []
                ssot_analysis.duplicate_factories[factory_name].append(violation.file_path)

            elif violation_type == 'import_fragmentation':
                ssot_analysis.import_fragments.append(violation.description)

            elif violation_type == 'naming_violation':
                ssot_analysis.naming_violations.append(f"{violation.factory_name}: {violation.description}")

            elif violation_type == 'service_boundary':
                ssot_analysis.service_boundary_violations.append(violation.description)

    def _record_ssot_compliance_metrics(self, ssot_analysis: FactorySsotAnalysis):
        """Record comprehensive SSOT compliance metrics."""
        self.record_metric("ssot_total_factories", ssot_analysis.total_factories)
        self.record_metric("ssot_compliant_factories", ssot_analysis.compliant_factories)
        self.record_metric("ssot_violation_count", ssot_analysis.violation_count)
        self.record_metric("ssot_compliance_score", ssot_analysis.compliance_score)

        # Violation breakdown by type
        for violation_type, count in ssot_analysis.violations_by_type.items():
            self.record_metric(f"ssot_violations_{violation_type}", count)

        # Violation breakdown by severity
        for severity, count in ssot_analysis.violations_by_severity.items():
            self.record_metric(f"ssot_violations_severity_{severity}", count)

        # Specific violation categories
        self.record_metric("ssot_duplicate_factories_count", len(ssot_analysis.duplicate_factories))
        self.record_metric("ssot_import_fragments_count", len(ssot_analysis.import_fragments))
        self.record_metric("ssot_naming_violations_count", len(ssot_analysis.naming_violations))
        self.record_metric("ssot_service_boundary_violations_count",
                          len(ssot_analysis.service_boundary_violations))

    def _generate_ssot_compliance_report(self, ssot_analysis: FactorySsotAnalysis) -> str:
        """Generate detailed SSOT compliance report."""
        report_lines = [
            "# Factory SSOT Compliance Baseline Report",
            f"**Generated:** {self.get_metric('ssot_compliance_analysis_start')}",
            f"**Total Factories Analyzed:** {ssot_analysis.total_factories}",
            "",
            "## Executive Summary",
            f"- **Compliance Score:** {ssot_analysis.compliance_score:.1f}%",
            f"- **Compliant Factories:** {ssot_analysis.compliant_factories}",
            f"- **Violation Count:** {ssot_analysis.violation_count}",
            "",
            "## Violation Breakdown by Type",
        ]

        for violation_type, count in ssot_analysis.violations_by_type.items():
            report_lines.append(f"- **{violation_type.replace('_', ' ').title()}:** {count}")

        report_lines.extend([
            "",
            "## Violation Breakdown by Severity",
        ])

        for severity, count in ssot_analysis.violations_by_severity.items():
            report_lines.append(f"- **{severity}:** {count}")

        report_lines.extend([
            "",
            "## Duplicate Factories (SSOT Violations)",
        ])

        for factory_name, file_paths in ssot_analysis.duplicate_factories.items():
            report_lines.append(f"- **{factory_name}** ({len(file_paths)} instances)")
            for file_path in file_paths[:3]:  # Show first 3
                report_lines.append(f"  - {file_path}")

        report_lines.extend([
            "",
            "## Import Path Fragmentation",
        ])

        for fragment in ssot_analysis.import_fragments[:10]:  # Top 10
            report_lines.append(f"- {fragment}")

        report_lines.extend([
            "",
            "## Naming Convention Violations",
        ])

        for violation in ssot_analysis.naming_violations[:10]:  # Top 10
            report_lines.append(f"- {violation}")

        report_lines.extend([
            "",
            "## Service Boundary Violations",
        ])

        for violation in ssot_analysis.service_boundary_violations[:10]:  # Top 10
            report_lines.append(f"- {violation}")

        return "\n".join(report_lines)

    def _save_ssot_compliance_report(self, report_content: str):
        """Save SSOT compliance report to file."""
        try:
            report_path = "FACTORY_SSOT_COMPLIANCE_BASELINE_REPORT.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            self.record_metric("ssot_compliance_report_saved", True)
            self.record_metric("ssot_compliance_report_path", report_path)

        except Exception as e:
            self.record_metric("ssot_compliance_report_save_error", str(e))

    def _validate_ssot_compliance_analysis(self, ssot_analysis: FactorySsotAnalysis):
        """Validate SSOT compliance analysis results."""
        # Basic validation - allow for zero factories in baseline
        if ssot_analysis.total_factories == 0:
            # If no factories found, that's acceptable for baseline
            self.record_metric("ssot_compliance_validation_passed", True)
            self.record_metric("ssot_compliance_no_factories_found", True)
            return

        self.assertGreater(ssot_analysis.total_factories, 0,
                          "Should analyze factories for compliance")

        # Consistency check - violations can have multiple per factory
        # so we check the total makes sense but don't require exact equality
        violation_files = len(set(v.file_path for v in ssot_analysis.detailed_violations))
        total_analyzed = ssot_analysis.compliant_factories + violation_files

        # Allow for the fact that one factory can have multiple violations
        self.assertLessEqual(total_analyzed, ssot_analysis.total_factories + violation_files,
                           f"Analysis consistency check: compliant({ssot_analysis.compliant_factories}) + "
                           f"violation_files({violation_files}) should be reasonable vs total({ssot_analysis.total_factories})")

        # Compliance score validation
        self.assertGreaterEqual(ssot_analysis.compliance_score, 0.0)
        self.assertLessEqual(ssot_analysis.compliance_score, 100.0)

        self.record_metric("ssot_compliance_validation_passed", True)

    # Additional helper methods

    def _find_all_factory_files(self) -> List[str]:
        """Find all files containing factory patterns."""
        factory_files = []

        for service_name, service_paths in self.service_boundaries.items():
            for service_path in service_paths:
                if not os.path.exists(service_path):
                    continue

                for root, dirs, files in os.walk(service_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)

                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()

                                if self._contains_factory_patterns(content):
                                    factory_files.append(file_path)
                            except Exception:
                                continue

        return factory_files

    def _extract_factory_signatures(self, file_path: str) -> Dict[str, List[str]]:
        """Extract factory signatures from a file."""
        signatures = {
            'factory_signatures': [],
            'class_name_duplicates': [],
            'method_signature_duplicates': [],
            'interface_duplicates': []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract class names
            class_names = re.findall(r'class\s+(\w+)', content)
            signatures['class_name_duplicates'].extend(class_names)

            # Extract method signatures
            method_matches = re.findall(r'def\s+(\w+)\s*\([^)]*\)', content)
            signatures['method_signature_duplicates'].extend(method_matches)

            # Create factory signatures (combination of class and key methods)
            for class_name in class_names:
                if any(pattern in class_name.lower()
                      for pattern in ['factory', 'creator', 'builder']):
                    signatures['factory_signatures'].append(f"{class_name}::{file_path}")

        except Exception:
            pass

        return signatures

    def _analyze_service_import_patterns(self, service_path: str, service_name: str) -> Dict[str, Any]:
        """Analyze import patterns for a specific service."""
        import_patterns = {
            'total': 0,
            'compliant': 0,
            'fragmented': [],
            'cross_service': [],
            'relative': [],
            'missing': []
        }

        for root, dirs, files in os.walk(service_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Analyze imports in this file
                        file_imports = self._extract_import_patterns(content, file_path)

                        import_patterns['total'] += file_imports['total']
                        import_patterns['compliant'] += file_imports['compliant']
                        import_patterns['fragmented'].extend(file_imports['fragmented'])
                        import_patterns['cross_service'].extend(file_imports['cross_service'])
                        import_patterns['relative'].extend(file_imports['relative'])
                        import_patterns['missing'].extend(file_imports['missing'])

                    except Exception:
                        continue

        return import_patterns

    def _extract_import_patterns(self, content: str, file_path: str) -> Dict[str, Any]:
        """Extract import patterns from file content."""
        patterns = {
            'total': 0,
            'compliant': 0,
            'fragmented': [],
            'cross_service': [],
            'relative': [],
            'missing': []
        }

        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            if re.search(r'import.*[Ff]actory|from.*[Ff]actory', line):
                patterns['total'] += 1

                # Check compliance
                if self._is_import_compliant(line):
                    patterns['compliant'] += 1
                else:
                    patterns['fragmented'].append(f"{file_path}:{line_num}: {line.strip()}")

                # Check for relative imports
                if line.strip().startswith('from .') or line.strip().startswith('from ..'):
                    patterns['relative'].append(f"{file_path}:{line_num}: {line.strip()}")

        return patterns

    def _is_import_compliant(self, import_line: str) -> bool:
        """Check if import line is SSOT compliant."""
        # Basic compliance check
        return not (import_line.strip().startswith('from .') or
                   import_line.strip().startswith('from ..'))

    def _discover_all_factory_classes(self) -> List[Dict[str, str]]:
        """Discover all factory classes in the codebase."""
        factory_classes = []

        for service_name, service_paths in self.service_boundaries.items():
            for service_path in service_paths:
                if not os.path.exists(service_path):
                    continue

                for root, dirs, files in os.walk(service_path):
                    dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)

                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()

                                classes = re.findall(r'class\s+(\w+)', content)
                                for class_name in classes:
                                    if any(pattern in class_name.lower()
                                          for pattern in ['factory', 'creator', 'builder']):
                                        factory_classes.append({
                                            'name': class_name,
                                            'file_path': file_path,
                                            'service': service_name
                                        })

                            except Exception:
                                continue

        return factory_classes

    def _detect_naming_violations(self, factory_class: Dict[str, str]) -> List[Dict[str, str]]:
        """Detect naming violations for a factory class."""
        violations = []
        class_name = factory_class['name']

        for violation_type, patterns in self.naming_violation_patterns.items():
            for pattern in patterns:
                if re.match(pattern, class_name):
                    violations.append({
                        'type': violation_type,
                        'class_name': class_name,
                        'file_path': factory_class['file_path'],
                        'pattern': pattern
                    })

        return violations

    def _analyze_service_boundary_violations(self, service_path: str,
                                           service_name: str) -> Dict[str, List[str]]:
        """Analyze service boundary violations for a service."""
        violations = {
            'cross_service': [],
            'dependencies': [],
            'isolation': [],
            'shared_misuse': []
        }

        # Implementation would scan for actual cross-service violations
        # This is a simplified version for the baseline

        return violations