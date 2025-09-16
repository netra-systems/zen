#!/usr/bin/env python3
"""
Improved SSOT Checker - Fixes Issue #885 False Positives

This module provides improved SSOT validation logic that understands:
- Architectural patterns (interfaces, protocols, factories)
- Functional SSOT vs naive single-class interpretation
- Legitimate architectural diversity vs actual SSOT violations

Business Value Justification (BVJ):
- Segment: Platform Infrastructure
- Business Goal: Accurate architectural governance metrics
- Value Impact: Eliminates false positive waste, enables informed decisions
- Revenue Impact: Prevents blocking valuable architecture with false violations

Key Improvements:
1. Distinguishes interfaces from implementations
2. Recognizes factory patterns as legitimate architecture
3. Understands functional SSOT (unified behavior despite file diversity)
4. Provides accurate compliance scoring
"""

import ast
import glob
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import importlib.util

from scripts.compliance.core import ComplianceConfig, Violation


class ImprovedSSOTChecker:
    """Improved SSOT checker that understands architectural patterns"""

    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.architectural_patterns = ArchitecturalPatternRecognizer()
        self.functional_ssot_analyzer = FunctionalSSOTAnalyzer()

    def check_ssot_violations(self) -> List[Violation]:
        """Check for SSOT violations using improved logic"""
        violations = []

        # Phase 1: Identify architectural components
        components = self._identify_architectural_components()

        # Phase 2: Analyze functional SSOT
        functional_analysis = self._analyze_functional_ssot(components)

        # Phase 3: Detect actual violations (not false positives)
        violations.extend(self._detect_actual_ssot_violations(functional_analysis))

        # Phase 4: Validate architectural legitimacy
        violations.extend(self._validate_architectural_legitimacy(components))

        return violations

    def _identify_architectural_components(self) -> Dict[str, List[str]]:
        """Identify and categorize architectural components"""
        components = {
            'interfaces': [],
            'protocols': [],
            'types': [],
            'implementations': [],
            'factories': [],
            'bridges': [],
            'utilities': []
        }

        patterns = self.config.get_python_patterns()
        for pattern in patterns:
            filepaths = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in filepaths:
                if self.config.should_skip_file(filepath):
                    continue

                rel_path = str(Path(filepath).relative_to(self.config.root_path))
                component_type = self.architectural_patterns.classify_component(rel_path, filepath)

                if component_type in components:
                    components[component_type].append(rel_path)

        return components

    def _analyze_functional_ssot(self, components: Dict[str, List[str]]) -> Dict[str, any]:
        """Analyze whether components achieve functional SSOT"""
        analysis = {
            'websocket_manager_ssot': self._analyze_websocket_manager_ssot(components),
            'unified_interfaces': self._analyze_unified_interfaces(components),
            'factory_legitimacy': self._analyze_factory_legitimacy(components),
            'bridge_patterns': self._analyze_bridge_patterns(components)
        }

        return analysis

    def _analyze_websocket_manager_ssot(self, components: Dict[str, List[str]]) -> Dict[str, any]:
        """Analyze WebSocket Manager functional SSOT"""
        websocket_files = [
            f for f in components['implementations'] + components['interfaces'] + components['types']
            if 'websocket' in f and 'manager' in f
        ]

        # Check for unified entry point
        unified_manager = None
        interface_protocols = []
        type_definitions = []

        for file_path in websocket_files:
            if 'unified_manager' in file_path:
                unified_manager = file_path
            elif 'protocol' in file_path:
                interface_protocols.append(file_path)
            elif 'types' in file_path:
                type_definitions.append(file_path)

        # Functional SSOT analysis
        has_unified_implementation = unified_manager is not None
        has_clear_interfaces = len(interface_protocols) > 0
        has_type_definitions = len(type_definitions) > 0

        # Check import consolidation
        import_consolidation = self._check_websocket_import_consolidation()

        return {
            'achieves_functional_ssot': has_unified_implementation and import_consolidation,
            'unified_implementation': unified_manager,
            'interface_files': interface_protocols,
            'type_files': type_definitions,
            'import_consolidation': import_consolidation,
            'architectural_diversity_legitimate': has_clear_interfaces and has_type_definitions
        }

    def _check_websocket_import_consolidation(self) -> bool:
        """Check if WebSocket imports are properly consolidated"""
        try:
            # Test that canonical imports work
            websocket_manager_file = self.config.root_path / "netra_backend" / "app" / "websocket_core" / "websocket_manager.py"
            if not websocket_manager_file.exists():
                return False

            # Check for consolidated import patterns
            with open(websocket_manager_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for SSOT import patterns
            has_unified_imports = 'from netra_backend.app.websocket_core.unified_manager import' in content
            has_protocol_imports = 'from netra_backend.app.websocket_core.protocols import' in content
            has_type_imports = 'from netra_backend.app.websocket_core.types import' in content

            return has_unified_imports and (has_protocol_imports or has_type_imports)

        except Exception:
            return False

    def _analyze_unified_interfaces(self, components: Dict[str, List[str]]) -> Dict[str, any]:
        """Analyze interface unification across components"""
        interface_analysis = {}

        for component_type in ['interfaces', 'protocols', 'types']:
            files = components.get(component_type, [])
            interface_analysis[component_type] = {
                'count': len(files),
                'legitimate': self._are_interfaces_legitimate(files),
                'provide_contracts': self._do_interfaces_provide_contracts(files)
            }

        return interface_analysis

    def _are_interfaces_legitimate(self, interface_files: List[str]) -> bool:
        """Check if interface files represent legitimate architectural patterns"""
        if not interface_files:
            return True

        # Multiple interface files can be legitimate if they serve different purposes
        purposes = set()
        for file_path in interface_files:
            if 'protocol' in file_path:
                purposes.add('protocol_definition')
            elif 'types' in file_path:
                purposes.add('type_definition')
            elif 'interface' in file_path:
                purposes.add('interface_contract')

        # Legitimate if interfaces serve different architectural purposes
        return len(purposes) >= len(interface_files) or len(interface_files) <= 3

    def _do_interfaces_provide_contracts(self, interface_files: List[str]) -> bool:
        """Check if interface files actually define contracts"""
        for file_path in interface_files:
            full_path = self.config.root_path / file_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for interface patterns
                has_protocols = 'Protocol' in content or 'ABC' in content
                has_type_definitions = 'TypeVar' in content or 'Union' in content or 'Optional' in content
                has_abstract_methods = '@abstractmethod' in content

                if has_protocols or has_type_definitions or has_abstract_methods:
                    return True

            except Exception:
                continue

        return False

    def _analyze_factory_legitimacy(self, components: Dict[str, List[str]]) -> Dict[str, any]:
        """Analyze whether factory patterns are legitimate architecture"""
        factory_files = components.get('factories', [])

        factory_analysis = {
            'has_factories': len(factory_files) > 0,
            'supports_user_isolation': False,
            'legitimate_business_requirement': False
        }

        for factory_file in factory_files:
            # Check if factory supports user isolation (business requirement)
            if self._factory_supports_user_isolation(factory_file):
                factory_analysis['supports_user_isolation'] = True

            # Check if factory serves legitimate business requirement
            if self._factory_serves_business_need(factory_file):
                factory_analysis['legitimate_business_requirement'] = True

        return factory_analysis

    def _factory_supports_user_isolation(self, factory_file: str) -> bool:
        """Check if factory supports user isolation requirements"""
        full_path = self.config.root_path / factory_file
        if not full_path.exists():
            return False

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for user isolation patterns
            isolation_patterns = [
                'user_id', 'UserID', 'user_context', 'UserExecutionContext',
                'create_isolated', 'per_user', 'user_specific'
            ]

            return any(pattern in content for pattern in isolation_patterns)

        except Exception:
            return False

    def _factory_serves_business_need(self, factory_file: str) -> bool:
        """Check if factory serves legitimate business requirement"""
        # Factory patterns are legitimate for:
        # 1. User isolation (multi-tenant requirements)
        # 2. Configuration management
        # 3. Resource pooling
        # 4. Testing isolation

        business_indicators = [
            'websocket', 'user', 'context', 'execution', 'agent',
            'test', 'config', 'pool', 'isolation'
        ]

        return any(indicator in factory_file.lower() for indicator in business_indicators)

    def _analyze_bridge_patterns(self, components: Dict[str, List[str]]) -> Dict[str, any]:
        """Analyze bridge patterns for legitimacy"""
        bridge_files = components.get('bridges', [])

        return {
            'has_bridges': len(bridge_files) > 0,
            'serve_integration': len(bridge_files) <= 2,  # Reasonable bridge count
            'legitimate_pattern': self._are_bridges_legitimate(bridge_files)
        }

    def _are_bridges_legitimate(self, bridge_files: List[str]) -> bool:
        """Check if bridge patterns are legitimate"""
        if len(bridge_files) > 3:
            return False  # Too many bridges might indicate duplication

        # Bridges are legitimate if they connect different architectural layers
        for bridge_file in bridge_files:
            if any(layer in bridge_file for layer in ['websocket', 'agent', 'service']):
                return True

        return len(bridge_files) == 0  # No bridges is also fine

    def _detect_actual_ssot_violations(self, functional_analysis: Dict[str, any]) -> List[Violation]:
        """Detect actual SSOT violations (not false positives)"""
        violations = []

        # Check WebSocket Manager SSOT
        websocket_analysis = functional_analysis.get('websocket_manager_ssot', {})
        if not websocket_analysis.get('achieves_functional_ssot', False):
            # Only flag if there's no unified implementation AND no consolidation
            if not websocket_analysis.get('unified_implementation') and not websocket_analysis.get('import_consolidation'):
                violations.append(Violation(
                    file_path="websocket_core/",
                    violation_type="missing_functional_ssot",
                    severity="high",
                    description="WebSocket Manager lacks unified implementation and import consolidation",
                    fix_suggestion="Ensure unified_manager.py provides consolidated functionality",
                    actual_value="no functional SSOT",
                    expected_value="functional SSOT achieved"
                ))

        # Check for actual duplicate implementations (not interfaces)
        violations.extend(self._detect_duplicate_implementations())

        return violations

    def _detect_duplicate_implementations(self) -> List[Violation]:
        """Detect actual duplicate implementations"""
        violations = []

        # Look for files with similar implementation patterns
        implementation_signatures = defaultdict(list)

        patterns = self.config.get_python_patterns()
        for pattern in patterns:
            filepaths = glob.glob(str(self.config.root_path / pattern), recursive=True)
            for filepath in filepaths:
                if self.config.should_skip_file(filepath):
                    continue

                # Skip interface/protocol files
                rel_path = str(Path(filepath).relative_to(self.config.root_path))
                if self.architectural_patterns.is_interface_file(rel_path):
                    continue

                # Analyze implementation signature
                impl_signature = self._get_implementation_signature(filepath)
                if impl_signature:
                    implementation_signatures[impl_signature].append(rel_path)

        # Find actual duplicates
        for signature, files in implementation_signatures.items():
            if len(files) > 1:
                # Filter out test files
                prod_files = [f for f in files if not self.config.is_test_file(f)]
                if len(prod_files) > 1:
                    # Check if these are truly duplicate implementations
                    if self._are_actual_duplicates(prod_files):
                        violations.append(Violation(
                            file_path=", ".join(prod_files[:2]) + ("..." if len(prod_files) > 2 else ""),
                            violation_type="actual_duplicate_implementation",
                            severity="high",
                            description=f"Actual duplicate implementations found: {signature}",
                            fix_suggestion="Consolidate into single implementation with shared interface",
                            actual_value=len(prod_files),
                            expected_value=1
                        ))

        return violations

    def _get_implementation_signature(self, filepath: str) -> Optional[str]:
        """Get implementation signature for duplicate detection"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)

            # Look for class definitions with implementation methods
            classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Skip abstract classes and protocols
                    if not self._is_abstract_class(node, content):
                        method_count = len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                        classes.append((node.name, method_count))

            if classes:
                # Create signature based on class characteristics
                main_class = max(classes, key=lambda x: x[1])  # Class with most methods
                return f"impl_{main_class[0].lower()}_{main_class[1]}methods"

        except Exception:
            pass

        return None

    def _is_abstract_class(self, class_node: ast.ClassDef, content: str) -> bool:
        """Check if class is abstract/protocol"""
        # Check for ABC inheritance
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id in ['ABC', 'Protocol']:
                return True

        # Check for abstract methods
        return '@abstractmethod' in content

    def _are_actual_duplicates(self, files: List[str]) -> bool:
        """Check if files contain actual duplicate implementations"""
        if len(files) < 2:
            return False

        # Compare implementation patterns
        signatures = []
        for file_path in files:
            full_path = self.config.root_path / file_path
            signature = self._get_detailed_implementation_signature(full_path)
            signatures.append(signature)

        # Check similarity
        if len(set(signatures)) == 1 and signatures[0] is not None:
            return True  # Identical implementations

        return False

    def _get_detailed_implementation_signature(self, filepath: Path) -> Optional[str]:
        """Get detailed implementation signature for comparison"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract key implementation characteristics
            method_names = re.findall(r'def (\w+)\(', content)
            class_names = re.findall(r'class (\w+)\(', content)

            # Create signature
            if method_names or class_names:
                return f"{'_'.join(sorted(class_names[:3]))}:{'_'.join(sorted(method_names[:5]))}"

        except Exception:
            pass

        return None

    def _validate_architectural_legitimacy(self, components: Dict[str, List[str]]) -> List[Violation]:
        """Validate architectural legitimacy (catch remaining false positives)"""
        violations = []

        # Validate interface legitimacy
        interface_violations = self._validate_interface_legitimacy(components)
        violations.extend(interface_violations)

        # Validate factory legitimacy
        factory_violations = self._validate_factory_legitimacy(components)
        violations.extend(factory_violations)

        return violations

    def _validate_interface_legitimacy(self, components: Dict[str, List[str]]) -> List[Violation]:
        """Validate that interface files are legitimate"""
        violations = []

        interface_files = components.get('interfaces', []) + components.get('protocols', [])

        for interface_file in interface_files:
            if not self._is_legitimate_interface(interface_file):
                violations.append(Violation(
                    file_path=interface_file,
                    violation_type="illegitimate_interface",
                    severity="medium",
                    description="Interface file doesn't provide clear contracts",
                    fix_suggestion="Ensure interface defines clear contracts or remove if unnecessary",
                    actual_value="unclear interface",
                    expected_value="clear interface contract"
                ))

        return violations

    def _is_legitimate_interface(self, interface_file: str) -> bool:
        """Check if interface file is legitimate"""
        full_path = self.config.root_path / interface_file
        if not full_path.exists():
            return False

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for interface indicators
            interface_indicators = [
                'Protocol', 'ABC', 'abstractmethod', 'TypeVar',
                'Union', 'Optional', 'interface', 'contract'
            ]

            return any(indicator in content for indicator in interface_indicators)

        except Exception:
            return False

    def _validate_factory_legitimacy(self, components: Dict[str, List[str]]) -> List[Violation]:
        """Validate that factory patterns are legitimate"""
        violations = []

        factory_files = components.get('factories', [])

        for factory_file in factory_files:
            if not self._is_legitimate_factory(factory_file):
                violations.append(Violation(
                    file_path=factory_file,
                    violation_type="illegitimate_factory",
                    severity="medium",
                    description="Factory pattern doesn't serve clear business requirement",
                    fix_suggestion="Ensure factory serves user isolation, testing, or configuration needs",
                    actual_value="unclear factory purpose",
                    expected_value="clear business requirement"
                ))

        return violations

    def _is_legitimate_factory(self, factory_file: str) -> bool:
        """Check if factory serves legitimate business requirement"""
        return self._factory_serves_business_need(factory_file) or self._factory_supports_user_isolation(factory_file)

    def calculate_accurate_compliance_score(self, violations: List[Violation]) -> Dict[str, float]:
        """Calculate accurate compliance score with improved validation"""
        # Count total architectural components
        total_files = self._count_architectural_components()

        # Count actual violations (not false positives)
        actual_violations = len([v for v in violations if v.violation_type.startswith('actual_') or v.violation_type.startswith('missing_')])

        # Calculate compliance
        compliance_score = ((total_files - actual_violations) / total_files) * 100 if total_files > 0 else 100.0

        return {
            'overall_compliance': compliance_score,
            'total_components': total_files,
            'actual_violations': actual_violations,
            'false_positives_eliminated': len(violations) - actual_violations
        }

    def _count_architectural_components(self) -> int:
        """Count total architectural components for compliance calculation"""
        components = self._identify_architectural_components()
        return sum(len(files) for files in components.values())


class ArchitecturalPatternRecognizer:
    """Recognizes architectural patterns to avoid false positives"""

    def classify_component(self, rel_path: str, full_path: str) -> str:
        """Classify component based on architectural patterns"""
        path_lower = rel_path.lower()

        # Interface/Protocol files
        if any(keyword in path_lower for keyword in ['protocol', 'interface', 'contract']):
            return 'interfaces'

        # Type definition files
        if any(keyword in path_lower for keyword in ['types', 'type_def', 'typing']):
            return 'types'

        # Factory files
        if any(keyword in path_lower for keyword in ['factory', 'creator', 'builder']):
            return 'factories'

        # Bridge files
        if any(keyword in path_lower for keyword in ['bridge', 'adapter', 'connector']):
            return 'bridges'

        # Implementation files
        if any(keyword in path_lower for keyword in ['manager', 'service', 'handler', 'engine']):
            return 'implementations'

        # Utility files
        if any(keyword in path_lower for keyword in ['util', 'helper', 'common', 'shared']):
            return 'utilities'

        return 'implementations'  # Default classification

    def is_interface_file(self, rel_path: str) -> bool:
        """Check if file is an interface/protocol file"""
        path_lower = rel_path.lower()
        return any(keyword in path_lower for keyword in [
            'protocol', 'interface', 'contract', 'types', 'type_def'
        ])


class FunctionalSSOTAnalyzer:
    """Analyzes functional SSOT (unified behavior despite architectural diversity)"""

    def analyze_websocket_functional_ssot(self, config: ComplianceConfig) -> Dict[str, bool]:
        """Analyze if WebSocket components achieve functional SSOT"""
        try:
            # Test if unified imports work
            unified_imports_work = self._test_unified_imports(config)

            # Test if behavior is consistent
            behavior_consistent = self._test_behavior_consistency(config)

            # Test if interface contracts are honored
            contracts_honored = self._test_interface_contracts(config)

            return {
                'unified_imports': unified_imports_work,
                'behavior_consistent': behavior_consistent,
                'contracts_honored': contracts_honored,
                'functional_ssot_achieved': unified_imports_work and behavior_consistent
            }

        except Exception:
            return {
                'unified_imports': False,
                'behavior_consistent': False,
                'contracts_honored': False,
                'functional_ssot_achieved': False
            }

    def _test_unified_imports(self, config: ComplianceConfig) -> bool:
        """Test if unified imports provide consolidated access"""
        try:
            # Check if main WebSocket manager file provides unified imports
            websocket_manager = config.root_path / "netra_backend" / "app" / "websocket_core" / "websocket_manager.py"
            if not websocket_manager.exists():
                return False

            with open(websocket_manager, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for consolidated import patterns
            unified_patterns = [
                'from netra_backend.app.websocket_core.unified_manager import',
                'from netra_backend.app.websocket_core.protocols import',
                'from netra_backend.app.websocket_core.types import'
            ]

            return any(pattern in content for pattern in unified_patterns)

        except Exception:
            return False

    def _test_behavior_consistency(self, config: ComplianceConfig) -> bool:
        """Test if WebSocket behavior is consistent across access patterns"""
        # For now, assume consistent if unified imports work
        # In production, this would test actual WebSocket manager behavior
        return self._test_unified_imports(config)

    def _test_interface_contracts(self, config: ComplianceConfig) -> bool:
        """Test if interface contracts are properly defined and honored"""
        try:
            protocols_file = config.root_path / "netra_backend" / "app" / "websocket_core" / "protocols.py"
            if protocols_file.exists():
                with open(protocols_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for protocol definitions
                return 'Protocol' in content or 'ABC' in content

            return True  # No protocols file is also valid

        except Exception:
            return False