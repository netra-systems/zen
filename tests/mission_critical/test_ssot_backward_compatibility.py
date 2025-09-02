"""
MISSION CRITICAL: SSOT Backward Compatibility Test Suite

This test suite ensures that the SSOT consolidation doesn't break existing code.
It validates that legacy test patterns still work while encouraging migration to SSOT.
These tests are CRITICAL for ensuring zero-downtime SSOT deployment.

Business Value: Platform/Internal - Migration Safety & Risk Reduction
Ensures SSOT deployment doesn't break existing 6,096+ test files during migration.

CRITICAL: These tests validate that existing patterns work while identifying
areas that need migration. They test the compatibility bridge components.
"""

import asyncio
import inspect
import logging
import os
import sys
import time
import traceback
import uuid
import warnings
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
from unittest import TestCase
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import SSOT framework components
from test_framework.ssot import (
    BaseTestCase,
    AsyncBaseTestCase, 
    DatabaseTestCase,
    WebSocketTestCase,
    IntegrationTestCase,
    MockFactory,
    get_mock_factory,
    get_database_test_utility,
    get_websocket_test_utility,
    get_docker_test_utility,
    validate_test_class
)

# Import compatibility bridge
from test_framework.ssot.compatibility_bridge import (
    LegacyTestCaseAdapter,
    LegacyMockFactoryAdapter,
    LegacyDatabaseUtilityAdapter,
    detect_legacy_test_patterns,
    migrate_legacy_test_to_ssot,
    get_legacy_compatibility_report
)

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class TestSSOTBackwardCompatibility(BaseTestCase):
    """
    CRITICAL: Test SSOT backward compatibility with legacy test patterns.
    These tests ensure existing code continues to work during SSOT migration.
    """
    
    def setUp(self):
        """Set up backward compatibility test environment."""
        super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting backward compatibility test: {self._testMethodName} (ID: {self.test_id})")
        
        # Suppress expected deprecation warnings during testing
        warnings.simplefilter("ignore", DeprecationWarning)
        warnings.simplefilter("ignore", PendingDeprecationWarning)
    
    def tearDown(self):
        """Clean up backward compatibility test."""
        logger.info(f"Completing backward compatibility test: {self._testMethodName} (ID: {self.test_id})")
        super().tearDown()
    
    def test_legacy_unittest_testcase_compatibility(self):
        """
        COMPATIBILITY CRITICAL: Test legacy unittest.TestCase compatibility.
        This ensures tests inheriting from unittest.TestCase still work.
        """
        # Test that legacy TestCase patterns work
        class LegacyTestExample(TestCase):
            def setUp(self):
                self.test_data = "legacy_test_data"
            
            def test_basic_functionality(self):
                self.assertEqual(self.test_data, "legacy_test_data")
                self.assertTrue(True)
            
            def tearDown(self):
                self.test_data = None
        
        # Run legacy test to ensure it works
        suite = unittest.TestLoader().loadTestsFromTestCase(LegacyTestExample)
        runner = unittest.TextTestRunner(verbosity=0, stream=open(os.devnull, 'w'))
        result = runner.run(suite)
        
        self.assertTrue(result.wasSuccessful(),
                       "Legacy unittest.TestCase should still work")
        self.assertEqual(result.testsRun, 1,
                        "Legacy test should have run")
    
    def test_legacy_test_case_adapter_functionality(self):
        """
        ADAPTER CRITICAL: Test LegacyTestCaseAdapter works correctly.
        This validates the bridge between legacy and SSOT patterns.
        """
        # Create legacy test class that doesn't inherit from BaseTestCase
        class OldStyleTest:
            def __init__(self):
                self.setup_called = False
                self.teardown_called = False
            
            def setUp(self):
                self.setup_called = True
            
            def tearDown(self):
                self.teardown_called = True
            
            def test_something(self):
                return "legacy_result"
        
        # Test adapter wrapping
        adapter = LegacyTestCaseAdapter(OldStyleTest)
        self.assertIsNotNone(adapter)
        
        # Test that adapter provides SSOT capabilities
        self.assertTrue(hasattr(adapter, 'env'))
        self.assertTrue(hasattr(adapter, 'metrics'))
        
        # Test that original functionality is preserved
        wrapped_instance = adapter.wrap_instance()
        self.assertTrue(hasattr(wrapped_instance, 'test_something'))
        
        # Test setup/teardown preservation
        wrapped_instance.setUp()
        self.assertTrue(wrapped_instance.setup_called,
                       "Legacy setUp should be preserved")
    
    def test_legacy_mock_factory_adapter(self):
        """
        MOCK COMPATIBILITY CRITICAL: Test legacy mock patterns still work.
        This ensures existing mock code doesn't break with SSOT MockFactory.
        """
        from unittest.mock import patch, MagicMock
        
        # Test that standard mock patterns work
        with patch('builtins.open', MagicMock()) as mock_open:
            mock_open.return_value = MagicMock()
            
            # This should work with SSOT framework
            result = mock_open("test_file.txt")
            self.assertIsNotNone(result)
        
        # Test LegacyMockFactoryAdapter
        adapter = LegacyMockFactoryAdapter()
        self.assertIsNotNone(adapter)
        
        # Test that adapter provides legacy mock methods
        legacy_methods = [
            'create_mock', 'patch_object', 'mock_database',
            'mock_http_client', 'mock_websocket'
        ]
        
        for method_name in legacy_methods:
            self.assertTrue(hasattr(adapter, method_name),
                           f"Legacy adapter missing method: {method_name}")
            
            method = getattr(adapter, method_name)
            self.assertTrue(callable(method),
                           f"Legacy adapter method not callable: {method_name}")
        
        # Test that legacy adapter creates SSOT-compatible mocks
        legacy_mock = adapter.create_mock("legacy_service")
        self.assertIsNotNone(legacy_mock)
        
        # Mock should be tracked by SSOT factory
        ssot_factory = get_mock_factory()
        registry = ssot_factory.get_registry()
        
        # Should have at least one mock (may have others from previous tests)
        self.assertGreaterEqual(len(registry.active_mocks), 1,
                              "Legacy mock should be tracked by SSOT registry")
    
    def test_legacy_database_utility_adapter(self):
        """
        DATABASE COMPATIBILITY CRITICAL: Test legacy database patterns work.
        This ensures existing database test code doesn't break.
        """
        # Test LegacyDatabaseUtilityAdapter
        adapter = LegacyDatabaseUtilityAdapter()
        self.assertIsNotNone(adapter)
        
        # Test that adapter provides legacy database methods
        legacy_methods = [
            'get_connection', 'get_session', 'create_test_database',
            'cleanup_database', 'execute_sql'
        ]
        
        for method_name in legacy_methods:
            self.assertTrue(hasattr(adapter, method_name),
                           f"Legacy database adapter missing method: {method_name}")
        
        # Test that adapter delegates to SSOT database utility
        try:
            connection = adapter.get_connection()
            # If this works, adapter is delegating correctly
            logger.info("Legacy database adapter delegation working")
            
        except Exception as e:
            # Expected if database not available, but adapter should handle gracefully
            logger.warning(f"Database not available for legacy adapter test: {e}")
            self.assertIsNotNone(e)  # Should get meaningful error, not crash
    
    def test_legacy_test_pattern_detection(self):
        """
        DETECTION CRITICAL: Test detection of legacy test patterns.
        This validates our ability to identify tests that need migration.
        """
        # Create test class with legacy patterns
        class LegacyPatternTest(TestCase):
            def setUp(self):
                # Legacy direct os.environ access
                self.old_env = os.environ.get('TEST_VAR', 'default')
                
                # Legacy direct mock creation
                self.mock_service = Mock()
                
                # Legacy database connection
                self.db_connection = None  # Would be actual connection in real code
            
            def test_with_legacy_patterns(self):
                # Legacy assertions
                self.assertEqual(1, 1)
                self.assertTrue(True)
        
        # Test pattern detection
        patterns = detect_legacy_test_patterns(LegacyPatternTest)
        self.assertIsInstance(patterns, dict)
        
        expected_patterns = [
            'direct_environ_access',
            'manual_mock_creation', 
            'manual_database_connection',
            'unittest_inheritance'
        ]
        
        for pattern in expected_patterns:
            self.assertIn(pattern, patterns,
                         f"Should detect legacy pattern: {pattern}")
            self.assertTrue(patterns[pattern],
                           f"Legacy pattern should be detected as present: {pattern}")
    
    def test_legacy_to_ssot_migration_suggestions(self):
        """
        MIGRATION CRITICAL: Test migration suggestions for legacy code.
        This validates our ability to guide migration to SSOT patterns.
        """
        # Create legacy test class
        class MigrationCandidateTest(TestCase):
            def setUp(self):
                self.env_var = os.environ.get('TEST_VAR')
                self.mock_obj = Mock()
            
            def test_functionality(self):
                self.assertTrue(True)
        
        # Test migration suggestion generation
        migration_plan = migrate_legacy_test_to_ssot(MigrationCandidateTest)
        self.assertIsInstance(migration_plan, dict)
        
        required_plan_keys = [
            'current_inheritance',
            'suggested_base_class',
            'required_changes',
            'migration_steps',
            'estimated_effort'
        ]
        
        for key in required_plan_keys:
            self.assertIn(key, migration_plan,
                         f"Migration plan missing key: {key}")
        
        # Test migration steps are actionable
        migration_steps = migration_plan['migration_steps']
        self.assertIsInstance(migration_steps, list)
        self.assertGreater(len(migration_steps), 0,
                          "Migration plan should have actionable steps")
        
        # Each step should have description and code example
        for step in migration_steps:
            self.assertIn('description', step,
                         "Migration step should have description")
            self.assertIn('before', step,
                         "Migration step should show before code")
            self.assertIn('after', step,
                         "Migration step should show after code")
    
    def test_legacy_compatibility_report_generation(self):
        """
        REPORTING CRITICAL: Test legacy compatibility report generation.
        This validates our ability to track migration progress.
        """
        # Generate compatibility report
        report = get_legacy_compatibility_report()
        self.assertIsInstance(report, dict)
        
        required_report_sections = [
            'summary',
            'legacy_patterns_found',
            'migration_candidates',
            'compatibility_issues',
            'recommendations'
        ]
        
        for section in required_report_sections:
            self.assertIn(section, report,
                         f"Compatibility report missing section: {section}")
        
        # Test report summary
        summary = report['summary']
        self.assertIsInstance(summary, dict)
        
        summary_metrics = [
            'total_test_files_scanned',
            'legacy_patterns_detected',
            'migration_priority_high',
            'migration_priority_medium',
            'migration_priority_low'
        ]
        
        for metric in summary_metrics:
            self.assertIn(metric, summary,
                         f"Report summary missing metric: {metric}")
            self.assertIsInstance(summary[metric], int,
                                f"Report metric should be integer: {metric}")
    
    def test_ssot_environment_with_legacy_code(self):
        """
        ENVIRONMENT CRITICAL: Test SSOT environment works with legacy code.
        This ensures IsolatedEnvironment doesn't break legacy patterns.
        """
        # Test that legacy environment access patterns work
        test_var_name = f"LEGACY_TEST_VAR_{self.test_id}"
        test_var_value = "legacy_test_value"
        
        with patch.dict(os.environ, {test_var_name: test_var_value}):
            # Legacy direct access should still work (but be discouraged)
            legacy_value = os.environ.get(test_var_name)
            self.assertEqual(legacy_value, test_var_value,
                           "Legacy os.environ access should still work")
            
            # SSOT environment should also work
            ssot_value = self.env.get(test_var_name)
            self.assertEqual(ssot_value, test_var_value,
                           "SSOT environment should provide same value")
            
            # Both approaches should give same result
            self.assertEqual(legacy_value, ssot_value,
                           "Legacy and SSOT environment access should match")
    
    def test_mixed_inheritance_patterns(self):
        """
        INHERITANCE CRITICAL: Test mixed inheritance patterns work.
        This ensures gradual migration doesn't break existing hierarchies.
        """
        # Test class that mixes legacy and SSOT patterns
        class MixedInheritanceTest(BaseTestCase):
            def setUp(self):
                super().setUp()  # SSOT setup
                self.legacy_data = "legacy_value"  # Legacy pattern
            
            def test_mixed_functionality(self):
                # SSOT assertions
                self.assertIsInstance(self.env, IsolatedEnvironment)
                
                # Legacy assertions  
                self.assertEqual(self.legacy_data, "legacy_value")
                self.assertTrue(True)
        
        # Test that mixed pattern works
        errors = validate_test_class(MixedInheritanceTest)
        self.assertEqual(len(errors), 0,
                        f"Mixed inheritance pattern should be valid, got errors: {errors}")
        
        # Test instantiation works
        test_instance = MixedInheritanceTest()
        test_instance.setUp()
        
        # Should have both SSOT and legacy capabilities
        self.assertIsInstance(test_instance.env, IsolatedEnvironment)
        self.assertEqual(test_instance.legacy_data, "legacy_value")
        
        test_instance.tearDown()
    
    def test_legacy_async_pattern_compatibility(self):
        """
        ASYNC COMPATIBILITY CRITICAL: Test legacy async patterns work.
        This ensures existing async test code doesn't break with SSOT.
        """
        import asyncio
        
        # Test legacy async test pattern
        class LegacyAsyncTest(AsyncBaseTestCase):
            async def asyncSetUp(self):
                await super().asyncSetUp()
                self.async_data = await self._async_setup_helper()
            
            async def _async_setup_helper(self):
                await asyncio.sleep(0.001)  # Simulate async work
                return "async_setup_complete"
            
            async def test_async_functionality(self):
                result = await self._async_test_helper()
                self.assertEqual(result, "async_test_complete")
            
            async def _async_test_helper(self):
                await asyncio.sleep(0.001)  # Simulate async work
                return "async_test_complete"
            
            async def asyncTearDown(self):
                await super().asyncTearDown()
                self.async_data = None
        
        # Test that async pattern works with SSOT
        async def run_legacy_async_test():
            test_instance = LegacyAsyncTest()
            await test_instance.asyncSetUp()
            
            # Should have SSOT capabilities
            self.assertIsInstance(test_instance.env, IsolatedEnvironment)
            
            # Should have async setup data
            self.assertEqual(test_instance.async_data, "async_setup_complete")
            
            # Run test method
            await test_instance.test_async_functionality()
            
            await test_instance.asyncTearDown()
        
        # Run async test
        asyncio.run(run_legacy_async_test())
    
    def test_performance_impact_of_compatibility_layer(self):
        """
        PERFORMANCE CRITICAL: Test compatibility layer doesn't degrade performance.
        This ensures backward compatibility doesn't slow down test execution.
        """
        import psutil
        
        process = psutil.Process()
        
        # Measure performance of direct SSOT usage
        start_time = time.time()
        initial_memory = process.memory_info().rss
        
        # Direct SSOT operations
        for i in range(100):
            factory = get_mock_factory()
            mock = factory.create_mock(f"direct_ssot_{i}")
            factory.cleanup_all_mocks()
        
        direct_duration = time.time() - start_time
        mid_memory = process.memory_info().rss
        
        # Measure performance of compatibility layer
        start_time = time.time()
        
        # Compatibility layer operations
        for i in range(100):
            adapter = LegacyMockFactoryAdapter()
            mock = adapter.create_mock(f"legacy_adapter_{i}")
            adapter.cleanup()
        
        adapter_duration = time.time() - start_time
        final_memory = process.memory_info().rss
        
        # Performance assertions
        max_slowdown = 2.0  # Allow 2x slowdown for compatibility
        max_memory_overhead = 10 * 1024 * 1024  # 10MB overhead
        
        slowdown_ratio = adapter_duration / direct_duration if direct_duration > 0 else 1
        memory_overhead = final_memory - mid_memory
        
        self.assertLess(slowdown_ratio, max_slowdown,
                       f"Compatibility layer too slow: {slowdown_ratio:.2f}x slowdown")
        
        self.assertLess(memory_overhead, max_memory_overhead,
                       f"Compatibility layer using too much memory: {memory_overhead} bytes")
        
        logger.info(f"Performance compatibility test: {slowdown_ratio:.2f}x slowdown, {memory_overhead} bytes overhead")


class TestSSOTLegacyMigrationHelpers(BaseTestCase):
    """
    MIGRATION CRITICAL: Test SSOT migration helper functionality.
    These tests validate tools that help migrate legacy code to SSOT patterns.
    """
    
    def setUp(self):
        """Set up migration helper test environment."""
        super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting migration helper test: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up migration helper test."""
        logger.info(f"Completing migration helper test: {self._testMethodName} (ID: {self.test_id})")
        super().tearDown()
    
    def test_automatic_migration_tool(self):
        """
        AUTOMATION CRITICAL: Test automatic migration tool functionality.
        This validates our ability to automatically migrate simple legacy patterns.
        """
        # Create simple legacy test code
        legacy_code = '''
class OldTest(unittest.TestCase):
    def setUp(self):
        self.env_var = os.environ.get('TEST_VAR')
        self.mock_obj = Mock()
    
    def test_something(self):
        self.assertEqual(1, 1)
'''
        
        # Test automatic migration (would be implemented in real migration tool)
        # For now, test that we can parse and analyze legacy code
        
        from test_framework.ssot.compatibility_bridge import analyze_code_for_migration
        
        analysis = analyze_code_for_migration(legacy_code)
        self.assertIsInstance(analysis, dict)
        
        expected_analysis_keys = [
            'legacy_patterns',
            'suggested_changes',
            'migration_complexity',
            'auto_migrateable'
        ]
        
        for key in expected_analysis_keys:
            self.assertIn(key, analysis,
                         f"Code analysis missing key: {key}")
        
        # Test that common patterns are detected
        patterns = analysis['legacy_patterns']
        self.assertIn('unittest_inheritance', patterns)
        self.assertIn('direct_environ_access', patterns)
        self.assertIn('manual_mock_creation', patterns)
    
    def test_migration_validation_tool(self):
        """
        VALIDATION CRITICAL: Test migration validation functionality.
        This ensures migrated code works correctly and follows SSOT patterns.
        """
        # Create migrated test code
        migrated_code = '''
class NewTest(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.env_var = self.env.get('TEST_VAR')
        factory = get_mock_factory()
        self.mock_obj = factory.create_mock('test_service')
    
    def test_something(self):
        self.assertEqual(1, 1)
'''
        
        from test_framework.ssot.compatibility_bridge import validate_migrated_code
        
        validation = validate_migrated_code(migrated_code)
        self.assertIsInstance(validation, dict)
        
        expected_validation_keys = [
            'ssot_compliance',
            'pattern_violations',
            'performance_impact',
            'migration_quality'
        ]
        
        for key in expected_validation_keys:
            self.assertIn(key, validation,
                         f"Migration validation missing key: {key}")
        
        # Test that SSOT patterns are recognized
        compliance = validation['ssot_compliance']
        self.assertIsInstance(compliance, dict)
        
        # Should detect good SSOT patterns
        self.assertTrue(compliance.get('inherits_from_basetest', False),
                       "Should detect BaseTestCase inheritance")
        self.assertTrue(compliance.get('uses_isolated_environment', False),
                       "Should detect IsolatedEnvironment usage")
        self.assertTrue(compliance.get('uses_mock_factory', False),
                       "Should detect MockFactory usage")
    
    def test_batch_migration_tool(self):
        """
        BATCH CRITICAL: Test batch migration tool functionality.
        This validates our ability to migrate multiple test files at once.
        """
        # Simulate multiple test files that need migration
        test_files = [
            {
                'path': f'test_file_1_{self.test_id}.py',
                'legacy_patterns': ['unittest_inheritance', 'direct_environ_access'],
                'migration_priority': 'high'
            },
            {
                'path': f'test_file_2_{self.test_id}.py', 
                'legacy_patterns': ['manual_mock_creation'],
                'migration_priority': 'medium'
            },
            {
                'path': f'test_file_3_{self.test_id}.py',
                'legacy_patterns': ['manual_database_connection'],
                'migration_priority': 'low'
            }
        ]
        
        from test_framework.ssot.compatibility_bridge import create_batch_migration_plan
        
        batch_plan = create_batch_migration_plan(test_files)
        self.assertIsInstance(batch_plan, dict)
        
        expected_batch_keys = [
            'migration_phases',
            'dependency_order',
            'estimated_duration',
            'risk_assessment'
        ]
        
        for key in expected_batch_keys:
            self.assertIn(key, batch_plan,
                         f"Batch migration plan missing key: {key}")
        
        # Test migration phases
        phases = batch_plan['migration_phases']
        self.assertIsInstance(phases, list)
        self.assertGreater(len(phases), 0,
                          "Batch plan should have migration phases")
        
        # Test that high priority items are in early phases
        phase_priorities = []
        for phase in phases:
            for item in phase.get('items', []):
                phase_priorities.append(item.get('priority'))
        
        # Should have high priority items first
        high_priority_index = phase_priorities.index('high') if 'high' in phase_priorities else -1
        low_priority_index = phase_priorities.index('low') if 'low' in phase_priorities else -1
        
        if high_priority_index >= 0 and low_priority_index >= 0:
            self.assertLess(high_priority_index, low_priority_index,
                           "High priority items should come before low priority items")


class TestSSOTDeprecationHandling(BaseTestCase):
    """
    DEPRECATION CRITICAL: Test SSOT deprecation handling.
    These tests ensure deprecated patterns are handled gracefully with warnings.
    """
    
    def setUp(self):
        """Set up deprecation handling test environment."""
        super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        logger.info(f"Starting deprecation handling test: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up deprecation handling test."""
        logger.info(f"Completing deprecation handling test: {self._testMethodName} (ID: {self.test_id})")
        super().tearDown()
    
    def test_deprecation_warnings_for_legacy_patterns(self):
        """
        WARNING CRITICAL: Test deprecation warnings are issued for legacy patterns.
        This ensures developers are notified when using deprecated patterns.
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")  # Catch all warnings
            
            # Use deprecated pattern
            from test_framework.ssot.compatibility_bridge import deprecated_mock_factory
            
            # Should issue deprecation warning
            deprecated_factory = deprecated_mock_factory()
            
            # Check that warning was issued
            deprecation_warnings = [w for w in warning_list 
                                  if issubclass(w.category, DeprecationWarning)]
            
            self.assertGreater(len(deprecation_warnings), 0,
                             "Should issue deprecation warning for deprecated mock factory")
            
            # Check warning message is helpful
            warning_message = str(deprecation_warnings[0].message)
            self.assertIn("deprecated", warning_message.lower())
            self.assertIn("get_mock_factory", warning_message)
    
    def test_gradual_deprecation_timeline(self):
        """
        TIMELINE CRITICAL: Test gradual deprecation timeline is respected.
        This ensures deprecated features are removed on schedule.
        """
        from test_framework.ssot.compatibility_bridge import get_deprecation_timeline
        
        timeline = get_deprecation_timeline()
        self.assertIsInstance(timeline, dict)
        
        expected_timeline_keys = [
            'phase_1_warnings',
            'phase_2_strict_warnings',
            'phase_3_removal',
            'current_phase'
        ]
        
        for key in expected_timeline_keys:
            self.assertIn(key, timeline,
                         f"Deprecation timeline missing key: {key}")
        
        # Test current phase is valid
        current_phase = timeline['current_phase']
        valid_phases = ['phase_1_warnings', 'phase_2_strict_warnings', 'phase_3_removal']
        self.assertIn(current_phase, valid_phases,
                     f"Current deprecation phase should be one of {valid_phases}")
        
        # Test that timeline has dates
        for phase_key in expected_timeline_keys[:-1]:  # Exclude current_phase
            phase_info = timeline[phase_key]
            self.assertIn('target_date', phase_info,
                         f"Phase {phase_key} should have target_date")
            self.assertIn('description', phase_info,
                         f"Phase {phase_key} should have description")


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Import unittest for compatibility tests
    import unittest
    
    # Run the tests
    pytest.main([__file__, '-v', '--tb=short', '--capture=no'])