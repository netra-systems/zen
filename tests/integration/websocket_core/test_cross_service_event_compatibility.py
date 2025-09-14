#!/usr/bin/env python
"""Cross-Service Event Compatibility Test

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Service Integration
- Business Goal: $500K+ ARR protection through service interoperability
- Value Impact: Ensure WebSocket events work consistently across backend, auth, frontend
- Revenue Impact: Prevents service integration failures and system-wide outages

Test Strategy: This test MUST FAIL before SSOT consolidation and PASS after
- FAIL: Currently service-specific event format variations cause integration issues
- PASS: After SSOT consolidation, unified event structure across all services

Issue #1033: WebSocket Manager SSOT Consolidation
This test validates that WebSocket events work consistently across all services
in the Netra Apex platform, ensuring proper microservice integration.
"""

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Set, Any, Optional, Tuple
from enum import Enum
import pytest

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.logging.unified_logging_ssot import get_logger
from test_framework.ssot.base_integration_test import SSotBaseIntegrationTest as BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture

logger = get_logger(__name__)


class ServiceType(Enum):
    """Services in the Netra Apex platform."""
    BACKEND = "netra_backend"
    AUTH = "auth_service" 
    FRONTEND = "frontend"
    TEST_FRAMEWORK = "test_framework"


@dataclass
class ServiceEventCompatibility:
    """Event compatibility assessment between services."""
    service_a: ServiceType
    service_b: ServiceType
    compatible_events: List[str]
    incompatible_events: List[str]
    compatibility_score: float
    issues: List[str]


@dataclass
class EventFormatComparison:
    """Comparison of event formats across services."""
    event_type: str
    service_formats: Dict[ServiceType, Dict[str, Any]]
    format_consistency: bool
    format_differences: List[str]


class TestCrossServiceEventCompatibility(BaseIntegrationTest):
    """Test WebSocket event compatibility across all services.
    
    This test suite validates that WebSocket events maintain compatibility
    across the microservice architecture to ensure reliable system integration.
    """

    @pytest.mark.integration
    @pytest.mark.cross_service
    async def test_websocket_event_format_compatibility(self, real_services_fixture):
        """Test that WebSocket event formats are compatible across services.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently different services create incompatible event formats
        - PASS: After SSOT consolidation, all services use compatible formats
        
        This test validates that events created in one service can be properly
        consumed by other services in the platform.
        """
        logger.info("🔍 Testing WebSocket event format compatibility across services...")
        
        # Services to test for event compatibility
        services_to_test = [
            ServiceType.BACKEND,
            ServiceType.AUTH,
            ServiceType.TEST_FRAMEWORK
        ]
        
        # Critical events that must be compatible across services
        critical_events = [
            "user_authenticated",
            "agent_started", 
            "agent_completed",
            "websocket_connected",
            "websocket_disconnected",
            "error_occurred"
        ]
        
        compatibility_issues = []
        
        for event_type in critical_events:
            logger.info(f"Testing compatibility for event: {event_type}")
            
            # Get event format samples from each service
            service_formats = {}
            for service in services_to_test:
                try:
                    event_format = await self._get_service_event_format(service, event_type)
                    if event_format:
                        service_formats[service] = event_format
                except Exception as e:
                    logger.warning(f"Could not get {event_type} format from {service.value}: {e}")
            
            if len(service_formats) < 2:
                logger.warning(f"Only {len(service_formats)} services provide {event_type}, skipping compatibility test")
                continue
            
            # Analyze format compatibility
            format_analysis = self._analyze_event_format_compatibility(event_type, service_formats)
            
            if not format_analysis.format_consistency:
                compatibility_issues.append({
                    "event_type": event_type,
                    "services": list(service_formats.keys()),
                    "differences": format_analysis.format_differences
                })
        
        if compatibility_issues:
            logger.error("SSOT VIOLATIONS: Cross-service event format compatibility issues:")
            for issue in compatibility_issues:
                logger.error(f"  - Event '{issue['event_type']}': {len(issue['differences'])} format differences")
                for diff in issue['differences'][:3]:  # Show first 3 differences
                    logger.error(f"    * {diff}")
        
        # SSOT VIOLATION CHECK: All services should use compatible event formats
        # This assertion WILL FAIL until event format standardization is complete
        assert len(compatibility_issues) == 0, (
            f"SSOT VIOLATION: Found {len(compatibility_issues)} cross-service event format incompatibilities. "
            f"All services must use compatible WebSocket event formats."
        )

    @pytest.mark.integration
    @pytest.mark.cross_service 
    async def test_service_event_consumption_compatibility(self, real_services_fixture):
        """Test that services can consume events created by other services.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently services cannot properly parse each other's events
        - PASS: After SSOT consolidation, all services parse all event formats
        
        This test validates that the event parsing logic in each service
        can handle events created by other services.
        """
        logger.info("🔍 Testing cross-service event consumption compatibility...")
        
        # Create test events from different services
        test_events = await self._create_cross_service_test_events()
        
        consumption_failures = []
        
        for producer_service, events in test_events.items():
            for consumer_service in [ServiceType.BACKEND, ServiceType.AUTH]:
                if producer_service == consumer_service:
                    continue
                
                logger.info(f"Testing {consumer_service.value} consuming {producer_service.value} events")
                
                for event in events:
                    try:
                        consumption_result = await self._test_event_consumption(
                            consumer_service, event, producer_service
                        )
                        
                        if not consumption_result['success']:
                            consumption_failures.append({
                                'producer': producer_service.value,
                                'consumer': consumer_service.value,
                                'event_type': event.get('event_type', 'unknown'),
                                'error': consumption_result.get('error', 'unknown error'),
                                'event_sample': event
                            })
                            
                    except Exception as e:
                        consumption_failures.append({
                            'producer': producer_service.value,
                            'consumer': consumer_service.value,
                            'event_type': event.get('event_type', 'unknown'),
                            'error': str(e),
                            'event_sample': event
                        })
        
        if consumption_failures:
            logger.error("SSOT VIOLATIONS: Cross-service event consumption failures:")
            for failure in consumption_failures[:10]:  # Show first 10 failures
                logger.error(f"  - {failure['consumer']} cannot consume {failure['producer']} {failure['event_type']}: {failure['error']}")
        
        # SSOT VIOLATION CHECK: All services should consume all event formats
        # This assertion WILL FAIL until consumption compatibility is achieved
        assert len(consumption_failures) == 0, (
            f"SSOT VIOLATION: Found {len(consumption_failures)} cross-service event consumption failures. "
            f"All services must be able to consume events from other services."
        )

    @pytest.mark.integration
    @pytest.mark.cross_service
    async def test_websocket_connection_interoperability(self, real_services_fixture):
        """Test WebSocket connection interoperability across services.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently WebSocket connections can't be shared between services
        - PASS: After SSOT consolidation, WebSocket state is shared properly
        
        This test validates that WebSocket connection state is properly
        shared and synchronized across all services in the platform.
        """
        logger.info("🔍 Testing WebSocket connection interoperability...")
        
        # Import WebSocket managers from different services  
        websocket_managers = await self._get_websocket_managers_from_services()
        
        if len(websocket_managers) < 2:
            pytest.skip("Need at least 2 WebSocket managers from different services")
        
        # Create a test connection through one service
        test_user_id = f"interop_user_{uuid.uuid4().hex[:8]}"
        test_connection_id = f"interop_conn_{uuid.uuid4().hex[:8]}"
        
        interoperability_issues = []
        
        # Establish connection through first manager
        primary_service = list(websocket_managers.keys())[0]
        primary_manager = websocket_managers[primary_service]
        
        try:
            if hasattr(primary_manager, 'add_connection'):
                await primary_manager.add_connection(test_connection_id, test_user_id)
            elif hasattr(primary_manager, 'connect'):
                await primary_manager.connect(test_connection_id, test_user_id)
                
            logger.info(f"Connection established via {primary_service.value}")
        except Exception as e:
            pytest.skip(f"Could not establish connection via {primary_service.value}: {e}")
        
        # Test if other services can see/interact with this connection
        for service, manager in websocket_managers.items():
            if service == primary_service:
                continue
                
            try:
                # Test if this service can see the connection
                connection_visible = await self._test_connection_visibility(
                    manager, test_connection_id, test_user_id
                )
                
                if not connection_visible:
                    interoperability_issues.append(
                        f"Service {service.value} cannot see connection created by {primary_service.value}"
                    )
                
                # Test if this service can send messages to the connection
                message_success = await self._test_cross_service_messaging(
                    manager, test_connection_id, f"test_message_from_{service.value}"
                )
                
                if not message_success:
                    interoperability_issues.append(
                        f"Service {service.value} cannot send messages to {primary_service.value} connection"
                    )
                    
            except Exception as e:
                interoperability_issues.append(
                    f"Service {service.value} interoperability test failed: {str(e)}"
                )
        
        if interoperability_issues:
            logger.error("SSOT VIOLATIONS: WebSocket connection interoperability issues:")
            for issue in interoperability_issues:
                logger.error(f"  - {issue}")
        
        # SSOT VIOLATION CHECK: WebSocket connections should be interoperable
        # This assertion WILL FAIL until connection interoperability is achieved
        assert len(interoperability_issues) == 0, (
            f"SSOT VIOLATION: Found {len(interoperability_issues)} WebSocket interoperability issues. "
            f"WebSocket connections must be interoperable across all services."
        )

    @pytest.mark.integration
    @pytest.mark.cross_service
    async def test_event_schema_validation_consistency(self, real_services_fixture):
        """Test that event schema validation is consistent across services.
        
        EXPECTED BEHAVIOR:
        - FAIL: Currently different services accept/reject different event formats
        - PASS: After SSOT consolidation, consistent validation across all services
        
        This test validates that all services apply the same validation rules
        to WebSocket events to ensure consistent behavior.
        """
        logger.info("🔍 Testing event schema validation consistency across services...")
        
        # Test events with various validation scenarios
        validation_test_cases = [
            {
                "name": "valid_canonical_event",
                "event": {
                    "event_type": "test_event",
                    "timestamp": time.time(),
                    "user_id": "test_user_123",
                    "thread_id": "test_thread_456",
                    "data": {"test": "data"}
                },
                "should_be_valid": True
            },
            {
                "name": "missing_required_fields",
                "event": {
                    "event_type": "test_event",
                    # Missing timestamp and user_id
                    "data": {"test": "data"}
                },
                "should_be_valid": False
            },
            {
                "name": "invalid_timestamp_type",
                "event": {
                    "event_type": "test_event", 
                    "timestamp": "not_a_number",  # Should be numeric
                    "user_id": "test_user_123"
                },
                "should_be_valid": False
            },
            {
                "name": "legacy_event_format",
                "event": {
                    "type": "test_event",  # Legacy field name
                    "time": time.time(),   # Legacy field name
                    "user": "test_user_123"  # Legacy field name
                },
                "should_be_valid": False  # Should be rejected by canonical validation
            }
        ]
        
        validation_inconsistencies = []
        
        for test_case in validation_test_cases:
            logger.info(f"Testing validation consistency for: {test_case['name']}")
            
            # Test validation across different services
            service_validation_results = {}
            
            try:
                # Get validation results from each service
                for service in [ServiceType.BACKEND, ServiceType.AUTH]:
                    validation_result = await self._test_event_validation(
                        service, test_case['event'], test_case['name']
                    )
                    service_validation_results[service] = validation_result
                
                # Check for consistency across services
                validation_outcomes = set(
                    result.get('is_valid', False) 
                    for result in service_validation_results.values()
                )
                
                if len(validation_outcomes) > 1:
                    # Services disagree on validation
                    validation_inconsistencies.append({
                        "test_case": test_case['name'],
                        "expected_valid": test_case['should_be_valid'],
                        "service_results": service_validation_results,
                        "issue": "Services disagree on validation outcome"
                    })
                
                # Check if validation outcome matches expected
                actual_outcome = list(validation_outcomes)[0] if validation_outcomes else False
                if actual_outcome != test_case['should_be_valid']:
                    validation_inconsistencies.append({
                        "test_case": test_case['name'],
                        "expected_valid": test_case['should_be_valid'],
                        "actual_valid": actual_outcome,
                        "issue": "Validation outcome doesn't match expected result"
                    })
                    
            except Exception as e:
                validation_inconsistencies.append({
                    "test_case": test_case['name'],
                    "error": str(e),
                    "issue": "Validation testing failed"
                })
        
        if validation_inconsistencies:
            logger.error("SSOT VIOLATIONS: Event schema validation inconsistencies:")
            for inconsistency in validation_inconsistencies:
                logger.error(f"  - {inconsistency['test_case']}: {inconsistency['issue']}")
        
        # SSOT VIOLATION CHECK: Event validation should be consistent across services
        # This assertion WILL FAIL until validation consistency is achieved
        assert len(validation_inconsistencies) == 0, (
            f"SSOT VIOLATION: Found {len(validation_inconsistencies)} event validation inconsistencies. "
            f"All services must apply consistent event validation rules."
        )

    async def _get_service_event_format(self, service: ServiceType, event_type: str) -> Optional[Dict[str, Any]]:
        """Get the event format used by a specific service for a specific event type."""
        # This would normally interface with actual service implementations
        # For testing, we return mock formats that represent current variations
        
        service_event_formats = {
            ServiceType.BACKEND: {
                "user_authenticated": {
                    "event_type": "user_authenticated",
                    "timestamp": 1633024800.123,
                    "user_id": "user_123",
                    "data": {"token": "jwt_token", "session_id": "session_456"}
                },
                "agent_started": {
                    "event_type": "agent_started",
                    "timestamp": 1633024801.456,
                    "user_id": "user_123",
                    "thread_id": "thread_789",
                    "data": {"agent_name": "cost_optimizer"}
                }
            },
            ServiceType.AUTH: {
                "user_authenticated": {
                    "type": "auth_success",  # Different field name
                    "time": "2023-10-01T10:00:00Z",  # String timestamp
                    "user": "user_123",  # Different field name
                    "token": "jwt_token",  # Flat structure
                    "session": "session_456"  # Flat structure
                },
                "websocket_connected": {
                    "event_type": "websocket_connected",
                    "timestamp": 1633024800,
                    "user_id": "user_123",
                    "connection_id": "conn_123"
                }
            },
            ServiceType.TEST_FRAMEWORK: {
                "agent_started": {
                    "event_type": "agent_started",
                    "timestamp": 1633024801,  # Integer timestamp
                    "user_id": "user_123",
                    "payload": {"agent_name": "cost_optimizer"}  # Different field name
                }
            }
        }
        
        return service_event_formats.get(service, {}).get(event_type)

    def _analyze_event_format_compatibility(self, event_type: str, service_formats: Dict[ServiceType, Dict[str, Any]]) -> EventFormatComparison:
        """Analyze compatibility of event formats across services."""
        format_differences = []
        
        if len(service_formats) < 2:
            return EventFormatComparison(
                event_type=event_type,
                service_formats=service_formats,
                format_consistency=True,
                format_differences=[]
            )
        
        # Get field sets from each service
        service_field_sets = {
            service: set(event_format.keys())
            for service, event_format in service_formats.items()
        }
        
        # Check for field name differences
        all_fields = set()
        for fields in service_field_sets.values():
            all_fields.update(fields)
        
        for field in all_fields:
            services_with_field = [
                service for service, fields in service_field_sets.items() 
                if field in fields
            ]
            
            if len(services_with_field) != len(service_formats):
                missing_services = [
                    service for service in service_formats.keys() 
                    if service not in services_with_field
                ]
                format_differences.append(
                    f"Field '{field}' missing in services: {[s.value for s in missing_services]}"
                )
        
        # Check for data type differences
        common_fields = set.intersection(*service_field_sets.values())
        for field in common_fields:
            field_types = set()
            for service, event_format in service_formats.items():
                field_types.add(type(event_format[field]))
            
            if len(field_types) > 1:
                format_differences.append(
                    f"Field '{field}' has different types across services: {field_types}"
                )
        
        return EventFormatComparison(
            event_type=event_type,
            service_formats=service_formats,
            format_consistency=len(format_differences) == 0,
            format_differences=format_differences
        )

    async def _create_cross_service_test_events(self) -> Dict[ServiceType, List[Dict[str, Any]]]:
        """Create test events representing what each service might produce."""
        return {
            ServiceType.BACKEND: [
                {
                    "event_type": "agent_completed",
                    "timestamp": time.time(),
                    "user_id": "test_user_backend",
                    "thread_id": "thread_123",
                    "data": {"result": {"recommendations": ["test"]}}
                }
            ],
            ServiceType.AUTH: [
                {
                    "type": "user_logout",  # Legacy format
                    "time": "2023-10-01T10:00:00Z",
                    "user": "test_user_auth",
                    "session_ended": True
                }
            ]
        }

    async def _test_event_consumption(self, consumer_service: ServiceType, event: Dict[str, Any], producer_service: ServiceType) -> Dict[str, Any]:
        """Test if a service can consume an event from another service."""
        try:
            # This would normally test actual service event consumption
            # For testing, we simulate consumption based on format compatibility
            
            required_fields = ["event_type", "timestamp", "user_id"]
            
            # Check if event has required fields in expected format
            for field in required_fields:
                if field not in event:
                    # Check for legacy field names
                    legacy_mapping = {
                        "event_type": ["type", "event"],
                        "timestamp": ["time", "when"],
                        "user_id": ["user", "user"]
                    }
                    
                    legacy_found = False
                    for legacy_field in legacy_mapping.get(field, []):
                        if legacy_field in event:
                            legacy_found = True
                            break
                    
                    if not legacy_found:
                        return {
                            "success": False,
                            "error": f"Missing required field: {field}"
                        }
            
            # Check timestamp format
            timestamp_field = event.get("timestamp") or event.get("time")
            if timestamp_field and isinstance(timestamp_field, str):
                return {
                    "success": False,
                    "error": "String timestamp not supported by consumer service"
                }
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_websocket_managers_from_services(self) -> Dict[ServiceType, Any]:
        """Get WebSocket managers from different services."""
        managers = {}
        
        try:
            # Try to import backend WebSocket manager
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            managers[ServiceType.BACKEND] = WebSocketManager()
        except ImportError as e:
            logger.warning(f"Could not import backend WebSocket manager: {e}")
        
        # Add other service managers if available
        # This would be expanded with actual service imports
        
        return managers

    async def _test_connection_visibility(self, manager: Any, connection_id: str, user_id: str) -> bool:
        """Test if a WebSocket manager can see a connection created by another manager."""
        try:
            if hasattr(manager, 'get_connection'):
                connection = await manager.get_connection(connection_id)
                return connection is not None
            elif hasattr(manager, 'has_connection'):
                return await manager.has_connection(connection_id)
            else:
                return False
        except Exception:
            return False

    async def _test_cross_service_messaging(self, manager: Any, connection_id: str, message: str) -> bool:
        """Test if a manager can send messages to connections created by other managers."""
        try:
            test_message = {
                "type": "cross_service_test",
                "message": message,
                "timestamp": time.time()
            }
            
            if hasattr(manager, 'send_message'):
                await manager.send_message(connection_id, test_message)
                return True
            elif hasattr(manager, 'emit_event'):
                await manager.emit_event(connection_id, "test", test_message)
                return True
            else:
                return False
        except Exception:
            return False

    async def _test_event_validation(self, service: ServiceType, event: Dict[str, Any], test_name: str) -> Dict[str, Any]:
        """Test event validation by a specific service."""
        try:
            # This would normally call actual service validation
            # For testing, we simulate validation based on canonical requirements
            
            required_fields = ["event_type", "timestamp", "user_id"]
            validation_errors = []
            
            # Check required fields
            for field in required_fields:
                if field not in event:
                    validation_errors.append(f"Missing required field: {field}")
            
            # Check field types
            if "timestamp" in event:
                if not isinstance(event["timestamp"], (int, float)):
                    validation_errors.append("timestamp must be numeric")
            
            if "user_id" in event:
                if not isinstance(event["user_id"], str):
                    validation_errors.append("user_id must be string")
            
            return {
                "is_valid": len(validation_errors) == 0,
                "errors": validation_errors
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [str(e)]
            }


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])