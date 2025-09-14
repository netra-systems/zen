"""NEW SSOT Test 1: MessageRouter Consolidation Pre/Post Validation

This test validates that MessageRouter consolidation maintains functionality while
achieving Single Source of Truth compliance. It tests the consolidation process
itself and validates that Golden Path functionality remains intact.

Business Value: Platform/Internal - SSOT Consolidation Success Validation
- Validates consolidation doesn't break $500K+ ARR chat functionality
- Ensures message routing remains reliable during SSOT migration
- Provides automated pre/post consolidation verification
- Protects against regression during MessageRouter unification

EXPECTED BEHAVIOR:
- FAIL initially: Multiple implementations detected, consolidation needed
- PASS after consolidation: Single implementation with preserved functionality
- Provides specific consolidation guidance and validation criteria

GitHub Issue: #952 - MessageRouter SSOT consolidation via gardener process
"""

import ast
import unittest
from typing import Dict, List, Set, Optional, Any, Tuple
from pathlib import Path

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestMessageRouterConsolidationValidation(SSotBaseTestCase, unittest.TestCase):
    """Validates MessageRouter consolidation process and functionality preservation."""

    def setUp(self):
        """Set up test fixtures."""
        if hasattr(super(), 'setUp'):
            super().setUp()
        
        # Initialize logger
        import logging
        self.logger = logging.getLogger(__name__)
        
        # Consolidation targets
        self.canonical_location = "netra_backend/app/websocket_core/handlers.py"
        self.canonical_class = "MessageRouter"
        
        # Known implementations (for consolidation tracking)
        self.known_implementations = {
            "netra_backend/app/core/message_router.py": "MessageRouter",
            "netra_backend/app/websocket_core/handlers.py": "MessageRouter",
            "netra_backend/app/services/websocket/quality_message_router.py": "QualityMessageRouter"
        }
        
        self.base_path = Path(__file__).parent.parent.parent
        
        # Critical functionality that must be preserved
        self.required_consolidation_methods = {
            '__init__',
            'add_handler',
            'route_message',
            'handlers'
        }

    def test_consolidation_readiness_assessment(self):
        """Test readiness for MessageRouter consolidation.
        
        EXPECTED: FAIL initially - Multiple implementations prevent consolidation
        EXPECTED: PASS after preparation - Ready for safe consolidation
        """
        readiness_issues = self._assess_consolidation_readiness()
        
        if readiness_issues['blocking_issues']:
            blocking_summary = self._format_blocking_issues(readiness_issues['blocking_issues'])
            self.fail(
                f" FAIL:  CONSOLIDATION NOT READY: {len(readiness_issues['blocking_issues'])} "
                f"blocking issues prevent safe MessageRouter consolidation.\n"
                f"BUSINESS IMPACT: Premature consolidation risks breaking $500K+ ARR chat functionality.\n"
                f"REQUIRED ACTIONS BEFORE CONSOLIDATION:\n{blocking_summary}"
            )
        
        if readiness_issues['warning_issues']:
            warning_summary = self._format_warning_issues(readiness_issues['warning_issues'])
            self.logger.warning(f"Consolidation warnings (review recommended):\n{warning_summary}")
        
        self.logger.info(" PASS:  MessageRouter consolidation readiness confirmed")

    def test_functional_equivalence_validation(self):
        """Test that all MessageRouter implementations provide equivalent core functionality.
        
        EXPECTED: FAIL initially - Implementations have different interfaces/capabilities
        EXPECTED: PASS during consolidation - Unified interface validated
        """
        implementations = self._discover_router_implementations()
        
        if len(implementations) <= 1:
            self.logger.info(" PASS:  Single implementation - functional equivalence not applicable")
            return
        
        equivalence_issues = self._validate_functional_equivalence(implementations)
        
        if equivalence_issues:
            equivalence_summary = self._format_equivalence_issues(equivalence_issues)
            self.fail(
                f" FAIL:  FUNCTIONAL EQUIVALENCE ISSUES: {len(equivalence_issues)} differences "
                f"between MessageRouter implementations.\n"
                f"BUSINESS IMPACT: Different interfaces cause routing inconsistencies and "
                f"potential chat functionality failures.\n"
                f"CONSOLIDATION REQUIREMENT: Resolve interface differences before merging.\n"
                f"EQUIVALENCE ISSUES:\n{equivalence_summary}"
            )
        
        self.logger.info(" PASS:  All MessageRouter implementations are functionally equivalent")

    def test_consolidation_target_validation(self):
        """Test that consolidation target location meets requirements.
        
        EXPECTED: FAIL initially - Target may not exist or be complete
        EXPECTED: PASS during consolidation - Target contains consolidated functionality
        """
        target_path = self.base_path / self.canonical_location
        
        if not target_path.exists():
            self.fail(
                f" FAIL:  CONSOLIDATION TARGET MISSING: {self.canonical_location} does not exist.\n"
                f"CONSOLIDATION REQUIREMENT: Target file must exist for consolidation."
            )
        
        target_validation = self._validate_consolidation_target(str(target_path))
        
        if target_validation['missing_methods']:
            missing_summary = ', '.join(target_validation['missing_methods'])
            self.fail(
                f" FAIL:  CONSOLIDATION TARGET INCOMPLETE: Target {self.canonical_location} "
                f"missing required methods: {missing_summary}.\n"
                f"BUSINESS IMPACT: Incomplete target causes chat functionality failures.\n"
                f"CONSOLIDATION REQUIREMENT: Target must contain all required functionality."
            )
        
        if target_validation['quality_issues']:
            quality_summary = '\n'.join(target_validation['quality_issues'])
            self.logger.warning(f"Target quality issues (review recommended):\n{quality_summary}")
        
        self.logger.info(f" PASS:  Consolidation target {self.canonical_location} is valid")

    def test_consumer_impact_assessment(self):
        """Test impact of consolidation on MessageRouter consumers.
        
        EXPECTED: FAIL initially - Consumers use different import paths
        EXPECTED: PASS after migration - All consumers use canonical path
        """
        consumer_analysis = self._analyze_consumer_impact()
        
        if consumer_analysis['high_risk_consumers']:
            high_risk_summary = self._format_consumer_risks(consumer_analysis['high_risk_consumers'])
            self.fail(
                f" FAIL:  HIGH RISK CONSUMERS: {len(consumer_analysis['high_risk_consumers'])} "
                f"consumers at high risk during MessageRouter consolidation.\n"
                f"BUSINESS IMPACT: Breaking changes cause immediate chat functionality failures.\n"
                f"CONSOLIDATION REQUIREMENT: Migrate high-risk consumers before consolidation.\n"
                f"HIGH RISK CONSUMERS:\n{high_risk_summary}"
            )
        
        if consumer_analysis['medium_risk_consumers']:
            medium_risk_summary = self._format_consumer_risks(consumer_analysis['medium_risk_consumers'])
            self.logger.warning(f"Medium risk consumers (test after consolidation):\n{medium_risk_summary}")
        
        self.logger.info(" PASS:  Consumer impact assessment successful")

    def test_post_consolidation_functionality_validation(self):
        """Test that post-consolidation MessageRouter maintains all required functionality.
        
        EXPECTED: FAIL if consolidation broke functionality
        EXPECTED: PASS after successful consolidation - All functionality preserved
        """
        implementations = self._discover_router_implementations()
        
        if len(implementations) > 1:
            self.logger.info(" SKIP:  Post-consolidation test - consolidation not yet complete")
            return
        
        if len(implementations) == 0:
            self.fail(
                f" FAIL:  POST-CONSOLIDATION FAILURE: No MessageRouter implementations found.\n"
                f"BUSINESS IMPACT: Complete loss of message routing breaks all chat functionality.\n"
                f"EMERGENCY ACTION: Restore MessageRouter implementation immediately."
            )
        
        # Validate single implementation functionality
        single_implementation = list(implementations.values())[0]
        functionality_issues = self._validate_post_consolidation_functionality(single_implementation)
        
        if functionality_issues['critical_issues']:
            critical_summary = '\n'.join(functionality_issues['critical_issues'])
            self.fail(
                f" FAIL:  POST-CONSOLIDATION CRITICAL ISSUES: Consolidated MessageRouter "
                f"has {len(functionality_issues['critical_issues'])} critical functionality issues.\n"
                f"BUSINESS IMPACT: Broken message routing causes immediate chat failures.\n"
                f"CRITICAL ISSUES:\n{critical_summary}"
            )
        
        if functionality_issues['warning_issues']:
            warning_summary = '\n'.join(functionality_issues['warning_issues'])
            self.logger.warning(f"Post-consolidation warnings:\n{warning_summary}")
        
        self.logger.info(" PASS:  Post-consolidation MessageRouter functionality validated")

    def _assess_consolidation_readiness(self) -> Dict[str, List[str]]:
        """Assess readiness for safe MessageRouter consolidation."""
        issues = {'blocking_issues': [], 'warning_issues': []}
        
        # Check for multiple implementations
        implementations = self._discover_router_implementations()
        if len(implementations) <= 1:
            issues['warning_issues'].append("Only 1 implementation found - consolidation may not be needed")
            return issues
        
        # Check target exists and is suitable
        target_path = self.base_path / self.canonical_location
        if not target_path.exists():
            issues['blocking_issues'].append(f"Consolidation target {self.canonical_location} does not exist")
        
        # Check for incompatible interfaces
        equivalence_issues = self._validate_functional_equivalence(implementations)
        if equivalence_issues:
            issues['blocking_issues'].append(f"{len(equivalence_issues)} interface incompatibilities detected")
        
        # Check consumer dependency complexity
        consumer_analysis = self._analyze_consumer_impact()
        if consumer_analysis['high_risk_consumers']:
            issues['blocking_issues'].append(
                f"{len(consumer_analysis['high_risk_consumers'])} high-risk consumers require migration"
            )
        
        return issues

    def _discover_router_implementations(self) -> Dict[str, Dict[str, Any]]:
        """Discover non-test MessageRouter implementations."""
        implementations = {}
        
        for rel_path, class_name in self.known_implementations.items():
            full_path = self.base_path / rel_path
            if full_path.exists():
                router_info = self._extract_router_info(str(full_path), class_name)
                if router_info:
                    implementations[rel_path] = router_info
        
        return implementations

    def _extract_router_info(self, file_path: str, class_name: str) -> Optional[Dict[str, Any]]:
        """Extract information about a router implementation."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    methods = []
                    properties = []
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append(item.name)
                        elif isinstance(item, ast.Assign):
                            # Extract property assignments
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    properties.append(target.id)
                    
                    return {
                        'class_name': class_name,
                        'file_path': file_path,
                        'methods': set(methods),
                        'properties': set(properties),
                        'line_number': node.lineno,
                        'line_count': (node.end_lineno or node.lineno) - node.lineno + 1
                    }
        
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            pass
        
        return None

    def _validate_functional_equivalence(self, implementations: Dict[str, Dict[str, Any]]) -> List[str]:
        """Validate that implementations provide equivalent functionality."""
        equivalence_issues = []
        
        if len(implementations) <= 1:
            return equivalence_issues
        
        # Compare method signatures across implementations
        all_methods = set()
        for impl in implementations.values():
            all_methods.update(impl['methods'])
        
        # Check each implementation has core methods
        for rel_path, impl in implementations.items():
            missing_core = self.required_consolidation_methods - impl['methods']
            if missing_core:
                equivalence_issues.append(
                    f"{rel_path} missing core methods: {', '.join(missing_core)}"
                )
        
        # Check for method signature consistency (simplified check)
        method_sources = {}
        for rel_path, impl in implementations.items():
            for method in impl['methods']:
                if method not in method_sources:
                    method_sources[method] = []
                method_sources[method].append(rel_path)
        
        # Report methods that exist in some but not all implementations
        for method, sources in method_sources.items():
            if len(sources) != len(implementations) and method in self.required_consolidation_methods:
                missing_in = set(implementations.keys()) - set(sources)
                equivalence_issues.append(
                    f"Core method '{method}' missing in: {', '.join(missing_in)}"
                )
        
        return equivalence_issues

    def _validate_consolidation_target(self, target_path: str) -> Dict[str, Any]:
        """Validate that consolidation target is suitable."""
        validation_result = {
            'missing_methods': [],
            'quality_issues': []
        }
        
        target_info = self._extract_router_info(target_path, self.canonical_class)
        if not target_info:
            validation_result['missing_methods'] = list(self.required_consolidation_methods)
            return validation_result
        
        # Check for required methods
        missing_methods = self.required_consolidation_methods - target_info['methods']
        validation_result['missing_methods'] = list(missing_methods)
        
        # Check quality indicators
        if target_info['line_count'] > 2000:
            validation_result['quality_issues'].append("Target class very large (>2000 lines)")
        
        if len(target_info['methods']) > 30:
            validation_result['quality_issues'].append("Target has many methods (>30) - consider refactoring")
        
        return validation_result

    def _analyze_consumer_impact(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze impact on MessageRouter consumers."""
        consumer_analysis = {
            'high_risk_consumers': [],
            'medium_risk_consumers': [],
            'low_risk_consumers': []
        }
        
        # Scan for import statements
        for py_file in self.base_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for MessageRouter imports
                risk_assessment = self._assess_consumer_risk(str(py_file), content)
                if risk_assessment:
                    if risk_assessment['risk_level'] == 'HIGH':
                        consumer_analysis['high_risk_consumers'].append(risk_assessment)
                    elif risk_assessment['risk_level'] == 'MEDIUM':
                        consumer_analysis['medium_risk_consumers'].append(risk_assessment)
                    else:
                        consumer_analysis['low_risk_consumers'].append(risk_assessment)
            
            except (UnicodeDecodeError, PermissionError):
                continue
        
        return consumer_analysis

    def _assess_consumer_risk(self, file_path: str, content: str) -> Optional[Dict[str, Any]]:
        """Assess consolidation risk for a single consumer file."""
        if 'MessageRouter' not in content or 'import' not in content:
            return None
        
        # Extract import statements
        import_lines = []
        for line_num, line in enumerate(content.split('\n'), 1):
            if 'import' in line and 'MessageRouter' in line:
                import_lines.append((line_num, line.strip()))
        
        if not import_lines:
            return None
        
        # Assess risk level
        risk_level = 'LOW'
        risk_factors = []
        
        # Check for direct instantiation
        if 'MessageRouter(' in content:
            risk_level = 'HIGH'
            risk_factors.append("Direct MessageRouter instantiation")
        
        # Check for method calls
        router_methods = ['add_handler', 'route_message', 'handlers']
        for method in router_methods:
            if f'.{method}(' in content:
                if risk_level == 'LOW':
                    risk_level = 'MEDIUM'
                risk_factors.append(f"Calls {method}() method")
        
        # Check for non-canonical imports
        for line_num, line in import_lines:
            if self.canonical_location.replace('/', '.').replace('.py', '') not in line:
                risk_level = 'HIGH'
                risk_factors.append(f"Non-canonical import at line {line_num}")
        
        return {
            'file_path': file_path,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'import_lines': import_lines
        }

    def _validate_post_consolidation_functionality(self, implementation: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate functionality after consolidation."""
        functionality_issues = {
            'critical_issues': [],
            'warning_issues': []
        }
        
        # Check for required methods
        missing_core = self.required_consolidation_methods - implementation['methods']
        if missing_core:
            functionality_issues['critical_issues'].append(
                f"Missing core methods: {', '.join(missing_core)}"
            )
        
        # Check for reasonable complexity
        if implementation['line_count'] > 3000:
            functionality_issues['warning_issues'].append(
                f"Very large implementation ({implementation['line_count']} lines)"
            )
        
        if len(implementation['methods']) > 50:
            functionality_issues['warning_issues'].append(
                f"Many methods ({len(implementation['methods'])}) - consider refactoring"
            )
        
        return functionality_issues

    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped."""
        skip_patterns = [
            '__pycache__', '.git', '.pytest_cache', 'node_modules',
            '.venv', '.test_venv', 'venv'
        ]
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _format_blocking_issues(self, issues: List[str]) -> str:
        """Format blocking issues for error reporting."""
        return '\n'.join(f"  - {issue}" for issue in issues)

    def _format_warning_issues(self, issues: List[str]) -> str:
        """Format warning issues for logging."""
        return '\n'.join(f"  - {issue}" for issue in issues)

    def _format_equivalence_issues(self, issues: List[str]) -> str:
        """Format equivalence issues for error reporting."""
        return '\n'.join(f"  - {issue}" for issue in issues)

    def _format_consumer_risks(self, consumers: List[Dict[str, Any]]) -> str:
        """Format consumer risks for reporting."""
        formatted = []
        for consumer in consumers[:5]:  # Limit to first 5 for readability
            rel_path = consumer['file_path'].replace(str(self.base_path), "").lstrip('/')
            factors = ', '.join(consumer['risk_factors'][:3])  # Limit factors
            formatted.append(f"  - {rel_path}: {factors}")
        
        if len(consumers) > 5:
            formatted.append(f"  ... and {len(consumers) - 5} more")
        
        return '\n'.join(formatted)


if __name__ == "__main__":
    import unittest
    unittest.main()