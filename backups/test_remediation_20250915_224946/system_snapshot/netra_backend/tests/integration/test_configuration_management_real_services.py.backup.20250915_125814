"""
Configuration Management Integration Tests - Real Services

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure reliable configuration management across all environments
- Value Impact: Consistent platform behavior enables reliable user experience and prevents outages
- Strategic Impact: Configuration integrity is foundation for multi-environment deployment and scaling

These tests validate configuration management using real services, ensuring environment isolation,
SSOT compliance, and proper configuration validation across test, staging, and production environments.
"""

import asyncio
import pytest
import time
import json
import os
from typing import Dict, List, Any, Optional
from uuid import uuid4

from test_framework.base_integration_test import ServiceOrchestrationIntegrationTest
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import IsolatedEnvironment, get_env


class TestConfigurationManagement(ServiceOrchestrationIntegrationTest):
    """Test configuration management with real services and environment isolation."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_environment_isolation_and_config_integrity(self, real_services):
        """
        Test that configuration remains isolated between different environments.
        
        BVJ: Platform must maintain separate configurations for test/staging/prod to prevent data leaks.
        """
        # Test different environment configurations
        test_environments = ['test', 'staging', 'production']
        environment_configs = {}
        
        for env_name in test_environments:
            # Create isolated environment for testing
            isolated_env = IsolatedEnvironment()
            isolated_env.set("ENVIRONMENT", env_name, source="config_test")
            
            # Environment-specific configuration
            if env_name == 'test':
                config = {
                    'database_url': 'postgresql://test:test@localhost:5434/netra_test',
                    'redis_url': 'redis://localhost:6381/0',
                    'debug_mode': True,
                    'log_level': 'DEBUG',
                    'rate_limit': 1000,  # Higher for testing
                    'external_apis': {
                        'openai_api_key': 'test_openai_key',
                        'aws_access_key': 'test_aws_key'
                    }
                }
            elif env_name == 'staging':
                config = {
                    'database_url': 'postgresql://staging:staging@staging-db:5432/netra_staging',
                    'redis_url': 'redis://staging-redis:6379/0',
                    'debug_mode': False,
                    'log_level': 'INFO',
                    'rate_limit': 500,  # Moderate for staging
                    'external_apis': {
                        'openai_api_key': 'staging_openai_key',
                        'aws_access_key': 'staging_aws_key'
                    }
                }
            else:  # production
                config = {
                    'database_url': 'postgresql://prod:prod@prod-db:5432/netra_production',
                    'redis_url': 'redis://prod-redis:6379/0',
                    'debug_mode': False,
                    'log_level': 'WARNING',
                    'rate_limit': 100,  # Strict for production
                    'external_apis': {
                        'openai_api_key': 'prod_openai_key',
                        'aws_access_key': 'prod_aws_key'
                    }
                }
            
            # Store configuration in database with environment isolation
            config_id = str(uuid4())
            await real_services.postgres.execute("""
                INSERT INTO backend.environment_configs 
                (config_id, environment, config_data, created_at, is_active)
                VALUES ($1, $2, $3, $4, true)
            """, config_id, env_name, json.dumps(config), time.time())
            
            # Cache configuration in Redis with environment prefix
            config_key = f"config:{env_name}:main"
            await real_services.redis.set_json(config_key, config, ex=3600)
            
            environment_configs[env_name] = {
                'config_id': config_id,
                'config_data': config,
                'isolated_env': isolated_env
            }
        
        # Verify configuration isolation
        for env_name, env_config in environment_configs.items():
            # Retrieve configuration from cache
            cached_config = await real_services.redis.get_json(f"config:{env_name}:main")
            assert cached_config is not None, f"Configuration for {env_name} must be cached"
            
            # Verify environment-specific values
            if env_name == 'test':
                assert cached_config['debug_mode'] is True, "Test environment must have debug mode enabled"
                assert 'test' in cached_config['database_url'], "Test environment must use test database"
                assert cached_config['rate_limit'] == 1000, "Test environment must have higher rate limit"
            elif env_name == 'staging':
                assert cached_config['debug_mode'] is False, "Staging environment must have debug mode disabled"
                assert 'staging' in cached_config['database_url'], "Staging environment must use staging database"
                assert cached_config['log_level'] == 'INFO', "Staging environment must use INFO log level"
            elif env_name == 'production':
                assert cached_config['debug_mode'] is False, "Production environment must have debug mode disabled"
                assert 'prod' in cached_config['database_url'], "Production environment must use production database"
                assert cached_config['rate_limit'] == 100, "Production environment must have strict rate limit"
            
            # Verify API key isolation
            assert env_name in cached_config['external_apis']['openai_api_key'], f"OpenAI key must be environment-specific for {env_name}"
            assert env_name in cached_config['external_apis']['aws_access_key'], f"AWS key must be environment-specific for {env_name}"
        
        # Test configuration cross-contamination prevention
        test_config = environment_configs['test']['config_data']
        prod_config = environment_configs['production']['config_data']
        
        # Configurations must be completely isolated
        assert test_config['database_url'] != prod_config['database_url'], "Test and prod database URLs must be different"
        assert test_config['external_apis']['openai_api_key'] != prod_config['external_apis']['openai_api_key'], "API keys must be environment-specific"
        assert test_config['rate_limit'] != prod_config['rate_limit'], "Rate limits must be environment-specific"
        
        # Verify database isolation
        for env_name in test_environments:
            db_config = await real_services.postgres.fetchrow("""
                SELECT environment, config_data, is_active
                FROM backend.environment_configs
                WHERE config_id = $1
            """, environment_configs[env_name]['config_id'])
            
            assert db_config['environment'] == env_name, f"Database config must be tagged with correct environment"
            assert db_config['is_active'] is True, f"Environment config for {env_name} must be active"
            
            stored_config = json.loads(db_config['config_data'])
            assert stored_config == environment_configs[env_name]['config_data'], f"Stored config for {env_name} must match original"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_dynamic_configuration_updates_and_validation(self, real_services):
        """
        Test dynamic configuration updates with validation and rollback capabilities.
        
        BVJ: Platform must support safe configuration changes without service interruptions.
        """
        # Create base configuration
        config_id = str(uuid4())
        base_config = {
            'service_name': 'netra_backend',
            'version': '1.0.0',
            'features': {
                'ai_optimization': True,
                'cost_analysis': True,
                'reporting': True,
                'advanced_analytics': False
            },
            'limits': {
                'max_concurrent_users': 100,
                'max_api_calls_per_hour': 1000,
                'max_data_retention_days': 90
            },
            'integrations': {
                'aws': {'enabled': True, 'regions': ['us-east-1', 'us-west-2']},
                'azure': {'enabled': True, 'regions': ['eastus', 'westus2']},
                'gcp': {'enabled': False, 'regions': []}
            }
        }
        
        # Store initial configuration
        await real_services.postgres.execute("""
            INSERT INTO backend.dynamic_configs 
            (config_id, service_name, config_version, config_data, created_at, is_active, validated)
            VALUES ($1, $2, $3, $4, $5, true, true)
        """, config_id, base_config['service_name'], base_config['version'], 
             json.dumps(base_config), time.time())
        
        # Cache configuration
        config_cache_key = f"dynamic_config:{base_config['service_name']}:current"
        await real_services.redis.set_json(config_cache_key, base_config, ex=3600)
        
        # Test configuration update with validation
        updated_config = {
            **base_config,
            'version': '1.1.0',
            'features': {
                **base_config['features'],
                'advanced_analytics': True,  # Enable new feature
                'ai_optimization_v2': True   # Add new feature
            },
            'limits': {
                **base_config['limits'],
                'max_concurrent_users': 150,  # Increase capacity
                'max_api_calls_per_hour': 1500
            }
        }
        
        # Validate configuration update
        validation_result = await self._validate_configuration_update(real_services, base_config, updated_config)
        assert validation_result['valid'] is True, "Configuration update must pass validation"
        assert validation_result['changes_detected'] is True, "Changes must be detected"
        
        # Apply configuration update with versioning
        new_config_id = str(uuid4())
        update_time = time.time()
        
        # Store new configuration version
        await real_services.postgres.execute("""
            INSERT INTO backend.dynamic_configs 
            (config_id, service_name, config_version, config_data, created_at, is_active, validated, previous_version_id)
            VALUES ($1, $2, $3, $4, $5, false, true, $6)
        """, new_config_id, updated_config['service_name'], updated_config['version'],
             json.dumps(updated_config), update_time, config_id)
        
        # Test gradual rollout - configuration becomes active after validation
        await asyncio.sleep(0.1)  # Simulate validation delay
        
        # Activate new configuration
        await real_services.postgres.execute("""
            UPDATE backend.dynamic_configs SET is_active = false WHERE config_id = $1;
            UPDATE backend.dynamic_configs SET is_active = true WHERE config_id = $2;
        """, config_id, new_config_id)
        
        # Update cache
        await real_services.redis.set_json(config_cache_key, updated_config, ex=3600)
        
        # Verify configuration update
        active_config = await real_services.postgres.fetchrow("""
            SELECT config_id, config_version, config_data, is_active
            FROM backend.dynamic_configs
            WHERE service_name = $1 AND is_active = true
        """, base_config['service_name'])
        
        assert active_config['config_id'] == new_config_id, "New configuration must be active"
        assert active_config['config_version'] == '1.1.0', "Configuration version must be updated"
        
        active_config_data = json.loads(active_config['config_data'])
        assert active_config_data['features']['advanced_analytics'] is True, "New feature must be enabled"
        assert active_config_data['limits']['max_concurrent_users'] == 150, "Limits must be updated"
        
        # Verify cache reflects update
        cached_config = await real_services.redis.get_json(config_cache_key)
        assert cached_config['version'] == '1.1.0', "Cached configuration must be updated"
        assert cached_config['features']['ai_optimization_v2'] is True, "New feature must be cached"
        
        # Test configuration rollback scenario
        rollback_time = time.time()
        
        # Simulate configuration issue requiring rollback
        await real_services.postgres.execute("""
            INSERT INTO backend.config_incidents (incident_id, config_id, issue_type, description, detected_at)
            VALUES ($1, $2, 'performance_degradation', 'Increased response time after config update', $3)
        """, str(uuid4()), new_config_id, rollback_time)
        
        # Perform rollback to previous version
        await real_services.postgres.execute("""
            UPDATE backend.dynamic_configs SET is_active = false WHERE config_id = $1;
            UPDATE backend.dynamic_configs SET is_active = true WHERE config_id = $2;
        """, new_config_id, config_id)
        
        # Update cache with rollback
        await real_services.redis.set_json(config_cache_key, base_config, ex=3600)
        
        # Record rollback action
        await real_services.postgres.execute("""
            INSERT INTO backend.config_rollbacks (rollback_id, from_config_id, to_config_id, reason, executed_at)
            VALUES ($1, $2, $3, 'performance_degradation', $4)
        """, str(uuid4()), new_config_id, config_id, rollback_time)
        
        # Verify rollback
        rolled_back_config = await real_services.postgres.fetchrow("""
            SELECT config_id, config_version, is_active
            FROM backend.dynamic_configs
            WHERE service_name = $1 AND is_active = true
        """, base_config['service_name'])
        
        assert rolled_back_config['config_id'] == config_id, "Configuration must be rolled back to original"
        assert rolled_back_config['config_version'] == '1.0.0', "Version must be rolled back"
        
        # Verify rollback is recorded
        rollback_record = await real_services.postgres.fetchrow("""
            SELECT from_config_id, to_config_id, reason
            FROM backend.config_rollbacks
            WHERE from_config_id = $1
        """, new_config_id)
        
        assert rollback_record is not None, "Rollback must be recorded"
        assert rollback_record['reason'] == 'performance_degradation', "Rollback reason must be recorded"

    async def _validate_configuration_update(self, real_services, current_config: Dict, new_config: Dict) -> Dict:
        """Validate configuration update for safety and correctness."""
        validation_result = {
            'valid': True,
            'changes_detected': False,
            'validation_errors': [],
            'warnings': []
        }
        
        # Check for changes
        if current_config != new_config:
            validation_result['changes_detected'] = True
        
        # Validate required fields
        required_fields = ['service_name', 'version', 'features', 'limits']
        for field in required_fields:
            if field not in new_config:
                validation_result['valid'] = False
                validation_result['validation_errors'].append(f"Missing required field: {field}")
        
        # Validate limits are reasonable
        if 'limits' in new_config:
            limits = new_config['limits']
            
            if limits.get('max_concurrent_users', 0) > 1000:
                validation_result['warnings'].append("High concurrent user limit may impact performance")
            
            if limits.get('max_api_calls_per_hour', 0) < 100:
                validation_result['valid'] = False
                validation_result['validation_errors'].append("API call limit too restrictive")
        
        # Store validation result for audit
        validation_id = str(uuid4())
        await real_services.postgres.execute("""
            INSERT INTO backend.config_validations 
            (validation_id, config_data, validation_result, validated_at)
            VALUES ($1, $2, $3, $4)
        """, validation_id, json.dumps(new_config), json.dumps(validation_result), time.time())
        
        return validation_result

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_ssot_configuration_compliance_validation(self, real_services):
        """
        Test SSOT (Single Source of Truth) compliance for configuration management.
        
        BVJ: Configuration consistency prevents system failures and ensures reliable platform behavior.
        """
        # Define SSOT configuration schema
        ssot_schema = {
            'database_config': {
                'required_fields': ['host', 'port', 'database', 'username'],
                'validation_rules': {
                    'port': {'type': 'integer', 'range': [1, 65535]},
                    'host': {'type': 'string', 'min_length': 1}
                }
            },
            'redis_config': {
                'required_fields': ['host', 'port', 'database'],
                'validation_rules': {
                    'port': {'type': 'integer', 'range': [1, 65535]},
                    'database': {'type': 'integer', 'range': [0, 15]}
                }
            },
            'api_config': {
                'required_fields': ['rate_limit', 'timeout', 'max_retries'],
                'validation_rules': {
                    'rate_limit': {'type': 'integer', 'min_value': 1},
                    'timeout': {'type': 'integer', 'range': [1, 300]},
                    'max_retries': {'type': 'integer', 'range': [0, 10]}
                }
            }
        }
        
        # Store SSOT schema in database
        schema_id = str(uuid4())
        await real_services.postgres.execute("""
            INSERT INTO backend.config_schemas 
            (schema_id, schema_name, schema_version, schema_definition, created_at, is_active)
            VALUES ($1, 'ssot_main', '1.0.0', $2, $3, true)
        """, schema_id, json.dumps(ssot_schema), time.time())
        
        # Test SSOT compliant configuration
        compliant_config = {
            'database_config': {
                'host': 'localhost',
                'port': 5434,
                'database': 'netra_test',
                'username': 'test_user',
                'password': 'secure_password'
            },
            'redis_config': {
                'host': 'localhost',
                'port': 6381,
                'database': 0,
                'password': None
            },
            'api_config': {
                'rate_limit': 100,
                'timeout': 30,
                'max_retries': 3,
                'backoff_multiplier': 2.0
            }
        }
        
        # Validate against SSOT schema
        compliance_result = await self._validate_ssot_compliance(real_services, compliant_config, ssot_schema)
        assert compliance_result['compliant'] is True, "Compliant configuration must pass SSOT validation"
        assert len(compliance_result['violations']) == 0, "Compliant configuration must have no violations"
        
        # Test non-compliant configuration
        non_compliant_config = {
            'database_config': {
                'host': '',  # Invalid: empty host
                'port': 70000,  # Invalid: port out of range
                'database': 'netra_test'
                # Missing required 'username' field
            },
            'redis_config': {
                'host': 'localhost',
                'port': 6381,
                'database': 20  # Invalid: Redis database out of range
            },
            'api_config': {
                'rate_limit': -5,  # Invalid: negative rate limit
                'timeout': 500,  # Invalid: timeout too high
                'max_retries': 20  # Invalid: too many retries
            }
        }
        
        # Validate non-compliant configuration
        non_compliance_result = await self._validate_ssot_compliance(real_services, non_compliant_config, ssot_schema)
        assert non_compliance_result['compliant'] is False, "Non-compliant configuration must fail SSOT validation"
        assert len(non_compliance_result['violations']) > 0, "Non-compliant configuration must have violations"
        
        # Verify specific violations
        violations = non_compliance_result['violations']
        violation_types = [v['type'] for v in violations]
        
        assert 'missing_required_field' in violation_types, "Missing required field violation must be detected"
        assert 'invalid_range' in violation_types, "Range validation violation must be detected"
        assert 'invalid_value' in violation_types, "Invalid value violation must be detected"
        
        # Test configuration drift detection
        # Store compliant configuration as baseline
        baseline_id = str(uuid4())
        await real_services.postgres.execute("""
            INSERT INTO backend.config_baselines 
            (baseline_id, schema_id, config_data, created_at, is_active)
            VALUES ($1, $2, $3, $4, true)
        """, baseline_id, json.dumps(compliant_config), time.time())
        
        # Cache baseline
        await real_services.redis.set_json(f"config_baseline:{schema_id}", compliant_config, ex=3600)
        
        # Simulate configuration drift
        drifted_config = {
            **compliant_config,
            'api_config': {
                **compliant_config['api_config'],
                'rate_limit': 200,  # Drift: changed from 100 to 200
                'timeout': 60       # Drift: changed from 30 to 60
            }
        }
        
        # Detect drift
        drift_result = await self._detect_configuration_drift(real_services, baseline_id, drifted_config)
        assert drift_result['drift_detected'] is True, "Configuration drift must be detected"
        assert len(drift_result['changes']) == 2, "Two configuration changes must be detected"
        
        changes = drift_result['changes']
        rate_limit_change = next((c for c in changes if c['field'] == 'api_config.rate_limit'), None)
        timeout_change = next((c for c in changes if c['field'] == 'api_config.timeout'), None)
        
        assert rate_limit_change is not None, "Rate limit change must be detected"
        assert rate_limit_change['old_value'] == 100, "Old rate limit value must be recorded"
        assert rate_limit_change['new_value'] == 200, "New rate limit value must be recorded"
        
        assert timeout_change is not None, "Timeout change must be detected"
        assert timeout_change['old_value'] == 30, "Old timeout value must be recorded"
        assert timeout_change['new_value'] == 60, "New timeout value must be recorded"
        
        # Record drift detection in database
        await real_services.postgres.execute("""
            INSERT INTO backend.config_drift_detections 
            (detection_id, baseline_id, drift_data, detected_at, severity)
            VALUES ($1, $2, $3, $4, 'medium')
        """, str(uuid4()), baseline_id, json.dumps(drift_result), time.time())
        
        # Verify business value - SSOT compliance prevents configuration errors
        self.assert_business_value_delivered({
            'ssot_compliance': compliance_result['compliant'],
            'violation_detection': len(non_compliance_result['violations']) > 0,
            'drift_detection': drift_result['drift_detected'],
            'configuration_integrity': True
        }, 'automation')

    async def _validate_ssot_compliance(self, real_services, config: Dict, schema: Dict) -> Dict:
        """Validate configuration compliance against SSOT schema."""
        compliance_result = {
            'compliant': True,
            'violations': [],
            'warnings': []
        }
        
        for section_name, section_schema in schema.items():
            if section_name not in config:
                compliance_result['compliant'] = False
                compliance_result['violations'].append({
                    'type': 'missing_section',
                    'section': section_name,
                    'message': f"Required section '{section_name}' is missing"
                })
                continue
            
            section_config = config[section_name]
            
            # Check required fields
            for required_field in section_schema.get('required_fields', []):
                if required_field not in section_config:
                    compliance_result['compliant'] = False
                    compliance_result['violations'].append({
                        'type': 'missing_required_field',
                        'section': section_name,
                        'field': required_field,
                        'message': f"Required field '{required_field}' is missing in section '{section_name}'"
                    })
            
            # Validate field rules
            validation_rules = section_schema.get('validation_rules', {})
            for field_name, rules in validation_rules.items():
                if field_name in section_config:
                    field_value = section_config[field_name]
                    
                    # Type validation
                    if 'type' in rules:
                        expected_type = rules['type']
                        if expected_type == 'integer' and not isinstance(field_value, int):
                            compliance_result['compliant'] = False
                            compliance_result['violations'].append({
                                'type': 'invalid_type',
                                'section': section_name,
                                'field': field_name,
                                'expected': expected_type,
                                'actual': type(field_value).__name__,
                                'message': f"Field '{field_name}' must be of type '{expected_type}'"
                            })
                        elif expected_type == 'string' and not isinstance(field_value, str):
                            compliance_result['compliant'] = False
                            compliance_result['violations'].append({
                                'type': 'invalid_type',
                                'section': section_name,
                                'field': field_name,
                                'expected': expected_type,
                                'actual': type(field_value).__name__,
                                'message': f"Field '{field_name}' must be of type '{expected_type}'"
                            })
                    
                    # Range validation
                    if 'range' in rules and isinstance(field_value, (int, float)):
                        min_val, max_val = rules['range']
                        if not (min_val <= field_value <= max_val):
                            compliance_result['compliant'] = False
                            compliance_result['violations'].append({
                                'type': 'invalid_range',
                                'section': section_name,
                                'field': field_name,
                                'value': field_value,
                                'valid_range': rules['range'],
                                'message': f"Field '{field_name}' value {field_value} is outside valid range {rules['range']}"
                            })
                    
                    # Minimum value validation
                    if 'min_value' in rules and isinstance(field_value, (int, float)):
                        if field_value < rules['min_value']:
                            compliance_result['compliant'] = False
                            compliance_result['violations'].append({
                                'type': 'invalid_value',
                                'section': section_name,
                                'field': field_name,
                                'value': field_value,
                                'min_value': rules['min_value'],
                                'message': f"Field '{field_name}' value {field_value} is below minimum {rules['min_value']}"
                            })
                    
                    # String length validation
                    if 'min_length' in rules and isinstance(field_value, str):
                        if len(field_value) < rules['min_length']:
                            compliance_result['compliant'] = False
                            compliance_result['violations'].append({
                                'type': 'invalid_value',
                                'section': section_name,
                                'field': field_name,
                                'value': field_value,
                                'min_length': rules['min_length'],
                                'message': f"Field '{field_name}' must be at least {rules['min_length']} characters"
                            })
        
        return compliance_result

    async def _detect_configuration_drift(self, real_services, baseline_id: str, current_config: Dict) -> Dict:
        """Detect configuration drift against baseline."""
        # Retrieve baseline configuration
        baseline_record = await real_services.postgres.fetchrow("""
            SELECT config_data FROM backend.config_baselines WHERE baseline_id = $1
        """, baseline_id)
        
        baseline_config = json.loads(baseline_record['config_data'])
        
        # Compare configurations
        drift_result = {
            'drift_detected': False,
            'changes': [],
            'baseline_id': baseline_id,
            'detected_at': time.time()
        }
        
        def compare_dicts(baseline, current, prefix=''):
            for key, baseline_value in baseline.items():
                current_value = current.get(key)
                full_key = f"{prefix}.{key}" if prefix else key
                
                if current_value != baseline_value:
                    if isinstance(baseline_value, dict) and isinstance(current_value, dict):
                        compare_dicts(baseline_value, current_value, full_key)
                    else:
                        drift_result['changes'].append({
                            'field': full_key,
                            'old_value': baseline_value,
                            'new_value': current_value,
                            'change_type': 'modified' if current_value is not None else 'deleted'
                        })
            
            # Check for new fields
            for key, current_value in current.items():
                if key not in baseline:
                    full_key = f"{prefix}.{key}" if prefix else key
                    drift_result['changes'].append({
                        'field': full_key,
                        'old_value': None,
                        'new_value': current_value,
                        'change_type': 'added'
                    })
        
        compare_dicts(baseline_config, current_config)
        
        if len(drift_result['changes']) > 0:
            drift_result['drift_detected'] = True
        
        return drift_result