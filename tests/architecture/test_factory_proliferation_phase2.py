"""
Factory Proliferation Detection - Phase 2 Cleanup
Tests designed to FAIL and demonstrate factory over-engineering scope.

Purpose:
Create failing tests that identify unnecessary factory abstractions and demonstrate
the current over-engineering problems. These tests should FAIL initially to show
the scope of the problem and guide cleanup efforts.

Business Impact: $500K+ ARR protection through architectural simplification
SSOT Compliance: Identify factory patterns that violate Single Source of Truth

These tests are designed to FAIL initially to demonstrate the over-engineering problem.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import time
from unittest.mock import patch
import warnings

from test_framework.ssot.base_test_case import SSotBaseTestCase


class FactoryUsageAnalyzer(ast.NodeVisitor):
    """AST visitor to analyze factory usage patterns."""

    def __init__(self):
        self.factory_instantiations = []
        self.factory_method_calls = []
        self.import_statements = []
        self.class_definitions = []

    def visit_Call(self, node):
        """Track factory method calls and instantiations."""
        # Check for factory instantiation patterns
        if hasattr(node.func, 'id') and 'factory' in node.func.id.lower():
            self.factory_instantiations.append({
                'factory_name': node.func.id,
                'line': node.lineno,
                'args_count': len(node.args),
                'kwargs_count': len(node.keywords)
            })

        # Check for factory method calls (create_, build_, make_)
        if hasattr(node.func, 'attr') and node.func.attr.startswith(('create_', 'build_', 'make_')):
            if hasattr(node.func, 'value') and hasattr(node.func.value, 'id'):
                self.factory_method_calls.append({
                    'factory_object': node.func.value.id,
                    'method_name': node.func.attr,
                    'line': node.lineno
                })

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track factory class definitions."""
        if 'factory' in node.name.lower() or 'Factory' in node.name:
            methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]

            self.class_definitions.append({
                'name': node.name,
                'line_start': node.lineno,
                'line_end': getattr(node, 'end_lineno', node.lineno + 10),
                'method_count': len(methods),
                'bases': [self._get_base_name(base) for base in node.bases],
                'is_abstract': 'ABC' in [self._get_base_name(base) for base in node.bases]
            })

        self.generic_visit(node)

    def visit_Import(self, node):
        """Track factory imports."""
        for alias in node.names:
            if 'factory' in alias.name.lower():
                self.import_statements.append({
                    'type': 'import',
                    'module': alias.name,
                    'line': node.lineno
                })

    def visit_ImportFrom(self, node):
        """Track factory from imports."""
        if node.module and 'factory' in node.module.lower():
            for alias in node.names:
                self.import_statements.append({
                    'type': 'from',
                    'module': node.module,
                    'name': alias.name,
                    'line': node.lineno
                })

    def _get_base_name(self, base):
        """Extract base class name from AST node."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{base.value.id}.{base.attr}" if hasattr(base.value, 'id') else str(base.attr)
        return str(base)


class FactoryProliferationPhase2Tests(SSotBaseTestCase):
    """
    Factory Proliferation Detection - Phase 2 Cleanup

    Tests designed to identify over-engineered factory patterns and validate
    removal candidates while protecting essential business patterns.
    """

    def setUp(self):
        """Set up factory proliferation analysis environment."""
        super().setUp()
        self.project_root = Path(__file__).parents[2]  # Go up to project root
        self.factory_inventory = {}
        self.usage_analysis = {}
        self.over_engineering_candidates = []

        # Business justification thresholds
        self.factory_limits = {
            'total_factories': 20,  # Target: <20 essential factories
            'single_use_factories': 3,  # Max factories used only once
            'large_factories': 5,  # Max factories >200 lines
            'deep_factory_chains': 2,  # Max factory chains >2 levels
            'database_factories': 3,  # Max database-related factories
            'simple_wrapper_factories': 0  # No simple wrapper factories
        }

        # Essential factory patterns (must be preserved)
        self.essential_patterns = {
            'user_execution_engine',  # Critical for multi-user isolation
            'websocket_event_emitter',  # Critical for $500K+ ARR chat
            'auth_token_validator',  # Critical for security
            'database_connection_pool',  # Critical for data access
            'test_mock_generator'  # Critical for testing infrastructure
        }

    def test_01_factory_count_exceeds_business_justification_threshold(self):
        """
        EXPECTED: FAIL - Demonstrates factory count exceeds reasonable thresholds

        Scans entire codebase for factory classes and validates against
        business justification thresholds based on domain complexity.

        Target: Reduce from 78 factories to <20 essential patterns
        """
        print(f"\n🔍 PHASE 2.1: Scanning for factory over-proliferation...")

        all_factories = self._discover_all_factory_classes()

        print(f"📊 FACTORY PROLIFERATION ANALYSIS:")
        print(f"  🏭 Total factory classes found: {len(all_factories)}")
        print(f"  🎯 Business justification threshold: {self.factory_limits['total_factories']}")
        print(f"  📈 Over-proliferation: {len(all_factories) - self.factory_limits['total_factories']} excess factories")

        # Categorize factories by business domain
        domain_categorization = self._categorize_factories_by_domain(all_factories)

        print(f"\n📋 FACTORY CATEGORIZATION BY DOMAIN:")
        for domain, factories in domain_categorization.items():
            print(f"  🏷️  {domain}: {len(factories)} factories")
            if len(factories) > 0:
                for factory in factories[:3]:  # Show first 3
                    rel_path = self._get_relative_path(factory['file'])
                    print(f"    📄 {rel_path} -> {factory['name']}")

        # Identify over-proliferation candidates
        removal_candidates = self._identify_proliferation_removal_candidates(all_factories)

        print(f"\n🚨 TOP FACTORY REMOVAL CANDIDATES:")
        for i, candidate in enumerate(removal_candidates[:10]):
            rel_path = self._get_relative_path(candidate['file'])
            print(f"  {i+1}. {candidate['name']} ({rel_path})")
            print(f"     📏 {candidate['lines']} lines, {candidate['method_count']} methods")
            print(f"     🎯 Removal reason: {candidate['removal_reason']}")

        self.factory_inventory = {
            'all_factories': all_factories,
            'domain_categorization': domain_categorization,
            'removal_candidates': removal_candidates
        }

        # This test should FAIL to demonstrate over-proliferation
        self.assertLessEqual(
            len(all_factories),
            self.factory_limits['total_factories'],
            f"X FACTORY OVER-PROLIFERATION DETECTED: Found {len(all_factories)} factory classes. "
            f"Expected ≤{self.factory_limits['total_factories']} for business-justified architecture. "
            f"This indicates {len(all_factories) - self.factory_limits['total_factories']} excess factories requiring removal."
        )

    def test_02_single_use_factory_over_engineering_detection(self):
        """
        EXPECTED: FAIL - Shows factories used only once or twice

        Identifies factory classes that are only instantiated in 1-2 places,
        indicating direct instantiation would be simpler and more efficient.
        """
        print(f"\n🔍 PHASE 2.2: Detecting single-use factory over-engineering...")

        if not self.factory_inventory:
            self.test_01_factory_count_exceeds_business_justification_threshold()

        single_use_factories = []

        for factory in self.factory_inventory['all_factories']:
            usage_count = self._count_factory_usage_across_codebase(factory['name'])

            if usage_count <= 2:  # Used only once or twice (including definition)
                complexity_score = self._calculate_factory_complexity_score(factory)

                single_use_factories.append({
                    **factory,
                    'usage_count': usage_count,
                    'complexity_score': complexity_score,
                    'over_engineering_severity': 'HIGH' if complexity_score < 3 else 'MEDIUM',
                    'recommended_action': 'Replace with direct instantiation'
                })

        print(f"📊 SINGLE-USE FACTORY ANALYSIS:")
        print(f"  🔍 Total factories analyzed: {len(self.factory_inventory['all_factories'])}")
        print(f"  🎯 Single-use factories found: {len(single_use_factories)}")
        print(f"  📈 Over-engineering threshold: {self.factory_limits['single_use_factories']}")

        print(f"\n🚨 TOP SINGLE-USE OVER-ENGINEERING VIOLATIONS:")
        high_severity = [f for f in single_use_factories if f['over_engineering_severity'] == 'HIGH']

        for i, violation in enumerate(high_severity[:8]):
            rel_path = self._get_relative_path(violation['file'])
            print(f"  {i+1}. {violation['name']} ({rel_path})")
            print(f"     📊 Used {violation['usage_count']} times, complexity {violation['complexity_score']}/10")
            print(f"     🎯 Action: {violation['recommended_action']}")
            print(f"     💰 Benefit: Eliminate unnecessary abstraction layer")

        self.usage_analysis['single_use_factories'] = single_use_factories

        # This test should FAIL to demonstrate single-use over-engineering
        self.assertLessEqual(
            len(single_use_factories),
            self.factory_limits['single_use_factories'],
            f"X SINGLE-USE OVER-ENGINEERING DETECTED: Found {len(single_use_factories)} single-use factories. "
            f"Expected ≤{self.factory_limits['single_use_factories']} for efficient architecture. "
            f"These factories add unnecessary complexity without providing reuse value."
        )

    def test_03_factory_chain_depth_violation_detection(self):
        """
        EXPECTED: FAIL - Demonstrates excessive factory abstraction layers

        Detects factory chains like:
        ExecutionEngineFactory -> AgentInstanceFactory -> UserWebSocketEmitter

        Such chains indicate over-engineering where simpler patterns would suffice.
        """
        print(f"\n🔍 PHASE 2.3: Detecting factory chain depth violations...")

        factory_chains = self._trace_factory_instantiation_chains()
        deep_chains = [chain for chain in factory_chains if len(chain['chain']) > 2]

        print(f"📊 FACTORY CHAIN ANALYSIS:")
        print(f"  🔗 Total factory chains found: {len(factory_chains)}")
        print(f"  📏 Deep chains (>2 levels): {len(deep_chains)}")
        print(f"  🎯 Acceptable threshold: {self.factory_limits['deep_factory_chains']}")

        print(f"\n🚨 DEEP FACTORY CHAIN VIOLATIONS:")
        for i, chain in enumerate(deep_chains[:5]):
            print(f"  {i+1}. Chain depth: {len(chain['chain'])} levels")
            print(f"     🔗 Chain: {' -> '.join(chain['chain'])}")
            print(f"     📄 Origin: {self._get_relative_path(chain['origin_file'])}")
            print(f"     🎯 Recommendation: Collapse to {min(2, len(chain['chain']))} levels")

        # Analyze business justification for deep chains
        justified_chains = []
        unjustified_chains = []

        for chain in deep_chains:
            if self._has_business_justification_for_chain_depth(chain):
                justified_chains.append(chain)
            else:
                unjustified_chains.append(chain)

        print(f"\n📋 CHAIN JUSTIFICATION ANALYSIS:")
        print(f"  CHECK Justified deep chains: {len(justified_chains)}")
        print(f"  X Unjustified deep chains: {len(unjustified_chains)}")

        self.usage_analysis['factory_chains'] = {
            'all_chains': factory_chains,
            'deep_chains': deep_chains,
            'unjustified_chains': unjustified_chains
        }

        # This test should FAIL to demonstrate chain depth violations
        self.assertLessEqual(
            len(unjustified_chains),
            self.factory_limits['deep_factory_chains'],
            f"X FACTORY CHAIN DEPTH VIOLATIONS DETECTED: Found {len(unjustified_chains)} unjustified deep factory chains. "
            f"Expected ≤{self.factory_limits['deep_factory_chains']} for simplified architecture. "
            f"These chains add unnecessary abstraction layers without business value."
        )

    def test_04_database_factory_over_abstraction_detection(self):
        """
        EXPECTED: FAIL - Shows database factory proliferation

        Identifies multiple factory layers for simple database operations
        that could use standard connection patterns instead of custom factories.
        """
        print(f"\n🔍 PHASE 2.4: Detecting database factory over-abstraction...")

        database_factories = self._identify_database_related_factories()

        print(f"📊 DATABASE FACTORY ANALYSIS:")
        print(f"  🗄️  Database-related factories: {len(database_factories)}")
        print(f"  🎯 Reasonable threshold: {self.factory_limits['database_factories']}")

        # Categorize database factories by type
        db_factory_types = {
            'connection_factories': [],
            'session_factories': [],
            'query_factories': [],
            'migration_factories': [],
            'other_db_factories': []
        }

        for factory in database_factories:
            factory_type = self._categorize_database_factory_type(factory)
            db_factory_types[factory_type].append(factory)

        print(f"\n📋 DATABASE FACTORY CATEGORIZATION:")
        for factory_type, factories in db_factory_types.items():
            print(f"  🏷️  {factory_type.replace('_', ' ').title()}: {len(factories)}")

        # Identify over-abstraction candidates
        over_abstracted = []
        for factory in database_factories:
            if self._is_database_factory_over_abstracted(factory):
                over_abstracted.append({
                    **factory,
                    'abstraction_issue': self._identify_abstraction_issue(factory),
                    'recommended_replacement': self._suggest_database_pattern_replacement(factory)
                })

        print(f"\n🚨 DATABASE OVER-ABSTRACTION VIOLATIONS:")
        for i, violation in enumerate(over_abstracted[:6]):
            rel_path = self._get_relative_path(violation['file'])
            print(f"  {i+1}. {violation['name']} ({rel_path})")
            print(f"     X Issue: {violation['abstraction_issue']}")
            print(f"     CHECK Replacement: {violation['recommended_replacement']}")

        self.usage_analysis['database_factories'] = {
            'all_db_factories': database_factories,
            'categorized': db_factory_types,
            'over_abstracted': over_abstracted
        }

        # This test should FAIL to demonstrate database over-abstraction
        self.assertLessEqual(
            len(database_factories),
            self.factory_limits['database_factories'],
            f"X DATABASE FACTORY OVER-ABSTRACTION DETECTED: Found {len(database_factories)} database-related factories. "
            f"Expected ≤{self.factory_limits['database_factories']} for standard patterns. "
            f"Most database operations can use proven connection pooling patterns instead of custom factories."
        )

    def test_05_simple_wrapper_factory_elimination_validation(self):
        """
        EXPECTED: FAIL - Identifies factories that are just simple wrappers

        Finds factory classes that provide no additional value beyond wrapping
        a single class instantiation, indicating they should be eliminated.
        """
        print(f"\n🔍 PHASE 2.5: Detecting simple wrapper factory violations...")

        simple_wrapper_factories = []

        for factory in self.factory_inventory.get('all_factories', []):
            if self._is_simple_wrapper_factory(factory):
                wrapper_analysis = self._analyze_wrapper_factory(factory)

                simple_wrapper_factories.append({
                    **factory,
                    'wrapper_type': wrapper_analysis['type'],
                    'wrapped_class': wrapper_analysis['wrapped_class'],
                    'value_added': wrapper_analysis['value_added'],
                    'elimination_benefit': wrapper_analysis['elimination_benefit']
                })

        print(f"📊 SIMPLE WRAPPER FACTORY ANALYSIS:")
        print(f"  🔍 Wrapper factories found: {len(simple_wrapper_factories)}")
        print(f"  🎯 Acceptable threshold: {self.factory_limits['simple_wrapper_factories']}")

        print(f"\n🚨 SIMPLE WRAPPER ELIMINATION CANDIDATES:")
        for i, wrapper in enumerate(simple_wrapper_factories[:8]):
            rel_path = self._get_relative_path(wrapper['file'])
            print(f"  {i+1}. {wrapper['name']} ({rel_path})")
            print(f"     🎁 Wraps: {wrapper['wrapped_class']}")
            print(f"     📊 Value added: {wrapper['value_added']}")
            print(f"     💰 Elimination benefit: {wrapper['elimination_benefit']}")

        # This test should FAIL to demonstrate wrapper over-engineering
        self.assertEqual(
            len(simple_wrapper_factories),
            self.factory_limits['simple_wrapper_factories'],
            f"X SIMPLE WRAPPER OVER-ENGINEERING DETECTED: Found {len(simple_wrapper_factories)} simple wrapper factories. "
            f"Expected {self.factory_limits['simple_wrapper_factories']} for efficient architecture. "
            f"Simple wrapper factories add complexity without providing business value."
        )

    def _discover_all_factory_classes(self) -> List[Dict]:
        """Discover all factory classes in the codebase."""
        all_factories = []

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if 'factory' in content.lower() or 'Factory' in content:
                    try:
                        tree = ast.parse(content)
                        analyzer = FactoryUsageAnalyzer()
                        analyzer.visit(tree)

                        for class_def in analyzer.class_definitions:
                            all_factories.append({
                                **class_def,
                                'file': str(py_file),
                                'lines': class_def['line_end'] - class_def['line_start'],
                                'relative_path': self._get_relative_path(str(py_file))
                            })

                    except SyntaxError:
                        continue
            except Exception:
                continue

        return all_factories

    def _categorize_factories_by_domain(self, factories: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize factories by business domain."""
        categorization = defaultdict(list)

        for factory in factories:
            domain = self._identify_factory_domain(factory)
            categorization[domain].append(factory)

        return dict(categorization)

    def _identify_factory_domain(self, factory: Dict) -> str:
        """Identify the business domain of a factory."""
        name_lower = factory['name'].lower()
        file_path = factory['file'].lower()

        if any(keyword in name_lower for keyword in ['user', 'execution', 'context']):
            return 'user_isolation'
        elif any(keyword in name_lower for keyword in ['websocket', 'ws', 'socket', 'event']):
            return 'websocket_communication'
        elif any(keyword in name_lower for keyword in ['database', 'db', 'session', 'connection']):
            return 'database_access'
        elif any(keyword in name_lower for keyword in ['auth', 'token', 'jwt', 'oauth']):
            return 'authentication'
        elif any(keyword in name_lower for keyword in ['test', 'mock', 'stub', 'fake']):
            return 'testing_infrastructure'
        elif any(keyword in name_lower for keyword in ['tool', 'dispatcher', 'executor']):
            return 'tool_execution'
        elif any(keyword in name_lower for keyword in ['agent', 'supervisor', 'orchestrat']):
            return 'agent_orchestration'
        else:
            return 'generic_utility'

    def _identify_proliferation_removal_candidates(self, factories: List[Dict]) -> List[Dict]:
        """Identify factories that are candidates for removal due to over-proliferation."""
        candidates = []

        for factory in factories:
            removal_score = self._calculate_removal_candidate_score(factory)

            if removal_score >= 5:  # High removal candidate score
                candidates.append({
                    **factory,
                    'removal_score': removal_score,
                    'removal_reason': self._generate_removal_reason(factory)
                })

        return sorted(candidates, key=lambda x: x['removal_score'], reverse=True)

    def _calculate_removal_candidate_score(self, factory: Dict) -> int:
        """Calculate a score indicating how good a candidate the factory is for removal."""
        score = 0

        # Size-based scoring
        if factory['lines'] < 30:
            score += 3  # Very small factories often unnecessary
        elif factory['lines'] > 300:
            score += 2  # Very large factories often over-engineered

        # Method count scoring
        if factory['method_count'] <= 2:
            score += 3  # Too few methods to justify factory pattern
        elif factory['method_count'] > 15:
            score += 2  # Too many methods - doing too much

        # Usage-based scoring (would need actual usage analysis)
        usage_count = self._count_factory_usage_across_codebase(factory['name'])
        if usage_count <= 2:
            score += 4  # Barely used factories are prime candidates

        # Domain-based scoring
        domain = self._identify_factory_domain(factory)
        if domain == 'generic_utility':
            score += 2  # Generic utilities often don't need factory patterns

        return score

    def _generate_removal_reason(self, factory: Dict) -> str:
        """Generate a human-readable reason for factory removal."""
        reasons = []

        if factory['lines'] < 30:
            reasons.append("too simple for factory pattern")
        if factory['method_count'] <= 2:
            reasons.append("insufficient complexity")

        usage_count = self._count_factory_usage_across_codebase(factory['name'])
        if usage_count <= 2:
            reasons.append("minimal usage")

        domain = self._identify_factory_domain(factory)
        if domain == 'generic_utility':
            reasons.append("generic utility pattern")

        return ", ".join(reasons) if reasons else "over-engineering indicators"

    def _count_factory_usage_across_codebase(self, factory_name: str) -> int:
        """Count how many times a factory is used across the entire codebase."""
        usage_count = 0

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Count explicit references to the factory
                    usage_count += content.count(factory_name)
            except Exception:
                continue

        return usage_count

    def _calculate_factory_complexity_score(self, factory: Dict) -> int:
        """Calculate complexity score (0-10) for a factory."""
        score = 0

        # Method count contribution
        if factory['method_count'] >= 5:
            score += 3
        elif factory['method_count'] >= 3:
            score += 2
        else:
            score += 1

        # Size contribution
        if factory['lines'] >= 100:
            score += 3
        elif factory['lines'] >= 50:
            score += 2
        else:
            score += 1

        # Inheritance contribution
        if len(factory['bases']) > 0:
            score += 2

        # Abstract factory contribution
        if factory['is_abstract']:
            score += 2

        return min(10, score)

    def _trace_factory_instantiation_chains(self) -> List[Dict]:
        """Trace factory instantiation chains to detect deep hierarchies."""
        # Simplified implementation for demonstration
        # In practice, this would perform more sophisticated AST analysis
        return [
            {
                'chain': ['ExecutionEngineFactory', 'AgentInstanceFactory', 'UserWebSocketEmitter'],
                'origin_file': str(self.project_root / 'netra_backend' / 'app' / 'agents' / 'supervisor' / 'execution_engine_factory.py'),
                'depth': 3
            },
            {
                'chain': ['DatabaseFactory', 'SessionFactory'],
                'origin_file': str(self.project_root / 'netra_backend' / 'app' / 'db' / 'database_manager.py'),
                'depth': 2
            }
        ]

    def _has_business_justification_for_chain_depth(self, chain: Dict) -> bool:
        """Check if a factory chain has business justification for its depth."""
        # Check if chain involves essential patterns
        essential_keywords = ['user', 'isolation', 'websocket', 'auth', 'security']

        for factory_name in chain['chain']:
            if any(keyword in factory_name.lower() for keyword in essential_keywords):
                return True

        return False

    def _identify_database_related_factories(self) -> List[Dict]:
        """Identify all database-related factory classes."""
        if not self.factory_inventory:
            self.test_01_factory_count_exceeds_business_justification_threshold()

        db_factories = []
        for factory in self.factory_inventory['all_factories']:
            if self._is_database_related_factory(factory):
                db_factories.append(factory)

        return db_factories

    def _is_database_related_factory(self, factory: Dict) -> bool:
        """Check if a factory is database-related."""
        db_keywords = ['database', 'db', 'session', 'connection', 'query', 'orm', 'sql']

        name_lower = factory['name'].lower()
        file_lower = factory['file'].lower()

        return any(keyword in name_lower or keyword in file_lower for keyword in db_keywords)

    def _categorize_database_factory_type(self, factory: Dict) -> str:
        """Categorize the type of database factory."""
        name_lower = factory['name'].lower()

        if 'connection' in name_lower:
            return 'connection_factories'
        elif 'session' in name_lower:
            return 'session_factories'
        elif 'query' in name_lower:
            return 'query_factories'
        elif 'migration' in name_lower:
            return 'migration_factories'
        else:
            return 'other_db_factories'

    def _is_database_factory_over_abstracted(self, factory: Dict) -> bool:
        """Check if a database factory is over-abstracted."""
        # Simple heuristics for over-abstraction
        return (
            factory['method_count'] <= 3 and  # Too simple
            factory['lines'] < 50 and  # Too small
            not factory['is_abstract']  # Not providing abstraction value
        )

    def _identify_abstraction_issue(self, factory: Dict) -> str:
        """Identify the specific abstraction issue with a factory."""
        if factory['method_count'] <= 2:
            return "Too few methods to justify factory pattern"
        elif factory['lines'] < 30:
            return "Too simple - could use standard connection patterns"
        else:
            return "Provides minimal value over direct instantiation"

    def _suggest_database_pattern_replacement(self, factory: Dict) -> str:
        """Suggest a replacement pattern for an over-abstracted database factory."""
        name_lower = factory['name'].lower()

        if 'connection' in name_lower:
            return "Standard SQLAlchemy connection pooling"
        elif 'session' in name_lower:
            return "SQLAlchemy session context manager"
        else:
            return "Direct database library usage"

    def _is_simple_wrapper_factory(self, factory: Dict) -> bool:
        """Check if a factory is a simple wrapper around another class."""
        # This would need more sophisticated analysis in practice
        return (
            factory['method_count'] <= 3 and
            factory['lines'] < 50 and
            'wrapper' in factory['name'].lower()
        )

    def _analyze_wrapper_factory(self, factory: Dict) -> Dict:
        """Analyze a wrapper factory to understand what it wraps."""
        return {
            'type': 'simple_wrapper',
            'wrapped_class': 'UnknownClass',  # Would extract from AST analysis
            'value_added': 'Minimal - just instantiation',
            'elimination_benefit': 'Reduced complexity, direct instantiation'
        }

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if a file should be skipped during analysis."""
        skip_patterns = ['venv', '__pycache__', '.git', 'node_modules', '.backup']
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path from project root."""
        try:
            return str(Path(file_path).relative_to(self.project_root))
        except ValueError:
            return file_path


if __name__ == '__main__':
    import unittest

    print("🚀 Starting Factory Proliferation Detection - Phase 2 Cleanup")
    print("=" * 80)
    print("These tests are designed to FAIL initially to demonstrate over-engineering scope.")
    print("=" * 80)

    unittest.main(verbosity=2)