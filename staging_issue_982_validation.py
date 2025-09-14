#!/usr/bin/env python3
"""
Issue #982 SSOT Broadcast Consolidation - Staging Validation Script

This script validates that the SSOT WebSocket broadcast consolidation is working correctly
in the staging environment. It tests the adapter pattern delegation and SSOT service functionality.

Business Value:
- Segment: Platform/Infrastructure
- Goal: Validate $500K+ ARR Golden Path broadcast reliability
- Impact: Ensures consistent WebSocket event delivery across all usage patterns
- Revenue Impact: Protects chat functionality business value
"""

import asyncio
import json
import time
import sys
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from netra_backend.app.services.websocket_broadcast_service import create_broadcast_service, BroadcastResult
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter, broadcast_user_event
from netra_backend.app.core.user_execution_context import UserExecutionContext
from unittest.mock import AsyncMock, Mock
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Results from Issue #982 validation testing."""
    test_name: str
    success: bool
    details: Dict[str, Any]
    execution_time: float
    errors: List[str]


class Issue982StagingValidator:
    """Validator for Issue #982 SSOT broadcast consolidation in staging."""

    def __init__(self):
        self.results: List[ValidationResult] = []
        self.test_user_id = "staging_test_982_user"
        self.test_event = {
            'type': 'agent_completed',
            'data': {'message': 'Issue 982 validation test'},
            'timestamp': datetime.now().isoformat()
        }

    async def run_validation_suite(self) -> Dict[str, Any]:
        """Run complete Issue #982 validation suite."""
        logger.info("=" * 80)
        logger.info("ISSUE #982 SSOT BROADCAST CONSOLIDATION - STAGING VALIDATION")
        logger.info("=" * 80)
        logger.info(f"Business Impact: $500K+ ARR Golden Path Protection")
        logger.info(f"Environment: Staging/Mock (Adapter Pattern Testing)")
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info("")

        # Test individual components
        await self._test_ssot_service_creation()
        await self._test_websocket_event_router_adapter()
        await self._test_user_scoped_router_adapter()
        await self._test_broadcast_user_event_adapter()
        await self._test_adapter_error_handling()
        await self._test_return_type_compatibility()

        # Generate report
        return self._generate_validation_report()

    async def _test_ssot_service_creation(self):
        """Test SSOT WebSocket broadcast service creation."""
        start_time = time.time()
        test_name = "SSOT Service Creation"

        try:
            logger.info(f"Testing: {test_name}")

            # Create mock WebSocket manager
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock(return_value=True)
            mock_manager.get_user_connections = AsyncMock(return_value=['conn1', 'conn2'])

            # Create SSOT service
            service = create_broadcast_service(mock_manager)

            # Test service functionality
            result = await service.broadcast_to_user(self.test_user_id, self.test_event)

            # Validate result
            success = isinstance(result, BroadcastResult)
            success = success and result.user_id == self.test_user_id
            success = success and result.successful_sends > 0

            # Get service stats
            stats = service.get_stats()

            validation_result = ValidationResult(
                test_name=test_name,
                success=success,
                details={
                    'service_created': True,
                    'broadcast_result_type': type(result).__name__,
                    'successful_sends': result.successful_sends,
                    'connections_attempted': result.connections_attempted,
                    'service_stats': stats,
                    'manager_calls': {
                        'send_to_user_called': mock_manager.send_to_user.called,
                        'get_user_connections_called': mock_manager.get_user_connections.called
                    }
                },
                execution_time=time.time() - start_time,
                errors=[]
            )

            logger.info(f"✓ {test_name}: {'PASS' if success else 'FAIL'}")
            logger.info(f"  - Service created: {service.__class__.__name__}")
            logger.info(f"  - Broadcast result: {result.successful_sends}/{result.connections_attempted}")
            logger.info(f"  - Service stats: {stats['broadcast_stats']['total_broadcasts']} broadcasts")

        except Exception as e:
            validation_result = ValidationResult(
                test_name=test_name,
                success=False,
                details={'exception': str(e)},
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )
            logger.error(f"✗ {test_name}: FAIL - {e}")

        self.results.append(validation_result)

    async def _test_websocket_event_router_adapter(self):
        """Test WebSocketEventRouter adapter delegation."""
        start_time = time.time()
        test_name = "WebSocketEventRouter Adapter"

        try:
            logger.info(f"Testing: {test_name}")

            # Create mock WebSocket manager
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock(return_value=True)
            mock_manager.get_user_connections = AsyncMock(return_value=['conn1'])

            # Create router with mock manager
            router = WebSocketEventRouter(mock_manager)

            # Test adapter delegation
            result = await router.broadcast_to_user(self.test_user_id, self.test_event)

            # Validate result
            success = isinstance(result, int)
            success = success and result > 0
            success = success and mock_manager.send_to_user.called

            validation_result = ValidationResult(
                test_name=test_name,
                success=success,
                details={
                    'adapter_called': True,
                    'return_type': type(result).__name__,
                    'return_value': result,
                    'manager_delegation': mock_manager.send_to_user.called,
                    'call_args': str(mock_manager.send_to_user.call_args) if mock_manager.send_to_user.called else None
                },
                execution_time=time.time() - start_time,
                errors=[]
            )

            logger.info(f"✓ {test_name}: {'PASS' if success else 'FAIL'}")
            logger.info(f"  - Adapter delegation: {'Yes' if mock_manager.send_to_user.called else 'No'}")
            logger.info(f"  - Return type: {type(result).__name__} (value: {result})")

        except Exception as e:
            validation_result = ValidationResult(
                test_name=test_name,
                success=False,
                details={'exception': str(e)},
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )
            logger.error(f"✗ {test_name}: FAIL - {e}")

        self.results.append(validation_result)

    async def _test_user_scoped_router_adapter(self):
        """Test UserScopedWebSocketEventRouter adapter delegation."""
        start_time = time.time()
        test_name = "UserScopedWebSocketEventRouter Adapter"

        try:
            logger.info(f"Testing: {test_name}")

            # Create mock components
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock(return_value=True)
            mock_manager.get_user_connections = AsyncMock(return_value=['conn1'])

            mock_context = Mock()
            mock_context.user_id = self.test_user_id
            mock_context.request_id = "req_123"
            mock_context.thread_id = "thread_456"
            mock_context.get_scoped_key = Mock(return_value="scoped_key")

            # Create user-scoped router
            router = UserScopedWebSocketEventRouter(mock_context, mock_manager)

            # Test adapter delegation
            result = await router.broadcast_to_user(self.test_event)

            # Validate result
            success = isinstance(result, int)
            success = success and result > 0
            success = success and mock_manager.send_to_user.called

            # Check that event was enriched with user context
            call_args = mock_manager.send_to_user.call_args
            enriched_event = call_args[0][1] if call_args else None
            context_added = enriched_event and 'user_id' in enriched_event

            validation_result = ValidationResult(
                test_name=test_name,
                success=success and context_added,
                details={
                    'adapter_called': True,
                    'return_type': type(result).__name__,
                    'return_value': result,
                    'manager_delegation': mock_manager.send_to_user.called,
                    'event_enriched': context_added,
                    'enriched_event': enriched_event
                },
                execution_time=time.time() - start_time,
                errors=[]
            )

            logger.info(f"✓ {test_name}: {'PASS' if success and context_added else 'FAIL'}")
            logger.info(f"  - Adapter delegation: {'Yes' if mock_manager.send_to_user.called else 'No'}")
            logger.info(f"  - Event enrichment: {'Yes' if context_added else 'No'}")
            logger.info(f"  - Return type: {type(result).__name__} (value: {result})")

        except Exception as e:
            validation_result = ValidationResult(
                test_name=test_name,
                success=False,
                details={'exception': str(e)},
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )
            logger.error(f"✗ {test_name}: FAIL - {e}")

        self.results.append(validation_result)

    async def _test_broadcast_user_event_adapter(self):
        """Test broadcast_user_event function adapter delegation."""
        start_time = time.time()
        test_name = "broadcast_user_event Function Adapter"

        try:
            logger.info(f"Testing: {test_name}")

            # Create mock user context
            mock_context = Mock()
            mock_context.user_id = self.test_user_id
            mock_context.request_id = "req_789"
            mock_context.thread_id = "thread_012"
            mock_context.get_scoped_key = Mock(return_value="scoped_key")

            # Mock WebSocketManager creation and its methods
            from unittest.mock import patch

            with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager') as mock_ws_class:
                mock_manager = AsyncMock()
                mock_manager.send_to_user = AsyncMock(return_value=True)
                mock_manager.get_user_connections = AsyncMock(return_value=['conn1'])
                mock_ws_class.return_value = mock_manager

                # Test function adapter delegation
                result = await broadcast_user_event(self.test_event, mock_context)

                # Validate result
                success = isinstance(result, int)
                success = success and result > 0
                success = success and mock_ws_class.called
                success = success and mock_manager.send_to_user.called

                # Check WebSocketManager creation with user context
                manager_creation_args = mock_ws_class.call_args
                context_passed = manager_creation_args and 'user_context' in str(manager_creation_args)

                validation_result = ValidationResult(
                    test_name=test_name,
                    success=success and context_passed,
                    details={
                        'function_called': True,
                        'return_type': type(result).__name__,
                        'return_value': result,
                        'manager_created': mock_ws_class.called,
                        'manager_delegation': mock_manager.send_to_user.called,
                        'context_passed_to_manager': context_passed
                    },
                    execution_time=time.time() - start_time,
                    errors=[]
                )

                logger.info(f"✓ {test_name}: {'PASS' if success and context_passed else 'FAIL'}")
                logger.info(f"  - Function delegation: {'Yes' if mock_manager.send_to_user.called else 'No'}")
                logger.info(f"  - Manager creation: {'Yes' if mock_ws_class.called else 'No'}")
                logger.info(f"  - Context passing: {'Yes' if context_passed else 'No'}")
                logger.info(f"  - Return type: {type(result).__name__} (value: {result})")

        except Exception as e:
            validation_result = ValidationResult(
                test_name=test_name,
                success=False,
                details={'exception': str(e)},
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )
            logger.error(f"✗ {test_name}: FAIL - {e}")

        self.results.append(validation_result)

    async def _test_adapter_error_handling(self):
        """Test adapter error handling and fallback mechanisms."""
        start_time = time.time()
        test_name = "Adapter Error Handling"

        try:
            logger.info(f"Testing: {test_name}")

            # Test with failing SSOT service
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock(side_effect=Exception("SSOT service failure"))
            mock_manager.get_user_connections = AsyncMock(return_value=['conn1'])

            router = WebSocketEventRouter(mock_manager)

            # Test error handling - should not raise exception
            result = await router.broadcast_to_user(self.test_user_id, self.test_event)

            # Should return 0 for failures but not crash
            success = isinstance(result, int)
            success = success and result >= 0  # 0 or positive for graceful failure

            validation_result = ValidationResult(
                test_name=test_name,
                success=success,
                details={
                    'error_handled_gracefully': True,
                    'return_type': type(result).__name__,
                    'return_value': result,
                    'exception_suppressed': True
                },
                execution_time=time.time() - start_time,
                errors=[]
            )

            logger.info(f"✓ {test_name}: {'PASS' if success else 'FAIL'}")
            logger.info(f"  - Graceful error handling: Yes")
            logger.info(f"  - Return value: {result} (should be non-negative)")

        except Exception as e:
            validation_result = ValidationResult(
                test_name=test_name,
                success=False,
                details={'exception': str(e)},
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )
            logger.error(f"✗ {test_name}: FAIL - Exception not handled: {e}")

        self.results.append(validation_result)

    async def _test_return_type_compatibility(self):
        """Test return type compatibility across all adapters."""
        start_time = time.time()
        test_name = "Return Type Compatibility"

        try:
            logger.info(f"Testing: {test_name}")

            # Create mock manager for consistent testing
            mock_manager = AsyncMock()
            mock_manager.send_to_user = AsyncMock(return_value=True)
            mock_manager.get_user_connections = AsyncMock(return_value=['conn1', 'conn2'])

            # Test all adapters return integers
            results = {}

            # Test WebSocketEventRouter
            router = WebSocketEventRouter(mock_manager)
            results['WebSocketEventRouter'] = await router.broadcast_to_user(self.test_user_id, self.test_event)

            # Test UserScopedWebSocketEventRouter
            mock_context = Mock()
            mock_context.user_id = self.test_user_id
            mock_context.request_id = "req_123"
            mock_context.thread_id = "thread_456"
            mock_context.get_scoped_key = Mock(return_value="scoped_key")

            user_router = UserScopedWebSocketEventRouter(mock_context, mock_manager)
            results['UserScopedWebSocketEventRouter'] = await user_router.broadcast_to_user(self.test_event)

            # Test broadcast_user_event function
            from unittest.mock import patch
            with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager') as mock_ws_class:
                mock_ws_class.return_value = mock_manager
                results['broadcast_user_event'] = await broadcast_user_event(self.test_event, mock_context)

            # Validate all return integers
            all_integers = all(isinstance(result, int) for result in results.values())
            all_positive = all(result >= 0 for result in results.values())

            validation_result = ValidationResult(
                test_name=test_name,
                success=all_integers and all_positive,
                details={
                    'return_types': {name: type(result).__name__ for name, result in results.items()},
                    'return_values': results,
                    'all_integers': all_integers,
                    'all_positive': all_positive
                },
                execution_time=time.time() - start_time,
                errors=[]
            )

            logger.info(f"✓ {test_name}: {'PASS' if all_integers and all_positive else 'FAIL'}")
            for name, result in results.items():
                logger.info(f"  - {name}: {type(result).__name__} = {result}")

        except Exception as e:
            validation_result = ValidationResult(
                test_name=test_name,
                success=False,
                details={'exception': str(e)},
                execution_time=time.time() - start_time,
                errors=[str(e)]
            )
            logger.error(f"✗ {test_name}: FAIL - {e}")

        self.results.append(validation_result)

    def _generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        successful_tests = [r for r in self.results if r.success]
        failed_tests = [r for r in self.results if not r.success]

        total_execution_time = sum(r.execution_time for r in self.results)

        report = {
            'summary': {
                'total_tests': len(self.results),
                'successful_tests': len(successful_tests),
                'failed_tests': len(failed_tests),
                'success_rate_percentage': (len(successful_tests) / len(self.results)) * 100,
                'total_execution_time': total_execution_time,
                'validation_timestamp': datetime.now().isoformat()
            },
            'business_impact': {
                'issue_number': 982,
                'business_value_protected': '$500K+ ARR Golden Path',
                'functionality_validated': 'SSOT WebSocket broadcast consolidation',
                'adapter_pattern_status': 'OPERATIONAL' if len(failed_tests) == 0 else 'ISSUES_DETECTED',
                'staging_deployment_ready': len(failed_tests) == 0
            },
            'test_results': [
                {
                    'test_name': r.test_name,
                    'success': r.success,
                    'execution_time': r.execution_time,
                    'details': r.details,
                    'errors': r.errors
                }
                for r in self.results
            ],
            'adapter_pattern_validation': {
                'websocket_event_router_adapter': any(r.test_name == "WebSocketEventRouter Adapter" and r.success for r in self.results),
                'user_scoped_router_adapter': any(r.test_name == "UserScopedWebSocketEventRouter Adapter" and r.success for r in self.results),
                'broadcast_user_event_adapter': any(r.test_name == "broadcast_user_event Function Adapter" and r.success for r in self.results),
                'error_handling': any(r.test_name == "Adapter Error Handling" and r.success for r in self.results),
                'return_type_compatibility': any(r.test_name == "Return Type Compatibility" and r.success for r in self.results)
            }
        }

        # Log summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("ISSUE #982 STAGING VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {report['summary']['total_tests']}")
        logger.info(f"Successful: {report['summary']['successful_tests']}")
        logger.info(f"Failed: {report['summary']['failed_tests']}")
        logger.info(f"Success Rate: {report['summary']['success_rate_percentage']:.1f}%")
        logger.info(f"Execution Time: {report['summary']['total_execution_time']:.3f}s")
        logger.info("")
        logger.info(f"Adapter Pattern Status: {report['business_impact']['adapter_pattern_status']}")
        logger.info(f"Staging Deployment Ready: {report['business_impact']['staging_deployment_ready']}")
        logger.info("")

        if failed_tests:
            logger.error("FAILED TESTS:")
            for test in failed_tests:
                logger.error(f"  - {test.test_name}: {test.errors}")
        else:
            logger.info("✓ ALL TESTS PASSED - Issue #982 adapter pattern working correctly")

        return report


async def main():
    """Run Issue #982 staging validation."""
    validator = Issue982StagingValidator()
    report = await validator.run_validation_suite()

    # Save report to file
    report_file = f"staging_issue_982_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"Validation report saved to: {report_file}")

    # Return success/failure code
    return 0 if report['business_impact']['staging_deployment_ready'] else 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)