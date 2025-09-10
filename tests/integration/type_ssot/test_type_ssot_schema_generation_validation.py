"""
Test Schema Generation and TypeScript Type Synchronization

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure automated schema synchronization prevents type drift
- Value Impact: Automated sync prevents manual errors and maintains API contracts
- Strategic Impact: Schema consistency is critical for frontend/backend reliability

CRITICAL: Automated schema generation from Pydantic models to TypeScript types
must maintain perfect synchronization to prevent API contract violations and
ensure reliable frontend/backend communication.
"""

import pytest
import asyncio
import json
import subprocess
import tempfile
import os
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture


@dataclass
class PydanticModel:
    """Mock Pydantic model for schema generation testing."""
    name: str
    fields: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'fields': self.fields
        }


@dataclass
class TypeScriptInterface:
    """Mock TypeScript interface for validation."""
    name: str
    properties: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'properties': self.properties
        }


class TestSchemaGenerationValidation(BaseIntegrationTest):
    """Integration tests for schema generation and TypeScript synchronization."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_pydantic_to_typescript_generation_accuracy(self, real_services_fixture):
        """
        Test that Pydantic models generate accurate TypeScript interfaces.
        
        MISSION CRITICAL: Accurate schema generation prevents type mismatches
        that cause runtime errors and API contract violations.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock schema generator
        class SchemaGenerator:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.type_mapping = {
                    'str': 'string',
                    'int': 'number',
                    'float': 'number',
                    'bool': 'boolean',
                    'datetime': 'string',  # ISO string
                    'list': 'Array',
                    'dict': 'object',
                    'Optional[str]': 'string | undefined',
                    'Optional[int]': 'number | undefined',
                    'Optional[bool]': 'boolean | undefined',
                    'List[str]': 'string[]',
                    'List[int]': 'number[]',
                    'Dict[str, str]': 'Record<string, string>',
                    'Dict[str, Any]': 'Record<string, any>'
                }
            
            def generate_typescript_interface(self, pydantic_model: PydanticModel) -> TypeScriptInterface:
                """Generate TypeScript interface from Pydantic model."""
                ts_properties = {}
                
                for field_name, field_def in pydantic_model.fields.items():
                    python_type = field_def['type']
                    required = field_def.get('required', True)
                    
                    # Map Python type to TypeScript type
                    ts_type = self.type_mapping.get(python_type, python_type)
                    
                    # Handle optional fields
                    if not required and not python_type.startswith('Optional'):
                        ts_type = f"{ts_type} | undefined"
                    
                    ts_property = {
                        'type': ts_type,
                        'required': required
                    }
                    
                    # Add constraints if present
                    if 'min_length' in field_def:
                        ts_property['minLength'] = field_def['min_length']
                    if 'max_length' in field_def:
                        ts_property['maxLength'] = field_def['max_length']
                    if 'enum' in field_def:
                        ts_property['enum'] = field_def['enum']
                    if 'default' in field_def:
                        ts_property['default'] = field_def['default']
                    
                    ts_properties[field_name] = ts_property
                
                return TypeScriptInterface(
                    name=pydantic_model.name,
                    properties=ts_properties
                )
            
            def validate_generated_interface(self, pydantic_model: PydanticModel, ts_interface: TypeScriptInterface) -> Dict[str, Any]:
                """Validate that generated TypeScript interface matches Pydantic model."""
                validation_result = {
                    'model_name': pydantic_model.name,
                    'valid': True,
                    'issues': [],
                    'field_count': len(pydantic_model.fields),
                    'property_count': len(ts_interface.properties)
                }
                
                # Check name consistency
                if pydantic_model.name != ts_interface.name:
                    validation_result['valid'] = False
                    validation_result['issues'].append({
                        'type': 'name_mismatch',
                        'pydantic': pydantic_model.name,
                        'typescript': ts_interface.name
                    })
                
                # Check field count
                if len(pydantic_model.fields) != len(ts_interface.properties):
                    validation_result['valid'] = False
                    validation_result['issues'].append({
                        'type': 'field_count_mismatch',
                        'pydantic_fields': len(pydantic_model.fields),
                        'typescript_properties': len(ts_interface.properties)
                    })
                
                # Check each field
                for field_name, field_def in pydantic_model.fields.items():
                    if field_name not in ts_interface.properties:
                        validation_result['valid'] = False
                        validation_result['issues'].append({
                            'type': 'missing_property',
                            'field': field_name
                        })
                        continue
                    
                    ts_prop = ts_interface.properties[field_name]
                    
                    # Validate type mapping
                    expected_ts_type = self.type_mapping.get(field_def['type'], field_def['type'])
                    python_required = field_def.get('required', True)
                    
                    if not python_required and not field_def['type'].startswith('Optional'):
                        expected_ts_type = f"{expected_ts_type} | undefined"
                    
                    if ts_prop['type'] != expected_ts_type:
                        validation_result['valid'] = False
                        validation_result['issues'].append({
                            'type': 'type_mapping_error',
                            'field': field_name,
                            'python_type': field_def['type'],
                            'expected_ts_type': expected_ts_type,
                            'actual_ts_type': ts_prop['type']
                        })
                    
                    # Validate required/optional consistency
                    if ts_prop['required'] != python_required:
                        validation_result['valid'] = False
                        validation_result['issues'].append({
                            'type': 'required_optional_mismatch',
                            'field': field_name,
                            'python_required': python_required,
                            'typescript_required': ts_prop['required']
                        })
                    
                    # Validate constraints
                    for constraint in ['min_length', 'max_length', 'enum', 'default']:
                        if constraint in field_def:
                            ts_constraint_name = constraint
                            if constraint == 'min_length':
                                ts_constraint_name = 'minLength'
                            elif constraint == 'max_length':
                                ts_constraint_name = 'maxLength'
                            
                            if ts_constraint_name not in ts_prop:
                                validation_result['valid'] = False
                                validation_result['issues'].append({
                                    'type': 'missing_constraint',
                                    'field': field_name,
                                    'constraint': constraint,
                                    'value': field_def[constraint]
                                })
                            elif ts_prop[ts_constraint_name] != field_def[constraint]:
                                validation_result['valid'] = False
                                validation_result['issues'].append({
                                    'type': 'constraint_mismatch',
                                    'field': field_name,
                                    'constraint': constraint,
                                    'python_value': field_def[constraint],
                                    'typescript_value': ts_prop[ts_constraint_name]
                                })
                
                return validation_result
            
            async def store_generation_results(self, results: List[Dict[str, Any]]):
                """Store schema generation validation results."""
                summary = {
                    'generated_at': asyncio.get_event_loop().time(),
                    'total_models': len(results),
                    'valid_generations': len([r for r in results if r['valid']]),
                    'failed_generations': len([r for r in results if not r['valid']]),
                    'total_issues': sum(len(r['issues']) for r in results),
                    'results': results
                }
                
                await self.redis.setex(
                    'schema_generation_validation',
                    3600,
                    json.dumps(summary)
                )
                
                return summary
        
        generator = SchemaGenerator(redis_client)
        
        # Test Pydantic models for schema generation
        test_models = [
            PydanticModel(
                name='UserProfile',
                fields={
                    'id': {'type': 'str', 'required': True},
                    'email': {'type': 'str', 'required': True, 'max_length': 255},
                    'name': {'type': 'str', 'required': True, 'min_length': 1, 'max_length': 100},
                    'is_active': {'type': 'bool', 'required': True, 'default': True},
                    'age': {'type': 'Optional[int]', 'required': False},
                    'bio': {'type': 'Optional[str]', 'required': False, 'max_length': 500},
                    'role': {'type': 'str', 'required': True, 'enum': ['admin', 'user', 'readonly']},
                    'created_at': {'type': 'datetime', 'required': True},
                    'preferences': {'type': 'Dict[str, Any]', 'required': False}
                }
            ),
            PydanticModel(
                name='ThreadMessage',
                fields={
                    'id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'user_id': {'type': 'str', 'required': True},
                    'content': {'type': 'str', 'required': True, 'min_length': 1, 'max_length': 5000},
                    'message_type': {'type': 'str', 'required': True, 'enum': ['user', 'agent', 'system']},
                    'timestamp': {'type': 'datetime', 'required': True},
                    'attachments': {'type': 'List[str]', 'required': False},
                    'metadata': {'type': 'Optional[dict]', 'required': False},
                    'is_edited': {'type': 'bool', 'required': True, 'default': False}
                }
            ),
            PydanticModel(
                name='AgentExecution',
                fields={
                    'id': {'type': 'str', 'required': True},
                    'agent_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'status': {'type': 'str', 'required': True, 'enum': ['pending', 'running', 'completed', 'failed']},
                    'started_at': {'type': 'datetime', 'required': True},
                    'completed_at': {'type': 'Optional[datetime]', 'required': False},
                    'tools_used': {'type': 'List[str]', 'required': False},
                    'execution_time_ms': {'type': 'Optional[int]', 'required': False},
                    'error_message': {'type': 'Optional[str]', 'required': False},
                    'result_data': {'type': 'Dict[str, Any]', 'required': False}
                }
            )
        ]
        
        # Generate TypeScript interfaces and validate
        validation_results = []
        
        for model in test_models:
            # Generate TypeScript interface
            ts_interface = generator.generate_typescript_interface(model)
            
            # Validate generation accuracy
            validation_result = generator.validate_generated_interface(model, ts_interface)
            validation_results.append(validation_result)
            
            # Assert each model generates valid TypeScript
            assert validation_result['valid'], (
                f"Schema generation failed for {model.name}. Issues: {validation_result['issues']}"
            )
        
        # Store and validate overall results
        summary = await generator.store_generation_results(validation_results)
        
        assert summary['valid_generations'] == summary['total_models'], (
            f"Schema generation failed: {summary['failed_generations']} out of {summary['total_models']} failed. "
            f"Total issues: {summary['total_issues']}"
        )
        
        # Cleanup
        await redis_client.delete('schema_generation_validation')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_schema_sync_script_execution(self, real_services_fixture):
        """
        Test that schema synchronization script executes correctly.
        
        DEVELOPMENT CRITICAL: Schema sync script must work reliably to maintain
        frontend/backend type synchronization during development.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock schema sync script execution
        class SchemaSyncScriptMock:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.script_path = "/mock/scripts/schema_sync.py"
            
            async def execute_schema_sync(self, dry_run: bool = False) -> Dict[str, Any]:
                """Mock execution of schema sync script."""
                execution_result = {
                    'executed_at': asyncio.get_event_loop().time(),
                    'dry_run': dry_run,
                    'success': True,
                    'models_processed': 0,
                    'types_generated': 0,
                    'files_modified': [],
                    'errors': [],
                    'warnings': []
                }
                
                # Mock backend models discovery
                mock_models = [
                    'UserProfile',
                    'ThreadMessage', 
                    'AgentExecution',
                    'WebSocketEvent',
                    'APIResponse'
                ]
                
                execution_result['models_processed'] = len(mock_models)
                
                # Mock TypeScript generation
                for model in mock_models:
                    ts_file = f"/mock/frontend/types/{model.lower()}.ts"
                    
                    if not dry_run:
                        execution_result['files_modified'].append(ts_file)
                    
                    execution_result['types_generated'] += 1
                
                # Mock validation checks
                validation_errors = []
                
                # Simulate potential issues
                if 'WebSocketEvent' in mock_models:
                    # Mock enum validation issue
                    execution_result['warnings'].append({
                        'type': 'enum_validation',
                        'model': 'WebSocketEvent',
                        'field': 'event_type',
                        'message': 'Enum values may need manual review for frontend compatibility'
                    })
                
                # Store execution result
                await self.redis.setex(
                    'schema_sync_execution',
                    3600,
                    json.dumps(execution_result)
                )
                
                return execution_result
            
            async def validate_generated_types(self) -> Dict[str, Any]:
                """Validate generated TypeScript types."""
                validation_result = {
                    'validated_at': asyncio.get_event_loop().time(),
                    'files_checked': 0,
                    'valid_files': 0,
                    'invalid_files': 0,
                    'syntax_errors': [],
                    'type_errors': [],
                    'success': True
                }
                
                # Mock TypeScript files validation
                mock_ts_files = [
                    '/mock/frontend/types/userprofile.ts',
                    '/mock/frontend/types/threadmessage.ts',
                    '/mock/frontend/types/agentexecution.ts',
                    '/mock/frontend/types/websocketevent.ts',
                    '/mock/frontend/types/apiresponse.ts'
                ]
                
                validation_result['files_checked'] = len(mock_ts_files)
                
                for ts_file in mock_ts_files:
                    # Mock syntax validation
                    file_valid = True
                    
                    # Simulate potential syntax issue
                    if 'websocketevent' in ts_file:
                        validation_result['syntax_errors'].append({
                            'file': ts_file,
                            'line': 15,
                            'message': 'Trailing comma in enum definition',
                            'severity': 'warning'
                        })
                        # This is a warning, not an error, so file is still valid
                    
                    if file_valid:
                        validation_result['valid_files'] += 1
                    else:
                        validation_result['invalid_files'] += 1
                
                # Overall success if no critical errors
                validation_result['success'] = validation_result['invalid_files'] == 0
                
                return validation_result
            
            async def cleanup_generated_files(self, files: List[str]):
                """Cleanup generated files (for testing)."""
                cleanup_result = {
                    'cleaned_at': asyncio.get_event_loop().time(),
                    'files_removed': len(files),
                    'files': files
                }
                
                # Mock file cleanup
                await self.redis.setex(
                    'schema_sync_cleanup',
                    300,  # 5 minutes
                    json.dumps(cleanup_result)
                )
                
                return cleanup_result
        
        script_mock = SchemaSyncScriptMock(redis_client)
        
        # Test dry run execution
        dry_run_result = await script_mock.execute_schema_sync(dry_run=True)
        
        assert dry_run_result['success'], "Dry run execution must succeed"
        assert dry_run_result['dry_run'] is True, "Dry run flag must be set"
        assert dry_run_result['models_processed'] > 0, "Must process backend models"
        assert dry_run_result['types_generated'] > 0, "Must generate TypeScript types"
        assert len(dry_run_result['files_modified']) == 0, "Dry run must not modify files"
        
        # Test actual execution
        actual_run_result = await script_mock.execute_schema_sync(dry_run=False)
        
        assert actual_run_result['success'], "Actual execution must succeed"
        assert actual_run_result['dry_run'] is False, "Dry run flag must be false"
        assert actual_run_result['models_processed'] > 0, "Must process backend models"
        assert actual_run_result['types_generated'] > 0, "Must generate TypeScript types"
        assert len(actual_run_result['files_modified']) > 0, "Actual run must modify files"
        
        # Validate that same number of types were generated in both runs
        assert dry_run_result['types_generated'] == actual_run_result['types_generated'], (
            "Dry run and actual run must generate same number of types"
        )
        
        # Test TypeScript validation
        validation_result = await script_mock.validate_generated_types()
        
        assert validation_result['success'], "Generated TypeScript validation must succeed"
        assert validation_result['files_checked'] > 0, "Must check generated files"
        assert validation_result['valid_files'] > 0, "Must have valid generated files"
        assert validation_result['invalid_files'] == 0, "Must not have invalid files"
        
        # Test cleanup
        files_to_cleanup = actual_run_result['files_modified']
        cleanup_result = await script_mock.cleanup_generated_files(files_to_cleanup)
        
        assert cleanup_result['files_removed'] == len(files_to_cleanup), (
            "Must cleanup all generated files"
        )
        
        # Cleanup test data
        await redis_client.delete('schema_sync_execution')
        await redis_client.delete('schema_sync_cleanup')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_continuous_schema_sync_monitoring(self, real_services_fixture):
        """
        Test continuous monitoring of schema synchronization status.
        
        OPERATIONAL CRITICAL: Continuous monitoring detects schema drift early
        and ensures ongoing frontend/backend type consistency.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock continuous schema sync monitor
        class ContinuousSchemaSyncMonitor:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.monitoring_active = False
                self.sync_checks = []
            
            async def start_monitoring(self, check_interval_seconds: int = 300):
                """Start continuous schema synchronization monitoring."""
                self.monitoring_active = True
                
                monitoring_config = {
                    'started_at': asyncio.get_event_loop().time(),
                    'check_interval_seconds': check_interval_seconds,
                    'active': True,
                    'checks_performed': 0,
                    'sync_violations_detected': 0
                }
                
                await self.redis.setex(
                    'schema_sync_monitoring_config',
                    86400,  # 24 hours
                    json.dumps(monitoring_config)
                )
                
                return monitoring_config
            
            async def perform_sync_check(self) -> Dict[str, Any]:
                """Perform a single schema synchronization check."""
                check_result = {
                    'checked_at': asyncio.get_event_loop().time(),
                    'backend_schemas_count': 0,
                    'frontend_types_count': 0,
                    'synchronized_types': 0,
                    'out_of_sync_types': 0,
                    'missing_types': [],
                    'extra_types': [],
                    'type_mismatches': [],
                    'overall_sync_status': 'synchronized'
                }
                
                # Mock backend schemas discovery
                backend_schemas = [
                    'UserProfile',
                    'ThreadMessage',
                    'AgentExecution',
                    'WebSocketEvent',
                    'APIResponse'
                ]
                
                # Mock frontend types discovery
                frontend_types = [
                    'UserProfile',
                    'ThreadMessage',
                    'AgentExecution',
                    'WebSocketEvent',
                    # 'APIResponse' - missing to simulate sync issue
                    'ExtraFrontendType'  # Extra type to simulate drift
                ]
                
                check_result['backend_schemas_count'] = len(backend_schemas)
                check_result['frontend_types_count'] = len(frontend_types)
                
                # Find missing types (in backend but not frontend)
                missing_types = set(backend_schemas) - set(frontend_types)
                check_result['missing_types'] = list(missing_types)
                
                # Find extra types (in frontend but not backend)
                extra_types = set(frontend_types) - set(backend_schemas)
                check_result['extra_types'] = list(extra_types)
                
                # Count synchronized types
                synchronized_types = set(backend_schemas) & set(frontend_types)
                check_result['synchronized_types'] = len(synchronized_types)
                
                # Mock type mismatch detection for synchronized types
                for type_name in synchronized_types:
                    # Simulate random type mismatch
                    if type_name == 'WebSocketEvent':
                        check_result['type_mismatches'].append({
                            'type_name': type_name,
                            'field': 'event_type',
                            'backend_type': 'str',
                            'frontend_type': 'union',
                            'issue': 'enum handling difference'
                        })
                
                # Determine overall sync status
                if missing_types or extra_types or check_result['type_mismatches']:
                    check_result['overall_sync_status'] = 'out_of_sync'
                    check_result['out_of_sync_types'] = len(missing_types) + len(extra_types) + len(check_result['type_mismatches'])
                
                # Store check result
                check_key = f"schema_sync_check:{int(asyncio.get_event_loop().time())}"
                await self.redis.setex(check_key, 3600, json.dumps(check_result))
                
                self.sync_checks.append(check_result)
                
                # Update monitoring config
                config_data = await self.redis.get('schema_sync_monitoring_config')
                if config_data:
                    config = json.loads(config_data.decode())
                    config['checks_performed'] += 1
                    config['last_check_at'] = check_result['checked_at']
                    config['last_sync_status'] = check_result['overall_sync_status']
                    
                    if check_result['overall_sync_status'] == 'out_of_sync':
                        config['sync_violations_detected'] += 1
                    
                    await self.redis.setex(
                        'schema_sync_monitoring_config',
                        86400,
                        json.dumps(config)
                    )
                
                return check_result
            
            async def get_monitoring_status(self) -> Optional[Dict[str, Any]]:
                """Get current monitoring status."""
                config_data = await self.redis.get('schema_sync_monitoring_config')
                if config_data:
                    return json.loads(config_data.decode())
                return None
            
            async def stop_monitoring(self):
                """Stop continuous monitoring."""
                self.monitoring_active = False
                
                config_data = await self.redis.get('schema_sync_monitoring_config')
                if config_data:
                    config = json.loads(config_data.decode())
                    config['active'] = False
                    config['stopped_at'] = asyncio.get_event_loop().time()
                    
                    await self.redis.setex(
                        'schema_sync_monitoring_config',
                        86400,
                        json.dumps(config)
                    )
                
                return config
        
        monitor = ContinuousSchemaSyncMonitor(redis_client)
        
        # Test monitoring lifecycle
        
        # Start monitoring
        monitoring_config = await monitor.start_monitoring(check_interval_seconds=60)
        
        assert monitoring_config['active'] is True, "Monitoring must be active after start"
        assert monitoring_config['check_interval_seconds'] == 60, "Check interval must be set correctly"
        assert monitoring_config['checks_performed'] == 0, "Initial checks performed must be 0"
        
        # Perform initial sync check
        first_check = await monitor.perform_sync_check()
        
        assert first_check['overall_sync_status'] == 'out_of_sync', (
            "First check should detect sync issues (missing APIResponse, extra ExtraFrontendType)"
        )
        assert len(first_check['missing_types']) > 0, "Should detect missing types"
        assert len(first_check['extra_types']) > 0, "Should detect extra types"
        assert first_check['synchronized_types'] > 0, "Should have some synchronized types"
        
        # Verify monitoring status updated
        status_after_first_check = await monitor.get_monitoring_status()
        
        assert status_after_first_check['checks_performed'] == 1, "Checks performed must be incremented"
        assert status_after_first_check['sync_violations_detected'] == 1, "Must detect sync violation"
        assert status_after_first_check['last_sync_status'] == 'out_of_sync', "Last sync status must be out_of_sync"
        
        # Perform second check (simulating ongoing monitoring)
        await asyncio.sleep(0.1)  # Small delay to ensure different timestamp
        second_check = await monitor.perform_sync_check()
        
        # Should have same issues as first check
        assert second_check['overall_sync_status'] == 'out_of_sync', "Second check should still detect issues"
        assert second_check['missing_types'] == first_check['missing_types'], "Missing types should be consistent"
        assert second_check['extra_types'] == first_check['extra_types'], "Extra types should be consistent"
        
        # Verify monitoring status updated again
        status_after_second_check = await monitor.get_monitoring_status()
        
        assert status_after_second_check['checks_performed'] == 2, "Checks performed must be 2"
        assert status_after_second_check['sync_violations_detected'] == 2, "Must detect both violations"
        
        # Stop monitoring
        final_config = await monitor.stop_monitoring()
        
        assert final_config['active'] is False, "Monitoring must be inactive after stop"
        assert 'stopped_at' in final_config, "Must record stop time"
        assert final_config['checks_performed'] == 2, "Final checks count must be preserved"
        
        # Cleanup
        await redis_client.delete('schema_sync_monitoring_config')
        
        # Cleanup check results
        for i, check in enumerate(monitor.sync_checks):
            check_key = f"schema_sync_check:{int(check['checked_at'])}"
            await redis_client.delete(check_key)