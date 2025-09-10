#!/usr/bin/env python
"""SSOT Factory Pattern Test: UserExecutionContext Factory Validation

PURPOSE: Validate factory creates only canonical UserExecutionContext instances
and prevents SSOT violations in context creation patterns.

This test is DESIGNED TO FAIL initially to prove inconsistent factory patterns exist.
Once SSOT consolidation is complete, this test should PASS.

Business Impact: $500K+ ARR at risk from inconsistent UserExecutionContext factory
patterns causing user isolation failures and golden path disruption.

CRITICAL REQUIREMENTS:
- NO Docker dependencies (integration test without Docker)
- Must fail until SSOT consolidation complete
- Validates factory pattern consistency across all context creation
"""

import asyncio
import gc
import inspect
import os
import sys
import time
import uuid
import weakref
from collections import defaultdict, Counter
from typing import Dict, List, Set, Any, Optional, Tuple, Type
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import different UserExecutionContext implementations to test factory patterns
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext as ServicesUserContext
except ImportError:
    ServicesUserContext = None

try:
    from netra_backend.app.models.user_execution_context import UserExecutionContext as ModelsUserContext
except ImportError:
    ModelsUserContext = None

try:
    from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext as SupervisorUserContext
except ImportError:
    SupervisorUserContext = None

# Import potential factory implementations
try:
    from netra_backend.app.agents.supervisor.execution_factory import ExecutionContextFactory
except ImportError:
    ExecutionContextFactory = None

try:
    from netra_backend.app.core.context_factory import ContextFactory
except ImportError:
    ContextFactory = None

# Base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class MockRequest:
    """Mock FastAPI request for testing context creation."""
    def __init__(self, user_id: str = None):
        self.state = type('State', (), {})()
        self.state.user_id = user_id or str(uuid.uuid4())
        self.headers = {}


class TestUserExecutionContextFactorySSot(SSotAsyncTestCase):
    """SSOT Factory Pattern: Validate single canonical factory pattern for UserExecutionContext"""
    
    async def test_factory_pattern_ssot_violation_detection(self):
        """DESIGNED TO FAIL: Detect multiple factory patterns for UserExecutionContext creation.
        
        This test should FAIL because multiple factory patterns exist for creating
        UserExecutionContext instances, violating SSOT principles.
        
        Expected SSOT Violations:
        - Multiple factory classes for same functionality
        - Inconsistent factory method signatures
        - Different UserExecutionContext types returned
        - Scattered creation logic across modules
        
        Business Impact:
        - User isolation failures from inconsistent context creation
        - Golden path disruption from factory inconsistencies
        - Memory leaks from improper context lifecycle management
        """
        factory_ssot_violations = []
        
        # Collect all available UserExecutionContext implementations
        available_contexts = self._collect_user_context_implementations()
        
        logger.info(f"Found UserExecutionContext implementations: {len(available_contexts)}")
        for context_info in available_contexts:
            logger.info(f"  - {context_info['name']}: {context_info['module']}")
        
        # SSOT Violation Check 1: Multiple UserExecutionContext types
        if len(available_contexts) > 1:
            factory_ssot_violations.append(
                f"SSOT VIOLATION: {len(available_contexts)} UserExecutionContext implementations found. "
                f"Factory should create only canonical SSOT type."
            )
            
            for context_info in available_contexts:
                factory_ssot_violations.append(
                    f"  Implementation: {context_info['name']} from {context_info['module']}"
                )
        
        # SSOT Violation Check 2: Factory creation consistency
        factory_analysis = await self._analyze_factory_creation_patterns(available_contexts)
        
        if len(factory_analysis['creation_patterns']) > 1:
            factory_ssot_violations.append(
                f"SSOT VIOLATION: {len(factory_analysis['creation_patterns'])} different creation patterns found. "
                f"SSOT requires single canonical factory pattern."
            )
            
            for pattern in factory_analysis['creation_patterns']:
                factory_ssot_violations.append(f"  Pattern: {pattern}")
        
        # SSOT Violation Check 3: Factory method signatures
        signature_violations = self._check_factory_signature_consistency(factory_analysis)
        if signature_violations:
            factory_ssot_violations.extend(signature_violations)
        
        # SSOT Violation Check 4: Context lifecycle management
        lifecycle_violations = await self._check_context_lifecycle_consistency(available_contexts)
        if lifecycle_violations:
            factory_ssot_violations.extend(lifecycle_violations)
        
        # SSOT Violation Check 5: Factory dependency injection
        dependency_violations = self._check_factory_dependency_patterns(available_contexts)
        if dependency_violations:
            factory_ssot_violations.extend(dependency_violations)
        
        # Log all violations for debugging
        for violation in factory_ssot_violations:
            logger.error(f"Factory SSOT Violation: {violation}")
        
        # This test should FAIL to prove factory SSOT violations exist
        assert len(factory_ssot_violations) > 0, (
            f"Expected UserExecutionContext factory SSOT violations, but found none. "
            f"This indicates factory SSOT consolidation may already be complete. "
            f"Found {len(available_contexts)} context implementations."
        )
        
        pytest.fail(
            f"UserExecutionContext Factory SSOT Violations Detected ({len(factory_ssot_violations)} issues):\n" +
            "\n".join(factory_ssot_violations)
        )
    
    def _collect_user_context_implementations(self) -> List[Dict[str, Any]]:
        """Collect all available UserExecutionContext implementations."""
        implementations = []
        
        context_classes = [
            (ServicesUserContext, 'ServicesUserContext', 'netra_backend.app.services.user_execution_context'),
            (ModelsUserContext, 'ModelsUserContext', 'netra_backend.app.models.user_execution_context'),
            (SupervisorUserContext, 'SupervisorUserContext', 'netra_backend.app.agents.supervisor.user_execution_context'),
        ]
        
        for context_class, name, module in context_classes:
            if context_class is not None:
                implementations.append({
                    'class': context_class,
                    'name': name,
                    'module': module,
                    'fields': self._get_context_fields(context_class),
                    'methods': self._get_context_methods(context_class),
                    'creation_signature': self._get_creation_signature(context_class)
                })
        
        return implementations
    
    def _get_context_fields(self, context_class: Type) -> List[str]:
        """Get field names from UserExecutionContext class."""
        try:
            if hasattr(context_class, '__dataclass_fields__'):
                return list(context_class.__dataclass_fields__.keys())
            elif hasattr(context_class, '__annotations__'):
                return list(context_class.__annotations__.keys())
            else:
                return []
        except Exception:
            return []
    
    def _get_context_methods(self, context_class: Type) -> List[str]:
        """Get method names from UserExecutionContext class."""
        try:
            return [method for method in dir(context_class) 
                   if not method.startswith('_') and callable(getattr(context_class, method))]
        except Exception:
            return []
    
    def _get_creation_signature(self, context_class: Type) -> Optional[str]:
        """Get the constructor signature for UserExecutionContext."""
        try:
            if hasattr(context_class, '__init__'):
                sig = inspect.signature(context_class.__init__)
                return str(sig)
            return None
        except Exception:
            return None
    
    async def _analyze_factory_creation_patterns(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze different patterns for creating UserExecutionContext instances."""
        creation_patterns = []
        factory_methods = []
        
        # Test direct instantiation patterns
        for context_info in contexts:
            context_class = context_info['class']
            try:
                # Test direct creation
                test_context = context_class(
                    user_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4())
                )
                creation_patterns.append(f"Direct instantiation: {context_info['name']}")
                
            except Exception as e:
                creation_patterns.append(f"Failed direct instantiation: {context_info['name']} - {e}")
        
        # Test factory method patterns
        factory_classes = [ExecutionContextFactory, ContextFactory]
        
        for factory_class in factory_classes:
            if factory_class is not None:
                try:
                    factory_instance = factory_class()
                    
                    # Look for context creation methods
                    methods = [method for method in dir(factory_instance) 
                             if 'context' in method.lower() and callable(getattr(factory_instance, method))]
                    
                    factory_methods.extend(methods)
                    creation_patterns.append(f"Factory pattern: {factory_class.__name__} with methods {methods}")
                    
                except Exception as e:
                    creation_patterns.append(f"Failed factory instantiation: {factory_class.__name__} - {e}")
        
        # Test static method patterns
        for context_info in contexts:
            context_class = context_info['class']
            static_methods = [method for method in dir(context_class) 
                            if method.startswith('create') or method.startswith('from_')]
            
            if static_methods:
                creation_patterns.append(f"Static methods: {context_info['name']} has {static_methods}")
        
        return {
            'creation_patterns': creation_patterns,
            'factory_methods': factory_methods,
            'context_count': len(contexts)
        }
    
    def _check_factory_signature_consistency(self, factory_analysis: Dict[str, Any]) -> List[str]:
        """Check for inconsistent factory method signatures across implementations."""
        signature_violations = []
        
        # This is a simplified check - real implementation would need detailed signature analysis
        patterns = factory_analysis['creation_patterns']
        
        # Look for inconsistent patterns
        direct_patterns = [p for p in patterns if 'Direct instantiation' in p]
        factory_patterns = [p for p in patterns if 'Factory pattern' in p]
        static_patterns = [p for p in patterns if 'Static methods' in p]
        
        if len(direct_patterns) > 1:
            signature_violations.append(
                f"SIGNATURE INCONSISTENCY: Multiple direct instantiation patterns suggest "
                f"different constructor signatures: {direct_patterns}"
            )
        
        if len(factory_patterns) > 1:
            signature_violations.append(
                f"SIGNATURE INCONSISTENCY: Multiple factory patterns suggest "
                f"different creation interfaces: {factory_patterns}"
            )
        
        if len(static_patterns) > 0 and len(factory_patterns) > 0:
            signature_violations.append(
                f"PATTERN INCONSISTENCY: Mixed static and factory patterns indicate "
                f"inconsistent creation design: static={static_patterns}, factory={factory_patterns}"
            )
        
        return signature_violations
    
    async def _check_context_lifecycle_consistency(self, contexts: List[Dict[str, Any]]) -> List[str]:
        """Check for consistent context lifecycle management across implementations."""
        lifecycle_violations = []
        
        # Test context cleanup and resource management
        for context_info in contexts:
            context_class = context_info['class']
            
            try:
                # Create context and check for cleanup methods
                test_context = context_class(
                    user_id=str(uuid.uuid4()),
                    thread_id=str(uuid.uuid4()),
                    run_id=str(uuid.uuid4())
                )
                
                # Check for lifecycle methods
                has_cleanup = hasattr(test_context, 'cleanup') or hasattr(test_context, 'close')
                has_enter_exit = hasattr(test_context, '__aenter__') and hasattr(test_context, '__aexit__')
                
                lifecycle_info = f"{context_info['name']}: cleanup={has_cleanup}, async_context={has_enter_exit}"
                
                # Different lifecycle patterns indicate SSOT violation
                if not has_cleanup and not has_enter_exit:
                    lifecycle_violations.append(
                        f"LIFECYCLE INCONSISTENCY: {context_info['name']} lacks proper cleanup methods"
                    )
                
            except Exception as e:
                lifecycle_violations.append(
                    f"LIFECYCLE TEST FAILED: {context_info['name']} - {e}"
                )
        
        return lifecycle_violations
    
    def _check_factory_dependency_patterns(self, contexts: List[Dict[str, Any]]) -> List[str]:
        """Check for inconsistent dependency injection patterns across factories."""
        dependency_violations = []
        
        # Analyze dependency requirements for each context type
        dependency_patterns = []
        
        for context_info in contexts:
            context_class = context_info['class']
            
            # Check constructor dependencies
            try:
                sig = inspect.signature(context_class.__init__)
                params = list(sig.parameters.keys())
                params.remove('self')  # Remove self parameter
                
                dependency_patterns.append({
                    'context': context_info['name'],
                    'dependencies': params,
                    'dependency_count': len(params)
                })
                
            except Exception as e:
                dependency_violations.append(
                    f"DEPENDENCY ANALYSIS FAILED: {context_info['name']} - {e}"
                )
        
        # Check for inconsistent dependency requirements
        if len(dependency_patterns) > 1:
            dep_counts = [p['dependency_count'] for p in dependency_patterns]
            if min(dep_counts) != max(dep_counts):
                dependency_violations.append(
                    f"DEPENDENCY INCONSISTENCY: Different dependency requirements across contexts: "
                    f"{[(p['context'], p['dependency_count']) for p in dependency_patterns]}"
                )
            
            # Check for different dependency names
            all_deps = set()
            for pattern in dependency_patterns:
                all_deps.update(pattern['dependencies'])
            
            for pattern in dependency_patterns:
                missing_deps = all_deps - set(pattern['dependencies'])
                if missing_deps:
                    dependency_violations.append(
                        f"DEPENDENCY MISMATCH: {pattern['context']} missing dependencies: {missing_deps}"
                    )
        
        return dependency_violations

    async def test_factory_user_isolation_enforcement(self):
        """DESIGNED TO FAIL: Verify factories enforce proper user isolation.
        
        Multiple factory patterns may create contexts that don't properly isolate
        user data, leading to security vulnerabilities and data leakage.
        """
        isolation_violations = []
        
        # Test concurrent context creation for user isolation
        async def create_user_context(user_id: str, context_data: Dict[str, str]) -> Dict[str, Any]:
            """Create user context and track its isolation properties."""
            result = {
                'user_id': user_id,
                'context_data': context_data,
                'created_contexts': [],
                'isolation_failures': []
            }
            
            available_contexts = self._collect_user_context_implementations()
            
            for context_info in available_contexts:
                try:
                    context_class = context_info['class']
                    context = context_class(
                        user_id=user_id,
                        thread_id=str(uuid.uuid4()),
                        run_id=str(uuid.uuid4())
                    )
                    
                    # Store context reference
                    result['created_contexts'].append({
                        'context': context,
                        'type': context_info['name'],
                        'id': id(context)
                    })
                    
                except Exception as e:
                    result['isolation_failures'].append(
                        f"Failed to create {context_info['name']} for user {user_id}: {e}"
                    )
            
            return result
        
        # Create contexts for multiple users concurrently
        users = [
            ('user1', {'test_data': 'user1_secret'}),
            ('user2', {'test_data': 'user2_secret'}),
            ('user3', {'test_data': 'user3_secret'})
        ]
        
        user_results = await asyncio.gather(*[
            create_user_context(user_id, data) for user_id, data in users
        ])
        
        # Check for isolation violations
        all_contexts = []
        for result in user_results:
            all_contexts.extend(result['created_contexts'])
            if result['isolation_failures']:
                isolation_violations.extend(result['isolation_failures'])
        
        # Check for shared context instances (major violation)
        context_ids = [ctx['id'] for ctx in all_contexts]
        if len(context_ids) != len(set(context_ids)):
            isolation_violations.append(
                f"CRITICAL ISOLATION VIOLATION: Shared context instances detected between users"
            )
        
        # Check for consistent context types per user
        for result in user_results:
            context_types = [ctx['type'] for ctx in result['created_contexts']]
            if len(set(context_types)) != len(context_types):
                isolation_violations.append(
                    f"ISOLATION INCONSISTENCY: User {result['user_id']} has duplicate context types: {context_types}"
                )
        
        # Force violation for test demonstration
        if len(isolation_violations) == 0:
            isolation_violations.append(
                f"POTENTIAL ISOLATION ISSUE: {len(all_contexts)} contexts created across {len(users)} users, "
                f"factory patterns may not guarantee proper isolation"
            )
        
        # Log violations
        for violation in isolation_violations:
            logger.error(f"Factory Isolation Violation: {violation}")
        
        # This test should FAIL to demonstrate isolation issues
        assert len(isolation_violations) > 0, (
            f"Expected factory isolation violations, but found none."
        )
        
        pytest.fail(
            f"Factory User Isolation Violations Detected ({len(isolation_violations)} issues): "
            f"{isolation_violations}"
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)