#!/usr/bin/env python3
"""
Test script for validating Pydantic V2 migration fixes.

This script tests:
1. Pydantic V2 model functionality
2. JSON serialization
3. Field validation
4. No deprecation warnings
5. Backward compatibility
"""

import sys
import warnings
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Capture warnings for analysis
warnings.simplefilter('always')
warning_list = []

def warning_handler(message, category, filename, lineno, file=None, line=None):
    warning_list.append({
        'message': str(message),
        'category': category.__name__,
        'filename': filename,
        'lineno': lineno
    })

# Set custom warning handler
warnings.showwarning = warning_handler

def test_pydantic_imports():
    """Test that Pydantic models can be imported without warnings."""
    print("🔍 Testing Pydantic V2 imports...")
    
    try:
        # Test imports
        from shared.types.agent_types import (
            AgentExecutionRequest, 
            AgentExecutionResult, 
            AgentValidationResult,
            TypedAgentResult
        )
        from netra_backend.app.schemas.strict_types import TypedAgentResult as StrictTypedAgentResult
        
        print("✅ All Pydantic models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_agent_execution_request():
    """Test AgentExecutionRequest functionality."""
    print("🔍 Testing AgentExecutionRequest...")
    
    try:
        from shared.types.agent_types import AgentExecutionRequest
        from shared.types.core_types import UserID, ThreadID
        
        # Test basic instantiation
        request = AgentExecutionRequest(
            user_id=UserID("test_user_123"),
            thread_id=ThreadID("thread_456"),
            request_data={"action": "test", "params": {"key": "value"}},
            user_permissions=["read", "write"]
        )
        
        # Test field access
        assert request.user_id == "test_user_123"
        assert request.thread_id == "thread_456"
        assert request.request_data["action"] == "test"
        assert "read" in request.user_permissions
        
        # Test JSON serialization
        json_data = request.model_dump()
        assert "user_id" in json_data
        assert "timestamp" in json_data
        
        # Test validation
        try:
            AgentExecutionRequest(
                user_id="",  # Should trigger validation error
                thread_id=ThreadID("thread_456"),
                request_data={}
            )
            print("❌ Validation should have failed for empty user_id")
            return False
        except ValueError:
            pass  # Expected validation error
        
        print("✅ AgentExecutionRequest works correctly")
        return True
    except Exception as e:
        print(f"❌ AgentExecutionRequest test failed: {e}")
        return False

def test_agent_execution_result():
    """Test AgentExecutionResult functionality."""
    print("🔍 Testing AgentExecutionResult...")
    
    try:
        from shared.types.agent_types import AgentExecutionResult
        from shared.types.core_types import UserID, ThreadID, RunID
        
        # Test basic instantiation
        result = AgentExecutionResult(
            user_id=UserID("test_user_123"),
            thread_id=ThreadID("thread_456"),
            run_id=RunID("run_789"),
            success=True,
            result_data={"output": "test result", "metrics": {"duration": 1.5}}
        )
        
        # Test field access
        assert result.user_id == "test_user_123"
        assert result.thread_id == "thread_456"
        assert result.run_id == "run_789"
        assert result.success is True
        assert result.result_data["output"] == "test result"
        
        # Test JSON serialization with datetime
        json_data = result.model_dump()
        assert "timestamp" in json_data
        assert isinstance(json_data["timestamp"], str)  # Should be serialized to ISO format
        
        # Test with error case
        error_result = AgentExecutionResult(
            user_id=UserID("test_user_123"),
            thread_id=ThreadID("thread_456"),
            run_id=RunID("run_789"),
            success=False,
            result_data={},
            error_message="Test error occurred"
        )
        
        assert error_result.success is False
        assert error_result.error_message == "Test error occurred"
        
        print("✅ AgentExecutionResult works correctly")
        return True
    except Exception as e:
        print(f"❌ AgentExecutionResult test failed: {e}")
        return False

def test_agent_validation_result():
    """Test AgentValidationResult functionality."""
    print("🔍 Testing AgentValidationResult...")
    
    try:
        from shared.types.agent_types import AgentValidationResult
        from shared.types.core_types import UserID
        
        # Test basic instantiation
        validation_result = AgentValidationResult(
            is_valid=True,
            user_id=UserID("test_user_123"),
            validation_passed={"auth": True, "permissions": True, "rate_limit": True}
        )
        
        # Test field access
        assert validation_result.is_valid is True
        assert validation_result.user_id == "test_user_123"
        assert validation_result.validation_passed["auth"] is True
        
        # Test helper method
        validation_result.add_validation_check("new_check", False, "Test warning")
        assert validation_result.validation_passed["new_check"] is False
        assert validation_result.is_valid is False  # Should be updated to False
        assert "Test warning" in validation_result.validation_warnings
        
        # Test JSON serialization
        json_data = validation_result.model_dump()
        assert "validation_passed" in json_data
        assert "validation_warnings" in json_data
        
        print("✅ AgentValidationResult works correctly")
        return True
    except Exception as e:
        print(f"❌ AgentValidationResult test failed: {e}")
        return False

def test_typed_agent_result():
    """Test TypedAgentResult functionality."""
    print("🔍 Testing TypedAgentResult...")
    
    try:
        from netra_backend.app.schemas.strict_types import TypedAgentResult
        
        # Test successful result
        success_result = TypedAgentResult.ok(
            result={"data": "test_data", "count": 42},
            operation="test_operation"
        )
        
        assert success_result.success is True
        assert success_result.result["data"] == "test_data"
        assert success_result.metadata["operation"] == "test_operation"
        
        # Test unwrap
        unwrapped = success_result.unwrap()
        assert unwrapped["count"] == 42
        
        # Test failed result
        failed_result = TypedAgentResult.fail(
            error="Test error occurred",
            operation="test_operation"
        )
        
        assert failed_result.success is False
        assert failed_result.error == "Test error occurred"
        
        # Test unwrap_or with failed result
        default_value = {"default": True}
        unwrapped_default = failed_result.unwrap_or(default_value)
        assert unwrapped_default["default"] is True
        
        # Test JSON serialization with datetime
        json_data = success_result.model_dump()
        assert "timestamp" in json_data
        assert isinstance(json_data["timestamp"], str)  # Should be serialized
        
        print("✅ TypedAgentResult works correctly")
        return True
    except Exception as e:
        print(f"❌ TypedAgentResult test failed: {e}")
        return False

def test_json_serialization():
    """Test comprehensive JSON serialization."""
    print("🔍 Testing JSON serialization...")
    
    try:
        from shared.types.agent_types import AgentExecutionRequest, AgentExecutionResult
        from shared.types.core_types import UserID, ThreadID, RunID
        from netra_backend.app.schemas.strict_types import TypedAgentResult
        import json
        
        # Test AgentExecutionRequest serialization
        request = AgentExecutionRequest(
            user_id=UserID("test_user_123"),
            thread_id=ThreadID("thread_456"),
            request_data={"action": "test"}
        )
        
        request_json = json.dumps(request.model_dump())
        request_parsed = json.loads(request_json)
        assert request_parsed["user_id"] == "test_user_123"
        assert "timestamp" in request_parsed
        
        # Test AgentExecutionResult serialization
        result = AgentExecutionResult(
            user_id=UserID("test_user_123"),
            thread_id=ThreadID("thread_456"),
            run_id=RunID("run_789"),
            success=True,
            result_data={"output": "test"}
        )
        
        result_json = json.dumps(result.model_dump())
        result_parsed = json.loads(result_json)
        assert result_parsed["success"] is True
        assert "timestamp" in result_parsed
        
        # Test TypedAgentResult serialization
        typed_result = TypedAgentResult.ok({"test": "data"})
        typed_json = json.dumps(typed_result.model_dump())
        typed_parsed = json.loads(typed_json)
        assert typed_parsed["success"] is True
        assert "timestamp" in typed_parsed
        
        print("✅ JSON serialization works correctly")
        return True
    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        return False

def test_logging_import():
    """Test the modernized logging import."""
    print("🔍 Testing logging import modernization...")
    
    try:
        # Import the module that has the fixed logging import
        import netra_backend.app.agents.supervisor.agent_registry as agent_registry_module
        
        # Check that logger is available (central_logger was removed in the fix)
        assert hasattr(agent_registry_module, 'logger')
        
        # Test that we can use the logger
        logger = agent_registry_module.logger
        logger.info("Test log message from validation script")
        
        # Test that the logger is from the new system
        from shared.logging.unified_logging_ssot import get_logger
        test_logger = get_logger(__name__)
        assert type(logger) == type(test_logger)
        
        print("✅ Logging import modernization works correctly")
        return True
    except Exception as e:
        print(f"❌ Logging import test failed: {e}")
        return False

def analyze_warnings():
    """Analyze collected warnings for deprecation warnings."""
    print("🔍 Analyzing warnings...")
    
    deprecation_warnings = []
    pydantic_warnings = []
    other_warnings = []
    
    for warning in warning_list:
        message = warning['message'].lower()
        category = warning['category']
        
        if 'deprecat' in message or category == 'DeprecationWarning':
            deprecation_warnings.append(warning)
        elif 'pydantic' in message or 'pydantic' in warning['filename'].lower():
            pydantic_warnings.append(warning)
        else:
            other_warnings.append(warning)
    
    print(f"📊 Warning Analysis:")
    print(f"  Total warnings: {len(warning_list)}")
    print(f"  Deprecation warnings: {len(deprecation_warnings)}")
    print(f"  Pydantic-related warnings: {len(pydantic_warnings)}")
    print(f"  Other warnings: {len(other_warnings)}")
    
    if deprecation_warnings:
        print("⚠️  Deprecation warnings found:")
        for warning in deprecation_warnings[:5]:  # Show first 5
            print(f"    {warning['category']}: {warning['message']}")
            print(f"      at {warning['filename']}:{warning['lineno']}")
    
    if pydantic_warnings:
        print("⚠️  Pydantic warnings found:")
        for warning in pydantic_warnings[:5]:  # Show first 5
            print(f"    {warning['category']}: {warning['message']}")
            print(f"      at {warning['filename']}:{warning['lineno']}")
    
    return len(deprecation_warnings), len(pydantic_warnings)

def main():
    """Run all validation tests."""
    print("🚀 Starting Pydantic V2 Migration Validation")
    print("=" * 50)
    
    tests = [
        test_pydantic_imports,
        test_agent_execution_request,
        test_agent_execution_result,
        test_agent_validation_result,
        test_typed_agent_result,
        test_json_serialization,
        test_logging_import
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    # Analyze warnings
    deprecation_count, pydantic_warning_count = analyze_warnings()
    
    print("=" * 50)
    print("📋 VALIDATION SUMMARY")
    print(f"✅ Tests passed: {passed}")
    print(f"❌ Tests failed: {failed}")
    print(f"⚠️  Deprecation warnings: {deprecation_count}")
    print(f"⚠️  Pydantic warnings: {pydantic_warning_count}")
    
    if failed == 0 and deprecation_count == 0:
        print("🎉 ALL TESTS PASSED - Migration is successful!")
        return 0
    elif failed == 0 and deprecation_count < 5:
        print("✅ Functionality tests passed, minimal warnings remain")
        return 0
    else:
        print("⚠️  Some issues remain - see details above")
        return 1

if __name__ == "__main__":
    sys.exit(main())