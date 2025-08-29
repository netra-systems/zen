"""Comprehensive test suite to prevent configuration loop regression across all environments.

This test suite ensures that configuration management works correctly across:
- Development
- Testing
- Staging  
- Production

It prevents the regression of the configuration loop issue where the system
incorrectly identified non-test environments as test contexts.
"""
import unittest
from unittest.mock import patch, MagicMock, call
import logging
import sys
from typing import Dict, Any, List, Optional
from netra_backend.app.core.configuration.base import UnifiedConfigManager
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.schemas.config import AppConfig


class ConfigurationRegressionTestBase:
    """Base class for configuration regression tests."""
    
    def create_mock_env(self, env_vars: Dict[str, Any]) -> MagicMock:
        """Create a mock environment with specific variables."""
        mock_env = MagicMock(spec=IsolatedEnvironment)
        mock_env.get.side_effect = lambda key, default=None: env_vars.get(key, default)
        return mock_env
    
    def count_cache_clears(self, log_calls: List[str]) -> int:
        """Count how many times configuration caches were cleared."""
        return sum(1 for msg in log_calls if "All configuration caches cleared" in str(msg))
    
    def assert_no_configuration_loop(self, config_manager: UnifiedConfigManager, 
                                    iterations: int = 10) -> None:
        """Assert that configuration is not repeatedly cleared."""
        # Track method calls to detect loops
        with patch.object(config_manager, '_clear_all_caches', 
                         wraps=config_manager._clear_all_caches) as mock_clear:
            # Call get_config multiple times
            for _ in range(iterations):
                _ = config_manager.get_config()
            
            # In non-test environments, caches should not be cleared repeatedly
            # Allow at most 1 clear (during initialization)
            self.assertLessEqual(
                mock_clear.call_count, 
                1,
                f"Configuration caches were cleared {mock_clear.call_count} times. "
                f"Expected at most 1 time. This indicates a configuration loop."
            )
    
    def assert_configuration_cached(self, config_manager: UnifiedConfigManager,
                                   iterations: int = 5) -> None:
        """Assert that configuration is properly cached."""
        configs = []
        for _ in range(iterations):
            configs.append(config_manager.get_config())
        
        # All configs should be the same cached instance
        for i in range(1, len(configs)):
            self.assertIs(
                configs[i], 
                configs[0],
                f"Configuration at index {i} is not the same cached instance as index 0"
            )


class TestDevelopmentEnvironment(unittest.TestCase, ConfigurationRegressionTestBase):
    """Test configuration behavior in development environment."""
    
    def test_no_loop_with_test_mode_false(self):
        """Test that TEST_MODE=false doesn't trigger test context."""
        env_vars = {
            'ENVIRONMENT': 'development',
            'TEST_MODE': 'false',  # Explicitly false
            'TESTING': None,
            'PYTEST_CURRENT_TEST': None
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env', 
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_no_configuration_loop(config_manager)
    
    def test_no_loop_with_empty_test_vars(self):
        """Test that empty test variables don't trigger test context."""
        env_vars = {
            'ENVIRONMENT': 'development',
            'TEST_MODE': '',  # Empty string
            'TESTING': '',
            'PYTEST_CURRENT_TEST': None
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_no_configuration_loop(config_manager)
    
    def test_caching_enabled_in_development(self):
        """Test that configuration caching works in development."""
        env_vars = {
            'ENVIRONMENT': 'development',
            'TEST_MODE': 'false',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_configuration_cached(config_manager)


class TestStagingEnvironment(unittest.TestCase, ConfigurationRegressionTestBase):
    """Test configuration behavior in staging environment."""
    
    def test_no_loop_in_staging(self):
        """Test that staging environment doesn't trigger test context."""
        env_vars = {
            'ENVIRONMENT': 'staging',
            'TEST_MODE': None,
            'TESTING': None,
            'PYTEST_CURRENT_TEST': None
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_no_configuration_loop(config_manager)
    
    def test_staging_with_accidentally_set_test_vars(self):
        """Test staging behavior even if test vars are accidentally set to false."""
        env_vars = {
            'ENVIRONMENT': 'staging',
            'TEST_MODE': 'false',  # Might be set accidentally
            'TESTING': '0',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_no_configuration_loop(config_manager)
    
    def test_caching_enabled_in_staging(self):
        """Test that configuration caching works in staging."""
        env_vars = {
            'ENVIRONMENT': 'staging',
            'GCP_PROJECT': 'netra-staging'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_configuration_cached(config_manager)


class TestProductionEnvironment(unittest.TestCase, ConfigurationRegressionTestBase):
    """Test configuration behavior in production environment."""
    
    def test_no_loop_in_production(self):
        """Test that production environment never triggers test context."""
        env_vars = {
            'ENVIRONMENT': 'production',
            'TEST_MODE': None,
            'TESTING': None,
            'PYTEST_CURRENT_TEST': None
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_no_configuration_loop(config_manager)
    
    def test_production_ignores_test_vars(self):
        """Test that production ignores test variables even if set."""
        env_vars = {
            'ENVIRONMENT': 'production',
            'TEST_MODE': 'false',  # Should be ignored
            'TESTING': 'false',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_no_configuration_loop(config_manager)
    
    def test_caching_always_enabled_in_production(self):
        """Test that configuration caching is always enabled in production."""
        env_vars = {
            'ENVIRONMENT': 'production',
            'GCP_PROJECT': 'netra-production',
            'CONFIG_HOT_RELOAD': 'false'  # Should never be true in prod
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assert_configuration_cached(config_manager, iterations=20)


class TestActualTestEnvironment(unittest.TestCase, ConfigurationRegressionTestBase):
    """Test that actual test environments work correctly."""
    
    def test_cache_clearing_when_actually_testing(self):
        """Test that cache clearing works when actually in test mode."""
        env_vars = {
            'ENVIRONMENT': 'testing',
            'TESTING': 'true',  # Explicitly true
            'TEST_MODE': 'true'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            
            with patch.object(config_manager, '_clear_all_caches',
                            wraps=config_manager._clear_all_caches) as mock_clear:
                # Call get_config multiple times
                for _ in range(3):
                    _ = config_manager.get_config()
                
                # In test context, we expect clearing on each call
                self.assertGreaterEqual(
                    mock_clear.call_count,
                    3,
                    "Configuration should be cleared on each call in test context"
                )
    
    def test_pytest_detection(self):
        """Test that pytest is properly detected as test context."""
        # Simulate pytest being loaded
        with patch.dict(sys.modules, {'pytest': MagicMock()}):
            env_vars = {
                'ENVIRONMENT': 'development',  # Even in dev
                'TEST_MODE': 'false'
            }
            
            with patch('netra_backend.app.core.configuration.base.get_env',
                      return_value=self.create_mock_env(env_vars)):
                config_manager = UnifiedConfigManager()
                
                # Should detect pytest and treat as test context
                self.assertTrue(config_manager._is_test_context())


class TestEdgeCases(unittest.TestCase, ConfigurationRegressionTestBase):
    """Test edge cases and boundary conditions."""
    
    def test_case_insensitive_test_values(self):
        """Test that test detection is case-insensitive."""
        test_cases = [
            ('TRUE', True),
            ('True', True),
            ('true', True),
            ('YES', True),
            ('Yes', True),
            ('yes', True),
            ('1', True),
            ('ON', True),
            ('on', True),
            ('FALSE', False),
            ('False', False),
            ('false', False),
            ('NO', False),
            ('no', False),
            ('0', False),
            ('OFF', False),
            ('off', False),
            ('', False),
            (None, False)
        ]
        
        for value, should_be_test in test_cases:
            with self.subTest(value=value):
                env_vars = {
                    'ENVIRONMENT': 'development',
                    'TEST_MODE': value,
                    'TESTING': None
                }
                
                with patch('netra_backend.app.core.configuration.base.get_env',
                          return_value=self.create_mock_env(env_vars)):
                    config_manager = UnifiedConfigManager()
                    is_test = config_manager._is_test_context()
                    
                    self.assertEqual(
                        is_test, 
                        should_be_test,
                        f"TEST_MODE={value} should result in test_context={should_be_test}"
                    )
    
    def test_environment_priority(self):
        """Test that ENVIRONMENT=test/testing takes priority."""
        env_vars = {
            'ENVIRONMENT': 'test',  # This should trigger test context
            'TEST_MODE': 'false',   # Even though this is false
            'TESTING': 'false'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            self.assertTrue(config_manager._is_test_context())
    
    def test_hot_reload_doesnt_cause_loop(self):
        """Test that hot reload doesn't cause configuration loops."""
        env_vars = {
            'ENVIRONMENT': 'development',
            'CONFIG_HOT_RELOAD': 'true',
            'TEST_MODE': 'false'
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            
            # Hot reload should work without causing loops
            config_manager.reload_config(force=True)
            
            # After reload, normal caching should still work
            self.assert_no_configuration_loop(config_manager)


class TestPerformance(unittest.TestCase, ConfigurationRegressionTestBase):
    """Test configuration performance characteristics."""
    
    def test_config_load_performance(self):
        """Test that configuration loading is performant."""
        import time
        
        env_vars = {
            'ENVIRONMENT': 'production',
            'TEST_MODE': None
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            
            # Measure time for multiple config accesses
            start_time = time.time()
            for _ in range(1000):
                _ = config_manager.get_config()
            elapsed = time.time() - start_time
            
            # Should be very fast due to caching (< 100ms for 1000 calls)
            self.assertLess(
                elapsed, 
                0.1,
                f"1000 config accesses took {elapsed:.3f}s, expected < 0.1s"
            )
    
    def test_memory_usage_stable(self):
        """Test that repeated config access doesn't leak memory."""
        env_vars = {
            'ENVIRONMENT': 'production',
            'TEST_MODE': None
        }
        
        with patch('netra_backend.app.core.configuration.base.get_env',
                  return_value=self.create_mock_env(env_vars)):
            config_manager = UnifiedConfigManager()
            
            # Get initial config
            first_config = config_manager.get_config()
            first_id = id(first_config)
            
            # Access config many times
            for _ in range(100):
                config = config_manager.get_config()
                # Should always be the same object (no new allocations)
                self.assertEqual(id(config), first_id)


def run_regression_suite():
    """Run the complete regression test suite."""
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestDevelopmentEnvironment,
        TestStagingEnvironment,
        TestProductionEnvironment,
        TestActualTestEnvironment,
        TestEdgeCases,
        TestPerformance
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == '__main__':
    # Run the full regression suite
    success = run_regression_suite()
    sys.exit(0 if success else 1)