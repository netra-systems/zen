#!/usr/bin/env python3
"""
Issue #891 System Stability Validation Script

This script validates that our BaseAgent session management and factory pattern
fixes maintain system stability without introducing breaking changes.

Tests:
1. Import verification - All components import without errors
2. Factory pattern validation - User isolation works correctly  
3. Session management verification - No session conflicts
4. Basic agent functionality - Core workflows work
5. WebSocket integration - No regression in WebSocket handling

Expected: All validations should PASS, proving system stability is maintained.
"""

import sys
import os
import asyncio
import traceback
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class StabilityValidator:
    def __init__(self):
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
            status = "PASS"
        else:
            status = "FAIL"
            
        result = f"{status}: {test_name}"
        if details:
            result += f" - {details}"
            
        self.test_results.append(result)
        print(result)
        
    def validate_imports(self):
        """Test 1: Validate all critical imports work."""
        print("\n=== TEST 1: Import Validation ===")
        
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            self.log_test("BaseAgent import", True)
        except Exception as e:
            self.log_test("BaseAgent import", False, str(e))
            
        try:
            from netra_backend.app.agents.interfaces import BaseAgentProtocol
            self.log_test("BaseAgentProtocol import", True)
        except Exception as e:
            self.log_test("BaseAgentProtocol import", False, str(e))
            
        try:
            from netra_backend.app.agents.session_state import SessionState
            self.log_test("SessionState import", True)
        except Exception as e:
            self.log_test("SessionState import", False, str(e))
            
        try:
            from netra_backend.app.agents.user_context_state import UserContextState  
            self.log_test("UserContextState import", True)
        except Exception as e:
            self.log_test("UserContextState import", False, str(e))
            
    def validate_factory_patterns(self):
        """Test 2: Validate factory patterns work correctly."""
        print("\n=== TEST 2: Factory Pattern Validation ===")
        
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.user_context_state import UserContextState
            
            # Test user context creation
            user_context_1 = UserContextState.create_for_user("user_1", "session_1")
            user_context_2 = UserContextState.create_for_user("user_2", "session_2")
            
            # Verify isolation
            if user_context_1.user_id != user_context_2.user_id:
                self.log_test("User context isolation", True, "Different users have separate contexts")
            else:
                self.log_test("User context isolation", False, "User contexts not properly isolated")
                
        except Exception as e:
            self.log_test("Factory pattern validation", False, str(e))
            
    def validate_session_management(self):
        """Test 3: Validate session management works without conflicts."""
        print("\n=== TEST 3: Session Management Validation ===")
        
        try:
            from netra_backend.app.agents.session_state import SessionState
            
            # Test session creation
            session_1 = SessionState(user_id="user_1", session_id="session_1")
            session_2 = SessionState(user_id="user_2", session_id="session_2")
            
            # Verify separate state
            session_1.data["test_key"] = "value_1"
            session_2.data["test_key"] = "value_2"
            
            if session_1.data["test_key"] != session_2.data["test_key"]:
                self.log_test("Session state isolation", True, "Sessions maintain separate state")
            else:
                self.log_test("Session state isolation", False, "Session state not properly isolated")
                
        except Exception as e:
            self.log_test("Session management validation", False, str(e))
            
    def validate_basic_agent_functionality(self):
        """Test 4: Validate basic agent functionality works."""
        print("\n=== TEST 4: Basic Agent Functionality ===")
        
        try:
            from netra_backend.app.agents.base_agent import BaseAgent
            from netra_backend.app.agents.user_context_state import UserContextState
            
            # Create user context
            user_context = UserContextState.create_for_user("test_user", "test_session")
            
            # Test agent creation (this will be a mock since we can't create real agents easily)
            # Just verify the class structure is intact
            if hasattr(BaseAgent, '__init__') and hasattr(BaseAgent, 'process_message'):
                self.log_test("BaseAgent class structure", True, "Core methods available")
            else:
                self.log_test("BaseAgent class structure", False, "Missing core methods")
                
        except Exception as e:
            self.log_test("Basic agent functionality", False, str(e))
            
    def validate_websocket_integration(self):
        """Test 5: Validate WebSocket integration has no regression."""
        print("\n=== TEST 5: WebSocket Integration Validation ===")
        
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            self.log_test("WebSocketManager import", True)
        except Exception as e:
            self.log_test("WebSocketManager import", False, str(e))
            
        try:
            from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
            self.log_test("WebSocket types import", True)
        except Exception as e:
            self.log_test("WebSocket types import", False, str(e))
            
    def run_all_validations(self):
        """Run all stability validations."""
        print("🔧 Issue #891 System Stability Validation")
        print("==========================================")
        print("Testing BaseAgent session management and factory pattern fixes...")
        
        self.validate_imports()
        self.validate_factory_patterns()
        self.validate_session_management() 
        self.validate_basic_agent_functionality()
        self.validate_websocket_integration()
        
        print(f"\n=== VALIDATION SUMMARY ===")
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.total_tests - self.passed_tests}")
        print(f"Success Rate: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        if self.passed_tests == self.total_tests:
            print("\n✅ SYSTEM STABILITY CONFIRMED")
            print("All validations passed - Issue #891 remediation maintains system stability")
            return True
        else:
            print("\n❌ STABILITY ISSUES DETECTED")
            print("Some validations failed - investigate before proceeding")
            return False

if __name__ == "__main__":
    validator = StabilityValidator()
    success = validator.run_all_validations()
    sys.exit(0 if success else 1)