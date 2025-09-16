"""
Unit Test for KeyError Reproduction in JSON Formatter

CRITICAL ISSUE REPRODUCTION:
This test reproduces the `KeyError: '"timestamp"'` issue in Loguru's format processing.

ROOT CAUSE:
The `_get_json_formatter()` method in `shared/logging/unified_logging_ssot.py` returns
a JSON string from line 472: `return json.dumps(log_entry, separators=(',', ':'))`

When Loguru receives this JSON string as a format string, it tries to interpret
it as a Loguru format pattern and looks for field names like "{timestamp}".
Since the JSON contains `"timestamp":"value"`, Loguru treats `"timestamp"` as
a format field and raises `KeyError: '"timestamp"'` when it can't find it.

BUSINESS IMPACT:
This blocks Cloud Run JSON logging which is critical for GCP Error Reporting
and $500K+ ARR Golden Path monitoring.

TEST APPROACH:
- Mock Cloud Run environment conditions to trigger JSON logging
- Call the _get_json_formatter() method directly
- Pass the formatter to Loguru's logger.add() method
- Trigger a log message to reproduce the KeyError
- Expect test to FAIL with KeyError: '"timestamp"'
"""
import json
import sys
from contextlib import redirect_stderr
from io import StringIO
from unittest.mock import MagicMock, patch
import pytest
from loguru import logger
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.logging.unified_logging_ssot import UnifiedLoggingSSOT, get_ssot_logger

class TestJsonFormatterKeyErrorReproduction(SSotBaseTestCase):
    """
    Unit test to reproduce the KeyError issue in JSON formatter.
    
    This test should FAIL with `KeyError: '"timestamp"'` to prove
    the issue is reproduced correctly.
    """

    def setUp(self):
        """Set up test environment with Cloud Run conditions."""
        super().setUp()
        from shared.logging import unified_logging_ssot
        unified_logging_ssot._ssot_logger_instance = None
        self.env_patcher = patch.object(IsolatedEnvironment, 'get_instance')
        self.mock_env = self.env_patcher.start()
        env_instance = MagicMock()
        env_instance.get.side_effect = lambda key, default=None: {'K_SERVICE': 'test-service', 'ENVIRONMENT': 'staging', 'TESTING': None, 'NETRA_SECRETS_LOADING': None, 'SERVICE_NAME': 'test-service', 'LOG_LEVEL': 'INFO'}.get(key, default)
        self.mock_env.return_value = env_instance
        logger.remove()

    def tearDown(self):
        """Clean up test environment."""
        super().tearDown()
        self.env_patcher.stop()
        try:
            logger.remove()
        except ValueError:
            pass

    def test_json_formatter_keyerror_reproduction(self):
        """
        CRITICAL TEST: Reproduce KeyError in JSON formatter.
        
        This test should FAIL with `KeyError: '"timestamp"'` when the 
        JSON formatter output is used as a Loguru format string.
        
        Expected failure demonstrates the root cause of issue #252.
        """
        ssot_logger = UnifiedLoggingSSOT()
        ssot_logger._config = {'log_level': 'INFO', 'enable_file_logging': False, 'enable_json_logging': True, 'log_file_path': 'logs/test.log'}
        ssot_logger._setup_complete = False
        json_formatter = ssot_logger._get_json_formatter()
        mock_record = {'level': MagicMock(name='INFO'), 'message': 'Test message', 'name': 'test_logger', 'exception': None, 'extra': {}}
        mock_record['level'].name = 'INFO'
        format_string = json_formatter(mock_record)
        parsed_json = json.loads(format_string)
        self.assertIn('timestamp', parsed_json)
        self.assertIn('severity', parsed_json)
        self.assertIn('message', parsed_json)
        keyerror_caught = []
        original_emit = None
        logger.remove()
        try:
            logger.add(sys.stdout, format=format_string, level='INFO')
            handlers = logger._core.handlers
            if handlers:
                handler_id = list(handlers.keys())[0]
                handler = handlers[handler_id]
                original_emit = handler._handler.emit

                def patched_emit(record):
                    try:
                        return original_emit(record)
                    except KeyError as e:
                        keyerror_caught.append(e)
                        raise
                handler._handler.emit = patched_emit
            logger.info('This should trigger the KeyError')
            if keyerror_caught:
                error = keyerror_caught[0]
                error_message = str(error)
                print(f'\n=== KEYERROR REPRODUCTION SUCCESSFUL ===')
                print(f'Error: {error}')
                print(f'Format string that caused error: {format_string[:100]}...')
                print(f'This proves the JSON formatter returns JSON strings')
                print(f'that Loguru incorrectly interprets as format strings.')
                print(f'=== END REPRODUCTION ===\n')
                self.assertIn('timestamp', error_message.lower())
                raise error
            else:
                self.fail('Expected KeyError: \'"timestamp"\' was not raised. The bug reproduction failed - JSON formatter issue may be fixed.')
        except KeyError as e:
            error_message = str(e)
            if 'timestamp' not in error_message.lower():
                self.fail(f'Got KeyError but not timestamp-related: {e}')
            print(f'\n=== KEYERROR REPRODUCTION SUCCESSFUL ===')
            print(f'Error: {e}')
            print(f'Format string that caused error: {format_string[:100]}...')
            print(f'This proves the JSON formatter returns JSON strings')
            print(f'that Loguru incorrectly interprets as format strings.')
            print(f'=== END REPRODUCTION ===\n')
            raise
        except Exception as e:
            self.fail(f"""Expected KeyError: '"timestamp"' but got {type(e).__name__}: {e}""")
        finally:
            if original_emit and handlers:
                handler_id = list(handlers.keys())[0]
                handler = handlers[handler_id]
                handler._handler.emit = original_emit

    def test_json_formatter_direct_call(self):
        """
        Test the JSON formatter method directly to show it returns JSON strings.
        
        This test demonstrates that _get_json_formatter() returns a function
        that produces JSON strings, not Loguru format strings.
        """
        ssot_logger = UnifiedLoggingSSOT()
        json_formatter = ssot_logger._get_json_formatter()
        mock_record = {'level': MagicMock(name='INFO'), 'message': 'Test log message', 'name': 'test.module', 'exception': None, 'extra': {'custom_field': 'custom_value'}}
        mock_record['level'].name = 'INFO'
        result = json_formatter(mock_record)
        parsed = json.loads(result)
        self.assertIn('timestamp', parsed)
        self.assertIn('severity', parsed)
        self.assertIn('service', parsed)
        self.assertIn('logger', parsed)
        self.assertIn('message', parsed)
        self.assertEqual(parsed['severity'], 'INFO')
        self.assertEqual(parsed['message'], 'Test log message')
        self.assertEqual(parsed['logger'], 'test.module')
        print(f'\n=== JSON FORMATTER OUTPUT ===')
        print(f'Result: {result}')
        print(f"""This JSON string contains '"timestamp"' which Loguru""")
        print(f'interprets as a format field, causing KeyError.')
        print(f'=== END OUTPUT ===\n')

    def test_cloud_run_environment_detection(self):
        """
        Test that Cloud Run environment properly triggers JSON logging.
        
        This verifies the conditions that lead to the problematic JSON formatter.
        """
        ssot_logger = UnifiedLoggingSSOT()
        should_use_json = ssot_logger._should_use_json_logging()
        self.assertTrue(should_use_json, 'Should use JSON logging in Cloud Run environment')
        config = ssot_logger._load_config()
        self.assertTrue(config['enable_json_logging'], 'JSON logging should be enabled')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')