"""
Phase 1: Factory Discovery and Classification Tests
Issue #1194 - Factory Over-Engineering Remediation

Purpose:
Comprehensive tests to discover, classify, and validate removal of over-engineered factory classes
while preserving essential factory patterns that provide genuine business value.

Test Design:
- Scans entire codebase for factory classes
- Classifies by complexity metrics and usage patterns
- Identifies over-engineering candidates for removal
- Validates business value justification for each factory

Business Impact: $500K+ ARR protection through architectural simplification
SSOT Compliance: Identifies duplicate factory patterns and consolidation opportunities

These tests are designed to FAIL initially to demonstrate the current over-engineering problem.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from unittest.mock import patch
import warnings

from test_framework.ssot.base_test_case import SSotBaseTestCase


class FactoryComplexityAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze factory class complexity."""

    def __init__(self):
        self.classes = []
        self.methods = []
        self.imports = []
        self.lines_of_code = 0
        self.cyclomatic_complexity = 0
        self.inheritance_depth = 0

    def visit_ClassDef(self, node):
        """Visit class definitions to analyze factory patterns."""
        is_factory = 'factory' in node.name.lower() or 'Factory' in node.name

        if is_factory:
            # Calculate method count and complexity
            methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
            static_methods = [m for m in methods if any(isinstance(d, ast.Name) and d.id == 'staticmethod' for d in m.decorator_list)]

            # Calculate inheritance depth
            bases = len(node.bases)

            class_info = {
                'name': node.name,
                'line_start': node.lineno,
                'line_end': node.end_lineno if hasattr(node, 'end_lineno') else node.lineno,
                'method_count': len(methods),
                'static_method_count': len(static_methods),
                'inheritance_depth': bases,
                'is_abstract': any(d.id == 'ABC' for d in node.bases if isinstance(d, ast.Name)),
                'docstring': ast.get_docstring(node),
                'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
            }
            self.classes.append(class_info)

        self.generic_visit(node)

    def visit_Import(self, node):
        """Track imports to understand dependencies."""
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        """Track from imports to understand dependencies."""
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")


class FactoryOverEngineeringDetectionTests(SSotBaseTestCase):
    """
    Phase 1: Factory Discovery and Classification

    Tests designed to identify over-engineered factory classes and validate
    removal candidates while protecting essential business patterns.
    """

    def setUp(self):
        """Set up test environment for factory analysis."""
        super().setUp()
        self.project_root = Path(__file__).parents[2]  # Go up to project root
        self.factory_files = []
        self.factory_classes = {}
        self.over_engineering_candidates = []

        # Business value thresholds for factory classification
        self.complexity_thresholds = {
            'simple_factory': {'methods': 3, 'lines': 50, 'static_methods': 2},
            'moderate_factory': {'methods': 8, 'lines': 200, 'static_methods': 5},
            'complex_factory': {'methods': 15, 'lines': 400, 'static_methods': 8},
            'over_engineered': {'methods': 20, 'lines': 600, 'static_methods': 10}
        }

        # Essential factory patterns that provide business value
        self.essential_patterns = {
            'user_isolation_factories',  # Critical for multi-user security
            'websocket_event_factories',  # Critical for $500K+ ARR chat functionality
            'database_connection_factories',  # Critical for data access patterns
            'auth_token_factories',  # Critical for security
            'test_mock_factories'  # Critical for testing infrastructure
        }

    def test_01_discover_all_factory_files(self):
        """
        Test 1: Comprehensive Factory File Discovery

        Scans entire codebase to find all files containing factory classes.
        This test should identify ALL factory implementations including hidden ones.

        Expected Result: FAIL - Demonstrates breadth of factory usage across codebase
        """
        print(f"\n🔍 PHASE 1.1: Scanning {self.project_root} for factory files...")

        factory_patterns = [
            r'.*factory.*\.py$',
            r'.*Factory.*\.py$',
            r'.*_factory\.py$',
            r'.*Factory_.*\.py$'
        ]

        discovered_files = []

        # Scan all Python files for factory patterns
        for pattern in factory_patterns:
            for py_file in self.project_root.rglob("*.py"):
                if re.match(pattern, py_file.name, re.IGNORECASE):
                    if py_file not in discovered_files:
                        discovered_files.append(py_file)

        # Also scan file contents for factory classes
        for py_file in self.project_root.rglob("*.py"):
            # Skip virtual environment and backup files
            if 'venv' in str(py_file) or '.backup' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if re.search(r'class\s+\w*[Ff]actory\w*\s*[\(\:]', content):
                        if py_file not in discovered_files:
                            discovered_files.append(py_file)
            except Exception as e:
                # Skip files we can't read
                continue

        self.factory_files = discovered_files

        print(f"📊 Discovered {len(discovered_files)} factory files")
        for file_path in discovered_files[:20]:  # Show first 20
            print(f"  📄 {file_path.relative_to(self.project_root)}")

        if len(discovered_files) > 20:
            print(f"  ... and {len(discovered_files) - 20} more files")

        # This test should FAIL to demonstrate the scope of factory usage
        self.assertLess(
            len(discovered_files),
            20,
            f"❌ OVER-ENGINEERING DETECTED: Found {len(discovered_files)} factory files. "
            f"Expected <20 for a healthy architecture. This demonstrates the scope of factory over-engineering."
        )

    def test_02_classify_factory_complexity_patterns(self):
        """
        Test 2: Factory Complexity Classification

        Analyzes each discovered factory class for complexity metrics:
        - Lines of code
        - Method count
        - Inheritance depth
        - Static method usage
        - Business value indicators

        Expected Result: FAIL - Demonstrates over-complex factory patterns
        """
        print(f"\n📏 PHASE 1.2: Analyzing factory complexity patterns...")

        if not self.factory_files:
            # Run discovery if not already done
            self.test_01_discover_all_factory_files()

        complexity_analysis = {
            'simple': [],
            'moderate': [],
            'complex': [],
            'over_engineered': []
        }

        total_factories = 0

        for factory_file in self.factory_files:
            try:
                with open(factory_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Parse AST to analyze structure
                try:
                    tree = ast.parse(content)
                    analyzer = FactoryComplexityAnalyzer()
                    analyzer.visit(tree)

                    for class_info in analyzer.classes:
                        total_factories += 1

                        # Calculate complexity score
                        lines = class_info['line_end'] - class_info['line_start']
                        methods = class_info['method_count']
                        static_methods = class_info['static_method_count']

                        # Classify by complexity
                        if (methods >= self.complexity_thresholds['over_engineered']['methods'] or
                            lines >= self.complexity_thresholds['over_engineered']['lines']):
                            category = 'over_engineered'
                        elif (methods >= self.complexity_thresholds['complex']['methods'] or
                              lines >= self.complexity_thresholds['complex']['lines']):
                            category = 'complex'
                        elif (methods >= self.complexity_thresholds['moderate']['methods'] or
                              lines >= self.complexity_thresholds['moderate']['lines']):
                            category = 'moderate'
                        else:
                            category = 'simple'

                        factory_data = {
                            'file': str(factory_file.relative_to(self.project_root)),
                            'class_name': class_info['name'],
                            'lines': lines,
                            'methods': methods,
                            'static_methods': static_methods,
                            'inheritance_depth': class_info['inheritance_depth'],
                            'has_docstring': class_info['docstring'] is not None,
                            'business_justification': self._extract_business_justification(class_info['docstring'])
                        }

                        complexity_analysis[category].append(factory_data)

                except SyntaxError:
                    # Skip files with syntax errors
                    continue

            except Exception as e:
                # Skip files we can't process
                continue

        print(f"\n📊 COMPLEXITY ANALYSIS RESULTS:")
        print(f"  ✅ Simple factories: {len(complexity_analysis['simple'])}")
        print(f"  ⚠️  Moderate factories: {len(complexity_analysis['moderate'])}")
        print(f"  🔴 Complex factories: {len(complexity_analysis['complex'])}")
        print(f"  💀 Over-engineered factories: {len(complexity_analysis['over_engineered'])}")
        print(f"  📈 Total factories analyzed: {total_factories}")

        # Show top over-engineered candidates
        print(f"\n🚨 TOP OVER-ENGINEERED FACTORY CANDIDATES:")
        over_engineered_sorted = sorted(
            complexity_analysis['over_engineered'],
            key=lambda x: x['methods'] + (x['lines'] / 10),
            reverse=True
        )

        for i, factory in enumerate(over_engineered_sorted[:10]):
            print(f"  {i+1}. {factory['class_name']} ({factory['file']})")
            print(f"     📏 {factory['lines']} lines, {factory['methods']} methods")
            print(f"     💼 Business justification: {factory['business_justification']}")

        self.factory_classes = complexity_analysis

        # This test should FAIL to demonstrate over-engineering
        over_engineered_count = len(complexity_analysis['over_engineered'])
        self.assertLessEqual(
            over_engineered_count,
            5,
            f"❌ OVER-ENGINEERING DETECTED: Found {over_engineered_count} over-engineered factories. "
            f"Expected ≤5 for healthy architecture. These factories are candidates for removal."
        )

    def test_03_identify_single_use_factory_patterns(self):
        """
        Test 3: Single-Use Factory Pattern Detection

        Identifies factory classes that are only used in one place, indicating
        potential over-engineering where direct instantiation would be simpler.

        Expected Result: FAIL - Shows factories that could be simplified
        """
        print(f"\n🔍 PHASE 1.3: Detecting single-use factory patterns...")

        if not self.factory_classes:
            self.test_02_classify_factory_complexity_patterns()

        single_use_candidates = []

        # Analyze usage patterns for each factory
        all_factories = (self.factory_classes['simple'] +
                        self.factory_classes['moderate'] +
                        self.factory_classes['complex'] +
                        self.factory_classes['over_engineered'])

        for factory in all_factories:
            usage_count = self._count_factory_usage(factory['class_name'])

            if usage_count <= 2:  # Only used once or twice (including definition)
                single_use_candidates.append({
                    **factory,
                    'usage_count': usage_count,
                    'removal_candidate': True,
                    'simplification_benefit': 'Replace with direct instantiation'
                })

        print(f"📊 SINGLE-USE FACTORY ANALYSIS:")
        print(f"  🔍 Total factories analyzed: {len(all_factories)}")
        print(f"  🎯 Single-use candidates: {len(single_use_candidates)}")

        print(f"\n🚨 TOP SINGLE-USE FACTORY REMOVAL CANDIDATES:")
        for i, candidate in enumerate(single_use_candidates[:15]):
            print(f"  {i+1}. {candidate['class_name']} ({candidate['file']})")
            print(f"     📊 Used {candidate['usage_count']} times, {candidate['lines']} lines")
            print(f"     🎯 Benefit: {candidate['simplification_benefit']}")

        # This test should FAIL to demonstrate single-use over-engineering
        self.assertLessEqual(
            len(single_use_candidates),
            3,
            f"❌ SINGLE-USE OVER-ENGINEERING DETECTED: Found {len(single_use_candidates)} single-use factories. "
            f"Expected ≤3 for efficient architecture. These factories can be replaced with direct instantiation."
        )

    def test_04_validate_business_value_justification(self):
        """
        Test 4: Business Value Justification Validation

        Validates that each factory class provides genuine business value through:
        - User isolation (multi-user security)
        - Performance optimization
        - Complex instantiation logic
        - Testing infrastructure needs

        Expected Result: FAIL - Shows factories without clear business justification
        """
        print(f"\n💼 PHASE 1.4: Validating business value justification...")

        if not self.factory_classes:
            self.test_02_classify_factory_complexity_patterns()

        unjustified_factories = []

        all_factories = (self.factory_classes['simple'] +
                        self.factory_classes['moderate'] +
                        self.factory_classes['complex'] +
                        self.factory_classes['over_engineered'])

        for factory in all_factories:
            business_value_score = self._calculate_business_value_score(factory)

            if business_value_score < 3:  # Threshold for justified business value
                unjustified_factories.append({
                    **factory,
                    'business_value_score': business_value_score,
                    'justification_issues': self._identify_justification_issues(factory)
                })

        print(f"📊 BUSINESS VALUE ANALYSIS:")
        print(f"  💼 Total factories analyzed: {len(all_factories)}")
        print(f"  ❌ Unjustified factories: {len(unjustified_factories)}")
        print(f"  ✅ Justified factories: {len(all_factories) - len(unjustified_factories)}")

        print(f"\n🚨 FACTORIES WITHOUT CLEAR BUSINESS JUSTIFICATION:")
        for i, factory in enumerate(unjustified_factories[:12]):
            print(f"  {i+1}. {factory['class_name']} ({factory['file']})")
            print(f"     🎯 Business value score: {factory['business_value_score']}/10")
            print(f"     ❌ Issues: {', '.join(factory['justification_issues'])}")

        # Store for later phases
        self.over_engineering_candidates = unjustified_factories

        # This test should FAIL to demonstrate lack of business justification
        self.assertLessEqual(
            len(unjustified_factories),
            5,
            f"❌ BUSINESS VALUE GAP DETECTED: Found {len(unjustified_factories)} factories without clear business justification. "
            f"Expected ≤5 for value-driven architecture. These factories are prime candidates for removal."
        )

    def test_05_generate_factory_removal_recommendations(self):
        """
        Test 5: Factory Removal Recommendations

        Generates comprehensive recommendations for factory removal based on:
        - Complexity analysis
        - Single-use patterns
        - Business value gaps
        - SSOT consolidation opportunities

        Expected Result: PASS - Provides actionable removal plan
        """
        print(f"\n📋 PHASE 1.5: Generating factory removal recommendations...")

        # Run all previous analyses if not done
        if not self.factory_classes:
            self.test_02_classify_factory_complexity_patterns()
        if not hasattr(self, 'over_engineering_candidates') or not self.over_engineering_candidates:
            self.test_04_validate_business_value_justification()

        removal_recommendations = {
            'immediate_removal': [],  # Can be removed immediately
            'consolidation_candidates': [],  # Should be consolidated with other factories
            'refactor_candidates': [],  # Should be simplified but kept
            'preserve_essential': []  # Must be preserved for business value
        }

        all_factories = (self.factory_classes['simple'] +
                        self.factory_classes['moderate'] +
                        self.factory_classes['complex'] +
                        self.factory_classes['over_engineered'])

        for factory in all_factories:
            recommendation = self._generate_factory_recommendation(factory)
            category = recommendation['category']
            removal_recommendations[category].append(recommendation)

        print(f"📋 FACTORY REMOVAL RECOMMENDATIONS:")
        print(f"  🗑️  Immediate removal: {len(removal_recommendations['immediate_removal'])}")
        print(f"  🔄 Consolidation candidates: {len(removal_recommendations['consolidation_candidates'])}")
        print(f"  ♻️  Refactor candidates: {len(removal_recommendations['refactor_candidates'])}")
        print(f"  ✅ Preserve essential: {len(removal_recommendations['preserve_essential'])}")

        print(f"\n🗑️ IMMEDIATE REMOVAL CANDIDATES (Top 10):")
        for i, rec in enumerate(removal_recommendations['immediate_removal'][:10]):
            print(f"  {i+1}. {rec['class_name']} ({rec['file']})")
            print(f"     🎯 Reason: {rec['removal_reason']}")
            print(f"     💰 Business impact: {rec['business_impact']}")

        # Calculate potential lines of code reduction
        total_loc_reduction = sum(
            rec['lines'] for rec in
            removal_recommendations['immediate_removal'] +
            removal_recommendations['consolidation_candidates']
        )

        print(f"\n📈 POTENTIAL ARCHITECTURAL IMPROVEMENTS:")
        print(f"  📉 Lines of code reduction: {total_loc_reduction:,}")
        print(f"  🏗️  Factory classes to remove: {len(removal_recommendations['immediate_removal'])}")
        print(f"  🔄 Factory classes to consolidate: {len(removal_recommendations['consolidation_candidates'])}")
        print(f"  🎯 Estimated complexity reduction: {(total_loc_reduction / 10):.0f}% easier maintenance")

        # Store recommendations for Phase 2
        self.removal_recommendations = removal_recommendations

        # This test should PASS - we want actionable recommendations
        total_removal_candidates = (len(removal_recommendations['immediate_removal']) +
                                   len(removal_recommendations['consolidation_candidates']))

        self.assertGreaterEqual(
            total_removal_candidates,
            10,
            f"✅ ACTIONABLE RECOMMENDATIONS: Found {total_removal_candidates} factories for removal/consolidation. "
            f"This provides substantial architectural simplification opportunities."
        )

    def _extract_business_justification(self, docstring: str) -> str:
        """Extract business justification from factory docstring."""
        if not docstring:
            return "No documentation"

        # Look for business value keywords
        business_keywords = [
            'business value', 'user isolation', 'performance', 'security',
            'concurrency', 'thread-safe', 'resource management', 'testing'
        ]

        for keyword in business_keywords:
            if keyword.lower() in docstring.lower():
                return keyword.replace('_', ' ').title()

        return "Generic factory pattern"

    def _count_factory_usage(self, factory_name: str) -> int:
        """Count how many times a factory is used across the codebase."""
        usage_count = 0

        # Simple grep-like search across Python files
        for py_file in self.project_root.rglob("*.py"):
            if 'venv' in str(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Count explicit references to the factory
                    usage_count += content.count(factory_name)
            except Exception:
                continue

        return usage_count

    def _calculate_business_value_score(self, factory: Dict) -> int:
        """Calculate business value score (0-10) for a factory."""
        score = 0

        # Check for business value indicators
        if 'user' in factory['class_name'].lower() or 'isolation' in factory.get('business_justification', '').lower():
            score += 4  # User isolation is critical

        if 'websocket' in factory['class_name'].lower() or 'event' in factory['class_name'].lower():
            score += 4  # WebSocket events critical for chat functionality

        if 'database' in factory['class_name'].lower() or 'session' in factory['class_name'].lower():
            score += 3  # Database patterns often justified

        if 'test' in factory['file'].lower() or 'mock' in factory['class_name'].lower():
            score += 2  # Testing infrastructure often justified

        if factory['methods'] > 10 and factory['lines'] > 100:
            score += 1  # Complex factories might have justification

        # Penalize for lack of documentation
        if not factory['has_docstring']:
            score -= 2

        # Penalize for generic names
        if 'Factory' == factory['class_name'] or 'BaseFactory' == factory['class_name']:
            score -= 1

        return max(0, min(10, score))

    def _identify_justification_issues(self, factory: Dict) -> List[str]:
        """Identify specific business justification issues."""
        issues = []

        if not factory['has_docstring']:
            issues.append("No documentation")

        if factory['methods'] <= 2:
            issues.append("Too simple - direct instantiation sufficient")

        if 'Factory' == factory['class_name']:
            issues.append("Generic name indicates lack of specific purpose")

        if factory['static_methods'] == factory['methods']:
            issues.append("All static methods - could be utility module")

        if factory['lines'] < 30:
            issues.append("Very small - questionable abstraction value")

        return issues

    def _generate_factory_recommendation(self, factory: Dict) -> Dict:
        """Generate specific recommendation for a factory."""
        business_score = self._calculate_business_value_score(factory)
        usage_count = self._count_factory_usage(factory['class_name'])

        # Determine recommendation category
        if (business_score <= 2 and usage_count <= 2 and factory['methods'] <= 3):
            category = 'immediate_removal'
            reason = 'Low business value, minimal usage, simple implementation'
            impact = 'Positive - reduces complexity without losing functionality'
        elif (business_score <= 4 and usage_count <= 5):
            category = 'consolidation_candidates'
            reason = 'Moderate business value but could be consolidated'
            impact = 'Positive - maintains functionality while reducing complexity'
        elif (business_score <= 6 or factory['methods'] > 15):
            category = 'refactor_candidates'
            reason = 'Has business value but could be simplified'
            impact = 'Positive - maintains business value with better design'
        else:
            category = 'preserve_essential'
            reason = 'High business value - essential for system operation'
            impact = 'Critical - must preserve for business functionality'

        return {
            **factory,
            'category': category,
            'removal_reason': reason,
            'business_impact': impact,
            'business_value_score': business_score,
            'usage_count': usage_count
        }


if __name__ == '__main__':
    import unittest

    # Run the factory discovery tests
    print("🚀 Starting Factory Over-Engineering Detection - Phase 1")
    print("=" * 80)

    unittest.main(verbosity=2)