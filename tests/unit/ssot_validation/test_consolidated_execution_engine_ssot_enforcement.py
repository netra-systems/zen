#!/usr/bin/env python
"""SSOT Violation Detection Tests for WorkflowOrchestrator Execution Engine Consolidation

PURPOSE: These tests are DESIGNED TO FAIL before SSOT consolidation and PASS afterward.
They detect current SSOT violations in execution engine implementations to support
GitHub Issue #208 (SSOT-incomplete-migration-WorkflowOrchestrator-multiple-execution-engines).

TEST STRATEGY: 20% new tests focused on detecting specific SSOT violations:
1. Multiple execution engine implementations exist (should fail now, pass after consolidation)
2. Deprecated imports still work (should fail now, pass when blocked)
3. Factory pattern not exclusively enforced (should fail now, pass when enforced)

Business Impact: $500K+ ARR at risk from execution engine inconsistencies
Architecture Impact: 60% reduction in duplicated execution logic needed
Testing Compliance: Follows SSOT test patterns from test_framework.ssot modules

NO DOCKER DEPENDENCIES - Unit testing with real services where possible
"""

import asyncio
import gc
import inspect
import logging
import sys
import time
import uuid
import weakref
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple, Type
import threading
import tracemalloc
import psutil

# Add project root to path for imports
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT base test case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import all execution engine implementations to detect SSOT violations
try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as SupervisorExecutionEngine
except ImportError as e:
    logger.warning(f"Could not import SupervisorExecutionEngine: {e}")
    SupervisorExecutionEngine = None

try:
    from netra_backend.app.agents.execution_engine_consolidated import (
        ExecutionEngine as ConsolidatedExecutionEngine,
        RequestScopedExecutionEngine,
        ExecutionEngineFactory as ConsolidatedFactory
    )
except ImportError as e:
    logger.warning(f"Could not import ConsolidatedExecutionEngine: {e}")
    ConsolidatedExecutionEngine = None
    RequestScopedExecutionEngine = None
    ConsolidatedFactory = None

try:
    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as CoreExecutionEngine
except ImportError as e:
    logger.warning(f"Could not import CoreExecutionEngine: {e}")
    CoreExecutionEngine = None

try:
    from netra_backend.app.services.unified_tool_registry.execution_engine import (
        ToolExecutionEngine as ToolRegistryExecutionEngine
    )
except ImportError as e:
    logger.warning(f"Could not import ToolRegistryExecutionEngine: {e}")
    ToolRegistryExecutionEngine = None

# Import factory implementations
try:
    from netra_backend.app.agents.supervisor.execution_engine_factory import (
        ExecutionEngineFactory as SupervisorFactory
    )
except ImportError as e:
    logger.warning(f"Could not import SupervisorFactory: {e}")
    SupervisorFactory = None

# Import context and user management
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestConsolidatedExecutionEngineSSotViolationDetection(SSotAsyncTestCase):
    """DESIGNED TO FAIL: Detect SSOT violations in execution engine implementations.
    
    These tests are specifically designed to FAIL before SSOT consolidation
    and PASS afterward. They validate the current problem state to demonstrate
    the need for consolidation.
    """
    
    async def test_multiple_execution_engine_implementations_detected(self):
        """DESIGNED TO FAIL: Detect duplicate execution engine implementations.
        
        This test should FAIL because we have multiple execution engine 
        implementations that violate SSOT principles. After consolidation,
        this test should PASS by detecting only a single implementation.
        
        Expected Issues (before consolidation):
        - SupervisorExecutionEngine vs ConsolidatedExecutionEngine vs CoreExecutionEngine
        - Multiple factory patterns (SupervisorFactory vs ConsolidatedFactory)
        - Inconsistent interfaces and method signatures
        
        Expected Behavior (after consolidation):
        - Single canonical ExecutionEngine implementation
        - Single factory pattern
        - Consistent interface across all uses
        """
        # Collect all available execution engine classes
        execution_engines = []
        engine_names = []
        
        if SupervisorExecutionEngine:
            execution_engines.append(SupervisorExecutionEngine)
            engine_names.append("SupervisorExecutionEngine")
            
        if ConsolidatedExecutionEngine:
            execution_engines.append(ConsolidatedExecutionEngine)
            engine_names.append("ConsolidatedExecutionEngine")
            
        if CoreExecutionEngine:
            execution_engines.append(CoreExecutionEngine)
            engine_names.append("CoreExecutionEngine")
            
        if ToolRegistryExecutionEngine:
            execution_engines.append(ToolRegistryExecutionEngine)
            engine_names.append("ToolRegistryExecutionEngine")
        
        logger.info(f"Found execution engines: {engine_names}")
        
        # Record current implementation count for test validation
        self.record_metric("execution_engine_count", len(execution_engines))
        self.record_metric("execution_engine_names", engine_names)
        
        # Analyze class hierarchies and methods
        engine_analysis = {}
        core_method_implementations = defaultdict(list)
        
        for engine_class, name in zip(execution_engines, engine_names):
            try:
                # Get public methods
                methods = set(method for method in dir(engine_class) 
                             if not method.startswith('_') and callable(getattr(engine_class, method)))
                
                # Get source file
                source_file = inspect.getfile(engine_class)
                
                # Analyze method resolution order
                mro = [base.__name__ for base in engine_class.__mro__[1:]]
                
                engine_analysis[name] = {
                    'methods': methods,
                    'source_file': source_file,
                    'base_classes': mro,
                    'method_count': len(methods)
                }
                
                # Track core methods that should be unique in SSOT
                core_methods = ['execute', 'run', 'process', 'handle_request', 'execute_pipeline',
                               'initialize', 'cleanup', 'validate', 'create', 'build']
                
                for method in core_methods:
                    if method in methods:
                        core_method_implementations[method].append(name)
                        
            except Exception as e:
                logger.error(f"Error analyzing {name}: {e}")
                engine_analysis[name] = {'error': str(e)}
        
        logger.info(f"Engine analysis: {engine_analysis}")
        logger.info(f"Core method implementations: {dict(core_method_implementations)}")
        
        # SSOT Violation Detection Logic
        ssot_violations = []
        
        # 1. Check for multiple implementations
        if len(execution_engines) > 1:
            ssot_violations.append(
                f"Multiple execution engine implementations detected: {engine_names}. "
                f"SSOT requires single canonical implementation."
            )
        
        # 2. Check for duplicate core method implementations
        for method, implementers in core_method_implementations.items():
            if len(implementers) > 1:
                ssot_violations.append(
                    f"Core method '{method}' implemented in multiple engines: {implementers}. "
                    f"SSOT violation - method should exist in only one place."
                )
        
        # 3. Check for inconsistent interfaces
        if len(engine_analysis) > 1:
            method_counts = [analysis.get('method_count', 0) for analysis in engine_analysis.values()]
            if method_counts and (max(method_counts) - min(method_counts) > 5):
                ssot_violations.append(
                    f"Inconsistent interface sizes detected: {method_counts}. "
                    f"SSOT requires consistent interfaces."
                )
        
        # 4. Check for scattered source files
        source_files = [analysis.get('source_file') for analysis in engine_analysis.values() 
                       if 'source_file' in analysis]
        unique_dirs = set(os.path.dirname(f) for f in source_files if f)
        if len(unique_dirs) > 2:  # Allow some separation but not excessive scattering
            ssot_violations.append(
                f"Execution engines scattered across {len(unique_dirs)} directories: {unique_dirs}. "
                f"SSOT prefers consolidated organization."
            )
        
        # Record violations for debugging
        self.record_metric("ssot_violations", ssot_violations)
        self.record_metric("violation_count", len(ssot_violations))
        
        # Log all violations for debugging
        for i, violation in enumerate(ssot_violations, 1):
            logger.error(f"SSOT Violation #{i}: {violation}")
        
        # TEST ASSERTION: This test is DESIGNED TO FAIL before consolidation
        if len(ssot_violations) == 0:
            # No violations found - consolidation might already be complete
            logger.warning(
                "No SSOT violations detected. This could mean: "
                "1. Consolidation is already complete, OR "
                "2. Imports failed and we're not seeing the real implementations, OR "
                "3. Test logic needs adjustment"
            )
            
            # Check if we have any engines at all
            if len(execution_engines) == 0:
                pytest.fail(
                    "No execution engine implementations found. "
                    "This indicates import failures or missing implementations."
                )
            elif len(execution_engines) == 1:
                logger.info(
                    f"Single execution engine found: {engine_names[0]}. "
                    f"This suggests consolidation may be complete."
                )
                # Test passes in post-consolidation state
                return
            else:
                pytest.fail(
                    f"Multiple engines found ({engine_names}) but no violations detected. "
                    f"Test logic may need adjustment."
                )
        
        # FAIL the test to demonstrate current SSOT violations
        pytest.fail(
            f"SSOT Violations Detected ({len(ssot_violations)} issues):\n" +
            "\n".join(f"  {i+1}. {violation}" for i, violation in enumerate(ssot_violations))
        )

    async def test_deprecated_import_patterns_still_functional(self):
        """DESIGNED TO FAIL: Detect deprecated import patterns that should be blocked.
        
        This test should FAIL because deprecated import patterns still work,
        indicating incomplete migration. After consolidation, these imports
        should either redirect to the canonical implementation or fail completely.
        
        Expected Issues (before consolidation):
        - Direct imports from supervisor/execution_engine.py still work
        - Old factory import patterns still functional
        - Multiple import paths to same functionality
        
        Expected Behavior (after consolidation):
        - Deprecated imports either redirect or fail with clear error messages
        - Single canonical import path enforced
        - Clear deprecation warnings for legacy patterns
        """
        deprecated_import_violations = []
        
        # Test deprecated import patterns that should be blocked post-consolidation
        deprecated_imports = [
            {
                'path': 'netra_backend.app.agents.supervisor.execution_engine',
                'name': 'ExecutionEngine',
                'should_exist': 'redirect_or_fail',
                'description': 'Supervisor-specific execution engine (should redirect to SSOT)'
            },
            {
                'path': 'netra_backend.app.core.execution_engine', 
                'name': 'ExecutionEngine',
                'should_exist': 'fail',
                'description': 'Core execution engine (duplicate, should be removed)'
            },
            {
                'path': 'netra_backend.app.services.unified_tool_registry.execution_engine',
                'name': 'ToolExecutionEngine',
                'should_exist': 'redirect_or_fail', 
                'description': 'Tool-specific execution engine (should redirect to SSOT)'
            }
        ]
        
        import importlib
        import warnings
        
        for import_spec in deprecated_imports:
            module_path = import_spec['path']
            class_name = import_spec['name']
            expected_behavior = import_spec['should_exist']
            description = import_spec['description']
            
            try:
                # Capture any deprecation warnings
                with warnings.catch_warnings(record=True) as warning_list:
                    warnings.simplefilter("always")
                    
                    # Try to import the deprecated module
                    module = importlib.import_module(module_path)
                    
                    # Try to get the deprecated class
                    if hasattr(module, class_name):
                        deprecated_class = getattr(module, class_name)
                        
                        # Check if it's a real implementation or redirect
                        is_real_implementation = hasattr(deprecated_class, '__module__') and \
                                               deprecated_class.__module__ == module_path
                        
                        # Check for deprecation warnings
                        has_deprecation_warning = any(
                            issubclass(w.category, DeprecationWarning) for w in warning_list
                        )
                        
                        if is_real_implementation and not has_deprecation_warning:
                            deprecated_import_violations.append(
                                f"Deprecated import '{module_path}.{class_name}' still functional "
                                f"without deprecation warning. {description}"
                            )
                        
                        logger.info(
                            f"Import test: {module_path}.{class_name} - "
                            f"exists={True}, real_impl={is_real_implementation}, "
                            f"warnings={len(warning_list)}"
                        )
                    else:
                        logger.info(f"Import test: {module_path}.{class_name} - class not found")
                        
            except ImportError as e:
                logger.info(f"Import test: {module_path}.{class_name} - import failed: {e}")
                # Import failure is expected post-consolidation for some paths
            except Exception as e:
                logger.warning(f"Import test error for {module_path}.{class_name}: {e}")
        
        # Test factory import patterns
        factory_import_violations = []
        factory_imports = [
            {
                'path': 'netra_backend.app.agents.supervisor.execution_engine_factory',
                'name': 'ExecutionEngineFactory',
                'description': 'Supervisor factory (should redirect to SSOT factory)'
            }
        ]
        
        for factory_spec in factory_imports:
            module_path = factory_spec['path'] 
            class_name = factory_spec['name']
            description = factory_spec['description']
            
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    factory_class = getattr(module, class_name)
                    
                    # Check if it's a real factory implementation
                    is_real_factory = hasattr(factory_class, '__module__') and \
                                     factory_class.__module__ == module_path
                    
                    if is_real_factory:
                        factory_import_violations.append(
                            f"Deprecated factory '{module_path}.{class_name}' still functional. "
                            f"{description}"
                        )
                        
            except ImportError:
                # Expected for some patterns post-consolidation
                pass
            except Exception as e:
                logger.warning(f"Factory import test error for {module_path}.{class_name}: {e}")
        
        # Combine all import violations
        all_import_violations = deprecated_import_violations + factory_import_violations
        
        # Record metrics for debugging
        self.record_metric("deprecated_import_violations", all_import_violations)
        self.record_metric("deprecated_violation_count", len(all_import_violations))
        
        # Log violations
        for i, violation in enumerate(all_import_violations, 1):
            logger.error(f"Deprecated Import Violation #{i}: {violation}")
        
        # TEST ASSERTION: This test is DESIGNED TO FAIL before consolidation
        if len(all_import_violations) == 0:
            logger.info(
                "No deprecated import violations detected. This suggests either: "
                "1. Import consolidation is complete, OR "
                "2. Imports are already failing (which is expected post-consolidation)"
            )
            # Test passes in post-consolidation state when deprecated imports are blocked
            return
        
        # FAIL the test to demonstrate current deprecated import issues
        pytest.fail(
            f"Deprecated Import Violations Detected ({len(all_import_violations)} issues):\n" +
            "\n".join(f"  {i+1}. {violation}" for i, violation in enumerate(all_import_violations))
        )

    async def test_factory_pattern_enforcement_incomplete(self):
        """DESIGNED TO FAIL: Detect non-exclusive factory pattern enforcement.
        
        This test should FAIL because factory patterns are not exclusively enforced,
        allowing direct instantiation of execution engines. After consolidation,
        factory patterns should be the ONLY way to create execution engines.
        
        Expected Issues (before consolidation):
        - Direct instantiation of execution engines still possible
        - Multiple factory patterns coexist
        - No enforcement of factory-only creation
        
        Expected Behavior (after consolidation):
        - Factory pattern is the ONLY way to create execution engines
        - Direct instantiation blocked or redirected through factory
        - Single canonical factory implementation
        """
        factory_enforcement_violations = []
        
        # Test direct instantiation patterns that should be blocked
        direct_instantiation_tests = []
        
        # Add available engines to test list
        if SupervisorExecutionEngine:
            direct_instantiation_tests.append({
                'class': SupervisorExecutionEngine,
                'name': 'SupervisorExecutionEngine',
                'should_block': True
            })
            
        if ConsolidatedExecutionEngine:
            direct_instantiation_tests.append({
                'class': ConsolidatedExecutionEngine,
                'name': 'ConsolidatedExecutionEngine', 
                'should_block': False  # This might be the SSOT implementation
            })
            
        if CoreExecutionEngine:
            direct_instantiation_tests.append({
                'class': CoreExecutionEngine,
                'name': 'CoreExecutionEngine',
                'should_block': True
            })
            
        if ToolRegistryExecutionEngine:
            direct_instantiation_tests.append({
                'class': ToolRegistryExecutionEngine,
                'name': 'ToolRegistryExecutionEngine',
                'should_block': True
            })
        
        # Test direct instantiation capabilities
        for test_spec in direct_instantiation_tests:
            engine_class = test_spec['class']
            engine_name = test_spec['name'] 
            should_block = test_spec['should_block']
            
            try:
                # Try to instantiate directly (this should be blocked post-consolidation)
                # Use minimal parameters to avoid constructor failures
                instance = None
                
                # Try different instantiation patterns
                try:
                    # Pattern 1: No parameters
                    instance = engine_class()
                    instantiation_method = "no_args"
                except TypeError:
                    try:
                        # Pattern 2: Mock parameters
                        mock_context = UserExecutionContext(
                            user_id=str(uuid.uuid4()),
                            thread_id=str(uuid.uuid4()),
                            run_id=str(uuid.uuid4())
                        )
                        instance = engine_class(context=mock_context)
                        instantiation_method = "with_context"
                    except (TypeError, AttributeError):
                        try:
                            # Pattern 3: Other common parameters
                            instance = engine_class(config={})
                            instantiation_method = "with_config"
                        except (TypeError, AttributeError):
                            instantiation_method = "failed"
                
                if instance is not None:
                    # Direct instantiation succeeded
                    if should_block:
                        factory_enforcement_violations.append(
                            f"Direct instantiation of {engine_name} succeeded via {instantiation_method}. "
                            f"Factory pattern not enforced - should block direct creation."
                        )
                    
                    logger.info(f"Direct instantiation test: {engine_name} - SUCCESS via {instantiation_method}")
                    
                    # Clean up instance
                    del instance
                else:
                    logger.info(f"Direct instantiation test: {engine_name} - BLOCKED (expected)")
                    
            except Exception as e:
                logger.info(f"Direct instantiation test: {engine_name} - BLOCKED with exception: {e}")
                # Exception during instantiation is expected post-consolidation
        
        # Test factory coexistence (multiple factories is a SSOT violation)
        factory_coexistence_violations = []
        available_factories = []
        
        if SupervisorFactory:
            available_factories.append("SupervisorFactory")
        if ConsolidatedFactory:
            available_factories.append("ConsolidatedFactory")
        
        if len(available_factories) > 1:
            factory_coexistence_violations.append(
                f"Multiple factory implementations coexist: {available_factories}. "
                f"SSOT requires single canonical factory."
            )
        
        # Test factory method consistency
        factory_method_violations = []
        
        if len(available_factories) >= 1:
            # Test if factories have consistent interfaces
            factory_classes = []
            if SupervisorFactory:
                factory_classes.append(('SupervisorFactory', SupervisorFactory))
            if ConsolidatedFactory:
                factory_classes.append(('ConsolidatedFactory', ConsolidatedFactory))
            
            factory_methods = {}
            for name, factory_class in factory_classes:
                methods = set(method for method in dir(factory_class) 
                             if not method.startswith('_') and callable(getattr(factory_class, method)))
                factory_methods[name] = methods
            
            # Check for inconsistent factory interfaces
            if len(factory_methods) > 1:
                all_methods = set()
                for methods in factory_methods.values():
                    all_methods.update(methods)
                
                for factory_name, methods in factory_methods.items():
                    missing_methods = all_methods - methods
                    if missing_methods:
                        factory_method_violations.append(
                            f"Factory {factory_name} missing methods: {missing_methods}. "
                            f"SSOT requires consistent factory interfaces."
                        )
        
        # Combine all factory enforcement violations
        all_factory_violations = (factory_enforcement_violations + 
                                factory_coexistence_violations + 
                                factory_method_violations)
        
        # Record metrics for debugging
        self.record_metric("factory_enforcement_violations", all_factory_violations)
        self.record_metric("available_factories", available_factories)
        self.record_metric("factory_violation_count", len(all_factory_violations))
        
        # Log violations
        for i, violation in enumerate(all_factory_violations, 1):
            logger.error(f"Factory Enforcement Violation #{i}: {violation}")
        
        # TEST ASSERTION: This test is DESIGNED TO FAIL before consolidation
        if len(all_factory_violations) == 0:
            logger.info(
                "No factory enforcement violations detected. This suggests: "
                "1. Factory pattern enforcement is complete, OR "
                "2. Direct instantiation is already blocked, OR "
                "3. Single factory pattern is in place"
            )
            # Test passes in post-consolidation state when factory patterns are enforced
            return
        
        # FAIL the test to demonstrate current factory enforcement issues
        pytest.fail(
            f"Factory Enforcement Violations Detected ({len(all_factory_violations)} issues):\n" +
            "\n".join(f"  {i+1}. {violation}" for i, violation in enumerate(all_factory_violations))
        )


class TestExecutionEngineSSotComplianceValidation(SSotAsyncTestCase):
    """Validate SSOT compliance requirements for execution engines.
    
    These tests verify that execution engines follow SSOT principles
    and integration patterns correctly.
    """
    
    async def test_user_execution_context_compatibility_enforced(self):
        """Validate that all execution engines use UserExecutionContext.
        
        This test ensures SSOT compliance with the UserExecutionContext pattern
        and detects engines that don't follow the unified context interface.
        """
        context_compliance_violations = []
        
        # Create test UserExecutionContext
        test_context = UserExecutionContext(
            user_id=str(uuid.uuid4()),
            thread_id=str(uuid.uuid4()),
            run_id=str(uuid.uuid4())
        )
        
        # Test available engines for UserExecutionContext compatibility
        engines_to_test = []
        
        if ConsolidatedExecutionEngine:
            engines_to_test.append(('ConsolidatedExecutionEngine', ConsolidatedExecutionEngine))
        if SupervisorExecutionEngine:
            engines_to_test.append(('SupervisorExecutionEngine', SupervisorExecutionEngine))
        
        for engine_name, engine_class in engines_to_test:
            try:
                # Check if engine accepts UserExecutionContext
                signature = inspect.signature(engine_class.__init__)
                params = list(signature.parameters.keys())
                
                # Look for context-related parameters
                context_params = [p for p in params if 'context' in p.lower()]
                
                if not context_params:
                    context_compliance_violations.append(
                        f"Engine {engine_name} has no context parameters in constructor. "
                        f"SSOT requires UserExecutionContext integration."
                    )
                    continue
                
                # Try to create engine with UserExecutionContext
                try:
                    if 'context' in params:
                        instance = engine_class(context=test_context)
                    elif 'user_context' in params:
                        instance = engine_class(user_context=test_context)
                    else:
                        # Try first context parameter
                        kwargs = {context_params[0]: test_context}
                        instance = engine_class(**kwargs)
                    
                    logger.info(f"UserExecutionContext compatibility: {engine_name} - SUCCESS")
                    
                    # Clean up
                    if hasattr(instance, 'cleanup'):
                        try:
                            if asyncio.iscoroutinefunction(instance.cleanup):
                                await instance.cleanup()
                            else:
                                instance.cleanup()
                        except:
                            pass
                    del instance
                    
                except Exception as e:
                    context_compliance_violations.append(
                        f"Engine {engine_name} failed to accept UserExecutionContext: {e}. "
                        f"SSOT requires standard context interface."
                    )
                    
            except Exception as e:
                context_compliance_violations.append(
                    f"Engine {engine_name} analysis failed: {e}. "
                    f"Cannot verify SSOT context compliance."
                )
        
        # Record results
        self.record_metric("context_compliance_violations", context_compliance_violations)
        self.record_metric("engines_tested", len(engines_to_test))
        
        # Log violations
        for i, violation in enumerate(context_compliance_violations, 1):
            logger.error(f"Context Compliance Violation #{i}: {violation}")
        
        # This test should pass in both pre and post consolidation states
        # if existing engines properly support UserExecutionContext
        if len(context_compliance_violations) > 0:
            pytest.fail(
                f"UserExecutionContext Compliance Violations ({len(context_compliance_violations)} issues):\n" +
                "\n".join(f"  {i+1}. {violation}" for i, violation in enumerate(context_compliance_violations))
            )
        
        logger.info("All tested execution engines are compatible with UserExecutionContext")

    async def test_import_path_consolidation_status(self):
        """Test the current status of import path consolidation.
        
        This test documents the current import landscape and will change
        behavior as consolidation progresses.
        """
        import_status = {
            'available_engines': [],
            'available_factories': [],
            'import_failures': [],
            'consolidation_indicators': []
        }
        
        # Test all known import paths
        import_tests = [
            ('netra_backend.app.agents.supervisor.execution_engine', 'ExecutionEngine'),
            ('netra_backend.app.agents.execution_engine_consolidated', 'ExecutionEngine'),
            ('netra_backend.app.core.execution_engine', 'ExecutionEngine'),
            ('netra_backend.app.services.unified_tool_registry.execution_engine', 'ToolExecutionEngine'),
            ('netra_backend.app.agents.supervisor.execution_engine_factory', 'ExecutionEngineFactory'),
            ('netra_backend.app.agents.execution_engine_consolidated', 'ExecutionEngineFactory')
        ]
        
        import importlib
        
        for module_path, class_name in import_tests:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, class_name):
                    full_name = f"{module_path}.{class_name}"
                    if 'factory' in class_name.lower():
                        import_status['available_factories'].append(full_name)
                    else:
                        import_status['available_engines'].append(full_name)
                else:
                    import_status['import_failures'].append(f"{module_path}.{class_name} - class not found")
            except ImportError as e:
                import_status['import_failures'].append(f"{module_path}.{class_name} - import error: {e}")
            except Exception as e:
                import_status['import_failures'].append(f"{module_path}.{class_name} - other error: {e}")
        
        # Analyze consolidation status
        engine_count = len(import_status['available_engines'])
        factory_count = len(import_status['available_factories'])
        
        if engine_count == 1:
            import_status['consolidation_indicators'].append("Single execution engine implementation detected")
        elif engine_count > 1:
            import_status['consolidation_indicators'].append(f"Multiple execution engines detected: {engine_count}")
        else:
            import_status['consolidation_indicators'].append("No execution engines found (possible import issues)")
        
        if factory_count == 1:
            import_status['consolidation_indicators'].append("Single factory implementation detected")
        elif factory_count > 1:
            import_status['consolidation_indicators'].append(f"Multiple factories detected: {factory_count}")
        else:
            import_status['consolidation_indicators'].append("No factories found (possible import issues)")
        
        # Record comprehensive status
        self.record_metric("import_status", import_status)
        self.record_metric("consolidation_progress", {
            'engine_count': engine_count,
            'factory_count': factory_count,
            'total_imports_working': engine_count + factory_count,
            'total_import_failures': len(import_status['import_failures'])
        })
        
        # Log current status
        logger.info(f"Import consolidation status: {import_status}")
        
        # This test documents status rather than failing
        logger.info(
            f"Execution Engine Import Status: "
            f"{engine_count} engines, {factory_count} factories available"
        )


if __name__ == "__main__":
    # Run tests directly for debugging
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"
    ], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr)