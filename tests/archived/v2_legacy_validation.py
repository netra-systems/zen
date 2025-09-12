#!/usr/bin/env python3
"""
V2 Legacy WebSocket Handler Pattern Validation

Test plan execution for issue #447 - Remove V2 Legacy WebSocket Handler Pattern.
This module provides focused validation of the current state of V2 legacy components.

FOCUS AREAS:
1. Current state validation of V2 components
2. Flag behavior verification 
3. WebSocket handler functionality tests
4. Pre-removal regression protection

EXECUTION REQUIREMENTS:
- NO Docker dependency
- Simple, focused validation
- Clear pass/fail results
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
    from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
    from netra_backend.app.services.message_handlers import MessageHandlerService
    print(" PASS:  Core imports successful")
except Exception as e:
    print(f" FAIL:  Import error: {e}")
    sys.exit(1)


class V2LegacyValidationRunner:
    """Simple validation runner for V2 legacy WebSocket handler components."""
    
    def __init__(self):
        """Initialize the validation runner."""
        self.results = {}
        self.errors = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = " PASS:  PASS" if passed else " FAIL:  FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        self.results[test_name] = {"passed": passed, "details": details}
        
    def log_error(self, test_name: str, error: Exception):
        """Log test error."""
        error_msg = f"{test_name}: {str(error)}"
        print(f" ALERT:  ERROR: {error_msg}")
        self.errors.append(error_msg)
        self.results[test_name] = {"passed": False, "error": str(error)}

    async def validate_current_state(self):
        """Test Category 1: Current State Validation"""
        print("\n=== CURRENT STATE VALIDATION ===")
        
        # Test 1.1: Check if V2 legacy method exists
        try:
            mock_service = Mock(spec=MessageHandlerService)
            handler = AgentMessageHandler(message_handler_service=mock_service)
            
            has_v2_method = hasattr(handler, '_handle_message_v2_legacy')
            self.log_result(
                "V2 legacy method exists", 
                has_v2_method,
                f"_handle_message_v2_legacy method found: {has_v2_method}"
            )
        except Exception as e:
            self.log_error("V2 legacy method exists", e)
            
        # Test 1.2: Check if V3 clean method exists  
        try:
            has_v3_method = hasattr(handler, '_handle_message_v3_clean')
            self.log_result(
                "V3 clean method exists",
                has_v3_method, 
                f"_handle_message_v3_clean method found: {has_v3_method}"
            )
        except Exception as e:
            self.log_error("V3 clean method exists", e)
            
        # Test 1.3: Check if USE_WEBSOCKET_SUPERVISOR_V3 flag is handled
        try:
            # Test with flag disabled
            with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "false"}):
                # Should be able to access the legacy method
                has_legacy_access = callable(getattr(handler, '_handle_message_v2_legacy', None))
                self.log_result(
                    "V2 legacy accessible when flag disabled",
                    has_legacy_access,
                    "Legacy method callable when USE_WEBSOCKET_SUPERVISOR_V3=false"
                )
        except Exception as e:
            self.log_error("V2 legacy accessible when flag disabled", e)
            
        # Test 1.4: Check if _route_agent_message_v2 exists
        try:
            has_v2_routing = hasattr(handler, '_route_agent_message_v2')
            self.log_result(
                "V2 routing method exists",
                has_v2_routing,
                f"_route_agent_message_v2 method found: {has_v2_routing}"
            )
        except Exception as e:
            self.log_error("V2 routing method exists", e)

    async def validate_flag_behavior(self):
        """Test Category 2: Flag Behavior Verification"""
        print("\n=== FLAG BEHAVIOR VERIFICATION ===")
        
        try:
            mock_service = Mock(spec=MessageHandlerService)
            handler = AgentMessageHandler(message_handler_service=mock_service)
            
            # Test 2.1: Default flag behavior (should be V3 by default)
            default_flag = os.getenv("USE_WEBSOCKET_SUPERVISOR_V3", "true").lower() == "true"
            self.log_result(
                "Default flag behavior",
                default_flag,
                f"USE_WEBSOCKET_SUPERVISOR_V3 defaults to: {os.getenv('USE_WEBSOCKET_SUPERVISOR_V3', 'true')}"
            )
            
            # Test 2.2: Flag handling in main method
            mock_websocket = Mock()
            mock_message = Mock()
            mock_message.type = MessageType.USER_MESSAGE
            mock_message.payload = {"content": "test"}
            
            # Mock the V2 and V3 methods to track which gets called
            with patch.object(handler, '_handle_message_v2_legacy', return_value=True) as mock_v2:
                with patch.object(handler, '_handle_message_v3_clean', return_value=True) as mock_v3:
                    
                    # Test with V3 enabled (default)
                    with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "true"}):
                        try:
                            await handler.handle_message("test_user", mock_websocket, mock_message)
                            v3_called = mock_v3.called
                            v2_not_called = not mock_v2.called
                            self.log_result(
                                "V3 pattern selected when flag=true",
                                v3_called and v2_not_called,
                                f"V3 called: {v3_called}, V2 called: {mock_v2.called}"
                            )
                        except Exception as e:
                            # Expected due to mocking, but we can check call counts
                            v3_called = mock_v3.called
                            v2_not_called = not mock_v2.called
                            self.log_result(
                                "V3 pattern selected when flag=true",
                                v3_called and v2_not_called,
                                f"V3 called: {v3_called}, V2 called: {mock_v2.called} (with exception: {e})"
                            )
                    
                    # Reset mocks
                    mock_v2.reset_mock()
                    mock_v3.reset_mock()
                    
                    # Test with V3 disabled (legacy fallback)
                    with patch.dict(os.environ, {"USE_WEBSOCKET_SUPERVISOR_V3": "false"}):
                        try:
                            await handler.handle_message("test_user", mock_websocket, mock_message)
                            v2_called = mock_v2.called
                            v3_not_called = not mock_v3.called
                            self.log_result(
                                "V2 pattern selected when flag=false",
                                v2_called and v3_not_called,
                                f"V2 called: {v2_called}, V3 called: {mock_v3.called}"
                            )
                        except Exception as e:
                            v2_called = mock_v2.called  
                            v3_not_called = not mock_v3.called
                            self.log_result(
                                "V2 pattern selected when flag=false", 
                                v2_called and v3_not_called,
                                f"V2 called: {v2_called}, V3 called: {mock_v3.called} (with exception: {e})"
                            )
                            
        except Exception as e:
            self.log_error("Flag behavior verification", e)

    async def validate_websocket_functionality(self):
        """Test Category 3: WebSocket Handler Functionality"""  
        print("\n=== WEBSOCKET FUNCTIONALITY VALIDATION ===")
        
        try:
            mock_service = Mock(spec=MessageHandlerService)
            handler = AgentMessageHandler(message_handler_service=mock_service)
            
            # Test 3.1: Message type support
            expected_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
            
            supported_types = []
            for msg_type in expected_types:
                try:
                    if handler.can_handle(msg_type):
                        supported_types.append(msg_type)
                except:
                    pass  # can_handle method might not exist
                    
            types_match = len(supported_types) == len(expected_types)
            self.log_result(
                "Message type support",
                types_match,
                f"Supported types: {[str(t) for t in supported_types]}"
            )
            
            # Test 3.2: Handler statistics tracking
            has_stats = hasattr(handler, 'processing_stats')
            if has_stats:
                stats = getattr(handler, 'processing_stats', {})
                expected_stat_keys = ['messages_processed', 'start_agent_requests', 'user_messages', 'chat_messages', 'errors']
                has_expected_keys = all(key in stats for key in expected_stat_keys)
                self.log_result(
                    "Statistics tracking structure",
                    has_expected_keys,
                    f"Stats keys present: {list(stats.keys())}"
                )
            else:
                self.log_result(
                    "Statistics tracking structure",
                    False,
                    "No processing_stats attribute found"
                )
                
        except Exception as e:
            self.log_error("WebSocket functionality validation", e)

    async def validate_regression_protection(self):
        """Test Category 4: Regression Protection"""
        print("\n=== REGRESSION PROTECTION VALIDATION ===")
        
        try:
            # Test 4.1: Import stability
            modules_to_test = [
                'netra_backend.app.websocket_core.agent_handler',
                'netra_backend.app.websocket_core.types', 
                'netra_backend.app.services.message_handlers'
            ]
            
            import_success_count = 0
            for module in modules_to_test:
                try:
                    __import__(module)
                    import_success_count += 1
                except Exception as e:
                    print(f"   Import failed for {module}: {e}")
                    
            all_imports_successful = import_success_count == len(modules_to_test)
            self.log_result(
                "Critical imports stability",
                all_imports_successful,
                f"{import_success_count}/{len(modules_to_test)} imports successful"
            )
            
            # Test 4.2: Core instantiation
            mock_service = Mock(spec=MessageHandlerService)
            try:
                handler = AgentMessageHandler(message_handler_service=mock_service)
                instantiation_success = handler is not None
                self.log_result(
                    "Handler instantiation",
                    instantiation_success,
                    f"AgentMessageHandler created successfully: {instantiation_success}"
                )
            except Exception as e:
                self.log_result(
                    "Handler instantiation",
                    False,
                    f"Instantiation failed: {e}"
                )
                
        except Exception as e:
            self.log_error("Regression protection validation", e)

    def generate_summary(self) -> Dict[str, Any]:
        """Generate test execution summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result.get('passed', False))
        failed_tests = total_tests - passed_tests
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            "errors": self.errors,
            "detailed_results": self.results
        }

    async def run_all_validations(self):
        """Run all validation tests."""
        print("[U+1F680] Starting V2 Legacy WebSocket Handler Validation")
        print("=" * 60)
        
        try:
            await self.validate_current_state()
            await self.validate_flag_behavior() 
            await self.validate_websocket_functionality()
            await self.validate_regression_protection()
            
        except Exception as e:
            print(f" ALERT:  Critical error during validation: {e}")
            self.log_error("validation_runner", e)
            
        print("\n" + "=" * 60)
        print(" CHART:  VALIDATION SUMMARY")
        print("=" * 60)
        
        summary = self.generate_summary()
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        if self.errors:
            print(f"\n ALERT:  Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
                
        return summary


async def main():
    """Main execution function."""
    runner = V2LegacyValidationRunner()
    summary = await runner.run_all_validations()
    
    # Exit with appropriate code
    if summary['failed'] > 0 or len(summary['errors']) > 0:
        print(f"\n FAIL:  Validation failed with {summary['failed']} failures and {len(summary['errors'])} errors")
        sys.exit(1)
    else:
        print(f"\n PASS:  All validations passed ({summary['passed']}/{summary['total_tests']})")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())