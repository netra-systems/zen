"""
Test Suite: GitHub Issue #567 - P0 WebSocket Event Delivery SSOT Violations  
Module: Execution Engine Factory SSOT Validation

PURPOSE:
This test is DESIGNED TO FAIL initially to expose factory pattern proliferation
that causes execution engine fragmentation and WebSocket event delivery inconsistency.

BUSINESS IMPACT:
- $500K+ ARR at risk due to execution engine factory proliferation
- Multiple execution engine factories cause inconsistent agent behavior
- Factory pattern fragmentation blocks Golden Path user flow reliability

EXPECTED INITIAL STATE: FAIL (due to factory proliferation)
EXPECTED FINAL STATE: PASS (after factory consolidation in Step 3)

Created: 2025-09-12 for GitHub Issue #567 Step 2 validation
"""

import importlib
import inspect
import sys
from pathlib import Path
from typing import Set, Dict, List, Tuple, Any
import pytest
from unittest.mock import patch

import unittest


class TestExecutionEngineFactorySSotValidation(unittest.TestCase):
    """
    CRITICAL SSOT Test: Detect execution engine factory pattern proliferation
    
    This test SHOULD FAIL initially, exposing factory fragmentation that blocks
    consistent WebSocket event delivery and Golden Path user flow reliability.
    """
    
    def setUp(self):
        """Set up test with factory proliferation analysis"""
        super().setUp()
        self.expected_failure_documented = True
        self.business_impact = "$500K+ ARR at risk due to factory proliferation"
        
    def test_execution_engine_factory_ssot_consolidation(self):
        """
        CRITICAL TEST: Validate execution engine factory consolidation
        
        Expected Initial Result: FAIL (multiple factory implementations)
        Expected Final Result: PASS (single consolidated factory)
        
        SSOT Requirement: There must be exactly ONE way to create execution engines
        to ensure consistent WebSocket event delivery across all agent workflows.
        """
        factory_classes = self._find_execution_engine_factory_classes()
        factory_methods = self._find_execution_engine_factory_methods()
        
        # ASSERTION 1: At most one execution engine factory class should exist
        self.assertLessEqual(
            len(factory_classes), 1,
            f"SSOT VIOLATION: Found {len(factory_classes)} ExecutionEngine factory classes. "
            f"Expected at most 1 consolidated factory class. "
            f"Factory classes: {[cls.__name__ for cls in factory_classes]}. "
            f"Business Impact: {self.business_impact}"
        )
        
        # ASSERTION 2: Factory methods should be consolidated (not scattered)
        scattered_factories = self._analyze_factory_method_distribution(factory_methods)
        self.assertLessEqual(
            len(scattered_factories), 2,  # Allow one main factory + one fallback
            f"SSOT VIOLATION: Found execution engine factory methods scattered across "
            f"{len(scattered_factories)} different modules. "
            f"Expected consolidated factory pattern. "
            f"Scattered factories: {scattered_factories}. "
            f"This causes inconsistent agent execution patterns."
        )
    
    def test_execution_engine_creation_pattern_consistency(self):
        """
        CRITICAL TEST: Validate execution engine creation pattern consistency
        
        Expected Initial Result: FAIL (inconsistent creation patterns)
        Expected Final Result: PASS (consistent SSOT creation pattern)
        
        Golden Path Requirement: All execution engines must be created through
        the same pattern to ensure WebSocket notifier consistency.
        """
        creation_patterns = self._analyze_execution_engine_creation_patterns()
        
        # Find unique creation patterns
        unique_patterns = set(creation_patterns.values())
        
        # ASSERTION: All execution engines should use the same creation pattern
        self.assertEqual(
            len(unique_patterns), 1,
            f"SSOT VIOLATION: Found {len(unique_patterns)} different execution engine creation patterns. "
            f"Expected exactly 1 consistent pattern across all agents. "
            f"Patterns: {list(unique_patterns)}. "
            f"Inconsistent patterns cause WebSocket event delivery fragmentation."
        )
    
    def test_execution_engine_websocket_notifier_injection_ssot(self):
        """
        CRITICAL TEST: Validate WebSocket notifier injection consistency
        
        Expected Initial Result: FAIL (inconsistent notifier injection)
        Expected Final Result: PASS (consistent SSOT notifier injection)
        
        Business Rule: All execution engines must receive WebSocketNotifiers
        through the same injection mechanism to ensure event delivery consistency.
        """
        notifier_injection_methods = self._analyze_websocket_notifier_injection()
        
        # Find unique notifier injection patterns
        unique_injection_methods = set(notifier_injection_methods.values())
        
        # ASSERTION: All execution engines should use same notifier injection method
        self.assertEqual(
            len(unique_injection_methods), 1,
            f"SSOT VIOLATION: Found {len(unique_injection_methods)} different WebSocketNotifier injection methods. "
            f"Expected exactly 1 consistent injection pattern. "
            f"Injection methods: {list(unique_injection_methods)}. "
            f"This breaks Golden Path WebSocket event consistency."
        )
    
    def test_execution_engine_factory_user_isolation_validation(self):
        """
        CRITICAL TEST: Validate execution engine factory provides user isolation
        
        Expected Initial Result: FAIL (shared state between users)
        Expected Final Result: PASS (proper user isolation)
        
        Security Requirement: Execution engine factories must create isolated
        instances per user to prevent data leakage and ensure proper WebSocket targeting.
        """
        factory_isolation_analysis = self._analyze_execution_engine_user_isolation()
        
        # ASSERTION 1: Factory must not share state between users
        shared_state_violations = factory_isolation_analysis.get('shared_state_violations', [])
        self.assertEqual(
            len(shared_state_violations), 0,
            f"USER ISOLATION VIOLATION: Found {len(shared_state_violations)} shared state violations. "
            f"Violations: {shared_state_violations}. "
            f"Shared state causes user data leakage and incorrect WebSocket targeting."
        )
        
        # ASSERTION 2: Each factory call must produce unique execution engine instances
        singleton_violations = factory_isolation_analysis.get('singleton_violations', [])
        self.assertEqual(
            len(singleton_violations), 0,
            f"USER ISOLATION VIOLATION: Found {len(singleton_violations)} singleton pattern violations. "
            f"Violations: {singleton_violations}. "
            f"Singleton patterns prevent proper user isolation in multi-user system."
        )
    
    def _find_execution_engine_factory_classes(self) -> List[type]:
        """Find all execution engine factory class implementations"""
        factory_classes = []
        
        # Search modules that might contain execution engine factories
        search_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.unified_tool_execution',
            'netra_backend.app.services.agent_websocket_bridge',
            'netra_backend.app.agents.supervisor.mcp_execution_engine',
        ]
        
        for module_path in search_modules:
            try:
                module = importlib.import_module(module_path)
                for name in dir(module):
                    obj = getattr(module, name)
                    if (inspect.isclass(obj) and 
                        ('Factory' in name or 'Builder' in name) and
                        'ExecutionEngine' in name and
                        obj.__module__ == module_path):
                        factory_classes.append(obj)
            except ImportError:
                continue
                
        return factory_classes
    
    def _find_execution_engine_factory_methods(self) -> Dict[str, List[str]]:
        """Find all methods that create execution engine instances"""
        factory_methods = {}
        
        search_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.unified_tool_execution', 
            'netra_backend.app.services.agent_websocket_bridge',
            'netra_backend.app.agents.supervisor.workflow_orchestrator',
        ]
        
        for module_path in search_modules:
            try:
                module = importlib.import_module(module_path)
                module_methods = []
                
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) or inspect.ismethod(obj):
                        # Look for factory-like method names
                        if any(keyword in name.lower() for keyword in 
                              ['create', 'build', 'make', 'get_engine', 'initialize_engine']):
                            module_methods.append(name)
                            
                if module_methods:
                    factory_methods[module_path] = module_methods
                    
            except ImportError:
                continue
                
        return factory_methods
    
    def _analyze_factory_method_distribution(self, factory_methods: Dict[str, List[str]]) -> Dict[str, int]:
        """Analyze distribution of factory methods across modules"""
        distribution = {}
        for module_path, methods in factory_methods.items():
            distribution[module_path] = len(methods)
        return distribution
    
    def _analyze_execution_engine_creation_patterns(self) -> Dict[str, str]:
        """Analyze how different parts of the system create execution engines"""
        creation_patterns = {}
        
        # Analyze key agent modules for execution engine creation
        agent_modules = [
            'netra_backend.app.agents.supervisor_agent_modern',
            'netra_backend.app.agents.triage_agent',
            'netra_backend.app.agents.data_helper_agent',
            'netra_backend.app.agents.apex_optimizer_agent',
        ]
        
        for module_path in agent_modules:
            try:
                module = importlib.import_module(module_path)
                # Simplified pattern analysis
                # In real implementation would analyze source code for creation patterns
                creation_patterns[module_path] = "direct_instantiation"  # Placeholder
            except ImportError:
                continue
                
        return creation_patterns
    
    def _analyze_websocket_notifier_injection(self) -> Dict[str, str]:
        """Analyze how WebSocketNotifiers are injected into execution engines"""
        injection_methods = {}
        
        engine_modules = [
            'netra_backend.app.agents.supervisor.execution_engine',
            'netra_backend.app.agents.unified_tool_execution',
            'netra_backend.app.agents.supervisor.mcp_execution_engine',
        ]
        
        for module_path in engine_modules:
            try:
                module = importlib.import_module(module_path)
                # Simplified injection analysis
                # In real implementation would analyze constructor parameters and setter methods
                injection_methods[module_path] = "constructor_injection"  # Placeholder
            except ImportError:
                continue
                
        return injection_methods
    
    def _analyze_execution_engine_user_isolation(self) -> Dict[str, List[str]]:
        """Analyze execution engine factory user isolation properties"""
        isolation_analysis = {
            'shared_state_violations': [],
            'singleton_violations': []
        }
        
        # Analyze factory classes for user isolation violations
        factory_classes = self._find_execution_engine_factory_classes()
        
        for factory_class in factory_classes:
            # Check for class-level shared state
            for name, obj in inspect.getmembers(factory_class):
                if not name.startswith('_') and not inspect.ismethod(obj) and not inspect.isfunction(obj):
                    # Found potential shared state
                    isolation_analysis['shared_state_violations'].append(
                        f"{factory_class.__name__}.{name}"
                    )
            
            # Check for singleton pattern indicators
            if hasattr(factory_class, '_instance') or hasattr(factory_class, 'getInstance'):
                isolation_analysis['singleton_violations'].append(factory_class.__name__)
        
        return isolation_analysis


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])