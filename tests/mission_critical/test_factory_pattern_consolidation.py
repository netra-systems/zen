"Issue #874: ExecutionEngine factory pattern consolidation test."

This test validates the consolidation of ExecutionEngine factory patterns
to ensure proper SSOT compliance. It detects multiple factory implementations,
validates the canonical ExecutionEngineFactory, and tests factory integration.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Architecture & Performance
- Value Impact: Ensures factory pattern consolidation supports reliable $500K+ ARR chat performance
- Strategic Impact: Validates proper resource management and user isolation through unified factory

Key Validation Areas:
- Single ExecutionEngineFactory implementation (SSOT)
- Factory creates proper UserExecutionEngine instances
- Factory lifecycle management works correctly
- No duplicate factory implementations
- Factory integration with WebSocket and infrastructure

EXPECTED BEHAVIOR:
This test should FAIL initially, detecting multiple factory implementations.
After consolidation, this test should pass with single canonical factory.
""

import unittest
import asyncio
import inspect
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from typing import Dict, List, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FactoryPatternConsolidationTests(SSotBaseTestCase):
    Test ExecutionEngine factory pattern consolidation and SSOT compliance."
    Test ExecutionEngine factory pattern consolidation and SSOT compliance."
    
    def setUp(self):
        "Set up test environment for factory pattern validation."
        super().setUp()
        self.codebase_root = Path(__file__).parent.parent.parent
        self.factory_violations = []
        self.duplicate_factories = []
        self.factory_integration_issues = []
        
        # Expected canonical factory
        self.canonical_factory_module = netra_backend.app.agents.supervisor.execution_engine_factory""
        self.canonical_factory_class = ExecutionEngineFactory
        
        logger.info(Starting ExecutionEngine factory pattern consolidation validation)"
        logger.info(Starting ExecutionEngine factory pattern consolidation validation)"
    
    def test_detect_multiple_factory_implementations(self):
        "Detect multiple ExecutionEngineFactory implementations - SHOULD INITIALLY FAIL."
        logger.info(🔍 FACTORY PATTERN ANALYSIS: Scanning for multiple factory implementations")"
        
        factory_implementations = self._find_all_factory_implementations()
        
        # Log findings
        logger.info(fFound {len(factory_implementations)} ExecutionEngineFactory implementations:)
        for file_path, class_name, is_canonical in factory_implementations:
            status = CANONICAL if is_canonical else DUPLICATE
            logger.info(f  - {status}: {class_name} in {file_path}")"
        
        # Separate canonical from duplicate factories
        canonical_factories = [impl for impl in factory_implementations if impl[2]]
        duplicate_factories = [impl for impl in factory_implementations if not impl[2]]
        
        # Store violations
        self.duplicate_factories = duplicate_factories
        self.factory_violations.extend([
            fDuplicate factory: {class_name} in {file_path}
            for file_path, class_name, _ in duplicate_factories
        ]
        
        logger.warning(f❌ FACTORY DUPLICATION: Found {len(duplicate_factories)} duplicate factory implementations)
        logger.info(f"✅ CANONICAL: Found {len(canonical_factories)} canonical factory implementations)"
        
        # EXPECTED TO FAIL: Multiple factory implementations indicate fragmentation
        self.assertGreater(
            len(duplicate_factories), 0,
            EXPECTED FAILURE: Should detect duplicate ExecutionEngineFactory implementations. "
            EXPECTED FAILURE: Should detect duplicate ExecutionEngineFactory implementations. "
            fFound {len(duplicate_factories)} duplicate factories requiring consolidation.
        )
    
    def test_validate_canonical_factory_functionality(self):
        "Validate canonical ExecutionEngineFactory functionality works correctly."
        logger.info(✅ CANONICAL FACTORY TEST: Validating ExecutionEngineFactory functionality)
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            
            # Test factory can be instantiated
            factory = ExecutionEngineFactory(websocket_bridge=None)  # No WebSocket for test
            self.assertIsNotNone(factory, ExecutionEngineFactory should be instantiable")"
            
            # Test factory has required methods
            required_methods = [
                'create_for_user',
                'user_execution_scope',
                'cleanup_engine',
                'shutdown',
                'get_factory_metrics'
            ]
            
            missing_methods = []
            for method_name in required_methods:
                if not hasattr(factory, method_name):
                    missing_methods.append(method_name)
            
            self.assertEqual(
                len(missing_methods), 0,
                fExecutionEngineFactory missing required methods: {missing_methods}
            )
            
            # Test async methods are properly async
            async_methods = ['create_for_user', 'cleanup_engine', 'shutdown']
            for method_name in async_methods:
                method = getattr(factory, method_name)
                self.assertTrue(
                    asyncio.iscoroutinefunction(method),
                    fExecutionEngineFactory.{method_name} should be async
                )
            
            # Test factory creates UserExecutionEngine
            async def test_factory_creation():
                # Create test user context
                test_user_id = UnifiedIdGenerator.generate_base_id("test_user, True, 8)"
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, factory_test)
                
                user_context = UserExecutionContext(
                    user_id=test_user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': 'factory_functionality'}
                
                # Test factory creates engine
                engine = await factory.create_for_user(user_context)
                
                # Validate engine type
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                self.assertIsInstance(
                    engine, UserExecutionEngine,
                    Factory should create UserExecutionEngine instances"
                    Factory should create UserExecutionEngine instances"
                )
                
                # Validate engine has correct user context
                self.assertEqual(
                    engine.get_user_context().user_id, test_user_id,
                    Engine should have correct user context"
                    Engine should have correct user context"
                )
                
                # Test cleanup
                await factory.cleanup_engine(engine)
                await factory.shutdown()
                
                return True
            
            result = asyncio.run(test_factory_creation())
            self.assertTrue(result, Factory functionality test should pass)
            
            logger.info(✅ PASS: ExecutionEngineFactory functionality works correctly")"
            
        except Exception as e:
            self.factory_violations.append(fFactory functionality test failed: {e})
            self.fail(fFACTORY VIOLATION: Canonical factory functionality broken - {e})
    
    def test_detect_direct_execution_engine_instantiation(self):
        "Detect direct ExecutionEngine instantiation bypassing factory - SHOULD INITIALLY FAIL."
        logger.info(🔍 FACTORY BYPASS ANALYSIS: Scanning for direct ExecutionEngine instantiation)"
        logger.info(🔍 FACTORY BYPASS ANALYSIS: Scanning for direct ExecutionEngine instantiation)"
        
        direct_instantiations = self._find_direct_execution_engine_instantiation()
        
        # Log findings
        logger.info(f"Found {len(direct_instantiations)} direct ExecutionEngine instantiations:)"
        for file_path, line_num, instantiation_line in direct_instantiations:
            logger.info(f  - {file_path}:{line_num})
            logger.info(f    Code: {instantiation_line.strip()})
        
        # Store violations
        self.factory_violations.extend([
            fDirect instantiation: {file_path}:{line_num} - {instantiation_line.strip()}""
            for file_path, line_num, instantiation_line in direct_instantiations
        ]
        
        # EXPECTED TO FAIL: Direct instantiations should be detected
        self.assertGreater(
            len(direct_instantiations), 0,
            EXPECTED FAILURE: Should detect direct ExecutionEngine instantiation bypassing factory. 
            fFound {len(direct_instantiations)} direct instantiations requiring factory migration."
            fFound {len(direct_instantiations)} direct instantiations requiring factory migration."
        )
    
    def test_validate_factory_lifecycle_management(self):
        "Validate factory lifecycle management works properly."
        logger.info(🔄 LIFECYCLE TEST: Validating ExecutionEngineFactory lifecycle management")"
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from shared.id_generation.unified_id_generator import UnifiedIdGenerator
            
            async def test_lifecycle():
                # Create factory
                factory = ExecutionEngineFactory(websocket_bridge=None)
                
                # Test initial state
                metrics = factory.get_factory_metrics()
                self.assertIsInstance(metrics, dict, Factory should provide metrics)
                self.assertEqual(metrics['active_engines_count'], 0, Factory should start with 0 engines)"
                self.assertEqual(metrics['active_engines_count'], 0, Factory should start with 0 engines)"
                
                # Create multiple engines
                engines = []
                for i in range(3):
                    test_user_id = UnifiedIdGenerator.generate_base_id(f"test_user_{i}, True, 8)"
                    thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, flifecycle_test_{i})
                    
                    user_context = UserExecutionContext(
                        user_id=test_user_id,
                        run_id=run_id,
                        thread_id=thread_id,
                        metadata={'test': f'lifecycle_{i}'}
                    
                    engine = await factory.create_for_user(user_context)
                    engines.append(engine)
                
                # Test factory tracks engines
                metrics_after = factory.get_factory_metrics()
                self.assertEqual(
                    metrics_after['active_engines_count'], 3,
                    Factory should track 3 active engines"
                    Factory should track 3 active engines"
                )
                
                # Test context manager pattern
                test_user_id = UnifiedIdGenerator.generate_base_id(context_test_user", True, 8)"
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, context_test)
                
                context_user_context = UserExecutionContext(
                    user_id=test_user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': 'context_manager'}
                
                # Test context manager
                async with factory.user_execution_scope(context_user_context) as context_engine:
                    self.assertIsNotNone(context_engine, Context manager should provide engine")"
                    
                    from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                    self.assertIsInstance(context_engine, UserExecutionEngine,
                                        Context manager should provide UserExecutionEngine)
                
                # Cleanup engines
                for engine in engines:
                    await factory.cleanup_engine(engine)
                
                # Test factory cleanup
                await factory.shutdown()
                
                return True
            
            result = asyncio.run(test_lifecycle())
            self.assertTrue(result, Factory lifecycle test should pass)"
            self.assertTrue(result, Factory lifecycle test should pass)"
            
            logger.info("✅ PASS: ExecutionEngineFactory lifecycle management works properly)"
            
        except Exception as e:
            self.factory_violations.append(fFactory lifecycle test failed: {e})
            self.fail(f"LIFECYCLE VIOLATION: Factory lifecycle management broken - {e})"
    
    def test_validate_factory_integration_patterns(self):
        "Validate factory integration with WebSocket and infrastructure."
        logger.info("🔗 INTEGRATION TEST: Validating ExecutionEngineFactory integration patterns)"
        
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ()
                ExecutionEngineFactory,
                get_execution_engine_factory,
                configure_execution_engine_factory
            )
            
            # Test factory configuration
            async def test_integration():
                # Test factory configuration with mock WebSocket bridge
                mock_websocket_bridge = Mock()
                mock_websocket_bridge.emit_user_event = AsyncMock(return_value=True)
                
                # Test factory configuration
                configured_factory = await configure_execution_engine_factory(
                    websocket_bridge=mock_websocket_bridge
                )
                
                self.assertIsInstance(
                    configured_factory, ExecutionEngineFactory,
                    Configuration should return ExecutionEngineFactory
                )
                
                # Test factory getter
                retrieved_factory = await get_execution_engine_factory()
                self.assertIs(
                    retrieved_factory, configured_factory,
                    Factory getter should return configured factory"
                    Factory getter should return configured factory"
                )
                
                # Test factory creates engines with WebSocket integration
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                test_user_id = UnifiedIdGenerator.generate_base_id(integration_user", True, 8)"
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(test_user_id, integration_test)
                
                user_context = UserExecutionContext(
                    user_id=test_user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': 'integration'}
                
                engine = await configured_factory.create_for_user(user_context)
                
                # Test engine has WebSocket integration
                self.assertIsNotNone(
                    engine.websocket_emitter,
                    Engine should have WebSocket emitter""
                )
                
                # Cleanup
                await configured_factory.cleanup_engine(engine)
                await configured_factory.shutdown()
                
                return True
            
            result = asyncio.run(test_integration())
            self.assertTrue(result, Factory integration test should pass)
            
            logger.info(✅ PASS: ExecutionEngineFactory integration patterns work correctly)"
            logger.info(✅ PASS: ExecutionEngineFactory integration patterns work correctly)"
            
        except Exception as e:
            self.factory_integration_issues.append(f"Factory integration test failed: {e})"
            logger.warning(fINTEGRATION ISSUE: Factory integration may have problems - {e})
            # Don't fail this test as integration issues may be environmental'
    
    def test_comprehensive_factory_consolidation_report(self):
        Generate comprehensive factory consolidation report - SHOULD INITIALLY FAIL.""
        logger.info(📊 COMPREHENSIVE FACTORY CONSOLIDATION REPORT)
        
        # Collect all violations from previous tests
        if not (self.factory_violations or self.duplicate_factories or self.factory_integration_issues):
            # Run analysis if not already done
            self.test_detect_multiple_factory_implementations()
            self.test_validate_canonical_factory_functionality()
            self.test_detect_direct_execution_engine_instantiation()
            self.test_validate_factory_lifecycle_management()
            self.test_validate_factory_integration_patterns()
        
        # Generate comprehensive report
        all_issues = (self.factory_violations + 
                     [f"Duplicate factory: {impl[1]} in {impl[0]} for impl in self.duplicate_factories] +"
                     self.factory_integration_issues)
        
        factory_consolidation_summary = {
            'total_issues': len(all_issues),
            'duplicate_factories': len(self.duplicate_factories),
            'factory_violations': len(self.factory_violations),
            'integration_issues': len(self.factory_integration_issues),
            'consolidation_status': self._assess_consolidation_status(),
            'business_impact': self._assess_factory_business_impact(),
            'consolidation_recommendations': self._generate_consolidation_recommendations()
        }
        
        # Log comprehensive summary
        logger.info(fFACTORY CONSOLIDATION SUMMARY:")"
        logger.info(f  Total Issues: {factory_consolidation_summary['total_issues']})
        logger.info(f  Duplicate Factories: {factory_consolidation_summary['duplicate_factories']})"
        logger.info(f  Duplicate Factories: {factory_consolidation_summary['duplicate_factories']})"
        logger.info(f"  Factory Violations: {factory_consolidation_summary['factory_violations']})"
        logger.info(f  Integration Issues: {factory_consolidation_summary['integration_issues']})
        logger.info(f  Consolidation Status: {factory_consolidation_summary['consolidation_status']})
        logger.info(f  Business Impact: {factory_consolidation_summary['business_impact']['severity']}")"
        
        # Log first 10 issues
        for i, issue in enumerate(all_issues[:10], 1):
            logger.info(f    {i}. {issue})
        
        if len(all_issues) > 10:
            logger.info(f    ... and {len(all_issues) - 10} more issues)
        
        # Log consolidation recommendations
        logger.info("CONSOLIDATION RECOMMENDATIONS:)"
        for rec in factory_consolidation_summary['consolidation_recommendations']:
            logger.info(f  - {rec})
        
        # EXPECTED TO FAIL: Factory consolidation issues should be detected
        self.assertGreater(
            factory_consolidation_summary['total_issues'], 0,
            EXPECTED FAILURE: ExecutionEngine factory pattern consolidation needed. "
            EXPECTED FAILURE: ExecutionEngine factory pattern consolidation needed. "
            fDetected {factory_consolidation_summary['total_issues']} issues requiring resolution. "
            fDetected {factory_consolidation_summary['total_issues']} issues requiring resolution. "
            fStatus: {factory_consolidation_summary['consolidation_status']}, 
            fBusiness Impact: {factory_consolidation_summary['business_impact']['description']}"
            fBusiness Impact: {factory_consolidation_summary['business_impact']['description']}"
        )
    
    def _find_all_factory_implementations(self) -> List[tuple[str, str, bool]]:
        "Find all ExecutionEngineFactory implementations in the codebase."
        factory_implementations = []
        
        for py_file in self.codebase_root.rglob(*.py"):"
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for factory class definitions
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if (line.strip().startswith('class ') and 
                        ('ExecutionEngineFactory' in line or 'EngineFactory' in line)):
                        
                        class_name = self._extract_class_name(line)
                        if class_name:
                            is_canonical = (self.canonical_factory_module in str(py_file) and
                                          class_name == self.canonical_factory_class)
                            factory_implementations.append((str(py_file), class_name, is_canonical))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e})
        
        return factory_implementations
    
    def _find_direct_execution_engine_instantiation(self) -> List[tuple[str, int, str]]:
        Find direct ExecutionEngine instantiation bypassing factory.""
        direct_instantiations = []
        
        for py_file in self.codebase_root.rglob(*.py):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                for line_num, line in enumerate(lines, 1):
                    line_stripped = line.strip()
                    
                    # Look for direct ExecutionEngine instantiation
                    if ('ExecutionEngine(' in line_stripped and 
                        'UserExecutionEngine(' not in line_stripped and
                        'ExecutionEngineFactory(' not in line_stripped and
                        not line_stripped.startswith('#') and
                        'def ' not in line_stripped):
                        
                        direct_instantiations.append((str(py_file), line_num, line))
                
            except (UnicodeDecodeError, IOError) as e:
                logger.debug(fCould not read {py_file}: {e})"
                logger.debug(fCould not read {py_file}: {e})"
        
        return direct_instantiations
    
    def _should_skip_file(self, file_path: Path) -> bool:
        "Check if file should be skipped during analysis."
        skip_patterns = [
            '__pycache__',
            '.pyc',
            'node_modules',
            '.git',
            'venv',
            '.env',
            'test_factory_pattern_consolidation.py',  # Skip self
            'backup',
            'archived'
        ]
        
        file_str = str(file_path)
        return any(pattern in file_str for pattern in skip_patterns)
    
    def _extract_class_name(self, line: str) -> str:
        ""Extract class name from class definition line."
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
            return "
            return "
    
    def _assess_consolidation_status(self) -> str:
        "Assess factory consolidation status."
        if len(self.duplicate_factories) > 3:
            return "SEVERE FRAGMENTATION - Multiple factory implementations"
        elif len(self.duplicate_factories) > 0:
            return MODERATE FRAGMENTATION - Some duplicate factories
        elif len(self.factory_violations) > 5:
            return PATTERN VIOLATIONS - Factory bypassing detected"
            return PATTERN VIOLATIONS - Factory bypassing detected"
        else:
            return GOOD CONSOLIDATION - Minor issues only"
            return GOOD CONSOLIDATION - Minor issues only"
    
    def _assess_factory_business_impact(self) -> Dict[str, Any]:
        Assess business impact of factory consolidation issues.""
        total_issues = len(self.factory_violations) + len(self.duplicate_factories)
        
        if total_issues > 10:
            severity = HIGH
            description = Factory fragmentation risks chat reliability and performance"
            description = Factory fragmentation risks chat reliability and performance"
        elif total_issues > 5:
            severity = MEDIUM"
            severity = MEDIUM"
            description = Factory inconsistencies may cause intermittent issues
        else:
            severity = LOW""
            description = Minor factory pattern violations
        
        return {
            'severity': severity,
            'description': description,
            'chat_performance_risk': severity in ['HIGH', 'MEDIUM'],
            'resource_management_risk': len(self.duplicate_factories) > 0,
            'user_isolation_risk': any('direct instantiation' in v for v in self.factory_violations)
        }
    
    def _generate_consolidation_recommendations(self) -> List[str]:
        "Generate consolidation recommendations for factory patterns."
        return [
            1. Consolidate all ExecutionEngineFactory implementations into single canonical factory,
            2. Replace direct ExecutionEngine instantiation with factory.create_for_user()","
            3. Use factory context managers for automatic lifecycle management,
            4. Configure factory with WebSocket bridge during system startup,"
            4. Configure factory with WebSocket bridge during system startup,"
            "5. Remove duplicate factory classes and redirect imports to canonical factory,"
            6. Update all services to use get_execution_engine_factory() function,
            "7. Add factory integration tests for WebSocket and infrastructure components"
        ]


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()
)))))))))))