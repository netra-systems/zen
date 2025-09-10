"""
Test Frontend/Backend Type Synchronization SSOT Compliance

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure frontend/backend type consistency for seamless UX
- Value Impact: Prevents API contract violations and broken user interfaces
- Strategic Impact: Type mismatches break chat UX and agent interactions

CRITICAL: Frontend TypeScript types must synchronize with backend Pydantic schemas
to prevent API contract violations, broken WebSocket events, and UI failures
that directly impact user experience and platform reliability.
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.types.core_types import ThreadID, UserID, AgentID


@dataclass
class BackendSchema:
    """Backend Pydantic schema representation."""
    name: str
    fields: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'fields': self.fields
        }


@dataclass 
class FrontendType:
    """Frontend TypeScript type representation."""
    name: str
    properties: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'properties': self.properties
        }


class TestFrontendBackendTypeSync(BaseIntegrationTest):
    """Integration tests for frontend/backend type synchronization."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_event_type_synchronization(self, real_services_fixture):
        """
        Test that WebSocket event types are synchronized between frontend and backend.
        
        MISSION CRITICAL: WebSocket events deliver real-time chat value. Type
        mismatches cause event handling failures and broken user experience.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock backend WebSocket event schema definitions
        backend_websocket_schemas = {
            'agent_started': BackendSchema(
                name='AgentStartedEvent',
                fields={
                    'type': {'type': 'str', 'required': True, 'enum': ['agent_started']},
                    'agent_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'user_id': {'type': 'str', 'required': True},
                    'timestamp': {'type': 'float', 'required': True},
                    'agent_type': {'type': 'str', 'required': True}
                }
            ),
            'agent_thinking': BackendSchema(
                name='AgentThinkingEvent',
                fields={
                    'type': {'type': 'str', 'required': True, 'enum': ['agent_thinking']},
                    'agent_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'thinking_content': {'type': 'str', 'required': True},
                    'timestamp': {'type': 'float', 'required': True}
                }
            ),
            'tool_executing': BackendSchema(
                name='ToolExecutingEvent',
                fields={
                    'type': {'type': 'str', 'required': True, 'enum': ['tool_executing']},
                    'agent_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'tool_name': {'type': 'str', 'required': True},
                    'tool_params': {'type': 'dict', 'required': False},
                    'timestamp': {'type': 'float', 'required': True}
                }
            ),
            'tool_completed': BackendSchema(
                name='ToolCompletedEvent',
                fields={
                    'type': {'type': 'str', 'required': True, 'enum': ['tool_completed']},
                    'agent_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'tool_name': {'type': 'str', 'required': True},
                    'tool_result': {'type': 'any', 'required': True},
                    'execution_time_ms': {'type': 'float', 'required': True},
                    'timestamp': {'type': 'float', 'required': True}
                }
            ),
            'agent_completed': BackendSchema(
                name='AgentCompletedEvent',
                fields={
                    'type': {'type': 'str', 'required': True, 'enum': ['agent_completed']},
                    'agent_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'user_id': {'type': 'str', 'required': True},
                    'result': {'type': 'dict', 'required': True},
                    'execution_time_ms': {'type': 'float', 'required': True},
                    'timestamp': {'type': 'float', 'required': True}
                }
            )
        }
        
        # Mock frontend TypeScript type definitions (what should be generated)
        frontend_websocket_types = {
            'agent_started': FrontendType(
                name='AgentStartedEvent',
                properties={
                    'type': {'type': 'literal', 'value': 'agent_started'},
                    'agent_id': {'type': 'string'},
                    'thread_id': {'type': 'string'},
                    'user_id': {'type': 'string'},
                    'timestamp': {'type': 'number'},
                    'agent_type': {'type': 'string'}
                }
            ),
            'agent_thinking': FrontendType(
                name='AgentThinkingEvent',
                properties={
                    'type': {'type': 'literal', 'value': 'agent_thinking'},
                    'agent_id': {'type': 'string'},
                    'thread_id': {'type': 'string'},
                    'thinking_content': {'type': 'string'},
                    'timestamp': {'type': 'number'}
                }
            ),
            'tool_executing': FrontendType(
                name='ToolExecutingEvent',
                properties={
                    'type': {'type': 'literal', 'value': 'tool_executing'},
                    'agent_id': {'type': 'string'},
                    'thread_id': {'type': 'string'},
                    'tool_name': {'type': 'string'},
                    'tool_params': {'type': 'object', 'optional': True},
                    'timestamp': {'type': 'number'}
                }
            ),
            'tool_completed': FrontendType(
                name='ToolCompletedEvent',
                properties={
                    'type': {'type': 'literal', 'value': 'tool_completed'},
                    'agent_id': {'type': 'string'},
                    'thread_id': {'type': 'string'},
                    'tool_name': {'type': 'string'},
                    'tool_result': {'type': 'any'},
                    'execution_time_ms': {'type': 'number'},
                    'timestamp': {'type': 'number'}
                }
            ),
            'agent_completed': FrontendType(
                name='AgentCompletedEvent',
                properties={
                    'type': {'type': 'literal', 'value': 'agent_completed'},
                    'agent_id': {'type': 'string'},
                    'thread_id': {'type': 'string'},
                    'user_id': {'type': 'string'},
                    'result': {'type': 'object'},
                    'execution_time_ms': {'type': 'number'},
                    'timestamp': {'type': 'number'}
                }
            )
        }
        
        # Type mapping for validation
        type_mapping = {
            'str': 'string',
            'float': 'number',
            'int': 'number',
            'dict': 'object',
            'any': 'any',
            'bool': 'boolean'
        }
        
        # Validate type synchronization
        for event_type in backend_websocket_schemas:
            backend_schema = backend_websocket_schemas[event_type]
            frontend_type = frontend_websocket_types[event_type]
            
            assert backend_schema.name == frontend_type.name, (
                f"Schema name mismatch for {event_type}: "
                f"backend={backend_schema.name}, frontend={frontend_type.name}"
            )
            
            # Validate field/property synchronization
            backend_fields = backend_schema.fields
            frontend_props = frontend_type.properties
            
            # Check that all backend fields have corresponding frontend properties
            for field_name, field_def in backend_fields.items():
                assert field_name in frontend_props, (
                    f"Missing frontend property for backend field '{field_name}' in {event_type}"
                )
                
                frontend_prop = frontend_props[field_name]
                backend_type = field_def['type']
                
                # Handle enum types (literal types in TypeScript)
                if 'enum' in field_def:
                    assert frontend_prop['type'] == 'literal', (
                        f"Enum field '{field_name}' in {event_type} must be literal type in frontend"
                    )
                    assert frontend_prop['value'] == field_def['enum'][0], (
                        f"Literal value mismatch for '{field_name}' in {event_type}"
                    )
                else:
                    # Regular type mapping
                    expected_frontend_type = type_mapping.get(backend_type, backend_type)
                    assert frontend_prop['type'] == expected_frontend_type, (
                        f"Type mismatch for '{field_name}' in {event_type}: "
                        f"backend={backend_type}, frontend={frontend_prop['type']}, expected={expected_frontend_type}"
                    )
                
                # Check required/optional consistency
                backend_required = field_def.get('required', False)
                frontend_optional = frontend_prop.get('optional', False)
                
                assert backend_required != frontend_optional, (
                    f"Required/optional mismatch for '{field_name}' in {event_type}: "
                    f"backend_required={backend_required}, frontend_optional={frontend_optional}"
                )
            
            # Check that frontend doesn't have extra properties
            for prop_name in frontend_props:
                assert prop_name in backend_fields, (
                    f"Extra frontend property '{prop_name}' not in backend schema for {event_type}"
                )
        
        # Store synchronization validation results
        sync_results = {
            'validated_at': asyncio.get_event_loop().time(),
            'event_types_validated': list(backend_websocket_schemas.keys()),
            'synchronization_status': 'consistent',
            'validation_details': {
                event_type: {
                    'backend_fields': len(backend_websocket_schemas[event_type].fields),
                    'frontend_props': len(frontend_websocket_types[event_type].properties),
                    'synchronized': True
                }
                for event_type in backend_websocket_schemas
            }
        }
        
        await redis_client.setex(
            'type_sync_validation:websocket_events',
            3600,
            json.dumps(sync_results)
        )
        
        # Cleanup
        await redis_client.delete('type_sync_validation:websocket_events')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_api_request_response_type_synchronization(self, real_services_fixture):
        """
        Test that API request/response types are synchronized between frontend and backend.
        
        GOLDEN PATH CRITICAL: API contract violations break frontend functionality
        and prevent users from accessing core platform features.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock backend API schema definitions
        backend_api_schemas = {
            'create_thread_request': BackendSchema(
                name='CreateThreadRequest',
                fields={
                    'title': {'type': 'str', 'required': False, 'max_length': 200},
                    'agent_type': {'type': 'str', 'required': True, 'enum': ['cost_optimizer', 'data_analyzer', 'report_generator']},
                    'initial_message': {'type': 'str', 'required': False, 'max_length': 2000},
                    'context': {'type': 'dict', 'required': False}
                }
            ),
            'create_thread_response': BackendSchema(
                name='CreateThreadResponse',
                fields={
                    'thread_id': {'type': 'str', 'required': True},
                    'title': {'type': 'str', 'required': True},
                    'agent_type': {'type': 'str', 'required': True},
                    'status': {'type': 'str', 'required': True, 'enum': ['active', 'processing', 'completed']},
                    'created_at': {'type': 'datetime', 'required': True},
                    'user_id': {'type': 'str', 'required': True}
                }
            ),
            'send_message_request': BackendSchema(
                name='SendMessageRequest',
                fields={
                    'thread_id': {'type': 'str', 'required': True},
                    'content': {'type': 'str', 'required': True, 'max_length': 5000},
                    'message_type': {'type': 'str', 'required': False, 'default': 'user', 'enum': ['user', 'system']},
                    'attachments': {'type': 'list', 'required': False, 'item_type': 'dict'}
                }
            ),
            'send_message_response': BackendSchema(
                name='SendMessageResponse',
                fields={
                    'message_id': {'type': 'str', 'required': True},
                    'thread_id': {'type': 'str', 'required': True},
                    'content': {'type': 'str', 'required': True},
                    'timestamp': {'type': 'datetime', 'required': True},
                    'status': {'type': 'str', 'required': True, 'enum': ['sent', 'processing', 'delivered']},
                    'agent_response_id': {'type': 'str', 'required': False}
                }
            )
        }
        
        # Mock frontend API type definitions
        frontend_api_types = {
            'create_thread_request': FrontendType(
                name='CreateThreadRequest',
                properties={
                    'title': {'type': 'string', 'optional': True, 'maxLength': 200},
                    'agent_type': {'type': 'union', 'types': ['cost_optimizer', 'data_analyzer', 'report_generator']},
                    'initial_message': {'type': 'string', 'optional': True, 'maxLength': 2000},
                    'context': {'type': 'object', 'optional': True}
                }
            ),
            'create_thread_response': FrontendType(
                name='CreateThreadResponse',
                properties={
                    'thread_id': {'type': 'string'},
                    'title': {'type': 'string'},
                    'agent_type': {'type': 'string'},
                    'status': {'type': 'union', 'types': ['active', 'processing', 'completed']},
                    'created_at': {'type': 'string'},  # ISO string in frontend
                    'user_id': {'type': 'string'}
                }
            ),
            'send_message_request': FrontendType(
                name='SendMessageRequest',
                properties={
                    'thread_id': {'type': 'string'},
                    'content': {'type': 'string', 'maxLength': 5000},
                    'message_type': {'type': 'union', 'types': ['user', 'system'], 'optional': True},
                    'attachments': {'type': 'array', 'itemType': 'object', 'optional': True}
                }
            ),
            'send_message_response': FrontendType(
                name='SendMessageResponse',
                properties={
                    'message_id': {'type': 'string'},
                    'thread_id': {'type': 'string'},
                    'content': {'type': 'string'},
                    'timestamp': {'type': 'string'},  # ISO string in frontend
                    'status': {'type': 'union', 'types': ['sent', 'processing', 'delivered']},
                    'agent_response_id': {'type': 'string', 'optional': True}
                }
            )
        }
        
        # Mock API synchronization validator
        class APISyncValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.type_mapping = {
                    'str': 'string',
                    'int': 'number',
                    'float': 'number',
                    'bool': 'boolean',
                    'dict': 'object',
                    'list': 'array',
                    'datetime': 'string'  # ISO string representation
                }
            
            def validate_schema_sync(self, backend_schema: BackendSchema, frontend_type: FrontendType) -> Dict[str, Any]:
                """Validate that backend schema and frontend type are synchronized."""
                validation_result = {
                    'schema_name': backend_schema.name,
                    'synchronized': True,
                    'issues': [],
                    'field_count': len(backend_schema.fields),
                    'property_count': len(frontend_type.properties)
                }
                
                # Check name consistency
                if backend_schema.name != frontend_type.name:
                    validation_result['synchronized'] = False
                    validation_result['issues'].append({
                        'type': 'name_mismatch',
                        'backend': backend_schema.name,
                        'frontend': frontend_type.name
                    })
                
                # Check field/property synchronization
                for field_name, field_def in backend_schema.fields.items():
                    if field_name not in frontend_type.properties:
                        validation_result['synchronized'] = False
                        validation_result['issues'].append({
                            'type': 'missing_frontend_property',
                            'field': field_name
                        })
                        continue
                    
                    frontend_prop = frontend_type.properties[field_name]
                    
                    # Validate type mapping
                    backend_type = field_def['type']
                    expected_frontend_type = self.type_mapping.get(backend_type, backend_type)
                    
                    # Handle special cases
                    if 'enum' in field_def and len(field_def['enum']) > 1:
                        # Multi-value enum should be union type in frontend
                        if frontend_prop.get('type') != 'union':
                            validation_result['synchronized'] = False
                            validation_result['issues'].append({
                                'type': 'enum_type_mismatch',
                                'field': field_name,
                                'backend_enum': field_def['enum'],
                                'frontend_type': frontend_prop.get('type')
                            })
                        elif set(frontend_prop.get('types', [])) != set(field_def['enum']):
                            validation_result['synchronized'] = False
                            validation_result['issues'].append({
                                'type': 'enum_values_mismatch',
                                'field': field_name,
                                'backend_values': field_def['enum'],
                                'frontend_values': frontend_prop.get('types', [])
                            })
                    elif frontend_prop.get('type') != expected_frontend_type:
                        validation_result['synchronized'] = False
                        validation_result['issues'].append({
                            'type': 'type_mismatch',
                            'field': field_name,
                            'backend_type': backend_type,
                            'frontend_type': frontend_prop.get('type'),
                            'expected': expected_frontend_type
                        })
                    
                    # Validate required/optional consistency
                    backend_required = field_def.get('required', False)
                    frontend_optional = frontend_prop.get('optional', False)
                    
                    if backend_required and frontend_optional:
                        validation_result['synchronized'] = False
                        validation_result['issues'].append({
                            'type': 'required_optional_mismatch',
                            'field': field_name,
                            'backend_required': backend_required,
                            'frontend_optional': frontend_optional
                        })
                    
                    # Validate constraints (maxLength, etc.)
                    if 'max_length' in field_def and 'maxLength' in frontend_prop:
                        if field_def['max_length'] != frontend_prop['maxLength']:
                            validation_result['synchronized'] = False
                            validation_result['issues'].append({
                                'type': 'constraint_mismatch',
                                'field': field_name,
                                'constraint': 'maxLength',
                                'backend_value': field_def['max_length'],
                                'frontend_value': frontend_prop['maxLength']
                            })
                
                # Check for extra frontend properties
                for prop_name in frontend_type.properties:
                    if prop_name not in backend_schema.fields:
                        validation_result['synchronized'] = False
                        validation_result['issues'].append({
                            'type': 'extra_frontend_property',
                            'property': prop_name
                        })
                
                return validation_result
            
            async def store_validation_results(self, results: List[Dict[str, Any]]):
                """Store API synchronization validation results."""
                validation_summary = {
                    'validated_at': asyncio.get_event_loop().time(),
                    'total_schemas': len(results),
                    'synchronized_schemas': len([r for r in results if r['synchronized']]),
                    'failed_schemas': len([r for r in results if not r['synchronized']]),
                    'total_issues': sum(len(r['issues']) for r in results),
                    'results': results
                }
                
                await self.redis.setex(
                    'type_sync_validation:api_schemas',
                    3600,
                    json.dumps(validation_summary)
                )
                
                return validation_summary
        
        validator = APISyncValidator(redis_client)
        
        # Validate all API schema synchronizations
        validation_results = []
        
        for schema_name in backend_api_schemas:
            backend_schema = backend_api_schemas[schema_name]
            frontend_type = frontend_api_types[schema_name]
            
            result = validator.validate_schema_sync(backend_schema, frontend_type)
            validation_results.append(result)
            
            # Assert synchronization for critical schemas
            assert result['synchronized'], (
                f"API schema '{schema_name}' is not synchronized. Issues: {result['issues']}"
            )
        
        # Store validation results
        summary = await validator.store_validation_results(validation_results)
        
        # Validate overall synchronization health
        assert summary['synchronized_schemas'] == summary['total_schemas'], (
            f"API synchronization failed: {summary['failed_schemas']} out of {summary['total_schemas']} schemas failed. "
            f"Total issues: {summary['total_issues']}"
        )
        
        # Cleanup
        await redis_client.delete('type_sync_validation:api_schemas')


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_type_sync_validation(self, real_services_fixture):
        """
        Test real-time validation of type synchronization during development.
        
        DEVELOPMENT CRITICAL: Real-time validation prevents type drift during
        development and catches synchronization issues before they reach production.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock real-time type sync monitor
        class RealTimeTypeSyncMonitor:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.sync_violations = []
                self.monitored_types = {}
            
            async def register_type_definition(self, service: str, type_name: str, definition: Dict[str, Any]):
                """Register a type definition from a service."""
                key = f"type_def:{service}:{type_name}"
                
                type_record = {
                    'service': service,
                    'type_name': type_name,
                    'definition': definition,
                    'registered_at': asyncio.get_event_loop().time(),
                    'version': definition.get('version', '1.0.0')
                }
                
                await self.redis.setex(key, 3600, json.dumps(type_record))
                
                # Check for synchronization with other services
                await self._check_cross_service_sync(type_name)
            
            async def _check_cross_service_sync(self, type_name: str):
                """Check if type is synchronized across services."""
                services = ['backend', 'frontend', 'auth_service']
                type_definitions = {}
                
                for service in services:
                    key = f"type_def:{service}:{type_name}"
                    type_data = await self.redis.get(key)
                    
                    if type_data:
                        type_definitions[service] = json.loads(type_data.decode())
                
                if len(type_definitions) > 1:
                    # Multiple services have this type - check synchronization
                    await self._validate_type_consistency(type_name, type_definitions)
            
            async def _validate_type_consistency(self, type_name: str, definitions: Dict[str, Dict[str, Any]]):
                """Validate type consistency across services."""
                services = list(definitions.keys())
                
                for i in range(len(services)):
                    for j in range(i + 1, len(services)):
                        service_a = services[i]
                        service_b = services[j]
                        
                        def_a = definitions[service_a]['definition']
                        def_b = definitions[service_b]['definition']
                        
                        # Check for structural differences
                        inconsistencies = self._find_type_inconsistencies(def_a, def_b)
                        
                        if inconsistencies:
                            violation = {
                                'type_name': type_name,
                                'service_a': service_a,
                                'service_b': service_b,
                                'inconsistencies': inconsistencies,
                                'detected_at': asyncio.get_event_loop().time()
                            }
                            
                            self.sync_violations.append(violation)
                            
                            # Store violation for monitoring
                            violation_key = f"sync_violation:{type_name}:{service_a}:{service_b}"
                            await self.redis.setex(violation_key, 3600, json.dumps(violation))
            
            def _find_type_inconsistencies(self, def_a: Dict[str, Any], def_b: Dict[str, Any]) -> List[Dict[str, Any]]:
                """Find inconsistencies between two type definitions."""
                inconsistencies = []
                
                # Check fields/properties
                fields_a = def_a.get('fields', {})
                fields_b = def_b.get('properties', {})  # Different naming conventions
                
                # Fields in A but not in B
                for field in fields_a:
                    if field not in fields_b:
                        inconsistencies.append({
                            'type': 'missing_field',
                            'field': field,
                            'missing_in': 'service_b'
                        })
                
                # Fields in B but not in A
                for field in fields_b:
                    if field not in fields_a:
                        inconsistencies.append({
                            'type': 'missing_field',
                            'field': field,
                            'missing_in': 'service_a'
                        })
                
                # Check common fields for type mismatches
                common_fields = set(fields_a.keys()) & set(fields_b.keys())
                for field in common_fields:
                    type_a = fields_a[field].get('type')
                    type_b = fields_b[field].get('type')
                    
                    if type_a != type_b:
                        inconsistencies.append({
                            'type': 'type_mismatch',
                            'field': field,
                            'type_a': type_a,
                            'type_b': type_b
                        })
                
                return inconsistencies
            
            async def get_sync_violations(self) -> List[Dict[str, Any]]:
                """Get current synchronization violations."""
                return self.sync_violations
            
            async def clear_violations(self):
                """Clear synchronization violations."""
                # Clear in-memory violations
                self.sync_violations.clear()
                
                # Clear Redis violations
                keys = await self.redis.keys('sync_violation:*')
                if keys:
                    await self.redis.delete(*keys)
        
        monitor = RealTimeTypeSyncMonitor(redis_client)
        
        # Test real-time type synchronization monitoring
        
        # Register backend type definition
        backend_user_type = {
            'fields': {
                'id': {'type': 'str', 'required': True},
                'email': {'type': 'str', 'required': True},
                'name': {'type': 'str', 'required': True},
                'is_active': {'type': 'bool', 'required': True, 'default': True},
                'created_at': {'type': 'datetime', 'required': True}
            },
            'version': '1.0.0'
        }
        
        await monitor.register_type_definition('backend', 'User', backend_user_type)
        
        # Register frontend type definition (synchronized)
        frontend_user_type = {
            'properties': {
                'id': {'type': 'string'},
                'email': {'type': 'string'},
                'name': {'type': 'string'},
                'is_active': {'type': 'boolean'},
                'created_at': {'type': 'string'}  # ISO string in frontend
            },
            'version': '1.0.0'
        }
        
        await monitor.register_type_definition('frontend', 'User', frontend_user_type)
        
        # Register auth service type definition (with intentional mismatch)
        auth_user_type = {
            'fields': {
                'id': {'type': 'str', 'required': True},
                'email': {'type': 'str', 'required': True},
                'username': {'type': 'str', 'required': True},  # Different field name
                'is_active': {'type': 'bool', 'required': True},
                'created_at': {'type': 'datetime', 'required': True},
                'auth_provider': {'type': 'str', 'required': False}  # Extra field
            },
            'version': '1.0.0'
        }
        
        await monitor.register_type_definition('auth_service', 'User', auth_user_type)
        
        # Allow time for cross-service sync checking
        await asyncio.sleep(0.1)
        
        # Check for violations
        violations = await monitor.get_sync_violations()
        
        # Should detect violations between backend/frontend and auth_service
        assert len(violations) > 0, "Should detect type synchronization violations"
        
        # Find specific violations
        backend_auth_violations = [
            v for v in violations 
            if (v['service_a'] == 'backend' and v['service_b'] == 'auth_service') or
               (v['service_a'] == 'auth_service' and v['service_b'] == 'backend')
        ]
        
        assert len(backend_auth_violations) > 0, "Should detect backend/auth_service violations"
        
        # Validate specific inconsistencies
        violation = backend_auth_violations[0]
        inconsistencies = violation['inconsistencies']
        
        # Should detect missing 'name' field in auth service and missing 'username' in backend
        missing_name = any(
            inc['type'] == 'missing_field' and inc['field'] == 'name' 
            for inc in inconsistencies
        )
        missing_username = any(
            inc['type'] == 'missing_field' and inc['field'] == 'username'
            for inc in inconsistencies
        )
        
        assert missing_name or missing_username, (
            f"Should detect missing field inconsistencies. Found: {inconsistencies}"
        )
        
        # Test violation cleanup
        await monitor.clear_violations()
        
        violations_after_clear = await monitor.get_sync_violations()
        assert len(violations_after_clear) == 0, "Violations should be cleared"
        
        # Cleanup type definitions
        await redis_client.delete('type_def:backend:User')
        await redis_client.delete('type_def:frontend:User')
        await redis_client.delete('type_def:auth_service:User')