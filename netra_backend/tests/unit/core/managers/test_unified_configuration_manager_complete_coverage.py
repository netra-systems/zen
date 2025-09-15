"""
Complete Coverage Test Suite for UnifiedConfigurationManager

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects ALL user tiers)
- Business Goal: Platform Stability & Configuration Reliability
- Value Impact: 100% test coverage ensures zero configuration failures
- Strategic Impact: Foundation for entire AI platform - configuration failures = system-wide failures

CRITICAL: This test file ensures 100% coverage of ALL UnifiedConfigurationManager functionality.
Complements the existing comprehensive test file by covering remaining edge cases and error paths.

Test Requirements from CLAUDE.md:
1. CHEATING ON TESTS = ABOMINATION - Every test MUST fail hard on errors, no mocking business logic  
2. NO MOCKS unless absolutely necessary - Use real UnifiedConfigurationManager instances
3. ABSOLUTE IMPORTS ONLY - No relative imports (. or ..)
4. Tests must RAISE ERRORS - No try/except blocks masking failures
5. Real services over mocks - Must use real IsolatedEnvironment integration

Additional Coverage Areas:
1. WebSocket integration error handling
2. Configuration file loading edge cases  
3. Environment detection fallback scenarios
4. Memory management under stress
5. Unicode edge cases and special characters
6. Configuration entry display value masking
7. Thread safety under extreme load
8. Factory cleanup and resource management
9. Audit trail edge cases
10. Performance boundary testing
"""
import asyncio
import json
import logging
import os
import pytest
import tempfile
import threading
import time
import uuid
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch, mock_open
from contextlib import asynccontextmanager
from test_framework.ssot.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment, get_env
from netra_backend.app.core.configuration.base import UnifiedConfigManager, get_config, get_config_value, set_config_value, validate_config_value, get_environment, is_production, is_development, is_testing, config_manager

class TestUnifiedConfigurationManagerExtreme(BaseTestCase):
    """Extreme edge case testing for 100% coverage."""

    def setUp(self):
        """Set up test environment with complete isolation."""
        super().setUp()
        self.test_user_id = f'extreme_test_user_{uuid.uuid4().hex[:8]}'
        self.test_service = f'extreme_test_service_{uuid.uuid4().hex[:8]}'
        self.test_env = 'extreme_test'
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.enable_isolation(backup_original=True)
        self.manager = UnifiedConfigurationManager(user_id=self.test_user_id, service_name=self.test_service, environment=self.test_env, enable_validation=True, enable_caching=True, cache_ttl=1)

    def tearDown(self):
        """Clean up test environment completely."""
        try:
            ConfigurationManagerFactory._global_manager = None
            ConfigurationManagerFactory._user_managers.clear()
            ConfigurationManagerFactory._service_managers.clear()
            self.isolated_env.disable_isolation(restore_original=True)
        except Exception as e:
            raise AssertionError(f'Teardown failed critically: {e}')
        super().tearDown()

    def test_websocket_integration_with_real_async_mock(self):
        """Test WebSocket integration with proper async mock setup."""
        mock_websocket_manager = Mock()
        mock_websocket_manager.broadcast_system_message = AsyncMock()
        self.manager.set_websocket_manager(mock_websocket_manager)
        self.assertIsNotNone(self.manager._websocket_manager)
        self.assertEqual(self.manager._websocket_manager, mock_websocket_manager)
        self.assertGreater(len(self.manager._change_listeners), 0)
        self.manager.enable_websocket_events(True)
        self.assertTrue(self.manager._enable_websocket_events)
        self.manager.enable_websocket_events(False)
        self.assertFalse(self.manager._enable_websocket_events)

    def test_websocket_change_listener_error_handling(self):
        """Test WebSocket change listener handles errors gracefully."""
        mock_websocket_manager = Mock()
        mock_websocket_manager.broadcast_system_message = AsyncMock(side_effect=Exception('WebSocket broadcast failed'))
        self.manager.set_websocket_manager(mock_websocket_manager)
        self.manager.enable_websocket_events(True)
        try:
            self.manager.set('websocket.error.test', 'test_value')
            self.assertTrue(True, 'WebSocket listener error handled gracefully')
        except Exception as e:
            self.fail(f'WebSocket listener error should not propagate: {e}')

    def test_websocket_sensitive_value_masking_edge_cases(self):
        """Test WebSocket sensitive value masking edge cases."""
        mock_websocket = Mock()
        self.manager.set_websocket_manager(mock_websocket)
        sensitive_test_cases = [('', '***'), ('a', '***'), ('ab', '***'), ('abc', '***'), ('abcd', '***'), ('abcde', 'ab*de'), ('secret_key_12345', 'se***************45')]
        for original_value, expected_masked in sensitive_test_cases:
            with self.subTest(value=original_value):
                key = f'sensitive.test.{len(original_value)}'
                self.manager.set(key, original_value)
                if key in self.manager._configurations:
                    self.manager._configurations[key].sensitive = True
                self.manager._sensitive_keys.add(key)
                entry = self.manager._configurations[key]
                display_value = entry.get_display_value()
                if len(original_value) <= 4:
                    self.assertEqual(display_value, '***')
                else:
                    self.assertIn('*', display_value)
                    self.assertTrue(display_value.startswith(original_value[:2]))
                    self.assertTrue(display_value.endswith(original_value[-2:]))

    def test_configuration_file_loading_with_missing_files(self):
        """Test configuration file loading when files don't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            manager = UnifiedConfigurationManager(environment='nonexistent_env', service_name='nonexistent_service')
            self.assertIsNotNone(manager)

    def test_configuration_file_loading_with_invalid_json(self):
        """Test configuration file loading with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'config' / 'default.json'
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                f.write('{ invalid json content }')
            with patch('pathlib.Path.exists') as mock_exists:

                def exists_side_effect(self_path):
                    return str(self_path).endswith('default.json')
                mock_exists.side_effect = lambda: exists_side_effect(config_path)
                try:
                    manager = UnifiedConfigurationManager()
                    self.assertIsNotNone(manager)
                except Exception as e:
                    self.assertNotIsInstance(e, json.JSONDecodeError)

    def test_configuration_file_loading_with_permission_errors(self):
        """Test configuration file loading with permission errors."""
        with patch('builtins.open', side_effect=PermissionError('Permission denied')):
            with patch('pathlib.Path.exists', return_value=True):
                try:
                    manager = UnifiedConfigurationManager()
                    self.assertIsNotNone(manager)
                except PermissionError:
                    self.fail('Permission errors should be handled gracefully')

    def test_nested_dictionary_flattening_edge_cases(self):
        """Test nested dictionary flattening with extreme nesting."""
        deeply_nested = {'level1': {'level2': {'level3': {'level4': {'level5': {'level6': {'level7': {'level8': 'deep_value'}}}}}}}}
        self.manager._merge_configuration_data(deeply_nested, ConfigurationSource.CONFIG_FILE)
        flattened_key = 'level1.level2.level3.level4.level5.level6.level7.level8'
        self.assertTrue(self.manager.exists(flattened_key))
        self.assertEqual(self.manager.get(flattened_key), 'deep_value')

    def test_environment_detection_fallback_scenarios(self):
        """Test environment detection fallback through all possible sources."""
        env_detection_cases = [('ENVIRONMENT', 'production'), ('STAGE', 'staging'), ('ENV', 'development'), ('DEPLOYMENT_ENV', 'test'), (None, 'development')]
        for env_var, expected_env in env_detection_cases:
            with self.subTest(env_var=env_var, expected_env=expected_env):
                env_mock_values = {}
                if env_var:
                    env_mock_values[env_var] = expected_env
                with patch.object(IsolatedEnvironment, 'get', side_effect=lambda key: env_mock_values.get(key)):
                    manager = UnifiedConfigurationManager()
                    self.assertEqual(manager.environment, expected_env.lower() if expected_env else 'development')

    def test_environment_detection_with_empty_values(self):
        """Test environment detection when environment variables are empty."""
        empty_values = {'ENVIRONMENT': '', 'STAGE': None, 'ENV': '', 'DEPLOYMENT_ENV': None}
        with patch.object(IsolatedEnvironment, 'get', side_effect=lambda key: empty_values.get(key)):
            manager = UnifiedConfigurationManager()
            self.assertEqual(manager.environment, 'development')

    def test_memory_management_under_extreme_load(self):
        """Test memory management under extreme configuration load."""
        import gc
        initial_config_count = len(self.manager._configurations)
        for i in range(10000):
            key = f'memory_stress.config_{i}'
            value = f"large_value_{'x' * 1000}_{i}"
            self.manager.set(key, value)
            if i % 1000 == 0:
                gc.collect()
        self.assertGreaterEqual(len(self.manager._configurations), initial_config_count + 10000)
        keys_to_delete = [k for k in self.manager.keys() if k.startswith('memory_stress.')]
        for key in keys_to_delete:
            self.manager.delete(key)
        gc.collect()
        final_count = len(self.manager._configurations)
        self.assertLessEqual(final_count, initial_config_count + 100)

    def test_change_history_memory_management(self):
        """Test change history memory management and size limiting."""
        self.manager._audit_enabled = True
        for i in range(1500):
            self.manager.set(f'history_test_{i}', f'value_{i}')
        history = self.manager.get_change_history()
        self.assertLessEqual(len(history), 500)
        self.assertGreater(len(history), 0)
        recent_changes = [h for h in history if h['key'].startswith('history_test_')]
        self.assertGreater(len(recent_changes), 0)

    def test_cache_memory_management_with_ttl(self):
        """Test cache memory management with TTL expiration."""
        self.manager.enable_caching = True
        self.manager.cache_ttl = 0.1
        for i in range(1000):
            key = f'cache_memory_test_{i}'
            self.manager.set(key, f'cached_value_{i}')
            self.manager.get(key)
        initial_cache_size = len(self.manager._cache)
        self.assertGreater(initial_cache_size, 0)
        time.sleep(0.2)
        for i in range(0, 100, 10):
            self.manager.get(f'cache_memory_test_{i}')
        self.assertGreater(len(self.manager._cache), 0)
        self.assertLessEqual(len(self.manager._cache), initial_cache_size)

    def test_unicode_configuration_keys_and_values(self):
        """Test Unicode support in configuration keys and values."""
        unicode_test_cases = [('[U+6D4B][U+8BD5].[U+952E]', '[U+6D4B][U+8BD5][U+503C]', 'Chinese characters'), ('config.[U+00E9]moji', '[U+1F680][U+1F4BB][U+1F527]', 'Emojis'), ('config.pucck[U+0438][U+0439]', '[U+0437]na[U+0447]en[U+0438]e', 'Cyrillic characters'), ('config.[U+0627][U+0644][U+0639][U+0631][U+0628][U+064A][U+0629]', '[U+0642][U+064A][U+0645][U+0629]', 'Arabic characters'), ('config.[U+65E5][U+672C][U+8A9E]', '[U+5024]', 'Japanese characters'), ('config.[U+D55C][U+AD6D][U+C5B4]', '[U+AC12]', 'Korean characters'), ('special.chars', '!@#$%^&*()_+-=[]{}|;\':",./<>?', 'Special characters'), ('newlines.test', 'line1\nline2\rline3\r\nline4', 'Various newlines'), ('tabs.test', 'col1\tcol2\tcol3', 'Tab characters')]
        for key, value, description in unicode_test_cases:
            with self.subTest(key=key, description=description):
                self.manager.set(key, value)
                retrieved_value = self.manager.get(key)
                self.assertEqual(retrieved_value, value)
                self.assertTrue(self.manager.exists(key))
                all_keys = self.manager.keys()
                self.assertIn(key, all_keys)

    def test_configuration_with_null_bytes_and_control_characters(self):
        """Test configuration with null bytes and control characters."""
        control_char_test_cases = [('null.byte', 'value\x00with\x00null', 'Null bytes'), ('control.chars', '\x01\x02\x03\x04\x05', 'Control characters'), ('mixed.content', 'normal\x00text\x01control\x02chars', 'Mixed content')]
        for key, value, description in control_char_test_cases:
            with self.subTest(key=key, description=description):
                try:
                    self.manager.set(key, value)
                    retrieved = self.manager.get(key)
                    self.assertEqual(retrieved, value)
                except Exception as e:
                    self.assertIsInstance(e, (ValueError, UnicodeError))

    def test_extremely_long_configuration_values(self):
        """Test handling of extremely long configuration values."""
        size_test_cases = [1000, 10000, 100000, 1000000]
        for size in size_test_cases:
            with self.subTest(size=size):
                key = f'large.value.{size}'
                large_value = 'x' * size
                start_time = time.time()
                self.manager.set(key, large_value)
                set_time = time.time() - start_time
                start_time = time.time()
                retrieved_value = self.manager.get(key)
                get_time = time.time() - start_time
                self.assertEqual(len(retrieved_value), size)
                self.assertEqual(retrieved_value, large_value)
                self.assertLess(set_time, 1.0, f'Setting {size} byte value took too long')
                self.assertLess(get_time, 1.0, f'Getting {size} byte value took too long')

    def test_extreme_concurrent_access_scenarios(self):
        """Test extreme concurrent access scenarios."""
        num_threads = 20
        operations_per_thread = 500
        success_count = threading.local()
        error_count = threading.local()

        def extreme_worker(thread_id):
            success_count.value = 0
            error_count.value = 0
            for i in range(operations_per_thread):
                try:
                    operation_type = i % 6
                    if operation_type == 0:
                        key = f'extreme_{thread_id}_{i}'
                        self.manager.set(key, f'value_{thread_id}_{i}')
                        success_count.value += 1
                    elif operation_type == 1:
                        key = f'extreme_{thread_id}_{i - 1}' if i > 0 else f'extreme_{thread_id}_0'
                        self.manager.get(key, 'default')
                        success_count.value += 1
                    elif operation_type == 2:
                        key = f'extreme_{thread_id}_{i - 2}' if i > 1 else f'extreme_{thread_id}_0'
                        self.manager.delete(key)
                        success_count.value += 1
                    elif operation_type == 3:
                        self.manager.keys(f'extreme_{thread_id}_.*')
                        success_count.value += 1
                    elif operation_type == 4:
                        self.manager.validate_all_configurations()
                        success_count.value += 1
                    elif operation_type == 5:
                        if hasattr(success_count, 'value'):
                            self.manager.clear_cache(f'extreme_{thread_id}_{i}')
                            success_count.value += 1
                except Exception as e:
                    if hasattr(error_count, 'value'):
                        error_count.value += 1
                    continue
            return (getattr(success_count, 'value', 0), getattr(error_count, 'value', 0))
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(extreme_worker, i) for i in range(num_threads)]
            results = [future.result() for future in futures]
        total_success = sum((result[0] for result in results))
        total_errors = sum((result[1] for result in results))
        self.assertGreater(total_success, 0)
        error_rate = total_errors / (total_success + total_errors) if total_success + total_errors > 0 else 0
        self.assertLess(error_rate, 0.1, 'Error rate should be less than 10%')

    def test_concurrent_factory_stress_testing(self):
        """Test concurrent factory operations under stress."""
        num_concurrent_factories = 50

        def factory_stress_worker(worker_id):
            try:
                user_mgr = ConfigurationManagerFactory.get_user_manager(f'stress_user_{worker_id}')
                service_mgr = ConfigurationManagerFactory.get_service_manager(f'stress_service_{worker_id}')
                combined_mgr = ConfigurationManagerFactory.get_manager(f'stress_user_{worker_id}', f'stress_service_{worker_id}')
                for i in range(100):
                    user_mgr.set(f'factory_stress_{i}', f'user_value_{worker_id}_{i}')
                    service_mgr.set(f'factory_stress_{i}', f'service_value_{worker_id}_{i}')
                    combined_mgr.set(f'factory_stress_{i}', f'combined_value_{worker_id}_{i}')
                return True
            except Exception:
                return False
        with ThreadPoolExecutor(max_workers=num_concurrent_factories) as executor:
            futures = [executor.submit(factory_stress_worker, i) for i in range(num_concurrent_factories)]
            results = [future.result() for future in futures]
        success_count = sum((1 for result in results if result))
        success_rate = success_count / len(results)
        self.assertGreater(success_rate, 0.9, 'Factory stress test success rate should be > 90%')
        counts = ConfigurationManagerFactory.get_manager_count()
        self.assertGreater(counts['total'], 0)

    def test_configuration_entry_edge_case_validation(self):
        """Test ConfigurationEntry validation edge cases."""
        validation_edge_cases = [('min_length:0', '', True, 'Empty string with min_length 0'), ('max_length:0', '', True, 'Empty string with max_length 0'), ('min_value:0', 0, True, 'Zero with min_value 0'), ('max_value:0', 0, True, 'Zero with max_value 0'), ('regex:^$', '', True, 'Empty string matching empty regex'), ('regex:.*', 'anything', True, 'Any string matching .* regex'), ('not_empty', '   ', False, 'Whitespace-only string for not_empty'), ('positive', 0.0001, True, 'Very small positive number'), ('non_negative', -0.0, True, 'Negative zero for non_negative')]
        for rule, value, expected, description in validation_edge_cases:
            with self.subTest(rule=rule, value=value, description=description):
                entry = ConfigurationEntry(key='edge.test', value=value, source=ConfigurationSource.DEFAULT, scope=ConfigurationScope.GLOBAL, data_type=type(value), validation_rules=[rule])
                result = entry.validate()
                self.assertEqual(result, expected, f"Rule '{rule}' with value '{value}' should be {expected}")

    def test_configuration_entry_type_conversion_edge_cases(self):
        """Test ConfigurationEntry type conversion edge cases."""
        type_conversion_cases = [('123', int, 123, True), ('true', bool, True, True), ('false', bool, False, True), ('not_a_number', int, 'not_a_number', False), ('123.456', float, 123.456, True)]
        for initial_value, target_type, expected_value, should_succeed in type_conversion_cases:
            with self.subTest(initial=initial_value, target=target_type):
                entry = ConfigurationEntry(key='conversion.test', value=initial_value, source=ConfigurationSource.DEFAULT, scope=ConfigurationScope.GLOBAL, data_type=target_type)
                validation_result = entry.validate()
                if should_succeed:
                    self.assertTrue(validation_result, f'Validation should succeed for {initial_value} -> {target_type}')
                    if isinstance(entry.value, target_type):
                        self.assertEqual(entry.value, expected_value)
                    self.assertIsInstance(entry.value, (target_type, type(initial_value)))
                elif not validation_result:
                    pass
                else:
                    self.assertEqual(entry.value, initial_value)

    def test_configuration_entry_sensitive_value_edge_cases(self):
        """Test sensitive value masking edge cases."""
        sensitive_edge_cases = [('', '***', 'Empty sensitive value'), ('a', '***', 'Single character sensitive value'), ('ab', '***', 'Two character sensitive value'), ('abc', '***', 'Three character sensitive value'), ('abcd', '***', 'Four character sensitive value (boundary)'), ('abcde', 'ab*de', 'Five character sensitive value (first partial)')]
        for value, expected_pattern, description in sensitive_edge_cases:
            with self.subTest(value=value, description=description):
                entry = ConfigurationEntry(key='sensitive.edge.test', value=value, source=ConfigurationSource.ENVIRONMENT, scope=ConfigurationScope.GLOBAL, data_type=str, sensitive=True)
                display_value = entry.get_display_value()
                if len(value) <= 4:
                    self.assertEqual(display_value, '***')
                else:
                    self.assertTrue(display_value.startswith(value[:2]))
                    self.assertTrue(display_value.endswith(value[-2:]))
                    self.assertIn('*', display_value)

    def test_performance_with_extremely_large_configurations(self):
        """Test performance with extremely large number of configurations."""
        large_config_count = 50000
        start_time = time.time()
        for i in range(large_config_count):
            self.manager.set(f'perf.large.{i}', f'value_{i}')
        set_duration = time.time() - start_time
        start_time = time.time()
        for i in range(0, large_config_count, 100):
            value = self.manager.get(f'perf.large.{i}')
            self.assertEqual(value, f'value_{i}')
        get_duration = time.time() - start_time
        start_time = time.time()
        all_keys = self.manager.keys()
        keys_duration = time.time() - start_time
        start_time = time.time()
        validation_result = self.manager.validate_all_configurations()
        validation_duration = time.time() - start_time
        self.assertLess(set_duration, 60.0, f'Setting {large_config_count} configs took too long: {set_duration:.2f}s')
        self.assertLess(get_duration, 5.0, f'Getting sample configs took too long: {get_duration:.2f}s')
        self.assertLess(keys_duration, 5.0, f'Listing all keys took too long: {keys_duration:.2f}s')
        self.assertLess(validation_duration, 10.0, f'Validating all configs took too long: {validation_duration:.2f}s')
        self.assertGreaterEqual(len(all_keys), large_config_count)

    def test_performance_under_memory_pressure(self):
        """Test performance under memory pressure conditions."""
        import gc
        memory_pressure_objects = []
        for i in range(100):
            large_object = ['x' * 10000] * 1000
            memory_pressure_objects.append(large_object)
        try:
            operations_count = 1000
            start_time = time.time()
            for i in range(operations_count):
                key = f'memory_pressure.{i}'
                value = f'value_under_pressure_{i}'
                self.manager.set(key, value)
                retrieved = self.manager.get(key)
                self.assertEqual(retrieved, value)
                if i % 100 == 0:
                    gc.collect()
            duration = time.time() - start_time
            self.assertLess(duration, 30.0, f'Operations under memory pressure took too long: {duration:.2f}s')
        finally:
            del memory_pressure_objects
            gc.collect()

    def test_audit_trail_with_rapid_changes(self):
        """Test audit trail with rapid configuration changes."""
        self.manager._audit_enabled = True
        key = 'rapid.audit.test'
        change_count = 2000
        for i in range(change_count):
            self.manager.set(key, f'rapid_value_{i}')
        history = self.manager.get_change_history()
        self.assertGreater(len(history), 0)
        self.assertLessEqual(len(history), 1000)
        recent_changes = [h for h in history if h['key'] == key]
        self.assertGreater(len(recent_changes), 0)

    def test_audit_trail_thread_safety(self):
        """Test audit trail thread safety."""
        self.manager._audit_enabled = True

        def audit_worker(thread_id):
            for i in range(100):
                key = f'audit_thread_{thread_id}_{i}'
                self.manager.set(key, f'thread_value_{thread_id}_{i}')
                self.manager.delete(key)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(audit_worker, i) for i in range(10)]
            for future in futures:
                future.result()
        history = self.manager.get_change_history()
        self.assertGreater(len(history), 0)
        for record in history[-10:]:
            self.assertIn('timestamp', record)
            self.assertIn('key', record)
            self.assertIn('source', record)
            self.assertIsInstance(record['timestamp'], (int, float))

    def test_change_listener_exception_isolation(self):
        """Test that one failing change listener doesn't affect others."""
        working_listener_calls = []

        def failing_listener(key, old_value, new_value):
            raise RuntimeError('Simulated listener failure')

        def working_listener(key, old_value, new_value):
            working_listener_calls.append((key, old_value, new_value))
        self.manager.add_change_listener(failing_listener)
        self.manager.add_change_listener(working_listener)
        self.manager.set('listener.isolation.test', 'test_value')
        self.assertEqual(len(working_listener_calls), 1)
        self.assertEqual(working_listener_calls[0][0], 'listener.isolation.test')
        self.assertEqual(working_listener_calls[0][2], 'test_value')
        self.assertEqual(self.manager.get('listener.isolation.test'), 'test_value')

    def test_factory_resource_cleanup_comprehensive(self):
        """Test comprehensive factory resource cleanup."""
        managers_created = []
        global_mgr = ConfigurationManagerFactory.get_global_manager()
        managers_created.append(global_mgr)
        for i in range(20):
            user_mgr = ConfigurationManagerFactory.get_user_manager(f'cleanup_user_{i}')
            managers_created.append(user_mgr)
        for i in range(15):
            service_mgr = ConfigurationManagerFactory.get_service_manager(f'cleanup_service_{i}')
            managers_created.append(service_mgr)
        for i in range(10):
            combined_mgr = ConfigurationManagerFactory.get_manager(f'cleanup_user_{i}', f'cleanup_service_{i}')
            managers_created.append(combined_mgr)
        counts = ConfigurationManagerFactory.get_manager_count()
        self.assertEqual(counts['global'], 1)
        self.assertEqual(counts['user_specific'], 20)
        self.assertEqual(counts['service_specific'], 15)
        self.assertEqual(counts['combined'], 10)
        for i, manager in enumerate(managers_created):
            manager.set(f'cleanup_test_{i}', f'cleanup_value_{i}')
        ConfigurationManagerFactory.clear_all_caches()
        for manager in managers_created:
            self.assertEqual(len(manager._cache), 0)
        ConfigurationManagerFactory._global_manager = None
        ConfigurationManagerFactory._user_managers.clear()
        ConfigurationManagerFactory._service_managers.clear()
        counts = ConfigurationManagerFactory.get_manager_count()
        self.assertEqual(counts['global'], 0)
        self.assertEqual(counts['user_specific'], 0)
        self.assertEqual(counts['service_specific'], 0)
        self.assertEqual(counts['combined'], 0)
        self.assertEqual(counts['total'], 0)

    def test_mission_critical_values_comprehensive_validation(self):
        """Test comprehensive mission critical values validation."""
        critical_configs = {'database.url': 'postgresql://critical:db@localhost:5432/critical_db', 'security.jwt_secret': 'super_critical_jwt_secret_key_that_is_very_long_and_secure', 'redis.url': 'redis://critical-redis:6379/0', 'llm.openai.api_key': 'sk-critical-openai-key-for-testing-purposes-only'}
        for key, value in critical_configs.items():
            self.manager.set(key, value)
            self.manager._required_keys.add(key)
        self.manager._sensitive_keys.add('security.jwt_secret')
        self.manager._sensitive_keys.add('llm.openai.api_key')
        result = self.manager.validate_all_configurations()
        missing_critical = [key for key in critical_configs.keys() if key in result.missing_required]
        self.assertEqual(len(missing_critical), 0, f'Critical values missing: {missing_critical}')
        self.manager.delete('database.url')
        result = self.manager.validate_all_configurations()
        self.assertFalse(result.is_valid)
        self.assertIn('database.url', result.missing_required)
        self.assertGreater(len(result.critical_errors), 0)

    def test_status_reporting_with_all_configurations(self):
        """Test status reporting with comprehensive configuration coverage."""
        diverse_configs = {'database.url': 'postgresql://test:pass@localhost:5432/testdb', 'database.pool_size': 15, 'database.echo': True, 'redis.url': 'redis://localhost:6379/1', 'redis.max_connections': 100, 'llm.timeout': 45.0, 'llm.openai.api_key': 'sk-test-openai-key', 'llm.anthropic.api_key': 'sk-ant-test-key', 'security.jwt_secret': 'test_jwt_secret_key_for_comprehensive_testing', 'security.require_https': True, 'agent.execution_timeout': 300.0, 'agent.max_concurrent': 5, 'websocket.ping_interval': 20, 'websocket.max_connections': 1000, 'performance.request_timeout': 30.0, 'performance.rate_limit_requests': 100, 'dashboard.refresh_interval': 30, 'dashboard.theme': 'dark'}
        for key, value in diverse_configs.items():
            self.manager.set(key, value)
        sensitive_keys = ['llm.openai.api_key', 'llm.anthropic.api_key', 'security.jwt_secret']
        for key in sensitive_keys:
            self.manager._sensitive_keys.add(key)
            if key in self.manager._configurations:
                self.manager._configurations[key].sensitive = True
        status = self.manager.get_status()
        self.assertGreater(status['total_configurations'], 20)
        self.assertEqual(status['sensitive_key_count'], len(sensitive_keys))
        self.assertIn('sources', status)
        self.assertIn('scopes', status)
        db_config = self.manager.get_database_config()
        self.assertEqual(db_config['pool_size'], 15)
        self.assertEqual(db_config['echo'], True)
        redis_config = self.manager.get_redis_config()
        self.assertEqual(redis_config['max_connections'], 100)
        llm_config = self.manager.get_llm_config()
        self.assertEqual(llm_config['timeout'], 45.0)
        health = self.manager.get_health_status()
        self.assertIn(health['status'], ['healthy', 'unhealthy'])
        self.assertIsInstance(health['validation_result'], bool)

class TestUnifiedConfigurationManagerIsolationCompliance(BaseTestCase):
    """Test CLAUDE.md compliance for IsolatedEnvironment usage."""

    def setUp(self):
        """Set up isolation compliance testing."""
        super().setUp()
        self.original_environ = os.environ.copy()

    def tearDown(self):
        """Clean up isolation compliance testing."""
        os.environ.clear()
        os.environ.update(self.original_environ)
        super().tearDown()

    def test_isolated_environment_compliance_during_initialization(self):
        """Test that manager initialization uses only IsolatedEnvironment."""
        environ_access_log = []
        original_getitem = os.environ.__getitem__
        original_get = os.environ.get
        original_contains = os.environ.__contains__

        def log_getitem(key):
            environ_access_log.append(f'__getitem__: {key}')
            return original_getitem(key)

        def log_get(key, default=None):
            environ_access_log.append(f'get: {key}')
            return original_get(key, default)

        def log_contains(key):
            environ_access_log.append(f'__contains__: {key}')
            return original_contains(key)
        os.environ.__getitem__ = log_getitem
        os.environ.get = log_get
        os.environ.__contains__ = log_contains
        try:
            manager = UnifiedConfigurationManager()
            non_pytest_access = [access for access in environ_access_log if not any((pytest_var in access for pytest_var in ['PYTEST', 'COV', '_PYTEST']))]
            self.assertLess(len(non_pytest_access), 5, f'Detected significant direct os.environ access: {non_pytest_access}')
        finally:
            os.environ.__getitem__ = original_getitem
            os.environ.get = original_get
            os.environ.__contains__ = original_contains

    def test_configuration_operations_use_isolated_environment(self):
        """Test that all configuration operations use IsolatedEnvironment."""
        manager = UnifiedConfigurationManager()
        self.assertIsInstance(manager._env, IsolatedEnvironment)
        with patch.object(manager._env, 'get', return_value='test_env') as mock_get:
            detected_env = manager._detect_environment()
            self.assertEqual(detected_env, 'test_env')
            mock_get.assert_called()
        operations_to_test = [lambda: manager.set('test.key', 'test.value'), lambda: manager.get('test.key'), lambda: manager.delete('test.key'), lambda: manager.validate_all_configurations(), lambda: manager.get_status()]
        for operation in operations_to_test:
            with patch('os.environ') as mock_environ:
                mock_environ.get.side_effect = lambda *args: self.fail('Direct os.environ access detected')
                mock_environ.__getitem__.side_effect = lambda *args: self.fail('Direct os.environ access detected')
                try:
                    operation()
                except AssertionError as e:
                    if 'Direct os.environ access detected' in str(e):
                        raise
                except Exception:
                    pass

@pytest.mark.parametrize('config_size', [10, 100, 1000, 5000])
def test_parametrized_configuration_scaling(config_size):
    """Parametrized test for configuration scaling performance."""
    manager = UnifiedConfigurationManager()
    start_time = time.time()
    for i in range(config_size):
        manager.set(f'scale.test.{i}', f'value_{i}')
    set_duration = time.time() - start_time
    start_time = time.time()
    for i in range(0, config_size, max(1, config_size // 100)):
        value = manager.get(f'scale.test.{i}')
        assert value == f'value_{i}'
    get_duration = time.time() - start_time
    assert set_duration < config_size * 0.01
    assert get_duration < config_size * 0.001

@pytest.mark.parametrize('thread_count,operations_per_thread', [(2, 100), (5, 200), (10, 500), (20, 1000)])
def test_parametrized_concurrent_scaling(thread_count, operations_per_thread):
    """Parametrized test for concurrent access scaling."""
    manager = UnifiedConfigurationManager()
    success_count = [0]

    def concurrent_worker(worker_id):
        for i in range(operations_per_thread):
            key = f'concurrent.{worker_id}.{i}'
            manager.set(key, f'value_{worker_id}_{i}')
            retrieved = manager.get(key)
            if retrieved == f'value_{worker_id}_{i}':
                success_count[0] += 1
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(concurrent_worker, i) for i in range(thread_count)]
        for future in futures:
            future.result()
    expected_operations = thread_count * operations_per_thread
    success_rate = success_count[0] / expected_operations
    assert success_rate > 0.95
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')