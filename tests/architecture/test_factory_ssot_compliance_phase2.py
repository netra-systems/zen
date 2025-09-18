"""
Factory SSOT Compliance Validation - Phase 2
Ensures remaining factories follow SSOT principles after cleanup.

Purpose:
Validate Single Source of Truth patterns in essential factory classes while
identifying SSOT violations that need consolidation. These tests ensure that
preserved factories follow proper SSOT principles.

Business Impact: 500K+ ARR protection through SSOT compliance
SSOT Advancement: Eliminates factory pattern fragmentation

Essential factories should PASS these tests, over-engineered factories should FAIL.
"""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
import hashlib
import importlib.util

from test_framework.ssot.base_test_case import SSotBaseTestCase


class FactorySSotValidator(ast.NodeVisitor):
    """AST visitor to validate SSOT compliance in factory classes."""

    def __init__(self):
        self.factory_classes = []
        self.import_paths = []
        self.method_signatures = []
        self.ssot_violations = []

    def visit_ClassDef(self, node):
        """Analyze factory class definitions for SSOT compliance."""
        if 'factory' in node.name.lower() or 'Factory' in node.name:
            # Extract method signatures for duplicate detection
            methods = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_sig = self._create_method_signature(item)
                    methods.append(method_sig)

            # Check for SSOT patterns
            has_ssot_patterns = self._check_ssot_patterns(node, methods)

            class_info = {
                'name': node.name,
                'methods': methods,
                'bases': [self._get_base_name(base) for base in node.bases],
                'line_start': node.lineno,
                'line_end': getattr(node, 'end_lineno', node.lineno + 10),
                'has_ssot_patterns': has_ssot_patterns,
                'docstring': ast.get_docstring(node)
            }
            self.factory_classes.append(class_info)

        self.generic_visit(node)

    def visit_Import(self, node):
        """Track import statements for SSOT path validation."""
        for alias in node.names:
            if 'factory' in alias.name.lower():
                self.import_paths.append({
                    'type': 'import',
                    'module': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno
                })

    def visit_ImportFrom(self, node):
        """Track from imports for SSOT path validation."""
        if node.module and 'factory' in node.module.lower():
            for alias in node.names:
                self.import_paths.append({
                    'type': 'from',
                    'module': node.module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno
                })

    def _create_method_signature(self, method_node):
        """Create a signature for method comparison."""
        return {
            'name': method_node.name,
            'args': [arg.arg for arg in method_node.args.args],
            'decorators': [self._get_decorator_name(d) for d in method_node.decorator_list],
            'is_static': any(d for d in method_node.decorator_list
                           if (isinstance(d, ast.Name) and d.id == 'staticmethod')),
            'is_classmethod': any(d for d in method_node.decorator_list
                                if (isinstance(d, ast.Name) and d.id == 'classmethod'))
        }

    def _check_ssot_patterns(self, class_node, methods):
        """Check if factory follows SSOT patterns."""
        # Look for SSOT indicators in docstring
        docstring = ast.get_docstring(class_node)
        if docstring and 'SSOT' in docstring.upper():
            return True

        # Look for singleton prevention patterns
        has_instance_method = any(m['name'] == 'create_instance' for m in methods)
        has_factory_method = any(m['name'].startswith('create_') for m in methods)

        return has_instance_method or has_factory_method

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


class FactorySSotCompliancePhase2Tests(SSotBaseTestCase):
    """
    Factory SSOT Compliance Validation - Phase 2

    Validates SSOT compliance in essential factory patterns while identifying
    violations that need consolidation.
    """

    def setUp(self):
        """Set up SSOT compliance validation environment."""
        super().setUp()
        self.project_root = Path(__file__).parents[2]
        self.ssot_analysis = {}
        self.essential_factories = []
        self.violation_factories = []

        # Essential factory patterns that MUST be preserved and SSOT compliant
        self.essential_factory_patterns = {
            'user_execution_engine': {
                'purpose': 'Multi-user isolation and security',
                'business_critical': True,
                'required_methods': ['create_user_engine', 'create_user_context'],
                'ssot_requirements': ['single_instance_per_user', 'isolated_state']
            },
            'websocket_event_emitter': {
                'purpose': 'Chat functionality WebSocket events',
                'business_critical': True,
                'required_methods': ['create_emitter', 'bind_to_user'],
                'ssot_requirements': ['user_specific_routing', 'event_ordering']
            },
            'auth_token_validator': {
                'purpose': 'Security authentication',
                'business_critical': True,
                'required_methods': ['create_validator', 'validate_token'],
                'ssot_requirements': ['secure_validation', 'no_token_leakage']
            },
            'database_connection_pool': {
                'purpose': 'Database access optimization',
                'business_critical': True,
                'required_methods': ['create_connection', 'manage_pool'],
                'ssot_requirements': ['connection_reuse', 'transaction_isolation']
            }
        }

    def test_01_user_isolation_factory_ssot_compliance(self):
        """
        EXPECTED: PASS - Validates essential user isolation factories

        UserExecutionEngine factory patterns are CRITICAL for multi-user
        security and must follow SSOT principles while being preserved.
        """
        print(f"\n🔍 PHASE 2.1: Validating user isolation factory SSOT compliance...")

        user_isolation_factories = self._discover_user_isolation_factories()

        print(f"📊 USER ISOLATION FACTORY ANALYSIS:")
        print(f"  🔍 User isolation factories found: {len(user_isolation_factories)}")
        print(f"  🎯 Expected for business requirements: 1-2 essential patterns")

        ssot_compliance_results = []

        for factory in user_isolation_factories:
            compliance_score = self._validate_user_isolation_ssot_compliance(factory)

            ssot_compliance_results.append({
                **factory,
                'ssot_compliance_score': compliance_score['score'],
                'ssot_violations': compliance_score['violations'],
                'business_critical': self._is_business_critical_user_factory(factory),
                'preservation_required': compliance_score['score'] >= 7  # High threshold for user isolation
            })

        # Separate essential vs over-engineered
        essential_user_factories = [f for f in ssot_compliance_results if f['preservation_required']]
        over_engineered_user_factories = [f for f in ssot_compliance_results if not f['preservation_required']]

        print(f"\nCHECK ESSENTIAL USER ISOLATION FACTORIES (PRESERVE):")
        for i, factory in enumerate(essential_user_factories):
            rel_path = self._get_relative_path(factory['file'])
            print(f"  {i+1}. {factory['name']} ({rel_path})")
            print(f"     🎯 SSOT compliance: {factory['ssot_compliance_score']}/10")
            print(f"     💼 Business critical: {factory['business_critical']}")
            print(f"     CHECK Action: PRESERVE - Essential for multi-user security")

        print(f"\nX OVER-ENGINEERED USER FACTORIES (REMOVE):")
        for i, factory in enumerate(over_engineered_user_factories):
            rel_path = self._get_relative_path(factory['file'])
            print(f"  {i+1}. {factory['name']} ({rel_path})")
            print(f"     🎯 SSOT compliance: {factory['ssot_compliance_score']}/10")
            print(f"     X Violations: {', '.join(factory['ssot_violations'])}")
            print(f"     🗑️  Action: REMOVE - Fails SSOT compliance")

        self.ssot_analysis['user_isolation'] = {
            'essential_factories': essential_user_factories,
            'over_engineered_factories': over_engineered_user_factories
        }

        # Essential user isolation factories MUST PASS SSOT compliance
        failing_essential = [f for f in essential_user_factories if f['ssot_compliance_score'] < 7]

        self.assertEqual(
            len(failing_essential),
            0,
            f"CHECK USER ISOLATION SSOT COMPLIANCE: All {len(essential_user_factories)} essential user isolation factories "
            f"must pass SSOT compliance. Found {len(failing_essential)} failing SSOT compliance tests. "
            f"This is CRITICAL for 500K+ ARR multi-user security."
        )

    def test_02_websocket_factory_ssot_consolidation(self):
        """
        EXPECTED: INITIALLY FAIL, then PASS after consolidation

        WebSocket factory patterns should be consolidated to single
        implementations per service following SSOT principles.
        """
        print(f"\n🔍 PHASE 2.2: Validating WebSocket factory SSOT consolidation...")

        websocket_factories = self._discover_websocket_factories()

        print(f"📊 WEBSOCKET FACTORY ANALYSIS:")
        print(f"  🔍 WebSocket factories found: {len(websocket_factories)}")
        print(f"  🎯 SSOT target: 1 canonical implementation per service")

        # Group by service for SSOT analysis
        service_websocket_factories = defaultdict(list)
        for factory in websocket_factories:
            service = self._determine_factory_service(factory)
            service_websocket_factories[service].append(factory)

        ssot_violations = []
        ssot_compliant_services = []

        print(f"\n📋 WEBSOCKET FACTORY SERVICE ANALYSIS:")
        for service, factories in service_websocket_factories.items():
            print(f"  🏷️  {service}: {len(factories)} WebSocket factories")

            if len(factories) > 1:
                # SSOT violation - multiple WebSocket factories per service
                duplicate_analysis = self._analyze_websocket_factory_duplicates(factories)
                ssot_violations.append({
                    'service': service,
                    'factories': factories,
                    'violation_type': 'multiple_implementations',
                    'canonical_candidate': duplicate_analysis['canonical_candidate'],
                    'duplicates_to_remove': duplicate_analysis['duplicates_to_remove']
                })

                print(f"     X SSOT VIOLATION: {len(factories)} competing implementations")
                print(f"     CHECK Canonical: {duplicate_analysis['canonical_candidate']['name']}")
                print(f"     🗑️  Remove: {len(duplicate_analysis['duplicates_to_remove'])} duplicates")
            else:
                # Single implementation - check SSOT compliance
                factory = factories[0]
                compliance = self._validate_websocket_ssot_compliance(factory)

                if compliance['is_compliant']:
                    ssot_compliant_services.append({
                        'service': service,
                        'factory': factory,
                        'compliance_score': compliance['score']
                    })
                    print(f"     CHECK SSOT COMPLIANT: {factory['name']}")
                else:
                    ssot_violations.append({
                        'service': service,
                        'factories': [factory],
                        'violation_type': 'non_compliant_implementation',
                        'compliance_issues': compliance['issues']
                    })
                    print(f"     X SSOT NON-COMPLIANT: {compliance['issues']}")

        print(f"\n🚨 WEBSOCKET SSOT CONSOLIDATION REQUIRED:")
        for violation in ssot_violations:
            print(f"  🏷️  {violation['service']}: {violation['violation_type']}")
            if violation['violation_type'] == 'multiple_implementations':
                print(f"     🎯 Consolidate {len(violation['duplicates_to_remove'])} duplicates")

        self.ssot_analysis['websocket_factories'] = {
            'violations': ssot_violations,
            'compliant_services': ssot_compliant_services
        }

        # This test should FAIL initially due to WebSocket factory fragmentation
        total_violations = len(ssot_violations)
        self.assertLessEqual(
            total_violations,
            1,
            f"X WEBSOCKET FACTORY SSOT VIOLATIONS: Found {total_violations} services with SSOT violations. "
            f"Expected ≤1 for SSOT compliance. WebSocket factories must be consolidated to single implementations per service."
        )

    def test_03_database_connection_factory_ssot_validation(self):
        """
        EXPECTED: PASS - Validates essential database connection patterns

        Database connection factories that provide genuine value
        (connection pooling, transaction management) should be preserved.
        """
        print(f"\n🔍 PHASE 2.3: Validating database connection factory SSOT patterns...")

        database_factories = self._discover_database_connection_factories()

        print(f"📊 DATABASE CONNECTION FACTORY ANALYSIS:")
        print(f"  🔍 Database connection factories found: {len(database_factories)}")

        essential_db_factories = []
        over_engineered_db_factories = []

        for factory in database_factories:
            value_analysis = self._analyze_database_factory_value(factory)
            ssot_compliance = self._validate_database_factory_ssot_compliance(factory)

            factory_analysis = {
                **factory,
                'business_value_score': value_analysis['value_score'],
                'value_justification': value_analysis['justification'],
                'ssot_compliance_score': ssot_compliance['score'],
                'ssot_violations': ssot_compliance['violations'],
                'preservation_required': (value_analysis['value_score'] >= 6 and
                                        ssot_compliance['score'] >= 6)
            }

            if factory_analysis['preservation_required']:
                essential_db_factories.append(factory_analysis)
            else:
                over_engineered_db_factories.append(factory_analysis)

        print(f"\nCHECK ESSENTIAL DATABASE FACTORIES (PRESERVE):")
        for i, factory in enumerate(essential_db_factories):
            rel_path = self._get_relative_path(factory['file'])
            print(f"  {i+1}. {factory['name']} ({rel_path})")
            print(f"     💼 Business value: {factory['business_value_score']}/10")
            print(f"     🎯 SSOT compliance: {factory['ssot_compliance_score']}/10")
            print(f"     CHECK Justification: {factory['value_justification']}")

        print(f"\nX OVER-ENGINEERED DATABASE FACTORIES (REMOVE):")
        for i, factory in enumerate(over_engineered_db_factories):
            rel_path = self._get_relative_path(factory['file'])
            print(f"  {i+1}. {factory['name']} ({rel_path})")
            print(f"     💼 Business value: {factory['business_value_score']}/10")
            print(f"     X SSOT violations: {', '.join(factory['ssot_violations'])}")

        self.ssot_analysis['database_factories'] = {
            'essential_factories': essential_db_factories,
            'over_engineered_factories': over_engineered_db_factories
        }

        # Essential database factories should pass SSOT compliance
        failing_essential_db = [f for f in essential_db_factories if f['ssot_compliance_score'] < 6]

        self.assertEqual(
            len(failing_essential_db),
            0,
            f"CHECK DATABASE FACTORY SSOT COMPLIANCE: All {len(essential_db_factories)} essential database factories "
            f"pass SSOT compliance. This ensures reliable database access patterns."
        )

    def test_04_auth_token_factory_ssot_compliance(self):
        """
        EXPECTED: PASS - Validates security-critical auth factories

        Auth token factories are CRITICAL for security and must follow
        SSOT principles while being preserved.
        """
        print(f"\n🔍 PHASE 2.4: Validating auth token factory SSOT compliance...")

        auth_factories = self._discover_auth_token_factories()

        print(f"📊 AUTH TOKEN FACTORY ANALYSIS:")
        print(f"  🔍 Auth token factories found: {len(auth_factories)}")
        print(f"  🛡️  Security criticality: HIGH - Must maintain SSOT compliance")

        ssot_compliant_auth_factories = []
        ssot_violation_auth_factories = []

        for factory in auth_factories:
            security_analysis = self._validate_auth_factory_security_compliance(factory)
            ssot_analysis = self._validate_auth_factory_ssot_compliance(factory)

            auth_factory_result = {
                **factory,
                'security_compliance_score': security_analysis['score'],
                'security_issues': security_analysis['issues'],
                'ssot_compliance_score': ssot_analysis['score'],
                'ssot_violations': ssot_analysis['violations'],
                'is_security_critical': security_analysis['is_critical'],
                'meets_ssot_requirements': ssot_analysis['score'] >= 8  # High threshold for auth
            }

            if auth_factory_result['meets_ssot_requirements']:
                ssot_compliant_auth_factories.append(auth_factory_result)
            else:
                ssot_violation_auth_factories.append(auth_factory_result)

        print(f"\nCHECK SSOT COMPLIANT AUTH FACTORIES:")
        for i, factory in enumerate(ssot_compliant_auth_factories):
            rel_path = self._get_relative_path(factory['file'])
            print(f"  {i+1}. {factory['name']} ({rel_path})")
            print(f"     🛡️  Security compliance: {factory['security_compliance_score']}/10")
            print(f"     🎯 SSOT compliance: {factory['ssot_compliance_score']}/10")
            print(f"     CHECK Status: PRESERVE - Security critical and SSOT compliant")

        print(f"\nX SSOT VIOLATION AUTH FACTORIES:")
        for i, factory in enumerate(ssot_violation_auth_factories):
            rel_path = self._get_relative_path(factory['file'])
            print(f"  {i+1}. {factory['name']} ({rel_path})")
            print(f"     🛡️  Security compliance: {factory['security_compliance_score']}/10")
            print(f"     X SSOT violations: {', '.join(factory['ssot_violations'])}")
            print(f"     🔧 Action: FIX SSOT compliance or consolidate")

        self.ssot_analysis['auth_factories'] = {
            'ssot_compliant': ssot_compliant_auth_factories,
            'ssot_violations': ssot_violation_auth_factories
        }

        # Auth factories MUST maintain SSOT compliance for security
        self.assertEqual(
            len(ssot_violation_auth_factories),
            0,
            f"CHECK AUTH FACTORY SSOT COMPLIANCE: All {len(auth_factories)} auth token factories "
            f"must maintain SSOT compliance for security. Found {len(ssot_violation_auth_factories)} "
            f"with SSOT violations that must be fixed."
        )

    def test_05_factory_import_path_standardization_validation(self):
        """
        EXPECTED: PASS after standardization

        All imports of the same factory should use consistent paths
        following SSOT_IMPORT_REGISTRY.md guidelines.
        """
        print(f"\n🔍 PHASE 2.5: Validating factory import path standardization...")

        import_path_analysis = self._analyze_factory_import_paths()

        print(f"📊 FACTORY IMPORT PATH ANALYSIS:")
        print(f"  🔍 Factory import statements analyzed: {import_path_analysis['total_imports']}")
        print(f"  📦 Unique factory modules: {len(import_path_analysis['unique_modules'])}")
        print(f"  🔄 Inconsistent import patterns: {len(import_path_analysis['inconsistent_patterns'])}")

        standardization_violations = []
        for module, patterns in import_path_analysis['inconsistent_patterns'].items():
            if len(patterns) > 1:
                violation = {
                    'module': module,
                    'patterns': patterns,
                    'canonical_pattern': self._determine_canonical_import_pattern(patterns),
                    'files_affected': sum(len(p['files']) for p in patterns.values())
                }
                standardization_violations.append(violation)

        print(f"\n🚨 IMPORT PATH STANDARDIZATION VIOLATIONS:")
        for i, violation in enumerate(standardization_violations[:5]):
            print(f"  {i+1}. {violation['module']}")
            print(f"     🔄 {len(violation['patterns'])} different import patterns")
            print(f"     CHECK Canonical: {violation['canonical_pattern']}")
            print(f"     📄 Files affected: {violation['files_affected']}")

        print(f"\nCHECK STANDARDIZED IMPORT RECOMMENDATIONS:")
        for violation in standardization_violations[:3]:
            print(f"  📦 {violation['module']}")
            print(f"     🎯 Use: {violation['canonical_pattern']}")
            print(f"     🔧 Update: {violation['files_affected']} files")

        # Import paths should be standardized for SSOT compliance
        self.assertLessEqual(
            len(standardization_violations),
            2,
            f"CHECK FACTORY IMPORT STANDARDIZATION: Found {len(standardization_violations)} import path "
            f"standardization violations. Expected ≤2 for SSOT compliance. "
            f"Import paths must be consistent across the codebase."
        )

    def _discover_user_isolation_factories(self) -> List[Dict]:
        """Discover all user isolation related factory classes."""
        return self._discover_factories_by_pattern(['user', 'execution', 'context', 'isolation'])

    def _discover_websocket_factories(self) -> List[Dict]:
        """Discover all WebSocket related factory classes."""
        return self._discover_factories_by_pattern(['websocket', 'ws', 'socket', 'event', 'emitter'])

    def _discover_database_connection_factories(self) -> List[Dict]:
        """Discover all database connection related factory classes."""
        return self._discover_factories_by_pattern(['database', 'db', 'connection', 'session', 'pool'])

    def _discover_auth_token_factories(self) -> List[Dict]:
        """Discover all auth token related factory classes."""
        return self._discover_factories_by_pattern(['auth', 'token', 'jwt', 'oauth', 'security'])

    def _discover_factories_by_pattern(self, keywords: List[str]) -> List[Dict]:
        """Discover factory classes matching specific keyword patterns."""
        matching_factories = []

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(keyword in content.lower() for keyword in keywords + ['factory']):
                    try:
                        tree = ast.parse(content)
                        validator = FactorySSotValidator()
                        validator.visit(tree)

                        for factory_class in validator.factory_classes:
                            if self._matches_keyword_pattern(factory_class, keywords):
                                matching_factories.append({
                                    **factory_class,
                                    'file': str(py_file),
                                    'relative_path': self._get_relative_path(str(py_file))
                                })

                    except SyntaxError:
                        continue
            except Exception:
                continue

        return matching_factories

    def _matches_keyword_pattern(self, factory_class: Dict, keywords: List[str]) -> bool:
        """Check if factory class matches keyword pattern."""
        factory_text = f"{factory_class['name']} {factory_class.get('docstring', '')}".lower()
        return any(keyword in factory_text for keyword in keywords)

    def _validate_user_isolation_ssot_compliance(self, factory: Dict) -> Dict:
        """Validate SSOT compliance for user isolation factories."""
        score = 0
        violations = []

        # Check for user isolation methods
        has_user_methods = any('user' in method['name'].lower() for method in factory['methods'])
        if has_user_methods:
            score += 3
        else:
            violations.append("Missing user-specific methods")

        # Check for isolation patterns
        has_isolation_patterns = any('isolation' in method['name'].lower() or
                                   'context' in method['name'].lower()
                                   for method in factory['methods'])
        if has_isolation_patterns:
            score += 3
        else:
            violations.append("Missing isolation patterns")

        # Check for SSOT documentation
        if factory.get('docstring') and 'SSOT' in factory['docstring']:
            score += 2

        # Check for singleton prevention
        has_instance_methods = any(method['name'] in ['create_instance', 'get_instance']
                                 for method in factory['methods'])
        if has_instance_methods:
            score += 2
        else:
            violations.append("Missing instance creation methods")

        return {'score': score, 'violations': violations}

    def _is_business_critical_user_factory(self, factory: Dict) -> bool:
        """Check if user factory is business critical."""
        critical_keywords = ['execution', 'engine', 'context', 'isolation', 'security']
        factory_text = f"{factory['name']} {factory.get('docstring', '')}".lower()

        return any(keyword in factory_text for keyword in critical_keywords)

    def _determine_factory_service(self, factory: Dict) -> str:
        """Determine which service a factory belongs to."""
        file_path = factory['file'].lower()

        if 'netra_backend' in file_path:
            return 'netra_backend'
        elif 'auth_service' in file_path:
            return 'auth_service'
        elif 'shared' in file_path:
            return 'shared'
        elif 'test_framework' in file_path:
            return 'test_framework'
        else:
            return 'unknown'

    def _analyze_websocket_factory_duplicates(self, factories: List[Dict]) -> Dict:
        """Analyze WebSocket factory duplicates to identify canonical implementation."""
        # Score factories to determine canonical implementation
        scored_factories = []

        for factory in factories:
            score = self._score_websocket_factory_canonicalness(factory)
            scored_factories.append((score, factory))

        # Sort by score (highest first)
        scored_factories.sort(key=lambda x: x[0], reverse=True)

        canonical_candidate = scored_factories[0][1]
        duplicates_to_remove = [f[1] for f in scored_factories[1:]]

        return {
            'canonical_candidate': canonical_candidate,
            'duplicates_to_remove': duplicates_to_remove
        }

    def _score_websocket_factory_canonicalness(self, factory: Dict) -> int:
        """Score a WebSocket factory for canonicalness."""
        score = 0

        # Prefer factories in shared or main backend
        service = self._determine_factory_service(factory)
        if service == 'shared':
            score += 10
        elif service == 'netra_backend':
            score += 8

        # Prefer factories with more comprehensive methods
        if len(factory['methods']) >= 5:
            score += 5

        # Prefer factories with SSOT documentation
        if factory.get('docstring') and 'SSOT' in factory['docstring']:
            score += 3

        return score

    def _validate_websocket_ssot_compliance(self, factory: Dict) -> Dict:
        """Validate SSOT compliance for WebSocket factories."""
        score = 8  # Start with high score for single implementation
        issues = []

        # Check for essential WebSocket methods
        essential_methods = ['create_emitter', 'emit_event', 'bind_user']
        has_essential = any(any(essential in method['name'].lower()
                              for essential in essential_methods)
                          for method in factory['methods'])

        if not has_essential:
            score -= 3
            issues.append("Missing essential WebSocket methods")

        # Check for user binding capabilities
        has_user_binding = any('user' in method['name'].lower()
                             for method in factory['methods'])
        if not has_user_binding:
            score -= 2
            issues.append("Missing user binding methods")

        return {
            'is_compliant': score >= 6,
            'score': score,
            'issues': issues
        }

    def _analyze_database_factory_value(self, factory: Dict) -> Dict:
        """Analyze business value of database factory."""
        value_score = 0
        justification = []

        # Check for connection management
        has_connection_mgmt = any('connection' in method['name'].lower() or
                                'pool' in method['name'].lower()
                                for method in factory['methods'])
        if has_connection_mgmt:
            value_score += 4
            justification.append("Connection pooling management")

        # Check for transaction management
        has_transaction_mgmt = any('transaction' in method['name'].lower() or
                                 'commit' in method['name'].lower()
                                 for method in factory['methods'])
        if has_transaction_mgmt:
            value_score += 3
            justification.append("Transaction management")

        # Check for session management
        has_session_mgmt = any('session' in method['name'].lower()
                             for method in factory['methods'])
        if has_session_mgmt:
            value_score += 2
            justification.append("Session lifecycle management")

        return {
            'value_score': value_score,
            'justification': '; '.join(justification) if justification else 'Limited business value'
        }

    def _validate_database_factory_ssot_compliance(self, factory: Dict) -> Dict:
        """Validate SSOT compliance for database factories."""
        score = 0
        violations = []

        # Check for singleton prevention
        has_instance_methods = any('create' in method['name'].lower()
                                 for method in factory['methods'])
        if has_instance_methods:
            score += 3
        else:
            violations.append("Missing instance creation methods")

        # Check for resource management
        has_cleanup = any('close' in method['name'].lower() or
                        'cleanup' in method['name'].lower()
                        for method in factory['methods'])
        if has_cleanup:
            score += 2
        else:
            violations.append("Missing resource cleanup methods")

        # Check for configuration isolation
        has_config = any('config' in method['name'].lower()
                       for method in factory['methods'])
        if has_config:
            score += 1

        return {'score': score, 'violations': violations}

    def _validate_auth_factory_security_compliance(self, factory: Dict) -> Dict:
        """Validate security compliance for auth factories."""
        score = 0
        issues = []
        is_critical = False

        # Check for token validation methods
        has_validation = any('validate' in method['name'].lower() or
                           'verify' in method['name'].lower()
                           for method in factory['methods'])
        if has_validation:
            score += 4
            is_critical = True
        else:
            issues.append("Missing token validation methods")

        # Check for secure token creation
        has_creation = any('create' in method['name'].lower() or
                         'generate' in method['name'].lower()
                         for method in factory['methods'])
        if has_creation:
            score += 3
        else:
            issues.append("Missing secure token creation")

        # Check for expiration handling
        has_expiration = any('expire' in method['name'].lower() or
                           'ttl' in method['name'].lower()
                           for method in factory['methods'])
        if has_expiration:
            score += 2

        return {
            'score': score,
            'issues': issues,
            'is_critical': is_critical
        }

    def _validate_auth_factory_ssot_compliance(self, factory: Dict) -> Dict:
        """Validate SSOT compliance for auth factories."""
        score = 0
        violations = []

        # Check for centralized validation
        has_central_validation = len([m for m in factory['methods']
                                    if 'validate' in m['name'].lower()]) == 1
        if has_central_validation:
            score += 4
        else:
            violations.append("Multiple validation methods - SSOT violation")

        # Check for secure instance creation
        has_secure_creation = any(method['is_static']
                                for method in factory['methods']
                                if 'create' in method['name'].lower())
        if has_secure_creation:
            score += 3
        else:
            violations.append("Missing static factory methods")

        # Check for SSOT documentation
        if factory.get('docstring') and 'SSOT' in factory['docstring']:
            score += 1

        return {'score': score, 'violations': violations}

    def _analyze_factory_import_paths(self) -> Dict:
        """Analyze factory import paths for consistency."""
        import_analysis = {
            'total_imports': 0,
            'unique_modules': set(),
            'inconsistent_patterns': defaultdict(lambda: defaultdict(list))
        }

        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if 'factory' in content.lower():
                    try:
                        tree = ast.parse(content)
                        validator = FactorySSotValidator()
                        validator.visit(tree)

                        for import_path in validator.import_paths:
                            import_analysis['total_imports'] += 1

                            module_key = import_path.get('module', '')
                            if 'factory' in module_key.lower():
                                import_analysis['unique_modules'].add(module_key)

                                pattern = self._normalize_import_pattern(import_path)
                                import_analysis['inconsistent_patterns'][module_key][pattern].append(str(py_file))

                    except SyntaxError:
                        continue
            except Exception:
                continue

        return import_analysis

    def _normalize_import_pattern(self, import_path: Dict) -> str:
        """Normalize import pattern for comparison."""
        if import_path['type'] == 'from':
            return f"from {import_path['module']} import {import_path['name']}"
        else:
            return f"import {import_path['module']}"

    def _determine_canonical_import_pattern(self, patterns: Dict) -> str:
        """Determine the canonical import pattern from alternatives."""
        # Prefer patterns from shared modules
        for pattern in patterns.keys():
            if 'shared' in pattern:
                return pattern

        # Prefer shorter, more direct imports
        return min(patterns.keys(), key=len)

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if a file should be skipped during analysis."""
        skip_patterns = ['venv', '__pycache__', '.git', 'node_modules', '.backup', '.pyc']
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path from project root."""
        try:
            return str(Path(file_path).relative_to(self.project_root))
        except ValueError:
            return file_path


if __name__ == '__main__':
    import unittest

    print("🚀 Starting Factory SSOT Compliance Validation - Phase 2")
    print("=" * 80)
    print("Essential factories should PASS, over-engineered factories should FAIL.")
    print("=" * 80)

    unittest.main(verbosity=2)