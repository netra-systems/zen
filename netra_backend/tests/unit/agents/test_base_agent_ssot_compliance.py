from shared.isolated_environment import get_env
"""
BaseAgent SSOT (Single Source of Truth) Compliance Test Suite

This comprehensive test suite verifies SSOT compliance across the BaseAgent infrastructure.
Tests are designed to FAIL in the current state to detect multiple implementations of the same functionality.

CRITICAL: These tests ensure that there is only ONE implementation of each reliability pattern,
circuit breaker configuration, execution pattern, and related infrastructure components.

Expected Behavior:
- Each test should PASS once SSOT violations are fixed
- Tests are designed to detect duplicate implementations, inconsistent interfaces, and pattern violations
- WebSocket events should already PASS as they follow proper SSOT via WebSocketBridgeAdapter

Test Categories:
1. Circuit Breaker SSOT Compliance
2. Configuration SSOT Compliance
3. Reliability Manager SSOT Compliance
4. Execution Pattern SSOT Compliance
5. Retry Logic SSOT Compliance
6. WebSocket Event SSOT Compliance (should pass)
"""

import pytest
import inspect
import importlib
from typing import Dict, List, Any, Set, Tuple
from pathlib import Path
from dataclasses import fields
import ast
import sys
import os

# Add the project root to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter


class TestCircuitBreakerSSOTCompliance:
    """Test circuit breaker implementations for SSOT violations."""
    
    def test_single_circuit_breaker_implementation(self):
        """
        CRITICAL: Verify only ONE circuit breaker implementation exists.
        
        Current State: SHOULD FAIL - Multiple implementations detected
        Expected: Only netra_backend.app.core.circuit_breaker_core should be canonical
        """
        circuit_breaker_modules = self._find_circuit_breaker_modules()
        
        # Expected: Only one canonical implementation
        expected_canonical_module = "netra_backend.app.core.circuit_breaker_core"
        
        # Find all actual circuit breaker implementations
        implementations = []
        for module_path in circuit_breaker_modules:
            try:
                module = importlib.import_module(module_path)
                classes = self._find_circuit_breaker_classes(module)
                if classes:
                    implementations.append((module_path, classes))
            except ImportError:
                continue
        
        # ASSERTION: Should have only ONE implementation
        assert len(implementations) == 1, (
            f"SSOT VIOLATION: Found {len(implementations)} circuit breaker implementations. "
            f"Expected only 1 canonical implementation at {expected_canonical_module}. "
            f"Found implementations: {[impl[0] for impl in implementations]}. "
            f"Consolidate all circuit breaker logic into {expected_canonical_module}."
        )
        
        # Verify it's the expected canonical implementation
        canonical_found = any(impl[0] == expected_canonical_module for impl in implementations)
        assert canonical_found, (
            f"SSOT VIOLATION: Canonical circuit breaker implementation not found at {expected_canonical_module}. "
            f"All circuit breaker logic must be consolidated into this single module."
        )
    
    def test_circuit_breaker_config_consistency(self):
        """
        CRITICAL: Verify only ONE circuit breaker configuration class exists.
        
        Current State: SHOULD FAIL - Multiple config classes detected
        Expected: Single configuration class with consistent interface
        """
        config_classes = self._find_circuit_breaker_config_classes()
        
        # Check for multiple configuration classes
        unique_configs = {}
        for module_path, class_name, class_obj in config_classes:
            key = (class_name, self._get_class_signature(class_obj))
            if key not in unique_configs:
                unique_configs[key] = []
            unique_configs[key].append((module_path, class_obj))
        
        # ASSERTION: Should have only ONE configuration pattern
        config_patterns = len(unique_configs)
        assert config_patterns == 1, (
            f"SSOT VIOLATION: Found {config_patterns} different circuit breaker configuration patterns. "
            f"Expected only 1 unified configuration class. "
            f"Found patterns: {list(unique_configs.keys())}. "
            f"Consolidate all circuit breaker configurations into a single class."
        )
        
        # Check for field consistency across any remaining configs
        if len(config_classes) > 1:
            self._assert_config_field_consistency(config_classes)
    
    def test_circuit_breaker_interface_consistency(self):
        """
        CRITICAL: Verify all circuit breakers have consistent interfaces.
        
        Current State: SHOULD FAIL - Inconsistent method signatures detected
        Expected: All circuit breakers should implement the same interface
        """
        circuit_breaker_classes = self._find_all_circuit_breaker_classes()
        
        if len(circuit_breaker_classes) <= 1:
            pytest.skip("Only one or no circuit breaker classes found - SSOT already achieved")
        
        # Extract method signatures from each class
        method_signatures = {}
        for module_path, class_name, class_obj in circuit_breaker_classes:
            signatures = self._extract_method_signatures(class_obj)
            method_signatures[(module_path, class_name)] = signatures
        
        # Find common methods across all implementations
        common_methods = set.intersection(*[set(sigs.keys()) for sigs in method_signatures.values()])
        
        # Check consistency of common methods
        inconsistencies = []
        for method_name in common_methods:
            signatures_for_method = {}
            for (module_path, class_name), signatures in method_signatures.items():
                if method_name in signatures:
                    sig_key = str(signatures[method_name])
                    if sig_key not in signatures_for_method:
                        signatures_for_method[sig_key] = []
                    signatures_for_method[sig_key].append(f"{module_path}.{class_name}")
            
            # ASSERTION: Method should have consistent signature across implementations
            if len(signatures_for_method) > 1:
                inconsistencies.append({
                    'method': method_name,
                    'signatures': signatures_for_method
                })
        
        assert len(inconsistencies) == 0, (
            f"SSOT VIOLATION: Circuit breaker interface inconsistencies detected. "
            f"Method signature mismatches: {inconsistencies}. "
            f"All circuit breaker implementations must have identical interfaces."
        )
    
    def test_circuit_breaker_state_management_duplication(self):
        """
        CRITICAL: Verify no duplicate state management logic exists.
        
        Current State: SHOULD FAIL - Duplicate state tracking detected
        Expected: Single state management implementation
        """
        state_management_patterns = self._find_state_management_patterns()
        
        # Analyze patterns for duplication
        pattern_signatures = {}
        for module_path, pattern_info in state_management_patterns.items():
            # Create signature based on state fields and methods
            signature = self._create_state_signature(pattern_info)
            if signature not in pattern_signatures:
                pattern_signatures[signature] = []
            pattern_signatures[signature].append(module_path)
        
        # ASSERTION: Should have only ONE state management pattern
        unique_patterns = len(pattern_signatures)
        assert unique_patterns == 1, (
            f"SSOT VIOLATION: Found {unique_patterns} different state management patterns. "
            f"Expected only 1 unified state management implementation. "
            f"Duplicate patterns found in: {dict(pattern_signatures)}. "
            f"Consolidate all state management logic into single implementation."
        )
    
    def _find_circuit_breaker_modules(self) -> List[str]:
        """Find all modules that might contain circuit breaker implementations."""
        base_path = Path(__file__).parent.parent.parent.parent.parent
        circuit_breaker_files = list(base_path.rglob("*circuit_breaker*.py"))
        
        modules = []
        for file_path in circuit_breaker_files:
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue
            
            # Convert file path to module path
            relative_path = file_path.relative_to(base_path)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
            modules.append(module_path)
        
        return modules
    
    def _find_circuit_breaker_classes(self, module) -> List[Tuple[str, type]]:
        """Find circuit breaker classes in a module."""
        classes = []
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if "circuit" in name.lower() and "breaker" in name.lower():
                if not name.startswith("_"):  # Skip private classes
                    classes.append((name, obj))
        return classes
    
    def _find_circuit_breaker_config_classes(self) -> List[Tuple[str, str, type]]:
        """Find all circuit breaker configuration classes."""
        configs = []
        circuit_breaker_modules = self._find_circuit_breaker_modules()
        
        for module_path in circuit_breaker_modules:
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if ("config" in name.lower() and "circuit" in name.lower()) or \
                       (name.endswith("Config") and "circuit" in str(obj).lower()):
                        configs.append((module_path, name, obj))
            except ImportError:
                continue
        
        return configs
    
    def _find_all_circuit_breaker_classes(self) -> List[Tuple[str, str, type]]:
        """Find all circuit breaker classes across modules."""
        classes = []
        circuit_breaker_modules = self._find_circuit_breaker_modules()
        
        for module_path in circuit_breaker_modules:
            try:
                module = importlib.import_module(module_path)
                module_classes = self._find_circuit_breaker_classes(module)
                for class_name, class_obj in module_classes:
                    classes.append((module_path, class_name, class_obj))
            except ImportError:
                continue
        
        return classes
    
    def _get_class_signature(self, class_obj) -> str:
        """Get a signature string for a class based on its fields and methods."""
        if hasattr(class_obj, "__dataclass_fields__"):
            # Dataclass - use field names and types
            field_sigs = []
            for field in fields(class_obj):
                field_sigs.append(f"{field.name}:{field.type}")
            return f"dataclass({','.join(field_sigs)})"
        else:
            # Regular class - use method signatures
            methods = []
            for name, method in inspect.getmembers(class_obj, inspect.isfunction):
                if not name.startswith("_"):
                    try:
                        sig = inspect.signature(method)
                        methods.append(f"{name}{sig}")
                    except (ValueError, TypeError):
                        methods.append(name)
            return f"class({','.join(sorted(methods))})"
    
    def _assert_config_field_consistency(self, config_classes: List[Tuple[str, str, type]]):
        """Assert that configuration classes have consistent fields."""
        field_sets = {}
        
        for module_path, class_name, class_obj in config_classes:
            if hasattr(class_obj, "__dataclass_fields__"):
                field_names = set(field.name for field in fields(class_obj))
                field_sets[f"{module_path}.{class_name}"] = field_names
        
        if len(field_sets) > 1:
            # Check for field consistency
            all_fields = set.union(*field_sets.values())
            for config_name, config_fields in field_sets.items():
                missing_fields = all_fields - config_fields
                if missing_fields:
                    pytest.fail(
                        f"SSOT VIOLATION: Configuration field inconsistency in {config_name}. "
                        f"Missing fields: {missing_fields}. "
                        f"All configuration classes must have identical field sets."
                    )
    
    def _extract_method_signatures(self, class_obj) -> Dict[str, inspect.Signature]:
        """Extract method signatures from a class."""
        signatures = {}
        for name, method in inspect.getmembers(class_obj, inspect.isfunction):
            if not name.startswith("_"):  # Skip private methods
                try:
                    signatures[name] = inspect.signature(method)
                except (ValueError, TypeError):
                    # Skip methods where signature can't be determined
                    pass
        return signatures
    
    def _find_state_management_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Find state management patterns across circuit breaker implementations."""
        patterns = {}
        circuit_breaker_modules = self._find_circuit_breaker_modules()
        
        for module_path in circuit_breaker_modules:
            try:
                module = importlib.import_module(module_path)
                pattern_info = self._analyze_state_management(module)
                if pattern_info:
                    patterns[module_path] = pattern_info
            except ImportError:
                continue
        
        return patterns
    
    def _analyze_state_management(self, module) -> Dict[str, Any]:
        """Analyze state management patterns in a module."""
        state_info = {
            'enums': [],
            'state_fields': [],
            'state_methods': []
        }
        
        # Look for state-related patterns
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj):
                # Check for state enums
                if hasattr(obj, '__members__') and any(
                    state_keyword in str(obj).lower() 
                    for state_keyword in ['state', 'status', 'circuit']
                ):
                    state_info['enums'].append(name)
                
                # Check for state fields in dataclasses
                if hasattr(obj, "__dataclass_fields__"):
                    for field in fields(obj):
                        if 'state' in field.name.lower():
                            state_info['state_fields'].append(field.name)
            
            elif inspect.isfunction(obj):
                # Check for state-related methods
                if any(keyword in name.lower() for keyword in ['state', 'status', 'transition']):
                    state_info['state_methods'].append(name)
        
        return state_info if any(state_info.values()) else None
    
    def _create_state_signature(self, pattern_info: Dict[str, Any]) -> str:
        """Create a signature for state management pattern."""
        parts = []
        for key, values in pattern_info.items():
            if values:
                parts.append(f"{key}:{sorted(values)}")
        return "|".join(parts)


class TestConfigurationSSOTCompliance:
    """Test configuration management for SSOT violations."""
    
    def test_single_configuration_source_pattern(self):
        """
        CRITICAL: Verify configuration follows SSOT pattern.
        
        Current State: SHOULD FAIL - Multiple configuration patterns detected
        Expected: Single configuration access pattern across all agents
        """
        config_access_patterns = self._find_configuration_access_patterns()
        
        # Analyze patterns for consistency
        pattern_types = set()
        for module_path, accesses in config_access_patterns.items():
            for access_pattern in accesses:
                pattern_types.add(access_pattern['type'])
        
        # ASSERTION: Should use consistent configuration access
        assert len(pattern_types) <= 2, (  # Allow agent_config and get_config()
            f"SSOT VIOLATION: Found {len(pattern_types)} different configuration access patterns. "
            f"Expected at most 2 consistent patterns (agent_config and get_config()). "
            f"Found patterns: {pattern_types}. "
            f"Standardize configuration access across all components."
        )
        
        # Check for deprecated direct os.environ access
        direct_env_access = self._find_direct_env_access()
        assert len(direct_env_access) == 0, (
            f"SSOT VIOLATION: Direct os.environ access found in {len(direct_env_access)} locations. "
            f"Direct environment access violates SSOT. Use IsolatedEnvironment or agent_config instead. "
            f"Locations: {direct_env_access}"
        )
    
    def test_timeout_configuration_consistency(self):
        """
        CRITICAL: Verify timeout configurations are consistent.
        
        Current State: SHOULD FAIL - Multiple timeout configuration patterns
        Expected: Single timeout configuration source
        """
        timeout_configs = self._find_timeout_configurations()
        
        # Analyze timeout patterns
        timeout_patterns = {}
        for module_path, timeouts in timeout_configs.items():
            for timeout_info in timeouts:
                pattern_key = (timeout_info['field_name'], timeout_info['default_value'])
                if pattern_key not in timeout_patterns:
                    timeout_patterns[pattern_key] = []
                timeout_patterns[pattern_key].append(module_path)
        
        # Check for inconsistent timeout defaults
        field_defaults = {}
        for (field_name, default_value), modules in timeout_patterns.items():
            if field_name not in field_defaults:
                field_defaults[field_name] = {}
            if default_value not in field_defaults[field_name]:
                field_defaults[field_name][default_value] = []
            field_defaults[field_name][default_value].extend(modules)
        
        # ASSERTION: Each timeout field should have consistent defaults
        inconsistent_fields = []
        for field_name, defaults in field_defaults.items():
            if len(defaults) > 1:
                inconsistent_fields.append((field_name, defaults))
        
        assert len(inconsistent_fields) == 0, (
            f"SSOT VIOLATION: Inconsistent timeout configurations detected. "
            f"Fields with multiple defaults: {inconsistent_fields}. "
            f"All timeout configurations must use consistent default values."
        )
    
    def _find_configuration_access_patterns(self) -> Dict[str, List[Dict[str, str]]]:
        """Find configuration access patterns across modules."""
        patterns = {}
        
        # Analyze BaseAgent and related modules
        base_modules = [
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.agents.base.reliability_manager",
            "netra_backend.app.agents.base.executor",
        ]
        
        for module_path in base_modules:
            try:
                module = importlib.import_module(module_path)
                source_code = inspect.getsource(module)
                accesses = self._extract_config_accesses(source_code)
                if accesses:
                    patterns[module_path] = accesses
            except (ImportError, OSError):
                continue
        
        return patterns
    
    def _extract_config_accesses(self, source_code: str) -> List[Dict[str, str]]:
        """Extract configuration access patterns from source code."""
        accesses = []
        
        # Parse AST to find configuration accesses
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id == "get_config":
                            accesses.append({"type": "get_config", "location": f"line_{node.lineno}"})
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id == "agent_config":
                            accesses.append({"type": "agent_config", "location": f"line_{node.lineno}"})
        except SyntaxError:
            # If source can't be parsed, skip analysis
            pass
        
        return accesses
    
    def _find_direct_env_access(self) -> List[str]:
        """Find direct os.environ access violations."""
        violations = []
        
        base_modules = [
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.agents.base.reliability_manager",
            "netra_backend.app.agents.base.executor",
        ]
        
        for module_path in base_modules:
            try:
                module = importlib.import_module(module_path)
                source_code = inspect.getsource(module)
                if "os.environ" in source_code or "os.getenv" in source_code:
                    violations.append(module_path)
            except (ImportError, OSError):
                continue
        
        return violations
    
    def _find_timeout_configurations(self) -> Dict[str, List[Dict[str, Any]]]:
        """Find timeout configuration patterns."""
        timeout_configs = {}
        
        base_modules = [
            "netra_backend.app.agents.base_agent",
            "netra_backend.app.agents.base.reliability_manager",
            "netra_backend.app.agents.base.circuit_breaker",
        ]
        
        for module_path in base_modules:
            try:
                module = importlib.import_module(module_path)
                timeouts = self._extract_timeout_configs(module)
                if timeouts:
                    timeout_configs[module_path] = timeouts
            except ImportError:
                continue
        
        return timeout_configs
    
    def _extract_timeout_configs(self, module) -> List[Dict[str, Any]]:
        """Extract timeout configurations from a module."""
        timeouts = []
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and hasattr(obj, "__dataclass_fields__"):
                for field in fields(obj):
                    if "timeout" in field.name.lower():
                        timeouts.append({
                            "class_name": name,
                            "field_name": field.name,
                            "default_value": field.default if field.default != field.default_factory else None
                        })
        
        return timeouts


class TestReliabilityManagerSSOTCompliance:
    """Test reliability manager implementations for SSOT violations."""
    
    def test_single_reliability_manager_implementation(self):
        """
        CRITICAL: Verify only ONE reliability manager pattern exists.
        
        Current State: SHOULD FAIL - Multiple reliability managers detected
        Expected: Single ReliabilityManager class as SSOT
        """
        reliability_implementations = self._find_reliability_implementations()
        
        # ASSERTION: Should have only ONE primary implementation
        primary_implementations = [
            impl for impl in reliability_implementations 
            if not self._is_legacy_or_helper(impl[0])
        ]
        
        assert len(primary_implementations) == 1, (
            f"SSOT VIOLATION: Found {len(primary_implementations)} primary reliability manager implementations. "
            f"Expected only 1 canonical implementation. "
            f"Primary implementations: {[impl[0] for impl in primary_implementations]}. "
            f"Consolidate all reliability management logic into single class."
        )
        
        # Verify expected canonical implementation exists
        canonical_found = any(
            "base.reliability_manager" in impl[0] and impl[1] == "ReliabilityManager"
            for impl in primary_implementations
        )
        assert canonical_found, (
            "SSOT VIOLATION: Expected canonical ReliabilityManager not found in "
            "netra_backend.app.agents.base.reliability_manager. "
            "This should be the single source of truth for reliability management."
        )
    
    def test_reliability_interface_consistency(self):
        """
        CRITICAL: Verify reliability manager interfaces are consistent.
        
        Current State: SHOULD FAIL - Inconsistent method signatures
        Expected: All reliability managers implement identical interface
        """
        reliability_implementations = self._find_reliability_implementations()
        
        if len(reliability_implementations) <= 1:
            pytest.skip("Only one or no reliability implementations found")
        
        # Extract method signatures
        interface_signatures = {}
        for module_path, class_name, class_obj in reliability_implementations:
            key = f"{module_path}.{class_name}"
            interface_signatures[key] = self._extract_reliability_methods(class_obj)
        
        # Find core reliability methods that should be consistent
        core_methods = {"execute_safely", "execute_with_reliability", "get_health_status"}
        
        # Check method signature consistency
        inconsistencies = []
        for method_name in core_methods:
            signatures_found = {}
            for impl_key, methods in interface_signatures.items():
                if method_name in methods:
                    sig_str = str(methods[method_name])
                    if sig_str not in signatures_found:
                        signatures_found[sig_str] = []
                    signatures_found[sig_str].append(impl_key)
            
            if len(signatures_found) > 1:
                inconsistencies.append({
                    'method': method_name,
                    'signatures': signatures_found
                })
        
        assert len(inconsistencies) == 0, (
            f"SSOT VIOLATION: Reliability manager interface inconsistencies detected. "
            f"Method signature conflicts: {inconsistencies}. "
            f"All reliability managers must implement identical core interface."
        )
    
    def test_health_tracking_duplication(self):
        """
        CRITICAL: Verify no duplicate health tracking logic.
        
        Current State: SHOULD FAIL - Multiple health tracking implementations
        Expected: Single health tracking mechanism
        """
        health_tracking_patterns = self._find_health_tracking_patterns()
        
        # Analyze health tracking implementations
        tracking_signatures = {}
        for module_path, tracking_info in health_tracking_patterns.items():
            signature = self._create_health_signature(tracking_info)
            if signature not in tracking_signatures:
                tracking_signatures[signature] = []
            tracking_signatures[signature].append(module_path)
        
        # ASSERTION: Should have single health tracking pattern
        unique_patterns = len(tracking_signatures)
        assert unique_patterns == 1, (
            f"SSOT VIOLATION: Found {unique_patterns} different health tracking patterns. "
            f"Expected only 1 unified health tracking implementation. "
            f"Duplicate patterns in: {dict(tracking_signatures)}. "
            f"Consolidate health tracking into single mechanism."
        )
    
    def _find_reliability_implementations(self) -> List[Tuple[str, str, type]]:
        """Find all reliability manager implementations."""
        implementations = []
        
        # Search for reliability modules
        base_path = Path(__file__).parent.parent.parent.parent.parent
        reliability_files = list(base_path.rglob("*reliability*.py"))
        
        for file_path in reliability_files:
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue
            
            relative_path = file_path.relative_to(base_path)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
            
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if "reliability" in name.lower() and not name.startswith("_"):
                        implementations.append((module_path, name, obj))
            except ImportError:
                continue
        
        return implementations
    
    def _is_legacy_or_helper(self, module_path: str) -> bool:
        """Check if module is legacy or helper implementation."""
        legacy_indicators = ["legacy", "compat", "wrapper", "helper", "utils"]
        return any(indicator in module_path.lower() for indicator in legacy_indicators)
    
    def _extract_reliability_methods(self, class_obj) -> Dict[str, inspect.Signature]:
        """Extract reliability-related methods from class."""
        methods = {}
        for name, method in inspect.getmembers(class_obj):
            if (inspect.ismethod(method) or inspect.isfunction(method)) and not name.startswith("_"):
                try:
                    methods[name] = inspect.signature(method)
                except (ValueError, TypeError):
                    pass
        return methods
    
    def _find_health_tracking_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Find health tracking patterns across reliability implementations."""
        patterns = {}
        reliability_implementations = self._find_reliability_implementations()
        
        for module_path, class_name, class_obj in reliability_implementations:
            tracking_info = self._analyze_health_tracking(class_obj)
            if tracking_info:
                patterns[f"{module_path}.{class_name}"] = tracking_info
        
        return patterns
    
    def _analyze_health_tracking(self, class_obj) -> Dict[str, Any]:
        """Analyze health tracking implementation in a class."""
        health_info = {
            'health_methods': [],
            'stats_attributes': [],
            'monitoring_methods': []
        }
        
        for name, obj in inspect.getmembers(class_obj):
            if "health" in name.lower():
                if inspect.ismethod(obj) or inspect.isfunction(obj):
                    health_info['health_methods'].append(name)
                else:
                    health_info['stats_attributes'].append(name)
            elif any(keyword in name.lower() for keyword in ['stats', 'metric', 'monitor']):
                if inspect.ismethod(obj) or inspect.isfunction(obj):
                    health_info['monitoring_methods'].append(name)
                else:
                    health_info['stats_attributes'].append(name)
        
        return health_info if any(health_info.values()) else None
    
    def _create_health_signature(self, health_info: Dict[str, Any]) -> str:
        """Create signature for health tracking pattern."""
        parts = []
        for key, values in health_info.items():
            if values:
                parts.append(f"{key}:{sorted(values)}")
        return "|".join(parts)


class TestExecutionPatternSSOTCompliance:
    """Test execution pattern implementations for SSOT violations."""
    
    def test_single_execution_engine_pattern(self):
        """
        CRITICAL: Verify only ONE execution engine pattern exists.
        
        Current State: SHOULD FAIL - Multiple execution patterns detected
        Expected: BaseExecutionEngine as single execution orchestrator
        """
        execution_implementations = self._find_execution_implementations()
        
        # Filter for primary execution engines (not utilities or helpers)
        primary_engines = [
            impl for impl in execution_implementations
            if self._is_primary_execution_engine(impl[1])
        ]
        
        # ASSERTION: Should have only ONE primary execution engine
        assert len(primary_engines) == 1, (
            f"SSOT VIOLATION: Found {len(primary_engines)} primary execution engine implementations. "
            f"Expected only 1 canonical execution engine. "
            f"Primary engines: {[(impl[0], impl[1]) for impl in primary_engines]}. "
            f"Consolidate execution logic into BaseExecutionEngine."
        )
        
        # Verify expected canonical implementation
        canonical_found = any(
            impl[1] == "BaseExecutionEngine" and "base.executor" in impl[0]
            for impl in primary_engines
        )
        assert canonical_found, (
            "SSOT VIOLATION: Expected canonical BaseExecutionEngine not found in "
            "netra_backend.app.agents.base.executor. "
            "This should be the single execution orchestrator."
        )
    
    def test_execution_method_consistency_across_agents(self):
        """
        CRITICAL: Verify execution methods are consistent across agents.
        
        Current State: SHOULD FAIL - Inconsistent execution patterns in agents
        Expected: All agents use consistent execution patterns
        """
        agent_execution_patterns = self._find_agent_execution_patterns()
        
        # Analyze execution patterns
        pattern_signatures = {}
        for agent_path, patterns in agent_execution_patterns.items():
            signature = self._create_execution_signature(patterns)
            if signature not in pattern_signatures:
                pattern_signatures[signature] = []
            pattern_signatures[signature].append(agent_path)
        
        # ASSERTION: Should have consistent execution patterns
        unique_patterns = len(pattern_signatures)
        assert unique_patterns <= 2, (  # Allow modern + legacy patterns during transition
            f"SSOT VIOLATION: Found {unique_patterns} different execution patterns across agents. "
            f"Expected at most 2 patterns (modern + legacy during transition). "
            f"Pattern distribution: {dict(pattern_signatures)}. "
            f"Standardize execution patterns across all agents."
        )
        
        # Check that modern pattern is preferred
        modern_pattern_count = 0
        for signature, agents in pattern_signatures.items():
            if "execute_modern" in signature or "BaseExecutionEngine" in signature:
                modern_pattern_count += len(agents)
        
        total_agents = sum(len(agents) for agents in pattern_signatures.values())
        modern_adoption_rate = modern_pattern_count / total_agents if total_agents > 0 else 0
        
        assert modern_adoption_rate >= 0.7, (
            f"SSOT VIOLATION: Modern execution pattern adoption too low ({modern_adoption_rate:.2%}). "
            f"Expected at least 70% of agents using BaseExecutionEngine pattern. "
            f"Migrate remaining agents to modern execution patterns."
        )
    
    def test_execution_context_consistency(self):
        """
        CRITICAL: Verify execution context is consistent across implementations.
        
        Current State: SHOULD FAIL - Multiple execution context patterns
        Expected: Single ExecutionContext interface
        """
        context_implementations = self._find_execution_context_implementations()
        
        # Analyze context interfaces
        context_signatures = {}
        for module_path, class_name, class_obj in context_implementations:
            signature = self._get_context_signature(class_obj)
            key = f"{class_name}:{signature}"
            if key not in context_signatures:
                context_signatures[key] = []
            context_signatures[key].append(module_path)
        
        # ASSERTION: Should have single execution context pattern
        unique_contexts = len(context_signatures)
        assert unique_contexts == 1, (
            f"SSOT VIOLATION: Found {unique_contexts} different execution context implementations. "
            f"Expected only 1 unified ExecutionContext interface. "
            f"Context patterns: {list(context_signatures.keys())}. "
            f"Consolidate into single ExecutionContext definition."
        )
    
    def _find_execution_implementations(self) -> List[Tuple[str, str, type]]:
        """Find execution engine implementations."""
        implementations = []
        
        base_path = Path(__file__).parent.parent.parent.parent.parent
        execution_files = []
        
        # Search for execution-related files
        for pattern in ["*executor*.py", "*execution*.py", "*engine*.py"]:
            execution_files.extend(base_path.rglob(pattern))
        
        for file_path in execution_files:
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue
            
            relative_path = file_path.relative_to(base_path)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
            
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if any(keyword in name.lower() for keyword in ["executor", "execution", "engine"]):
                        if not name.startswith("_"):
                            implementations.append((module_path, name, obj))
            except ImportError:
                continue
        
        return implementations
    
    def _is_primary_execution_engine(self, class_name: str) -> bool:
        """Check if class is a primary execution engine."""
        primary_indicators = ["BaseExecutionEngine", "ExecutionEngine", "AgentExecutor"]
        exclude_indicators = ["Helper", "Util", "Monitor", "Config", "Context", "Result"]
        
        return (any(indicator in class_name for indicator in primary_indicators) and 
                not any(exclude in class_name for exclude in exclude_indicators))
    
    def _find_agent_execution_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Find execution patterns used by agents."""
        patterns = {}
        
        # Find agent implementations
        base_path = Path(__file__).parent.parent.parent.parent.parent
        agent_files = list(base_path.rglob("**/agents/*agent*.py"))
        
        for agent_file in agent_files:
            if "__pycache__" in str(agent_file) or "test" in str(agent_file):
                continue
            
            relative_path = agent_file.relative_to(base_path)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
            
            try:
                module = importlib.import_module(module_path)
                execution_methods = self._extract_execution_methods(module)
                if execution_methods:
                    patterns[module_path] = execution_methods
            except ImportError:
                continue
        
        return patterns
    
    def _extract_execution_methods(self, module) -> Dict[str, List[str]]:
        """Extract execution methods from a module."""
        methods = {
            'execute_methods': [],
            'reliability_methods': [],
            'modern_patterns': []
        }
        
        source_lines = []
        try:
            source_lines = inspect.getsource(module).split('\n')
        except OSError:
            return methods
        
        for line in source_lines:
            if 'def execute' in line:
                if 'execute_modern' in line:
                    methods['modern_patterns'].append('execute_modern')
                elif 'execute_with_reliability' in line:
                    methods['reliability_methods'].append('execute_with_reliability')
                elif 'def execute(' in line:
                    methods['execute_methods'].append('execute')
            
            if 'BaseExecutionEngine' in line:
                methods['modern_patterns'].append('BaseExecutionEngine')
        
        return methods
    
    def _create_execution_signature(self, patterns: Dict[str, List[str]]) -> str:
        """Create signature for execution pattern."""
        parts = []
        for key, values in patterns.items():
            if values:
                parts.append(f"{key}:{sorted(set(values))}")
        return "|".join(parts)
    
    def _find_execution_context_implementations(self) -> List[Tuple[str, str, type]]:
        """Find execution context implementations."""
        contexts = []
        
        base_path = Path(__file__).parent.parent.parent.parent.parent
        interface_files = list(base_path.rglob("**/interface*.py")) + list(base_path.rglob("**/context*.py"))
        
        for file_path in interface_files:
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue
            
            relative_path = file_path.relative_to(base_path)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
            
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if "context" in name.lower() and "execution" in name.lower():
                        contexts.append((module_path, name, obj))
            except ImportError:
                continue
        
        return contexts
    
    def _get_context_signature(self, class_obj) -> str:
        """Get signature for execution context class."""
        if hasattr(class_obj, "__dataclass_fields__"):
            field_names = [field.name for field in fields(class_obj)]
            return f"dataclass({sorted(field_names)})"
        else:
            attrs = [name for name in dir(class_obj) if not name.startswith("_")]
            return f"class({sorted(attrs)})"


class TestRetryLogicSSOTCompliance:
    """Test retry logic implementations for SSOT violations."""
    
    def test_single_retry_implementation(self):
        """
        CRITICAL: Verify only ONE retry logic implementation exists.
        
        Current State: SHOULD FAIL - Multiple retry implementations detected
        Expected: Single RetryManager as canonical retry implementation
        """
        retry_implementations = self._find_retry_implementations()
        
        # Filter for primary retry implementations
        primary_retry = [
            impl for impl in retry_implementations
            if self._is_primary_retry_implementation(impl[1])
        ]
        
        # ASSERTION: Should have only ONE primary retry implementation
        assert len(primary_retry) == 1, (
            f"SSOT VIOLATION: Found {len(primary_retry)} primary retry implementations. "
            f"Expected only 1 canonical retry manager. "
            f"Primary implementations: {[(impl[0], impl[1]) for impl in primary_retry]}. "
            f"Consolidate retry logic into single RetryManager."
        )
        
        # Verify expected canonical implementation
        canonical_found = any(
            impl[1] == "RetryManager" and "base.retry_manager" in impl[0]
            for impl in primary_retry
        )
        assert canonical_found, (
            "SSOT VIOLATION: Expected canonical RetryManager not found. "
            "RetryManager should be the single source of truth for retry logic."
        )
    
    def test_retry_configuration_consistency(self):
        """
        CRITICAL: Verify retry configurations are consistent.
        
        Current State: SHOULD FAIL - Inconsistent retry configurations
        Expected: Single retry configuration pattern
        """
        retry_configs = self._find_retry_configurations()
        
        # Analyze configuration patterns
        config_signatures = {}
        for module_path, config_info in retry_configs.items():
            signature = self._create_retry_config_signature(config_info)
            if signature not in config_signatures:
                config_signatures[signature] = []
            config_signatures[signature].append(module_path)
        
        # ASSERTION: Should have consistent retry configuration
        unique_configs = len(config_signatures)
        assert unique_configs == 1, (
            f"SSOT VIOLATION: Found {unique_configs} different retry configuration patterns. "
            f"Expected only 1 unified retry configuration. "
            f"Configuration patterns: {dict(config_signatures)}. "
            f"Standardize retry configuration across all components."
        )
    
    def test_exponential_backoff_duplication(self):
        """
        CRITICAL: Verify no duplicate exponential backoff implementations.
        
        Current State: SHOULD FAIL - Multiple backoff implementations detected
        Expected: Single backoff calculation logic
        """
        backoff_implementations = self._find_backoff_implementations()
        
        # Analyze backoff algorithms
        algorithm_signatures = {}
        for module_path, backoff_info in backoff_implementations.items():
            signature = self._create_backoff_signature(backoff_info)
            if signature not in algorithm_signatures:
                algorithm_signatures[signature] = []
            algorithm_signatures[signature].append(module_path)
        
        # ASSERTION: Should have single backoff algorithm
        unique_algorithms = len(algorithm_signatures)
        assert unique_algorithms == 1, (
            f"SSOT VIOLATION: Found {unique_algorithms} different exponential backoff implementations. "
            f"Expected only 1 unified backoff algorithm. "
            f"Algorithm patterns: {dict(algorithm_signatures)}. "
            f"Consolidate backoff logic into single implementation."
        )
    
    def _find_retry_implementations(self) -> List[Tuple[str, str, type]]:
        """Find retry logic implementations."""
        implementations = []
        
        base_path = Path(__file__).parent.parent.parent.parent.parent
        retry_files = list(base_path.rglob("*retry*.py"))
        
        for file_path in retry_files:
            if "__pycache__" in str(file_path) or "test" in str(file_path):
                continue
            
            relative_path = file_path.relative_to(base_path)
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
            
            try:
                module = importlib.import_module(module_path)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if "retry" in name.lower() and not name.startswith("_"):
                        implementations.append((module_path, name, obj))
            except ImportError:
                continue
        
        return implementations
    
    def _is_primary_retry_implementation(self, class_name: str) -> bool:
        """Check if class is a primary retry implementation."""
        primary_indicators = ["RetryManager", "RetryHandler", "Retry"]
        exclude_indicators = ["Config", "Exception", "Error", "Helper"]
        
        return (any(indicator in class_name for indicator in primary_indicators) and
                not any(exclude in class_name for exclude in exclude_indicators))
    
    def _find_retry_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Find retry configuration patterns."""
        configs = {}
        
        retry_implementations = self._find_retry_implementations()
        for module_path, class_name, class_obj in retry_implementations:
            config_info = self._extract_retry_config(class_obj)
            if config_info:
                configs[f"{module_path}.{class_name}"] = config_info
        
        return configs
    
    def _extract_retry_config(self, class_obj) -> Dict[str, Any]:
        """Extract retry configuration from class."""
        config = {
            'config_fields': [],
            'default_values': {},
            'max_retries': None,
            'base_delay': None
        }
        
        if hasattr(class_obj, "__dataclass_fields__"):
            for field in fields(class_obj):
                config['config_fields'].append(field.name)
                if hasattr(field, 'default') and field.default is not None:
                    config['default_values'][field.name] = field.default
                    
                    if 'retry' in field.name.lower():
                        config['max_retries'] = field.default
                    elif 'delay' in field.name.lower():
                        config['base_delay'] = field.default
        
        return config if config['config_fields'] else None
    
    def _create_retry_config_signature(self, config_info: Dict[str, Any]) -> str:
        """Create signature for retry configuration."""
        parts = [
            f"fields:{sorted(config_info['config_fields'])}",
            f"max_retries:{config_info['max_retries']}",
            f"base_delay:{config_info['base_delay']}"
        ]
        return "|".join(parts)
    
    def _find_backoff_implementations(self) -> Dict[str, Dict[str, Any]]:
        """Find exponential backoff implementations."""
        implementations = {}
        
        base_path = Path(__file__).parent.parent.parent.parent.parent
        
        # Search in retry and reliability modules
        search_patterns = ["*retry*.py", "*reliability*.py", "*backoff*.py"]
        
        for pattern in search_patterns:
            files = list(base_path.rglob(pattern))
            for file_path in files:
                if "__pycache__" in str(file_path) or "test" in str(file_path):
                    continue
                
                relative_path = file_path.relative_to(base_path)
                module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                        backoff_info = self._extract_backoff_logic(source_code)
                        if backoff_info:
                            implementations[module_path] = backoff_info
                except (IOError, UnicodeDecodeError):
                    continue
        
        return implementations
    
    def _extract_backoff_logic(self, source_code: str) -> Dict[str, Any]:
        """Extract backoff logic from source code."""
        backoff_info = {
            'exponential_patterns': [],
            'delay_calculations': [],
            'backoff_formulas': []
        }
        
        lines = source_code.split('\n')
        for line in lines:
            # Look for exponential backoff patterns
            if '2 **' in line or '2**' in line or 'pow(2' in line:
                backoff_info['exponential_patterns'].append(line.strip())
            
            # Look for delay calculations
            if 'delay' in line.lower() and ('*' in line or '+' in line):
                backoff_info['delay_calculations'].append(line.strip())
            
            # Look for backoff formulas
            if 'min(' in line and ('delay' in line.lower() or 'timeout' in line.lower()):
                backoff_info['backoff_formulas'].append(line.strip())
        
        return backoff_info if any(backoff_info.values()) else None
    
    def _create_backoff_signature(self, backoff_info: Dict[str, Any]) -> str:
        """Create signature for backoff implementation."""
        # Normalize patterns for comparison
        normalized_patterns = []
        for patterns in backoff_info.values():
            for pattern in patterns:
                # Normalize whitespace and variable names for comparison
                normalized = pattern.replace(' ', '').lower()
                # Replace variable names with placeholders
                for old, new in [('attempt', 'X'), ('retry', 'X'), ('count', 'X')]:
                    normalized = normalized.replace(old, new)
                normalized_patterns.append(normalized)
        
        return "|".join(sorted(set(normalized_patterns)))


class TestWebSocketEventSSOTCompliance:
    """Test WebSocket event system for SSOT compliance (should PASS)."""
    
    def test_websocket_bridge_adapter_ssot_pattern(self):
        """
        CRITICAL: Verify WebSocket events follow proper SSOT pattern.
        
        Current State: SHOULD PASS - WebSocket events properly implemented via SSOT
        Expected: Single WebSocketBridgeAdapter provides unified event interface
        """
        # Verify WebSocketBridgeAdapter exists and is used by BaseAgent
        base_agent = BaseAgent()
        
        # ASSERTION: BaseAgent should have WebSocket adapter
        assert hasattr(base_agent, '_websocket_adapter'), (
            "SSOT VIOLATION: BaseAgent missing WebSocket adapter. "
            "WebSocket events must use WebSocketBridgeAdapter for SSOT compliance."
        )
        
        assert isinstance(base_agent._websocket_adapter, WebSocketBridgeAdapter), (
            "SSOT VIOLATION: WebSocket adapter is not WebSocketBridgeAdapter instance. "
            "All agents must use WebSocketBridgeAdapter for unified event emission."
        )
    
    def test_websocket_event_method_coverage(self):
        """
        CRITICAL: Verify all WebSocket event methods are available through SSOT adapter.
        
        Current State: SHOULD PASS - All event methods available via adapter
        Expected: Complete event method coverage through single adapter
        """
        base_agent = BaseAgent()
        
        # Expected WebSocket event methods (SSOT interface)
        required_methods = [
            'emit_agent_started',
            'emit_thinking', 
            'emit_tool_executing',
            'emit_tool_completed',
            'emit_agent_completed',
            'emit_progress',
            'emit_error',
            'emit_subagent_started',
            'emit_subagent_completed'
        ]
        
        # ASSERTION: All required methods should be available
        missing_methods = []
        for method_name in required_methods:
            if not hasattr(base_agent, method_name):
                missing_methods.append(method_name)
        
        assert len(missing_methods) == 0, (
            f"SSOT VIOLATION: Missing WebSocket event methods: {missing_methods}. "
            f"All event methods must be available through WebSocketBridgeAdapter SSOT."
        )
        
        # Verify methods delegate to adapter
        for method_name in required_methods:
            method = getattr(base_agent, method_name)
            assert callable(method), (
                f"SSOT VIOLATION: WebSocket method {method_name} is not callable. "
                f"All event methods must be implemented through adapter delegation."
            )
    
    def test_websocket_bridge_singleton_behavior(self):
        """
        CRITICAL: Verify WebSocket bridge follows SSOT singleton pattern.
        
        Current State: SHOULD PASS - WebSocket bridge properly managed
        Expected: Single bridge instance coordinates all WebSocket events
        """
        # Create multiple agent instances
        agent1 = BaseAgent(name="Agent1")
        agent2 = BaseAgent(name="Agent2") 
        
        # Mock bridge setup
        mock_bridge = object()  # Simple mock object
        run_id = "test_run_123"
        
        # Set bridge for both agents
        agent1.set_websocket_bridge(mock_bridge, run_id)
        agent2.set_websocket_bridge(mock_bridge, run_id)
        
        # ASSERTION: Both agents should reference the same bridge through their adapters
        assert agent1._websocket_adapter._bridge is mock_bridge, (
            "SSOT VIOLATION: Agent1 WebSocket adapter not properly configured with bridge. "
            "Bridge must be set through SSOT adapter pattern."
        )
        
        assert agent2._websocket_adapter._bridge is mock_bridge, (
            "SSOT VIOLATION: Agent2 WebSocket adapter not properly configured with bridge. "
            "Bridge must be set through SSOT adapter pattern."
        )
        
        # Verify bridge context detection
        assert agent1.has_websocket_context(), (
            "SSOT VIOLATION: Agent1 cannot detect WebSocket context. "
            "WebSocket availability must be detectable through SSOT adapter."
        )
        
        assert agent2.has_websocket_context(), (
            "SSOT VIOLATION: Agent2 cannot detect WebSocket context. "
            "WebSocket availability must be detectable through SSOT adapter."
        )
    
    def test_no_direct_websocket_dependencies(self):
        """
        CRITICAL: Verify agents have no direct WebSocket dependencies.
        
        Current State: SHOULD PASS - All WebSocket interaction via adapter
        Expected: No direct WebSocket imports or usage outside adapter
        """
        # Check BaseAgent source for direct WebSocket imports
        base_agent_module = inspect.getmodule(BaseAgent)
        source_code = inspect.getsource(base_agent_module)
        
        # ASSERTION: Should not have direct WebSocket imports
        forbidden_imports = [
            'import websocket',
            'from websocket',
            'import socketio', 
            'from socketio',
            'WebSocketManager',
            'websocket_manager'
        ]
        
        violations = []
        for forbidden in forbidden_imports:
            if forbidden in source_code:
                violations.append(forbidden)
        
        assert len(violations) == 0, (
            f"SSOT VIOLATION: Direct WebSocket dependencies found in BaseAgent: {violations}. "
            f"All WebSocket interaction must go through WebSocketBridgeAdapter SSOT."
        )
        
        # Check that WebSocket functionality is accessed only through adapter
        websocket_method_lines = []
        lines = source_code.split('\n')
        for i, line in enumerate(lines):
            if 'emit_' in line and 'def ' in line:
                # This is a WebSocket event method definition
                method_body = []
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].strip().startswith('await self._websocket_adapter.'):
                        method_body.append("uses_adapter")
                        break
                    elif 'def ' in lines[j] and not lines[j].strip().startswith('#'):
                        break
                    method_body.append(lines[j].strip())
                
                websocket_method_lines.append((line.strip(), method_body))
        
        # ASSERTION: All WebSocket methods should delegate to adapter
        non_adapter_methods = []
        for method_def, body in websocket_method_lines:
            if "uses_adapter" not in body:
                non_adapter_methods.append(method_def)
        
        assert len(non_adapter_methods) == 0, (
            f"SSOT VIOLATION: WebSocket methods not using adapter delegation: {non_adapter_methods}. "
            f"All WebSocket event methods must delegate to WebSocketBridgeAdapter."
        )


class TestComprehensiveIntegrationSSOTCompliance:
    """Comprehensive integration tests for SSOT compliance across components."""
    
    def test_base_agent_ssot_infrastructure_integration(self):
        """
        CRITICAL: Verify BaseAgent integrates all SSOT components correctly.
        
        Current State: SHOULD FAIL - Multiple infrastructure patterns used
        Expected: BaseAgent uses unified SSOT infrastructure for all components
        """
        base_agent = BaseAgent(enable_reliability=True, enable_execution_engine=True)
        
        # ASSERTION: Should have unified infrastructure components
        infrastructure_components = {
            'reliability_manager': base_agent.reliability_manager,
            'execution_engine': base_agent.execution_engine,
            'websocket_adapter': base_agent._websocket_adapter
        }
        
        missing_components = []
        for name, component in infrastructure_components.items():
            if component is None:
                missing_components.append(name)
        
        assert len(missing_components) == 0, (
            f"SSOT VIOLATION: Missing infrastructure components in BaseAgent: {missing_components}. "
            f"BaseAgent must integrate all SSOT infrastructure components."
        )
        
        # Verify legacy reliability exists for backward compatibility
        assert base_agent.legacy_reliability is not None, (
            "SSOT VIOLATION: Legacy reliability wrapper missing. "
            "Backward compatibility layer required during SSOT transition."
        )
    
    def test_configuration_access_ssot_compliance(self):
        """
        CRITICAL: Verify all configuration access follows SSOT patterns.
        
        Current State: SHOULD FAIL - Multiple configuration access patterns
        Expected: Consistent configuration access through unified interface
        """
        # Test agent configuration access
        base_agent = BaseAgent()
        
        # ASSERTION: Agent should not access configuration directly
        forbidden_attributes = ['os.environ', 'getenv', 'config.get']
        
        # Check source code for forbidden patterns
        source_code = inspect.getsource(BaseAgent)
        violations = []
        
        for forbidden in forbidden_attributes:
            if forbidden in source_code:
                violations.append(forbidden)
        
        # Allow agent_config and get_config as approved SSOT patterns
        allowed_patterns = ['agent_config', 'get_config()']
        
        assert len(violations) == 0, (
            f"SSOT VIOLATION: Forbidden configuration access patterns: {violations}. "
            f"Use only approved SSOT patterns: {allowed_patterns}."
        )
    
    def test_error_handling_ssot_compliance(self):
        """
        CRITICAL: Verify error handling follows SSOT patterns.
        
        Current State: SHOULD FAIL - Multiple error handling approaches
        Expected: Unified error handling through SSOT infrastructure
        """
        base_agent = BaseAgent(enable_reliability=True)
        
        # Check that error handling is unified through reliability infrastructure
        reliability_manager = base_agent.reliability_manager
        
        # ASSERTION: Reliability manager should provide unified error handling
        assert hasattr(reliability_manager, '_handle_execution_failure'), (
            "SSOT VIOLATION: Reliability manager missing unified error handling. "
            "All error handling must go through SSOT reliability infrastructure."
        )
        
        # Check for consistent error handling patterns
        legacy_reliability = base_agent.legacy_reliability
        assert hasattr(legacy_reliability, 'execute_safely'), (
            "SSOT VIOLATION: Legacy reliability wrapper missing error handling interface. "
            "Backward compatibility error handling required."
        )
    
    def test_monitoring_integration_ssot_compliance(self):
        """
        CRITICAL: Verify monitoring integration follows SSOT patterns.
        
        Current State: SHOULD FAIL - Multiple monitoring approaches
        Expected: Unified monitoring through SSOT execution infrastructure
        """
        base_agent = BaseAgent(enable_execution_engine=True)
        
        # ASSERTION: Should have unified monitoring infrastructure
        execution_monitor = base_agent.execution_monitor
        assert execution_monitor is not None, (
            "SSOT VIOLATION: Execution monitor not integrated. "
            "Monitoring must be unified through SSOT execution infrastructure."
        )
        
        # Verify monitoring integration points
        health_status = base_agent.get_health_status()
        
        # ASSERTION: Health status should integrate all monitoring components
        required_health_components = ['agent_name', 'state', 'websocket_available', 'overall_status']
        missing_health_components = []
        
        for component in required_health_components:
            if component not in health_status:
                missing_health_components.append(component)
        
        assert len(missing_health_components) == 0, (
            f"SSOT VIOLATION: Missing health status components: {missing_health_components}. "
            f"Health monitoring must provide comprehensive SSOT status."
        )
    
    def test_ssot_violations_detection_comprehensive(self):
        """
        CRITICAL: Comprehensive check for any remaining SSOT violations.
        
        Current State: SHOULD FAIL - Various SSOT violations detected
        Expected: No SSOT violations across entire BaseAgent infrastructure
        """
        violations = []
        
        # Check for duplicate implementations across categories
        circuit_breaker_count = len(self._count_circuit_breaker_implementations())
        if circuit_breaker_count > 1:
            violations.append(f"Circuit Breaker: {circuit_breaker_count} implementations")
        
        reliability_count = len(self._count_reliability_implementations())
        if reliability_count > 2:  # Allow modern + legacy during transition
            violations.append(f"Reliability Manager: {reliability_count} implementations")
        
        execution_count = len(self._count_execution_implementations())
        if execution_count > 1:
            violations.append(f"Execution Engine: {execution_count} implementations")
        
        retry_count = len(self._count_retry_implementations())
        if retry_count > 1:
            violations.append(f"Retry Logic: {retry_count} implementations")
        
        # ASSERTION: Should have minimal SSOT violations
        max_allowed_violations = 0  # Strict SSOT compliance
        assert len(violations) <= max_allowed_violations, (
            f"SSOT VIOLATIONS DETECTED: {len(violations)} categories have violations. "
            f"Violations: {violations}. "
            f"Maximum allowed violations: {max_allowed_violations}. "
            f"Complete SSOT consolidation required."
        )
    
    def _count_circuit_breaker_implementations(self) -> List[str]:
        """Count circuit breaker implementations."""
        implementations = []
        base_path = Path(__file__).parent.parent.parent.parent.parent
        
        for file_path in base_path.rglob("*circuit_breaker*.py"):
            if "__pycache__" not in str(file_path) and "test" not in str(file_path):
                implementations.append(str(file_path))
        
        return implementations
    
    def _count_reliability_implementations(self) -> List[str]:
        """Count reliability manager implementations.""" 
        implementations = []
        base_path = Path(__file__).parent.parent.parent.parent.parent
        
        for file_path in base_path.rglob("*reliability*.py"):
            if "__pycache__" not in str(file_path) and "test" not in str(file_path):
                implementations.append(str(file_path))
        
        return implementations
    
    def _count_execution_implementations(self) -> List[str]:
        """Count execution engine implementations."""
        implementations = []
        base_path = Path(__file__).parent.parent.parent.parent.parent
        
        for pattern in ["*executor*.py", "*execution_engine*.py"]:
            for file_path in base_path.rglob(pattern):
                if "__pycache__" not in str(file_path) and "test" not in str(file_path):
                    implementations.append(str(file_path))
        
        return implementations
    
    def _count_retry_implementations(self) -> List[str]:
        """Count retry logic implementations."""
        implementations = []
        base_path = Path(__file__).parent.parent.parent.parent.parent
        
        for file_path in base_path.rglob("*retry*.py"):
            if "__pycache__" not in str(file_path) and "test" not in str(file_path):
                implementations.append(str(file_path))
        
        return implementations


if __name__ == "__main__":
    # Run tests to verify SSOT compliance
    pytest.main([__file__, "-v", "--tb=short"])
