"""
Phase 2: SSOT Compliance Validation Tests
Issue #1194 - Factory Over-Engineering Remediation

Purpose:
Tests to detect duplicate factory implementations, import path inconsistencies,
and SSOT consolidation opportunities across factory classes.

Test Design:
- Scans for duplicate factory patterns across services
- Validates import path consistency
- Identifies competing factory implementations
- Tests SSOT consolidation opportunities

Business Impact: $500K+ ARR protection through SSOT compliance
SSOT Advancement: Eliminates factory pattern fragmentation

These tests are designed to FAIL initially to demonstrate current SSOT violations.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import hashlib

from test_framework.ssot.base_test_case import SSotBaseTestCase


class FactorySSotAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze SSOT compliance in factory classes."""

    def __init__(self):
        self.factory_classes = []
        self.import_statements = []
        self.method_signatures = []
        self.class_hierarchy = []

    def visit_ClassDef(self, node):
        """Analyze factory class definitions for SSOT compliance."""
        if 'factory' in node.name.lower() or 'Factory' in node.name:
            # Extract method signatures for duplicate detection
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    # Create method signature for comparison
                    method_signature = {
                        'name': item.name,
                        'args': [arg.arg for arg in item.args.args],
                        'decorators': [self._get_decorator_name(d) for d in item.decorator_list],
                        'returns': self._get_annotation_string(item.returns),
                        'is_async': isinstance(item, ast.AsyncFunctionDef)
                    }
                    methods.append(method_signature)

            class_info = {
                'name': node.name,
                'bases': [self._get_base_name(base) for base in node.bases],
                'methods': methods,
                'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
                'line_start': node.lineno,
                'line_end': getattr(node, 'end_lineno', node.lineno + 10)
            }
            self.factory_classes.append(class_info)

        self.generic_visit(node)

    def visit_Import(self, node):
        """Track import statements for path consistency analysis."""
        for alias in node.names:
            self.import_statements.append({
                'type': 'import',
                'module': alias.name,
                'alias': alias.asname,
                'line': node.lineno
            })

    def visit_ImportFrom(self, node):
        """Track from imports for path consistency analysis."""
        if node.module:
            for alias in node.names:
                self.import_statements.append({
                    'type': 'from',
                    'module': node.module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno
                })

    def _get_decorator_name(self, decorator):
        """Extract decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            return f"{decorator.value.id}.{decorator.attr}" if hasattr(decorator.value, 'id') else str(decorator.attr)
        return str(decorator)

    def _get_base_name(self, base):
        """Extract base class name from AST node."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else str(base.attr)
        return str(base)

    def _get_annotation_string(self, annotation):
        """Convert annotation to string for comparison."""
        if annotation is None:
            return None
        if isinstance(annotation, ast.Name):
            return annotation.id
        return str(annotation)


class FactorySSotViolationsTests(SSotBaseTestCase):
    """
    Phase 2: SSOT Compliance Validation

    Tests to detect and validate removal of SSOT violations in factory patterns.
    These tests identify duplicate implementations and consolidation opportunities.
    """

    def setUp(self):
        """Set up SSOT compliance analysis environment."""
        super().setUp()
        self.project_root = Path(__file__).parents[2]
        self.factory_analyses = {}
        self.ssot_violations = []
        self.consolidation_opportunities = []

        # Define services for cross-service analysis
        self.services = {
            'netra_backend': self.project_root / 'netra_backend',
            'auth_service': self.project_root / 'auth_service',
            'shared': self.project_root / 'shared',
            'test_framework': self.project_root / 'test_framework'
        }

    def test_01_detect_duplicate_factory_implementations(self):
        """
        Test 1: Duplicate Factory Implementation Detection

        Scans all services to find factory classes with identical or near-identical
        implementations, indicating SSOT violations that should be consolidated.

        Expected Result: FAIL - Demonstrates duplicate factory patterns
        """
        print(f"\n🔍 PHASE 2.1: Detecting duplicate factory implementations...")

        duplicate_groups = defaultdict(list)
        factory_signatures = {}

        # Analyze each service for factory patterns
        for service_name, service_path in self.services.items():
            if not service_path.exists():
                continue

            print(f"  🔍 Scanning {service_name}...")
            service_factories = self._analyze_service_factories(service_path)

            for factory_file, analysis in service_factories.items():
                for factory_class in analysis.factory_classes:
                    # Create signature for duplicate detection
                    signature = self._create_factory_signature(factory_class)
                    signature_hash = hashlib.md5(signature.encode()).hexdigest()[:8]

                    factory_info = {
                        'service': service_name,
                        'file': factory_file,
                        'class': factory_class,
                        'signature': signature,
                        'signature_hash': signature_hash
                    }

                    # Group by similar signatures
                    duplicate_groups[signature_hash].append(factory_info)

        # Identify actual duplicates (groups with >1 member)
        actual_duplicates = {k: v for k, v in duplicate_groups.items() if len(v) > 1}

        print(f"\n📊 DUPLICATE FACTORY ANALYSIS:")
        print(f"  🔍 Total factory classes analyzed: {sum(len(v) for v in duplicate_groups.values())}")
        print(f"  🚨 Duplicate signature groups: {len(actual_duplicates)}")
        print(f"  📈 Total duplicate instances: {sum(len(v) for v in actual_duplicates.values())}")

        print(f"\n🚨 TOP DUPLICATE FACTORY VIOLATIONS:")
        for i, (sig_hash, duplicates) in enumerate(list(actual_duplicates.items())[:8]):
            print(f"  {i+1}. Signature {sig_hash} ({len(duplicates)} duplicates)")
            for dup in duplicates:
                rel_path = Path(dup['file']).relative_to(self.project_root) if self.project_root in Path(dup['file']).parents else dup['file']
                print(f"     📄 {dup['service']}: {rel_path} -> {dup['class']['name']}")

        self.duplicate_factories = actual_duplicates

        # This test should FAIL to demonstrate SSOT violations
        total_duplicates = sum(len(v) for v in actual_duplicates.values())
        self.assertLessEqual(
            len(actual_duplicates),
            2,
            f"❌ SSOT VIOLATION DETECTED: Found {len(actual_duplicates)} duplicate factory signature groups "
            f"with {total_duplicates} total duplicate instances. Expected ≤2 for SSOT compliance."
        )

    def test_02_validate_factory_import_path_consistency(self):
        """
        Test 2: Factory Import Path Consistency Validation

        Analyzes import statements across all factory files to identify
        inconsistent import paths for the same factory classes.

        Expected Result: FAIL - Shows import path fragmentation
        """
        print(f"\n🔍 PHASE 2.2: Validating factory import path consistency...")

        import_patterns = defaultdict(set)
        factory_imports = defaultdict(list)

        # Analyze import patterns across all factory files
        for service_name, service_path in self.services.items():
            if not service_path.exists():
                continue

            for py_file in service_path.rglob("*.py"):
                if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                    continue

                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Parse AST for import analysis
                    try:
                        tree = ast.parse(content)
                        analyzer = FactorySSotAnalyzer()
                        analyzer.visit(tree)

                        # Analyze factory-related imports
                        for import_stmt in analyzer.import_statements:
                            if self._is_factory_related_import(import_stmt):
                                import_key = self._normalize_import_key(import_stmt)
                                import_info = {
                                    'file': str(py_file.relative_to(self.project_root)),
                                    'service': service_name,
                                    'import_statement': import_stmt,
                                    'line': import_stmt['line']
                                }

                                factory_imports[import_key].append(import_info)
                                import_patterns[import_key].add(self._get_import_pattern(import_stmt))

                    except SyntaxError:
                        continue

                except Exception:
                    continue

        # Identify inconsistent import patterns
        inconsistent_imports = {}
        for import_key, patterns in import_patterns.items():
            if len(patterns) > 1:  # Multiple patterns for same import
                inconsistent_imports[import_key] = {
                    'patterns': list(patterns),
                    'occurrences': factory_imports[import_key]
                }

        print(f"\n📊 IMPORT PATH CONSISTENCY ANALYSIS:")
        print(f"  🔍 Factory-related imports analyzed: {len(factory_imports)}")
        print(f"  🚨 Inconsistent import patterns: {len(inconsistent_imports)}")
        print(f"  📈 Total import occurrences: {sum(len(v) for v in factory_imports.values())}")

        print(f"\n🚨 TOP IMPORT PATH INCONSISTENCIES:")
        for i, (import_key, details) in enumerate(list(inconsistent_imports.items())[:10]):
            print(f"  {i+1}. {import_key}")
            print(f"     🔄 {len(details['patterns'])} different patterns:")
            for pattern in details['patterns']:
                print(f"       - {pattern}")
            print(f"     📍 Used in {len(details['occurrences'])} files")

        self.import_inconsistencies = inconsistent_imports

        # This test should FAIL to demonstrate import path fragmentation
        self.assertLessEqual(
            len(inconsistent_imports),
            3,
            f"❌ IMPORT PATH FRAGMENTATION DETECTED: Found {len(inconsistent_imports)} inconsistent factory import patterns. "
            f"Expected ≤3 for SSOT compliance. This indicates factory import path fragmentation."
        )

    def test_03_identify_competing_factory_patterns(self):
        """
        Test 3: Competing Factory Pattern Detection

        Identifies cases where multiple factory classes exist for the same purpose
        but with different implementations, indicating competing patterns.

        Expected Result: FAIL - Shows competing factory implementations
        """
        print(f"\n🔍 PHASE 2.3: Identifying competing factory patterns...")

        if not hasattr(self, 'duplicate_factories'):
            self.test_01_detect_duplicate_factory_implementations()

        competing_patterns = defaultdict(list)

        # Analyze all factory classes for purpose overlap
        all_factories = []
        for service_name, service_path in self.services.items():
            if not service_path.exists():
                continue

            service_factories = self._analyze_service_factories(service_path)
            for factory_file, analysis in service_factories.items():
                for factory_class in analysis.factory_classes:
                    factory_purpose = self._extract_factory_purpose(factory_class['name'])
                    all_factories.append({
                        'service': service_name,
                        'file': factory_file,
                        'class': factory_class,
                        'purpose': factory_purpose,
                        'capability_hash': self._create_capability_hash(factory_class)
                    })

        # Group by purpose to find competing implementations
        purpose_groups = defaultdict(list)
        for factory in all_factories:
            purpose_groups[factory['purpose']].append(factory)

        # Identify competing patterns (same purpose, different implementations)
        competing_implementations = {}
        for purpose, factories in purpose_groups.items():
            if len(factories) > 1:
                # Check if they have different implementations
                capability_hashes = set(f['capability_hash'] for f in factories)
                if len(capability_hashes) > 1:  # Different implementations
                    competing_implementations[purpose] = {
                        'factories': factories,
                        'implementation_variants': len(capability_hashes)
                    }

        print(f"\n📊 COMPETING PATTERN ANALYSIS:")
        print(f"  🔍 Factory purposes analyzed: {len(purpose_groups)}")
        print(f"  🚨 Competing implementations: {len(competing_implementations)}")
        print(f"  📈 Total factories with competition: {sum(len(v['factories']) for v in competing_implementations.values())}")

        print(f"\n🚨 TOP COMPETING FACTORY PATTERNS:")
        for i, (purpose, details) in enumerate(list(competing_implementations.items())[:8]):
            print(f"  {i+1}. {purpose} ({details['implementation_variants']} variants, {len(details['factories'])} implementations)")
            for factory in details['factories']:
                rel_path = Path(factory['file']).relative_to(self.project_root) if self.project_root in Path(factory['file']).parents else factory['file']
                print(f"     📄 {factory['service']}: {rel_path} -> {factory['class']['name']}")

        self.competing_patterns = competing_implementations

        # This test should FAIL to demonstrate competing patterns
        self.assertLessEqual(
            len(competing_implementations),
            3,
            f"❌ COMPETING PATTERNS DETECTED: Found {len(competing_implementations)} factory purposes with competing implementations. "
            f"Expected ≤3 for SSOT compliance. These should be consolidated to single implementations."
        )

    def test_04_validate_factory_inheritance_hierarchy_ssot(self):
        """
        Test 4: Factory Inheritance Hierarchy SSOT Validation

        Validates that factory inheritance hierarchies follow SSOT principles
        without unnecessary abstraction layers or duplicate base classes.

        Expected Result: FAIL - Shows over-complex inheritance hierarchies
        """
        print(f"\n🔍 PHASE 2.4: Validating factory inheritance hierarchy SSOT...")

        inheritance_analysis = {
            'base_factories': [],
            'abstract_factories': [],
            'concrete_factories': [],
            'deep_hierarchies': [],
            'duplicate_bases': defaultdict(list)
        }

        # Analyze inheritance patterns across all services
        for service_name, service_path in self.services.items():
            if not service_path.exists():
                continue

            service_factories = self._analyze_service_factories(service_path)
            for factory_file, analysis in service_factories.items():
                for factory_class in analysis.factory_classes:
                    # Analyze inheritance depth and patterns
                    inheritance_depth = len(factory_class['bases'])

                    factory_info = {
                        'service': service_name,
                        'file': factory_file,
                        'class_name': factory_class['name'],
                        'bases': factory_class['bases'],
                        'inheritance_depth': inheritance_depth,
                        'is_abstract': 'ABC' in factory_class['bases'] or 'Abstract' in factory_class['name']
                    }

                    # Categorize factory types
                    if inheritance_depth == 0:
                        inheritance_analysis['base_factories'].append(factory_info)
                    elif factory_info['is_abstract']:
                        inheritance_analysis['abstract_factories'].append(factory_info)
                    else:
                        inheritance_analysis['concrete_factories'].append(factory_info)

                    # Check for deep hierarchies (potential over-engineering)
                    if inheritance_depth > 2:
                        inheritance_analysis['deep_hierarchies'].append(factory_info)

                    # Track duplicate base class usage
                    for base in factory_class['bases']:
                        if 'Factory' in base:
                            inheritance_analysis['duplicate_bases'][base].append(factory_info)

        # Identify SSOT violations in inheritance
        inheritance_violations = []

        # Multiple base factories for same purpose
        duplicate_base_violations = {k: v for k, v in inheritance_analysis['duplicate_bases'].items() if len(v) > 2}

        # Deep inheritance hierarchies
        deep_hierarchy_violations = inheritance_analysis['deep_hierarchies']

        print(f"\n📊 INHERITANCE HIERARCHY ANALYSIS:")
        print(f"  🏗️  Base factories: {len(inheritance_analysis['base_factories'])}")
        print(f"  🔺 Abstract factories: {len(inheritance_analysis['abstract_factories'])}")
        print(f"  🏭 Concrete factories: {len(inheritance_analysis['concrete_factories'])}")
        print(f"  📏 Deep hierarchies (>2 levels): {len(deep_hierarchy_violations)}")
        print(f"  🔄 Duplicate base usage: {len(duplicate_base_violations)}")

        print(f"\n🚨 INHERITANCE HIERARCHY VIOLATIONS:")
        print(f"  📏 DEEP HIERARCHY VIOLATIONS:")
        for i, violation in enumerate(deep_hierarchy_violations[:5]):
            rel_path = Path(violation['file']).relative_to(self.project_root) if self.project_root in Path(violation['file']).parents else violation['file']
            print(f"    {i+1}. {violation['class_name']} ({violation['service']}: {rel_path})")
            print(f"       📏 Inheritance depth: {violation['inheritance_depth']} levels")
            print(f"       🏗️  Bases: {', '.join(violation['bases'])}")

        print(f"\n  🔄 DUPLICATE BASE CLASS VIOLATIONS:")
        for base_class, usages in list(duplicate_base_violations.items())[:3]:
            print(f"    🏗️  {base_class} ({len(usages)} usages)")
            for usage in usages[:3]:
                rel_path = Path(usage['file']).relative_to(self.project_root) if self.project_root in Path(usage['file']).parents else usage['file']
                print(f"      📄 {usage['service']}: {rel_path} -> {usage['class_name']}")

        total_violations = len(deep_hierarchy_violations) + len(duplicate_base_violations)

        # This test should FAIL to demonstrate inheritance complexity
        self.assertLessEqual(
            total_violations,
            5,
            f"❌ INHERITANCE HIERARCHY VIOLATIONS DETECTED: Found {len(deep_hierarchy_violations)} deep hierarchies "
            f"and {len(duplicate_base_violations)} duplicate base patterns. Expected ≤5 total for SSOT compliance."
        )

    def test_05_generate_ssot_consolidation_recommendations(self):
        """
        Test 5: SSOT Consolidation Recommendations

        Generates comprehensive recommendations for consolidating factory patterns
        to achieve SSOT compliance while maintaining business functionality.

        Expected Result: PASS - Provides actionable SSOT consolidation plan
        """
        print(f"\n📋 PHASE 2.5: Generating SSOT consolidation recommendations...")

        # Ensure previous analyses are run
        if not hasattr(self, 'duplicate_factories'):
            self.test_01_detect_duplicate_factory_implementations()
        if not hasattr(self, 'competing_patterns'):
            self.test_03_identify_competing_factory_patterns()

        consolidation_plan = {
            'immediate_consolidation': [],  # Direct duplicates to merge
            'pattern_unification': [],  # Competing patterns to unify
            'hierarchy_simplification': [],  # Complex hierarchies to flatten
            'import_standardization': [],  # Import paths to standardize
            'preserved_patterns': []  # Essential patterns to preserve
        }

        # Process duplicate factories for consolidation
        for sig_hash, duplicates in getattr(self, 'duplicate_factories', {}).items():
            if len(duplicates) > 1:
                # Identify canonical implementation (prefer shared > backend > auth > test)
                canonical_candidate = self._identify_canonical_implementation(duplicates)

                consolidation_plan['immediate_consolidation'].append({
                    'signature_hash': sig_hash,
                    'canonical_implementation': canonical_candidate,
                    'duplicates_to_remove': [d for d in duplicates if d != canonical_candidate],
                    'consolidation_benefit': f"Eliminate {len(duplicates)-1} duplicate implementations",
                    'business_risk': 'Low - identical functionality'
                })

        # Process competing patterns for unification
        for purpose, details in getattr(self, 'competing_patterns', {}).items():
            best_implementation = self._identify_best_implementation(details['factories'])

            consolidation_plan['pattern_unification'].append({
                'purpose': purpose,
                'recommended_implementation': best_implementation,
                'alternatives_to_deprecate': [f for f in details['factories'] if f != best_implementation],
                'unification_benefit': f"Single implementation for {purpose}",
                'business_risk': 'Medium - different implementations may have different features'
            })

        # Process import inconsistencies for standardization
        for import_key, details in getattr(self, 'import_inconsistencies', {}).items():
            canonical_pattern = self._identify_canonical_import_pattern(details['patterns'])

            consolidation_plan['import_standardization'].append({
                'import_target': import_key,
                'canonical_pattern': canonical_pattern,
                'patterns_to_update': [p for p in details['patterns'] if p != canonical_pattern],
                'files_affected': len(details['occurrences']),
                'standardization_benefit': 'Consistent import paths across codebase'
            })

        print(f"\n📋 SSOT CONSOLIDATION RECOMMENDATIONS:")
        print(f"  🔄 Immediate consolidations: {len(consolidation_plan['immediate_consolidation'])}")
        print(f"  🎯 Pattern unifications: {len(consolidation_plan['pattern_unification'])}")
        print(f"  🏗️  Hierarchy simplifications: {len(consolidation_plan['hierarchy_simplification'])}")
        print(f"  📦 Import standardizations: {len(consolidation_plan['import_standardization'])}")

        print(f"\n🔄 TOP IMMEDIATE CONSOLIDATION OPPORTUNITIES:")
        for i, consolidation in enumerate(consolidation_plan['immediate_consolidation'][:5]):
            canonical = consolidation['canonical_implementation']
            rel_path = Path(canonical['file']).relative_to(self.project_root) if self.project_root in Path(canonical['file']).parents else canonical['file']
            print(f"  {i+1}. Keep: {canonical['service']} -> {rel_path}")
            print(f"     🗑️  Remove {len(consolidation['duplicates_to_remove'])} duplicates")
            print(f"     💰 Benefit: {consolidation['consolidation_benefit']}")

        print(f"\n🎯 TOP PATTERN UNIFICATION OPPORTUNITIES:")
        for i, unification in enumerate(consolidation_plan['pattern_unification'][:5]):
            recommended = unification['recommended_implementation']
            rel_path = Path(recommended['file']).relative_to(self.project_root) if self.project_root in Path(recommended['file']).parents else recommended['file']
            print(f"  {i+1}. {unification['purpose']}")
            print(f"     ✅ Keep: {recommended['service']} -> {rel_path}")
            print(f"     🔄 Deprecate {len(unification['alternatives_to_deprecate'])} alternatives")
            print(f"     💰 Benefit: {unification['unification_benefit']}")

        # Calculate consolidation impact
        total_consolidations = (len(consolidation_plan['immediate_consolidation']) +
                               len(consolidation_plan['pattern_unification']))

        estimated_reduction = sum(len(c['duplicates_to_remove']) for c in consolidation_plan['immediate_consolidation'])
        estimated_reduction += sum(len(u['alternatives_to_deprecate']) for u in consolidation_plan['pattern_unification'])

        print(f"\n📈 CONSOLIDATION IMPACT ANALYSIS:")
        print(f"  🎯 Total consolidation opportunities: {total_consolidations}")
        print(f"  📉 Factory classes to remove/deprecate: {estimated_reduction}")
        print(f"  🔄 Import paths to standardize: {len(consolidation_plan['import_standardization'])}")
        print(f"  🏗️  Estimated complexity reduction: {(estimated_reduction * 15):.0f}% easier maintenance")

        self.consolidation_plan = consolidation_plan

        # This test should PASS - we want actionable consolidation recommendations
        self.assertGreaterEqual(
            total_consolidations,
            5,
            f"✅ SSOT CONSOLIDATION OPPORTUNITIES: Found {total_consolidations} consolidation opportunities. "
            f"This provides substantial SSOT compliance improvements."
        )

    def _analyze_service_factories(self, service_path: Path) -> Dict[str, FactorySSotAnalyzer]:
        """Analyze all factory files in a service."""
        service_analyses = {}

        for py_file in service_path.rglob("*.py"):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue

            # Check if file contains factory patterns
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if 'factory' in content.lower() or 'Factory' in content:
                    try:
                        tree = ast.parse(content)
                        analyzer = FactorySSotAnalyzer()
                        analyzer.visit(tree)

                        if analyzer.factory_classes:  # Only store if factories found
                            service_analyses[str(py_file)] = analyzer

                    except SyntaxError:
                        continue
            except Exception:
                continue

        return service_analyses

    def _create_factory_signature(self, factory_class: Dict) -> str:
        """Create a signature string for factory class comparison."""
        methods = sorted([m['name'] for m in factory_class['methods']])
        bases = sorted(factory_class['bases'])

        return f"methods:{','.join(methods)};bases:{','.join(bases)};decorators:{','.join(factory_class['decorators'])}"

    def _create_capability_hash(self, factory_class: Dict) -> str:
        """Create a hash representing factory capabilities."""
        # Focus on public methods (capabilities)
        public_methods = [m['name'] for m in factory_class['methods'] if not m['name'].startswith('_')]
        capability_string = ','.join(sorted(public_methods))
        return hashlib.md5(capability_string.encode()).hexdigest()[:8]

    def _extract_factory_purpose(self, class_name: str) -> str:
        """Extract the primary purpose from factory class name."""
        # Remove 'Factory' suffix and common prefixes
        name = class_name.replace('Factory', '').replace('SSOT', '').replace('Unified', '')

        # Convert camelCase to words
        words = re.findall(r'[A-Z][a-z]*', name)
        if not words:
            words = [name.lower()]

        return '_'.join(word.lower() for word in words[:2])  # Take first 2 words as purpose

    def _is_factory_related_import(self, import_stmt: Dict) -> bool:
        """Check if import statement is factory-related."""
        text = f"{import_stmt.get('module', '')} {import_stmt.get('name', '')}"
        return 'factory' in text.lower() or 'Factory' in text

    def _normalize_import_key(self, import_stmt: Dict) -> str:
        """Create normalized key for import comparison."""
        if import_stmt['type'] == 'from':
            return f"from {import_stmt['module']} import {import_stmt['name']}"
        else:
            return f"import {import_stmt['module']}"

    def _get_import_pattern(self, import_stmt: Dict) -> str:
        """Get the import pattern string."""
        return self._normalize_import_key(import_stmt)

    def _identify_canonical_implementation(self, duplicates: List[Dict]) -> Dict:
        """Identify the canonical implementation from duplicates."""
        # Priority: shared > netra_backend > auth_service > test_framework
        priority = {'shared': 4, 'netra_backend': 3, 'auth_service': 2, 'test_framework': 1}

        return max(duplicates, key=lambda d: priority.get(d['service'], 0))

    def _identify_best_implementation(self, implementations: List[Dict]) -> Dict:
        """Identify the best implementation from competing patterns."""
        # Score based on service priority, documentation, and complexity
        def score_implementation(impl):
            score = 0

            # Service priority
            priority = {'shared': 4, 'netra_backend': 3, 'auth_service': 2, 'test_framework': 1}
            score += priority.get(impl['service'], 0) * 10

            # Method count (moderate is better than too few or too many)
            method_count = len(impl['class']['methods'])
            if 3 <= method_count <= 8:
                score += 5
            elif method_count > 8:
                score -= 2

            # Has documentation
            if any(method.get('docstring') for method in impl['class'].get('methods', [])):
                score += 3

            return score

        return max(implementations, key=score_implementation)

    def _identify_canonical_import_pattern(self, patterns: List[str]) -> str:
        """Identify the canonical import pattern from alternatives."""
        # Prefer absolute imports from shared, then specific modules
        if any('shared' in p for p in patterns):
            return next(p for p in patterns if 'shared' in p)

        # Prefer shorter, more direct imports
        return min(patterns, key=len)


if __name__ == '__main__':
    import unittest

    print("🚀 Starting Factory SSOT Violations Detection - Phase 2")
    print("=" * 80)

    unittest.main(verbosity=2)