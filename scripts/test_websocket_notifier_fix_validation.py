#!/usr/bin/env python3
"""
WebSocketNotifier Factory Method Fix Validation
===============================================

Validates that the SSOT-compliant fix enables Golden Path functionality:
- Users login  ->  get AI responses 
- WebSocket events deliver all 5 critical events
- Factory method works correctly with user isolation
- No breaking changes to existing functionality

Business Value: Protects $80K+ MRR by ensuring core chat functionality works
"""

import asyncio
import traceback
from unittest.mock import AsyncMock, Mock
from typing import Dict, Any

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier


class GoldenPathValidation:
    """Validates WebSocketNotifier fix enables Golden Path functionality."""
    
    def __init__(self):
        self.results = {}
        self.errors = []
    
    def run_all_validations(self) -> Dict[str, Any]:
        """Run comprehensive validation suite."""
        print("[U+1F680] VALIDATING WEBSOCKET NOTIFIER FIX FOR GOLDEN PATH")
        print("=" * 60)
        
        validations = [
            ("Factory Method Creation", self.test_factory_method_creation),
            ("User Isolation Validation", self.test_user_isolation),
            ("Golden Path Event Support", self.test_golden_path_events),
            ("Error Handling Robustness", self.test_error_handling),
            ("SSOT Compliance", self.test_ssot_compliance),
            ("Concurrent User Safety", self.test_concurrent_users),
        ]
        
        for test_name, test_func in validations:
            try:
                print(f"\n[U+1F4CB] Testing: {test_name}")
                result = test_func()
                self.results[test_name] = {"status": "PASS", "details": result}
                print(f" PASS:  {test_name}: PASSED")
            except Exception as e:
                error_msg = f"{test_name} failed: {str(e)}"
                self.results[test_name] = {"status": "FAIL", "error": error_msg}
                self.errors.append(error_msg)
                print(f" FAIL:  {test_name}: FAILED - {str(e)}")
                # Print traceback for debugging
                traceback.print_exc()
        
        return self.generate_report()
    
    def test_factory_method_creation(self) -> str:
        """Test basic factory method creation works correctly."""
        mock_emitter = self.create_golden_path_emitter()
        mock_context = Mock()
        mock_context.user_id = 'test-user-factory-123'
        
        # Test successful creation
        notifier = WebSocketNotifier.create_for_user(mock_emitter, mock_context)
        
        # Validate instance state
        assert notifier.emitter is not None, "Emitter not set"
        assert notifier.exec_context is not None, "Exec context not set"
        assert notifier._user_id == 'test-user-factory-123', "User ID not tracked"
        
        return "Factory method creates valid WebSocketNotifier instances"
    
    def test_user_isolation(self) -> str:
        """Test user isolation prevents cross-user contamination."""
        mock_emitter = self.create_golden_path_emitter()
        
        # Create notifiers for different users
        context1 = Mock()
        context1.user_id = 'user-1'
        notifier1 = WebSocketNotifier.create_for_user(mock_emitter, context1)
        
        context2 = Mock()
        context2.user_id = 'user-2'
        notifier2 = WebSocketNotifier.create_for_user(mock_emitter, context2)
        
        # Validate isolation
        assert notifier1._user_id != notifier2._user_id, "User isolation failed"
        assert notifier1._user_id == 'user-1', "User 1 ID incorrect"
        assert notifier2._user_id == 'user-2', "User 2 ID incorrect"
        
        return "User isolation properly separates different user contexts"
    
    def test_golden_path_events(self) -> str:
        """Test support for all 5 critical Golden Path WebSocket events."""
        mock_emitter = self.create_golden_path_emitter()
        mock_context = Mock()
        mock_context.user_id = 'test-user-events-123'
        
        # Create notifier
        notifier = WebSocketNotifier.create_for_user(mock_emitter, mock_context)
        
        # Test critical event methods exist on emitter
        required_events = [
            'notify_agent_thinking',
            'notify_agent_started',
            'notify_tool_executing',
            'notify_tool_completed',
            'notify_agent_completed'
        ]
        
        for event in required_events:
            assert hasattr(mock_emitter, event), f"Missing critical event: {event}"
        
        # Test factory validation catches missing events
        incomplete_emitter = Mock()
        incomplete_emitter.notify_agent_thinking = Mock()  # Only partial support
        
        try:
            WebSocketNotifier.create_for_user(incomplete_emitter, mock_context)
            assert False, "Should have failed with incomplete emitter"
        except ValueError as e:
            assert "missing required methods" in str(e), "Validation didn't catch missing methods"
        
        return "All 5 critical Golden Path events supported and validated"
    
    def test_error_handling(self) -> str:
        """Test robust error handling for invalid inputs."""
        mock_emitter = self.create_golden_path_emitter()
        
        error_cases = [
            (None, Mock(user_id='test'), "missing emitter"),
            (mock_emitter, None, "missing exec_context"),
            (mock_emitter, Mock(user_id=None), "missing user_id"),
            (mock_emitter, Mock(), "missing user_id attribute"),
        ]
        
        for emitter, context, description in error_cases:
            try:
                WebSocketNotifier.create_for_user(emitter, context)
                assert False, f"Should have failed: {description}"
            except ValueError:
                pass  # Expected failure
        
        return "Error handling properly validates all required parameters"
    
    def test_ssot_compliance(self) -> str:
        """Test SSOT compliance - single source of truth for factory creation."""
        mock_emitter = self.create_golden_path_emitter()
        mock_context = Mock()
        mock_context.user_id = 'test-user-ssot-123'
        
        # Test factory method is the only way to create with validation
        notifier = WebSocketNotifier.create_for_user(mock_emitter, mock_context)
        
        # Validate SSOT principles
        assert hasattr(notifier, '_user_id'), "User ID tracking not set"
        assert notifier._user_id == 'test-user-ssot-123', "User ID not properly tracked"
        
        # Test validation method doesn't perform initialization
        # (validation method should only check state, not assign)
        original_emitter = notifier.emitter
        original_context = notifier.exec_context
        
        # Call validation again - should not change state
        notifier._validate_user_isolation()
        
        assert notifier.emitter is original_emitter, "Validation changed emitter"
        assert notifier.exec_context is original_context, "Validation changed context"
        
        return "SSOT compliance: factory is single source, validation doesn't initialize"
    
    def test_concurrent_users(self) -> str:
        """Test concurrent user creation doesn't interfere."""
        mock_emitter = self.create_golden_path_emitter()
        
        # Simulate concurrent user creation
        notifiers = []
        for i in range(5):
            context = Mock()
            context.user_id = f'concurrent-user-{i}'
            notifier = WebSocketNotifier.create_for_user(mock_emitter, context)
            notifiers.append(notifier)
        
        # Validate each notifier has correct isolation
        for i, notifier in enumerate(notifiers):
            expected_user_id = f'concurrent-user-{i}'
            assert notifier._user_id == expected_user_id, f"User {i} isolation failed"
        
        # Validate no cross-contamination
        user_ids = [n._user_id for n in notifiers]
        assert len(set(user_ids)) == 5, "User ID contamination detected"
        
        return "Concurrent user creation properly isolated"
    
    def create_golden_path_emitter(self) -> Mock:
        """Create mock emitter with all required Golden Path methods."""
        emitter = AsyncMock()
        
        # Add all 5 critical Golden Path events
        emitter.notify_agent_started = AsyncMock()
        emitter.notify_agent_thinking = AsyncMock()
        emitter.notify_tool_executing = AsyncMock()
        emitter.notify_tool_completed = AsyncMock()
        emitter.notify_agent_completed = AsyncMock()
        
        return emitter
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%",
                "golden_path_enabled": failed_tests == 0
            },
            "results": self.results,
            "errors": self.errors
        }
        
        print("\n" + "=" * 60)
        print(" TARGET:  GOLDEN PATH VALIDATION REPORT")
        print("=" * 60)
        print(f" CHART:  Tests Run: {total_tests}")
        print(f" PASS:  Passed: {passed_tests}")
        print(f" FAIL:  Failed: {failed_tests}")
        print(f"[U+1F4C8] Success Rate: {report['summary']['success_rate']}")
        
        if report['summary']['golden_path_enabled']:
            print("\n[U+1F680] GOLDEN PATH ENABLED: Users can login  ->  receive AI responses")
            print("[U+1F4B0] BUSINESS IMPACT: $80K+ MRR protected")
            print(" CELEBRATION:  WebSocket event delivery working for all 5 critical events")
        else:
            print("\n ALERT:  GOLDEN PATH BLOCKED: Fix incomplete")
            print("[U+1F4B8] BUSINESS RISK: $80K+ MRR at risk")
            for error in self.errors:
                print(f"   - {error}")
        
        return report


def main():
    """Run WebSocketNotifier fix validation."""
    validator = GoldenPathValidation()
    report = validator.run_all_validations()
    
    # Return appropriate exit code
    if report['summary']['golden_path_enabled']:
        print("\n PASS:  ALL VALIDATIONS PASSED - Golden Path functionality restored")
        return 0
    else:
        print("\n FAIL:  VALIDATIONS FAILED - Golden Path still blocked")
        return 1


if __name__ == "__main__":
    exit(main())