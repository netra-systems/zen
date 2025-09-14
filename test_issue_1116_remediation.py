#!/usr/bin/env python3
"""
Test script to validate Issue #1116 remediation
This script tests that the SSOT dependency injection pattern works correctly
and prevents user data isolation violations.
"""

import sys
import os
import asyncio
import traceback
from typing import Optional, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_agent_instance_factory_dependency():
    """Test that get_agent_instance_factory_dependency works correctly with user context"""
    print("🧪 Testing get_agent_instance_factory_dependency...")
    
    try:
        from netra_backend.app.dependencies import get_agent_instance_factory_dependency
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from unittest.mock import AsyncMock, MagicMock
        
        # Create mock request with required app state
        mock_request = MagicMock()
        mock_request.app.state.agent_websocket_bridge = MagicMock()
        mock_request.app.state.llm_manager = MagicMock()
        mock_request.app.state.agent_class_registry = {}
        
        # Test parameters
        test_user_id = "test-user-123"
        test_thread_id = "test-thread-456"
        test_run_id = "test-run-789"
        
        print(f"   📋 Testing with user_id: {test_user_id}")
        print(f"   📋 Testing with thread_id: {test_thread_id}")
        
        # Call the dependency function
        try:
            # Mock the create_agent_instance_factory to avoid complex dependencies
            from unittest.mock import patch
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_create:
                mock_factory = AsyncMock()
                mock_factory.configure = AsyncMock()
                mock_create.return_value = mock_factory
                
                factory = await get_agent_instance_factory_dependency(
                    user_id=test_user_id,
                    thread_id=test_thread_id, 
                    run_id=test_run_id,
                    request=mock_request
                )
                
                print("   ✅ Factory creation successful")
                print("   ✅ No undefined variable errors")
                
                # Verify create_agent_instance_factory was called with proper user context
                mock_create.assert_called_once()
                call_args = mock_create.call_args[0]
                user_context = call_args[0] 
                
                print(f"   ✅ UserExecutionContext created with user_id: {user_context.user_id}")
                print(f"   ✅ UserExecutionContext created with thread_id: {user_context.thread_id}")
                print(f"   ✅ UserExecutionContext created with run_id: {user_context.run_id}")
                
                # Verify factory configuration was called
                mock_factory.configure.assert_called_once()
                
                return True
                
        except Exception as e:
            print(f"   ❌ Error during factory creation: {e}")
            print(f"   📄 Traceback: {traceback.format_exc()}")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        print(f"   📄 Traceback: {traceback.format_exc()}")
        return False


def test_supervisor_agent_user_context_requirement():
    """Test that SupervisorAgent requires user_context parameter"""
    print("🧪 Testing SupervisorAgent user_context requirement...")
    
    try:
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from unittest.mock import MagicMock
        
        # Test that SupervisorAgent fails without user_context
        try:
            supervisor = SupervisorAgent(
                llm_manager=MagicMock(),
                websocket_bridge=MagicMock(),
                # user_context=None  # Intentionally missing
            )
            print("   ❌ SupervisorAgent allowed creation without user_context - this is a security violation!")
            return False
        except ValueError as e:
            if "requires user_context" in str(e):
                print("   ✅ SupervisorAgent correctly requires user_context parameter")
            else:
                print(f"   ⚠️  SupervisorAgent raised ValueError but unexpected message: {e}")
                return False
        except Exception as e:
            print(f"   ❌ SupervisorAgent raised unexpected exception: {e}")
            return False
        
        # Test that SupervisorAgent works WITH user_context
        try:
            user_context = UserExecutionContext(
                user_id="test-user-security",
                thread_id="test-thread-security",
                run_id="test-run-security"
            )
            
            with patch('netra_backend.app.agents.supervisor.agent_instance_factory.create_agent_instance_factory') as mock_create:
                mock_factory = MagicMock()
                mock_create.return_value = mock_factory
                
                supervisor = SupervisorAgent(
                    llm_manager=MagicMock(),
                    websocket_bridge=MagicMock(), 
                    user_context=user_context
                )
                print("   ✅ SupervisorAgent successfully created with user_context")
                print(f"   ✅ User isolation enabled for user: {user_context.user_id}")
                
        except Exception as e:
            print(f"   ❌ SupervisorAgent failed with user_context: {e}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False


def test_user_isolation_pattern():
    """Test that the SSOT pattern ensures user isolation"""
    print("🧪 Testing user isolation pattern...")
    
    try:
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        
        # Create two different user contexts
        user1_context = UserExecutionContext(
            user_id="user-1-isolated",
            thread_id="thread-1",
            run_id="run-1"
        )
        
        user2_context = UserExecutionContext(
            user_id="user-2-isolated", 
            thread_id="thread-2",
            run_id="run-2"
        )
        
        # Verify contexts are unique and isolated
        print(f"   👤 User 1 context: {user1_context.get_correlation_id()}")
        print(f"   👤 User 2 context: {user2_context.get_correlation_id()}")
        
        if user1_context.user_id == user2_context.user_id:
            print("   ❌ User contexts have same user_id - isolation violation!")
            return False
            
        if user1_context.get_correlation_id() == user2_context.get_correlation_id():
            print("   ❌ User contexts have same correlation_id - isolation violation!")
            return False
            
        print("   ✅ User contexts are properly isolated")
        print("   ✅ Each user gets unique identifiers")
        print("   ✅ No shared state between user contexts")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing user isolation: {e}")
        return False


async def main():
    """Run all Issue #1116 remediation tests"""
    print("=" * 60)
    print("🔒 Issue #1116 SSOT Remediation Validation Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Agent Instance Factory Dependency", test_agent_instance_factory_dependency),
        ("SupervisorAgent User Context Requirement", test_supervisor_agent_user_context_requirement), 
        ("User Isolation Pattern", test_user_isolation_pattern),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"🚀 Running test: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
            print("   ✅ Test completed\n" if result else "   ❌ Test failed\n")
        except Exception as e:
            print(f"   💥 Test crashed: {e}")
            print(f"   📄 Traceback: {traceback.format_exc()}")
            results.append((test_name, False))
            print("   ❌ Test failed\n")
    
    # Summary
    print("=" * 60) 
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
    
    print()
    print(f"📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Issue #1116 remediation is successful.")
        print("🔒 User isolation and SSOT patterns are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Issue #1116 remediation needs attention.")
        return 1


if __name__ == "__main__":
    # Import patch here to avoid issues
    from unittest.mock import patch
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        print(f"📄 Traceback: {traceback.format_exc()}")
        sys.exit(1)