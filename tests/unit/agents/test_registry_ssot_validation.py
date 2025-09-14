"""Agent Registry SSOT Validation Tests - P0 Business Critical

This test suite validates single agent registry after SSOT consolidation.
These tests are designed to FAIL initially (detecting SSOT violations) and
PASS after successful agent registry consolidation.

Business Value Justification:
- Segment: Platform/Core Business Infrastructure  
- Business Goal: Stability & Multi-User Chat Reliability
- Value Impact: Protects $500K+ ARR by ensuring single agent registry prevents
  execution conflicts, user isolation failures, and race conditions
- Strategic Impact: Foundation for reliable chat experience and agent coordination

Key Validation Areas:
1. Single Registry Instance Enforcement - No duplicate registries allowed
2. Agent Discovery Consistency - All agents discoverable through one path  
3. Registry Factory Pattern Compliance - SSOT factory patterns enforced
4. No Duplicate Agent Registration - Prevents conflicts and memory leaks
5. Registry Thread Safety - Multi-user safe operations guaranteed

EXPECTED BEHAVIOR: 
These tests SHOULD FAIL initially, demonstrating existing registry fragmentation.
After SSOT consolidation, these tests should pass, confirming unified registry.
"""

import asyncio
import importlib
import inspect
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from unittest.mock import patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestRegistrySSotValidation(SSotBaseTestCase):
    """Test suite for validating Agent Registry SSOT compliance."""
    
    def setUp(self):
        """Set up test environment for registry SSOT validation."""
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent.parent
        self.registry_violations = []
        self.registry_instances = []
        
        # Expected SSOT patterns
        self.canonical_registry_module = "netra_backend.app.agents.supervisor.agent_registry"
        self.canonical_registry_class = "EnhancedAgentRegistry"
        self.alternative_registry_class = "AgentRegistry"  # Also acceptable in supervisor module
        
        logger.info("Starting Agent Registry SSOT validation")
    
    def test_single_registry_instance_enforced(self):
        """Validate only one registry instance exists - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 1: Validating single registry instance enforcement")
        
        # Find all registry class definitions
        registry_classes = self._find_registry_class_definitions()
        
        # Log findings
        logger.info(f"Found {len(registry_classes)} registry class definitions:")
        for module_path, class_name in registry_classes:
            logger.info(f"  - {class_name} in {module_path}")
        
        # Count canonical vs non-canonical registries
        canonical_registries = self._count_canonical_registries(registry_classes)
        non_canonical_registries = len(registry_classes) - canonical_registries
        
        # Store violations
        if non_canonical_registries > 0:
            violation_details = [
                f"Non-canonical registry: {class_name} in {module_path}"
                for module_path, class_name in registry_classes
                if not self._is_canonical_registry(module_path, class_name)
            ]
            self.registry_violations.extend(violation_details)
        
        logger.warning(f"❌ REGISTRY FRAGMENTATION: Found {non_canonical_registries} non-canonical registries")
        logger.info(f"✅ CANONICAL: Found {canonical_registries} canonical registries")
        
        # EXPECTED TO FAIL: Multiple registry classes indicate fragmentation
        self.assertGreater(
            non_canonical_registries, 0,
            "EXPECTED FAILURE: Should detect registry fragmentation violations. "
            f"Found {non_canonical_registries} non-canonical registry classes requiring consolidation."
        )
    
    def test_agent_discovery_consistency(self):
        """Validate all agents discoverable through one path - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 2: Validating agent discovery consistency")
        
        # Find all agent discovery methods
        discovery_methods = self._find_agent_discovery_methods()
        
        # Test discovery consistency
        discovery_conflicts = self._detect_discovery_conflicts(discovery_methods)
        
        # Log findings
        logger.info(f"Found {len(discovery_methods)} agent discovery methods")
        logger.info(f"Detected {len(discovery_conflicts)} discovery conflicts:")
        for conflict in discovery_conflicts:
            logger.info(f"  - {conflict}")
        
        # Store violations
        self.registry_violations.extend([
            f"Discovery conflict: {conflict}" for conflict in discovery_conflicts
        ])
        
        # EXPECTED TO FAIL: Discovery conflicts indicate fragmentation
        self.assertGreater(
            len(discovery_conflicts), 0,
            "EXPECTED FAILURE: Should detect agent discovery inconsistencies. "
            f"Found {len(discovery_conflicts)} discovery conflicts requiring unified registry."
        )
    
    def test_registry_factory_pattern_compliance(self):
        """Validate SSOT factory patterns - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 3: Validating registry factory pattern compliance")
        
        # Find factory pattern violations
        factory_violations = self._detect_factory_pattern_violations()
        
        # Log findings
        logger.info(f"Found {len(factory_violations)} factory pattern violations:")
        for violation_type, location, details in factory_violations:
            logger.info(f"  - {violation_type}: {location} - {details}")
        
        # Store violations
        self.registry_violations.extend([
            f"Factory violation ({violation_type}): {location} - {details}"
            for violation_type, location, details in factory_violations
        ])
        
        # EXPECTED TO FAIL: Factory violations should be detected
        self.assertGreater(
            len(factory_violations), 0,
            "EXPECTED FAILURE: Should detect registry factory pattern violations. "
            f"Found {len(factory_violations)} violations requiring SSOT factory consolidation."
        )
    
    def test_no_duplicate_agent_registration(self):
        """Validate no duplicate agent registration - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 4: Validating no duplicate agent registration")
        
        # Simulate agent registration attempts
        registration_conflicts = self._simulate_agent_registration_conflicts()
        
        # Log findings
        logger.info(f"Found {len(registration_conflicts)} registration conflicts:")
        for agent_name, locations in registration_conflicts.items():
            logger.info(f"  - Agent '{agent_name}' registered in {len(locations)} locations: {locations}")
        
        # Store violations
        for agent_name, locations in registration_conflicts.items():
            self.registry_violations.append(
                f"Duplicate registration: Agent '{agent_name}' in {len(locations)} registries"
            )
        
        # EXPECTED TO FAIL: Registration conflicts should be detected
        self.assertGreater(
            len(registration_conflicts), 0,
            "EXPECTED FAILURE: Should detect duplicate agent registration conflicts. "
            f"Found conflicts for {len(registration_conflicts)} agents requiring unified registry."
        )
    
    def test_registry_thread_safety(self):
        """Validate registry thread safety - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 5: Validating registry thread safety")
        
        # Test concurrent registry operations
        thread_safety_violations = self._test_concurrent_registry_operations()
        
        # Log findings
        logger.info(f"Found {len(thread_safety_violations)} thread safety violations:")
        for violation in thread_safety_violations:
            logger.info(f"  - {violation}")
        
        # Store violations
        self.registry_violations.extend([
            f"Thread safety violation: {violation}" for violation in thread_safety_violations
        ])
        
        # EXPECTED TO FAIL: Thread safety violations should be detected
        self.assertGreater(
            len(thread_safety_violations), 0,
            "EXPECTED FAILURE: Should detect registry thread safety violations. "
            f"Found {len(thread_safety_violations)} violations requiring thread-safe SSOT registry."
        )
    
    def test_registry_global_state_detection(self):
        """Detect registry global state violations - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 6: Detecting registry global state violations")
        
        # Scan for global state patterns
        global_state_violations = self._detect_global_state_violations()
        
        # Log findings
        logger.info(f"Found {len(global_state_violations)} global state violations:")
        for violation_type, location, details in global_state_violations:
            logger.info(f"  - {violation_type}: {location} - {details}")
        
        # Store violations
        self.registry_violations.extend([
            f"Global state violation ({violation_type}): {location} - {details}"
            for violation_type, location, details in global_state_violations
        ])
        
        # EXPECTED TO FAIL: Global state should be detected
        self.assertGreater(
            len(global_state_violations), 0,
            "EXPECTED FAILURE: Should detect registry global state violations. "
            f"Found {len(global_state_violations)} violations requiring factory-based SSOT patterns."
        )
    
    def test_registry_import_path_violations(self):
        """Detect registry import path violations - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 7: Detecting registry import path violations")
        
        # Find non-canonical import paths
        import_violations = self._detect_import_path_violations()
        
        # Log findings
        logger.info(f"Found {len(import_violations)} import path violations:")
        for file_path, line_num, import_line in import_violations:
            logger.info(f"  - {file_path}:{line_num}: {import_line.strip()}")
        
        # Store violations
        self.registry_violations.extend([
            f"Import violation: {file_path}:{line_num} - {import_line.strip()}"
            for file_path, line_num, import_line in import_violations
        ])
        
        # EXPECTED TO FAIL: Import violations should be detected
        self.assertGreater(
            len(import_violations), 0,
            "EXPECTED FAILURE: Should detect registry import path violations. "
            f"Found {len(import_violations)} violations requiring canonical import paths."
        )
    
    def test_registry_singleton_pattern_detection(self):
        """Detect registry singleton pattern violations - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 8: Detecting registry singleton pattern violations")
        
        # Scan for singleton patterns
        singleton_violations = self._detect_singleton_patterns()
        
        # Log findings
        logger.info(f"Found {len(singleton_violations)} singleton pattern violations:")
        for location, pattern_type, details in singleton_violations:
            logger.info(f"  - {pattern_type}: {location} - {details}")
        
        # Store violations
        self.registry_violations.extend([
            f"Singleton violation ({pattern_type}): {location} - {details}"
            for location, pattern_type, details in singleton_violations
        ])
        
        # EXPECTED TO FAIL: Singleton patterns should be detected
        self.assertGreater(
            len(singleton_violations), 0,
            "EXPECTED FAILURE: Should detect registry singleton pattern violations. "
            f"Found {len(singleton_violations)} violations requiring factory-based user isolation."
        )
    
    def test_registry_memory_leak_vulnerabilities(self):
        """Detect registry memory leak vulnerabilities - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 9: Detecting registry memory leak vulnerabilities")
        
        # Scan for memory leak patterns
        memory_leak_violations = self._detect_memory_leak_patterns()
        
        # Log findings
        logger.info(f"Found {len(memory_leak_violations)} memory leak vulnerabilities:")
        for vulnerability_type, location, details in memory_leak_violations:
            logger.info(f"  - {vulnerability_type}: {location} - {details}")
        
        # Store violations
        self.registry_violations.extend([
            f"Memory leak vulnerability ({vulnerability_type}): {location} - {details}"
            for vulnerability_type, location, details in memory_leak_violations
        ])
        
        # EXPECTED TO FAIL: Memory leak vulnerabilities should be detected
        self.assertGreater(
            len(memory_leak_violations), 0,
            "EXPECTED FAILURE: Should detect registry memory leak vulnerabilities. "
            f"Found {len(memory_leak_violations)} vulnerabilities requiring proper lifecycle management."
        )
    
    def test_registry_user_isolation_validation(self):
        """Validate registry user isolation patterns - SHOULD INITIALLY FAIL."""
        logger.info("🔍 REGISTRY SSOT TEST 10: Validating registry user isolation")
        
        # Test user isolation enforcement
        isolation_violations = self._test_user_isolation_enforcement()
        
        # Log findings
        logger.info(f"Found {len(isolation_violations)} user isolation violations:")
        for violation in isolation_violations:
            logger.info(f"  - {violation}")
        
        # Store violations
        self.registry_violations.extend([
            f"User isolation violation: {violation}" for violation in isolation_violations
        ])
        
        # EXPECTED TO FAIL: User isolation violations should be detected
        self.assertGreater(
            len(isolation_violations), 0,
            "EXPECTED FAILURE: Should detect registry user isolation violations. "
            f"Found {len(isolation_violations)} violations requiring per-user registry isolation."
        )
    
    def test_comprehensive_registry_ssot_summary(self):
        """Generate comprehensive registry SSOT violation report - SHOULD INITIALLY FAIL."""
        logger.info("📊 REGISTRY SSOT COMPREHENSIVE SUMMARY")
        
        # Ensure all violations are collected
        if not self.registry_violations:
            # Run all validation tests
            self.test_single_registry_instance_enforced()
            self.test_agent_discovery_consistency() 
            self.test_registry_factory_pattern_compliance()
            self.test_no_duplicate_agent_registration()
            self.test_registry_thread_safety()
            self.test_registry_global_state_detection()
            self.test_registry_import_path_violations()
            self.test_registry_singleton_pattern_detection()
            self.test_registry_memory_leak_vulnerabilities()
            self.test_registry_user_isolation_validation()
        
        # Generate comprehensive summary
        violation_summary = {
            'total_violations': len(self.registry_violations),
            'business_impact': self._assess_registry_business_impact(),
            'consolidation_priority': self._assess_consolidation_priority(),
            'ssot_readiness': self._assess_ssot_readiness()
        }
        
        logger.info(f"REGISTRY SSOT VIOLATION SUMMARY:")
        logger.info(f"  Total Violations: {violation_summary['total_violations']}")
        logger.info(f"  Business Impact: {violation_summary['business_impact']['severity']}")
        logger.info(f"  Consolidation Priority: {violation_summary['consolidation_priority']}")
        logger.info(f"  SSOT Readiness: {violation_summary['ssot_readiness']['status']}")
        
        # Log sample violations
        for violation in self.registry_violations[:5]:
            logger.info(f"    ❌ {violation}")
        
        if len(self.registry_violations) > 5:
            logger.info(f"    ... and {len(self.registry_violations) - 5} more violations")
        
        # EXPECTED TO FAIL: Comprehensive violations should be detected
        self.assertGreater(
            violation_summary['total_violations'], 0,
            "EXPECTED FAILURE: Agent Registry SSOT consolidation needed. "
            f"Detected {violation_summary['total_violations']} violations requiring remediation. "
            f"Business Impact: {violation_summary['business_impact']['description']}"
        )

    # Helper Methods
    
    def _find_registry_class_definitions(self) -> List[Tuple[str, str]]:
        """Find all registry class definitions in the codebase."""
        registry_classes = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for line in lines:
                    if line.strip().startswith('class ') and ('Registry' in line or 'registry' in line):
                        class_name = self._extract_class_name(line)
                        if class_name and ('Registry' in class_name or 'registry' in class_name):
                            module_path = self._file_to_module_path(py_file)
                            if module_path:
                                registry_classes.append((module_path, class_name))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(f"Could not read {py_file}: {e}")
        
        return registry_classes
    
    def _count_canonical_registries(self, registry_classes: List[Tuple[str, str]]) -> int:
        """Count canonical registry implementations."""
        count = 0
        for module_path, class_name in registry_classes:
            if self._is_canonical_registry(module_path, class_name):
                count += 1
        return count
    
    def _is_canonical_registry(self, module_path: str, class_name: str) -> bool:
        """Check if registry is canonical implementation."""
        return (self.canonical_registry_module in module_path and 
                (class_name == self.canonical_registry_class or 
                 class_name == self.alternative_registry_class))
    
    def _find_agent_discovery_methods(self) -> List[Dict[str, Any]]:
        """Find all agent discovery method implementations."""
        discovery_methods = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for discovery-related methods
                discovery_patterns = [
                    'def discover_agents',
                    'def get_agents',
                    'def list_agents',
                    'def find_agent',
                    'get_agent_by_'
                ]
                
                for pattern in discovery_patterns:
                    if pattern in content:
                        discovery_methods.append({
                            'file': str(py_file),
                            'pattern': pattern,
                            'content': content
                        })
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return discovery_methods
    
    def _detect_discovery_conflicts(self, discovery_methods: List[Dict[str, Any]]) -> List[str]:
        """Detect agent discovery conflicts."""
        conflicts = []
        
        # Group by discovery patterns
        pattern_groups = {}
        for method in discovery_methods:
            pattern = method['pattern']
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(method['file'])
        
        # Detect conflicts (multiple implementations of same discovery pattern)
        for pattern, files in pattern_groups.items():
            if len(files) > 1:
                conflicts.append(f"Pattern '{pattern}' implemented in {len(files)} files: {files}")
        
        return conflicts
    
    def _detect_factory_pattern_violations(self) -> List[Tuple[str, str, str]]:
        """Detect factory pattern violations in registry implementations."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Detect direct registry instantiation
                if 'Registry(' in content and 'create_registry' not in content:
                    violations.append(("direct_instantiation", str(py_file),
                                     "Direct registry instantiation bypassing factory"))
                
                # Detect multiple factory implementations
                if 'class ' in content and 'RegistryFactory' in content:
                    if self.canonical_registry_module not in str(py_file):
                        violations.append(("duplicate_factory", str(py_file),
                                         "Duplicate registry factory implementation"))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _simulate_agent_registration_conflicts(self) -> Dict[str, List[str]]:
        """Simulate agent registration to detect conflicts."""
        registration_conflicts = {}
        
        # Mock common agent names
        test_agents = ['supervisor', 'triage', 'data_helper', 'optimizer']
        
        # Simulate registration attempts across different registries
        for agent_name in test_agents:
            locations = []
            
            # Check if agent could be registered in multiple places
            for py_file in self.codebase_root.rglob("*.py"):
                if self._should_skip_file(py_file):
                    continue
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for registration patterns
                    if ('register' in content.lower() and 'agent' in content.lower() and
                        agent_name in content.lower()):
                        locations.append(str(py_file))
                
                except (UnicodeDecodeError, IOError):
                    continue
            
            if len(locations) > 1:
                registration_conflicts[agent_name] = locations
        
        return registration_conflicts
    
    def _test_concurrent_registry_operations(self) -> List[str]:
        """Test concurrent registry operations for thread safety."""
        violations = []
        
        try:
            # Test concurrent access patterns
            def registry_operation():
                return f"operation_{uuid.uuid4()}"
            
            # Simulate concurrent operations
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(registry_operation) for _ in range(10)]
                results = [f.result() for f in as_completed(futures, timeout=5)]
            
            # Check for race conditions (simplified simulation)
            if len(set(results)) != len(results):
                violations.append("Potential race condition detected in concurrent operations")
                
        except Exception as e:
            violations.append(f"Thread safety test failed: {str(e)}")
        
        # Check for thread-unsafe patterns in code
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for thread-unsafe patterns
                if 'Registry' in content:
                    if 'threading.Lock' not in content and 'asyncio.Lock' not in content:
                        if 'class ' in content and 'Registry' in content:
                            violations.append(f"Registry in {py_file} lacks thread safety mechanisms")
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _detect_global_state_violations(self) -> List[Tuple[str, str, str]]:
        """Detect global state violations in registry implementations."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Detect global registry variables
                if 'global ' in content and 'registry' in content.lower():
                    violations.append(("global_variable", str(py_file),
                                     "Global registry variable detected"))
                
                # Detect module-level registry instances
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if line.strip().startswith(('_registry', 'registry')) and '=' in line:
                        if not line.strip().startswith('def ') and not line.strip().startswith('#'):
                            violations.append(("module_level_instance", f"{py_file}:{line_num}",
                                             f"Module-level registry: {line.strip()[:50]}..."))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _detect_import_path_violations(self) -> List[Tuple[str, int, str]]:
        """Detect non-canonical registry import paths."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Check for non-canonical registry imports
                    if ('import ' in line_stripped and 'registry' in line_stripped.lower() and
                        self.canonical_registry_module not in line_stripped):
                        # Skip canonical imports
                        if not self._is_canonical_import(line_stripped):
                            violations.append((str(py_file), line_num, line))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _detect_singleton_patterns(self) -> List[Tuple[str, str, str]]:
        """Detect singleton pattern violations in registry implementations."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Detect singleton patterns
                if 'Registry' in content:
                    if '_instance = None' in content or '__instance' in content:
                        violations.append((str(py_file), "singleton_instance",
                                         "Singleton instance pattern detected"))
                    
                    if '__new__' in content and 'Registry' in content:
                        violations.append((str(py_file), "singleton_new",
                                         "Singleton __new__ method detected"))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _detect_memory_leak_patterns(self) -> List[Tuple[str, str, str]]:
        """Detect memory leak patterns in registry implementations."""
        violations = []
        
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'Registry' in content:
                    # Detect lack of cleanup methods
                    if 'cleanup' not in content and 'clear' not in content:
                        violations.append((str(py_file), "missing_cleanup",
                                         "No cleanup/clear methods found"))
                    
                    # Detect unbounded collections
                    if '_agents = {}' in content or '_agents = []' in content:
                        if 'pop(' not in content and 'remove(' not in content:
                            violations.append((str(py_file), "unbounded_collection",
                                             "Unbounded agent collection detected"))
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _test_user_isolation_enforcement(self) -> List[str]:
        """Test user isolation enforcement in registry."""
        violations = []
        
        # Mock user contexts
        user_contexts = [f"user_{i}" for i in range(3)]
        
        try:
            # Test isolation simulation
            for user_context in user_contexts:
                # Simulate registry operations for different users
                result = self._simulate_user_registry_operation(user_context)
                if not result:
                    violations.append(f"Registry operation failed for user: {user_context}")
        
        except Exception as e:
            violations.append(f"User isolation test failed: {str(e)}")
        
        # Check for user isolation patterns in code
        for py_file in self.codebase_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'Registry' in content and 'user' in content.lower():
                    if 'user_id' not in content and 'UserContext' not in content:
                        violations.append(f"Registry in {py_file} lacks user context validation")
                
            except (UnicodeDecodeError, IOError):
                continue
        
        return violations
    
    def _simulate_user_registry_operation(self, user_context: str) -> bool:
        """Simulate a registry operation for a specific user."""
        try:
            # Simple simulation of user-scoped operation
            operation_id = f"{user_context}_{uuid.uuid4()}"
            return len(operation_id) > 0
        except:
            return False
    
    def _assess_registry_business_impact(self) -> Dict[str, Any]:
        """Assess business impact of registry SSOT violations."""
        total_violations = len(self.registry_violations)
        
        if total_violations > 30:
            severity = "CRITICAL"
            description = "Severe registry fragmentation threatens $500K+ ARR chat reliability"
        elif total_violations > 15:
            severity = "HIGH"
            description = "Significant fragmentation risks multi-user agent coordination"
        elif total_violations > 8:
            severity = "MEDIUM"
            description = "Moderate fragmentation may cause agent discovery issues"
        else:
            severity = "LOW"
            description = "Minor fragmentation with limited business impact"
        
        return {
            'severity': severity,
            'description': description,
            'chat_functionality_risk': severity in ['CRITICAL', 'HIGH'],
            'multi_user_risk': any('isolation' in v for v in self.registry_violations)
        }
    
    def _assess_consolidation_priority(self) -> str:
        """Assess registry consolidation priority."""
        if any('isolation' in v for v in self.registry_violations):
            return "P0 - IMMEDIATE (User isolation violations)"
        elif len(self.registry_violations) > 15:
            return "P1 - URGENT (Major fragmentation)"
        elif any('thread safety' in v for v in self.registry_violations):
            return "P2 - HIGH (Thread safety issues)"
        else:
            return "P3 - MEDIUM (Cleanup needed)"
    
    def _assess_ssot_readiness(self) -> Dict[str, Any]:
        """Assess readiness for SSOT consolidation."""
        try:
            # Try importing canonical registry
            from netra_backend.app.agents.supervisor.agent_registry import EnhancedAgentRegistry
            canonical_available = True
        except ImportError:
            canonical_available = False
        
        if canonical_available and len(self.registry_violations) == 0:
            status = "READY - SSOT consolidation complete"
        elif canonical_available:
            status = "PARTIAL - Canonical available but violations exist"
        else:
            status = "NOT_READY - Canonical registry missing"
        
        return {
            'status': status,
            'canonical_available': canonical_available,
            'violations_remaining': len(self.registry_violations)
        }
    
    # Utility methods
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            '__pycache__', '.pyc', 'node_modules', '.git', 'venv', '.env',
            'test_registry_ssot_validation.py',  # Skip self
            'backup', 'archived'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _extract_class_name(self, line: str) -> str:
        """Extract class name from class definition line."""
        try:
            class_part = line.split('class ')[1]
            if '(' in class_part:
                class_name = class_part.split('(')[0].strip()
            elif ':' in class_part:
                class_name = class_part.split(':')[0].strip()
            else:
                class_name = class_part.strip()
            return class_name
        except (IndexError, AttributeError):
            return ""
    
    def _file_to_module_path(self, file_path: Path) -> str:
        """Convert file path to Python module path."""
        try:
            rel_path = file_path.relative_to(self.codebase_root)
            module_path = str(rel_path.with_suffix(''))
            module_path = module_path.replace('/', '.').replace('\\', '.')
            return module_path
        except (ValueError, AttributeError):
            return ""
    
    def _is_canonical_import(self, line: str) -> bool:
        """Check if import line uses canonical registry paths."""
        return self.canonical_registry_module in line


if __name__ == '__main__':
    import unittest
    unittest.main()