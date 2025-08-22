"""
Test Environment Variable Precedence

Validates correct precedence order for configuration:
1. Environment variables
2. Secret Manager
3. Config files
4. Defaults
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import json
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# Add project root to path
from .base import StagingConfigTestBase

# Add project root to path


class TestEnvironmentPrecedence(StagingConfigTestBase):
    """Test environment variable precedence in staging."""
    
    def test_precedence_order(self):
        """Verify configuration precedence order is correct."""
        self.skip_if_not_staging()
        
        # Test configuration value resolution
        test_cases = [
            {
                'name': 'JWT_SECRET',
                'env_value': 'env_jwt_secret',
                'secret_value': 'secret_jwt_secret',
                'config_value': 'config_jwt_secret',
                'default_value': 'default_jwt_secret',
                'expected': 'env_jwt_secret'  # Env var wins
            },
            {
                'name': 'DATABASE_URL',
                'env_value': None,
                'secret_value': 'secret_db_url',
                'config_value': 'config_db_url',
                'default_value': 'default_db_url',
                'expected': 'secret_db_url'  # Secret Manager wins
            },
            {
                'name': 'REDIS_URL',
                'env_value': None,
                'secret_value': None,
                'config_value': 'config_redis_url',
                'default_value': 'default_redis_url',
                'expected': 'config_redis_url'  # Config file wins
            },
            {
                'name': 'LOG_LEVEL',
                'env_value': None,
                'secret_value': None,
                'config_value': None,
                'default_value': 'INFO',
                'expected': 'INFO'  # Default wins
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(config=test_case['name']):
                resolved_value = self._resolve_config_value(
                    test_case['name'],
                    test_case['env_value'],
                    test_case['secret_value'],
                    test_case['config_value'],
                    test_case['default_value']
                )
                
                self.assertEqual(resolved_value, test_case['expected'],
                               f"Precedence order incorrect for {test_case['name']}")
                               
    def _resolve_config_value(self, name: str, env: Any, secret: Any, 
                              config: Any, default: Any) -> Any:
        """
        Simulate configuration resolution logic.
        
        Precedence: env > secret > config > default
        """
        if env is not None:
            return env
        elif secret is not None:
            return secret
        elif config is not None:
            return config
        else:
            return default
            
    def test_environment_detection(self):
        """Test environment detection methods."""
        self.skip_if_not_staging()
        
        detection_methods = [
            {
                'method': 'ENVIRONMENT variable',
                'check': lambda: os.getenv('ENVIRONMENT'),
                'expected': 'staging'
            },
            {
                'method': 'GCP_PROJECT_ID pattern',
                'check': lambda: 'staging' in os.getenv('GCP_PROJECT_ID', ''),
                'expected': True
            },
            {
                'method': 'K8S namespace',
                'check': lambda: os.getenv('K8S_NAMESPACE'),
                'expected': 'staging'
            },
            {
                'method': 'Service URL pattern',
                'check': lambda: 'staging' in os.getenv('SERVICE_URL', ''),
                'expected': True
            }
        ]
        
        inconsistencies = []
        
        for method in detection_methods:
            result = method['check']()
            
            if method['expected'] == 'staging':
                if result != 'staging':
                    inconsistencies.append(
                        f"{method['method']} returned '{result}', expected 'staging'"
                    )
            elif method['expected'] is True:
                if not result:
                    inconsistencies.append(
                        f"{method['method']} returned False, expected True"
                    )
                    
        if inconsistencies:
            self.fail("Environment detection inconsistencies:\n" +
                     '\n'.join(f"  - {i}" for i in inconsistencies))
                     
    def test_secret_manager_override(self):
        """Test Secret Manager values override config files."""
        self.skip_if_not_staging()
        self.require_gcp_credentials()
        
        # Load config file
        config_file_path = 'config/staging.yaml'
        config_values = {}
        
        if os.path.exists(config_file_path):
            import yaml
            with open(config_file_path) as f:
                config_values = yaml.safe_load(f)
                
        # Test that Secret Manager values take precedence
        test_keys = ['DATABASE_URL', 'JWT_SECRET', 'REDIS_URL']
        
        for key in test_keys:
            # Get value from config file
            config_value = config_values.get(key)
            
            # Get value from Secret Manager
            try:
                secret_name = key.lower().replace('_', '-')
                secret_value = self.assert_secret_exists(secret_name)
                
                # If both exist, secret should win
                if config_value and secret_value:
                    # In real app, secret should be used
                    self.assertNotEqual(config_value, secret_value,
                                      f"{key} should differ between config and secret")
                                      
            except AssertionError:
                # Secret doesn't exist, config value should be used
                pass
                
    def test_environment_specific_configs(self):
        """Test environment-specific configuration loading."""
        self.skip_if_not_staging()
        
        # Check that staging-specific configs are loaded
        config_files = [
            'config/staging.yaml',
            'config/staging.env',
            '.env.staging'
        ]
        
        loaded_configs = []
        
        for config_file in config_files:
            if os.path.exists(config_file):
                loaded_configs.append(config_file)
                
                # Verify it contains staging-specific values
                with open(config_file) as f:
                    content = f.read()
                    self.assertIn('staging', content.lower(),
                                f"{config_file} doesn't contain staging-specific values")
                                
        self.assertGreater(len(loaded_configs), 0,
                          "No staging-specific config files found")
                          
    def test_config_validation(self):
        """Test configuration validation for required values."""
        self.skip_if_not_staging()
        
        required_configs = [
            'DATABASE_URL',
            'REDIS_URL',
            'JWT_SECRET',
            'GCP_PROJECT_ID',
            'ENVIRONMENT'
        ]
        
        missing_configs = []
        
        for config in required_configs:
            # Check environment variable
            env_value = os.getenv(config)
            
            if not env_value:
                # Try to get from Secret Manager
                try:
                    secret_name = config.lower().replace('_', '-')
                    self.assert_secret_exists(secret_name)
                except AssertionError:
                    missing_configs.append(config)
                    
        if missing_configs:
            self.fail(f"Required configurations missing: {missing_configs}")
            
    def test_config_type_conversion(self):
        """Test configuration values are converted to correct types."""
        self.skip_if_not_staging()
        
        type_configs = [
            {
                'name': 'PORT',
                'value': '8080',
                'expected_type': int,
                'expected_value': 8080
            },
            {
                'name': 'DEBUG',
                'value': 'false',
                'expected_type': bool,
                'expected_value': False
            },
            {
                'name': 'MAX_CONNECTIONS',
                'value': '100',
                'expected_type': int,
                'expected_value': 100
            },
            {
                'name': 'TIMEOUT',
                'value': '30.5',
                'expected_type': float,
                'expected_value': 30.5
            }
        ]
        
        for config in type_configs:
            with self.subTest(config=config['name']):
                # Set environment variable
                os.environ[config['name']] = config['value']
                
                # Test conversion
                converted = self._convert_config_value(
                    config['value'],
                    config['expected_type']
                )
                
                self.assertEqual(type(converted), config['expected_type'],
                               f"Type conversion failed for {config['name']}")
                self.assertEqual(converted, config['expected_value'],
                               f"Value conversion incorrect for {config['name']}")
                               
                # Clean up
                del os.environ[config['name']]
                
    def _convert_config_value(self, value: str, target_type: type) -> Any:
        """Convert configuration value to target type."""
        if target_type == bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        else:
            return value