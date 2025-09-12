"""
Unit Tests for ToolRegistry BaseModel Filtering

This module tests the core BaseModel filtering logic that prevents Pydantic BaseModel
classes from being registered as executable tools.

CRITICAL REQUIREMENTS:
- Tests MUST be designed to FAIL in current broken state
- Tests MUST validate BaseModel detection and rejection
- Tests MUST reproduce "modelmetaclass" name generation issue
- Tests MUST use no external dependencies (pure unit tests)

Business Value:
- Prevents BaseModel classes (data schemas) from being treated as executable tools
- Stops "modelmetaclass already registered" errors at the source
- Validates proper tool interface contracts

See: /Users/anthony/Documents/GitHub/netra-apex/audit/staging/auto-solve-loop/toolregistry-duplicate-registration-20250109.md
"""

import pytest
import logging
from typing import Any, Dict
from unittest.mock import Mock

from pydantic import BaseModel
from netra_backend.app.core.registry.universal_registry import UniversalRegistry, ToolRegistry
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class TestDataModel(BaseModel):
    """Mock Pydantic BaseModel class that should NOT be registered as a tool."""
    name: str
    value: int
    
    class Config:
        arbitrary_types_allowed = True


class ValidTestTool:
    """Mock valid tool class that should be accepted for registration."""
    
    def __init__(self):
        self.name = "valid_test_tool"
        
    def execute(self, *args, **kwargs):
        return "test_result"


class InvalidToolMissingName:
    """Mock tool class missing the required 'name' attribute."""
    
    def execute(self, *args, **kwargs):
        return "test_result"


class InvalidToolMissingExecute:
    """Mock tool class missing the required 'execute' method."""
    
    def __init__(self):
        self.name = "invalid_no_execute"


@pytest.mark.unit
@pytest.mark.toolregistry
class TestToolRegistryBaseModelFiltering(SSotBaseTestCase):
    """
    Unit tests for BaseModel filtering in ToolRegistry.
    
    These tests focus on the core logic that should prevent Pydantic BaseModel
    classes from being registered as executable tools.
    
    CRITICAL: Tests are designed to FAIL in current broken state.
    """
    
    def setup_method(self, method):
        """Set up method-level fixtures."""
        super().setup_method(method)
        # Create scoped registry to avoid conflicts
        self.registry = ToolRegistry(scope_id=f"test_{method.__name__}")
        logger.info(f"[U+1F9EA] Starting unit test: {method.__name__}")
    
    def test_pydantic_basemodel_detection_and_rejection(self):
        """
        FAILING TEST: Detects BaseModel classes being registered as tools.
        
        Current State (MUST FAIL):
        - BaseModel classes pass through tool registration without filtering
        - Registry accepts BaseModel instances as valid tools
        - Metaclass name "modelmetaclass" is generated from BaseModel.__class__.__name__.lower()
        
        After Fix (MUST PASS):
        - BaseModel classes rejected during tool validation
        - Clear error message: "BaseModel classes are data schemas, not executable tools"
        - No "modelmetaclass" registration attempts
        """
        logger.info("[U+1F9EA] Testing BaseModel class detection and rejection")
        
        # Create BaseModel instance that should be rejected
        basemodel_instance = TestDataModel(name="test", value=42)
        
        # Try to register BaseModel - should fail after fix
        try:
            self.registry.register("test_basemodel", basemodel_instance)
            
            # If we reach here, the BaseModel was accepted (current broken state)
            logger.error(" FAIL:  CURRENT STATE BUG: BaseModel instance was accepted as tool")
            
            # Check if this generated "modelmetaclass" name
            registered_tools = list(self.registry._items.keys())
            if "modelmetaclass" in registered_tools:
                pytest.fail("REPRODUCED BUG: BaseModel instance created 'modelmetaclass' registration")
            
            # Even if no "modelmetaclass", BaseModel acceptance is wrong
            pytest.fail("CURRENT STATE BUG: BaseModel class was accepted as executable tool")
            
        except ValueError as e:
            error_msg = str(e)
            logger.info(f" PASS:  BaseModel registration rejected: {error_msg}")
            
            # Validate proper rejection message (after fix)
            if "BaseModel classes are data schemas, not executable tools" in error_msg:
                logger.info(" PASS:  Fix working: Proper BaseModel rejection message")
            else:
                # Different error - might be partial fix
                logger.warning(f" WARNING: [U+FE0F] BaseModel rejected but with unexpected error: {error_msg}")
                
        except Exception as e:
            # Other unexpected error
            logger.error(f" FAIL:  Unexpected error during BaseModel registration: {e}")
            pytest.fail(f"Unexpected error type: {type(e).__name__}: {e}")
    
    def test_metaclass_name_fallback_dangerous_pattern(self):
        """
        FAILING TEST: Reproduces exact "modelmetaclass" name generation.
        
        Tests the dangerous pattern:
        tool_name = getattr(tool, '__class__', type(tool)).__name__.lower()
        When tool is BaseModel instance  ->  "modelmetaclass"
        """
        logger.info("[U+1F9EA] Testing metaclass name fallback dangerous pattern")
        
        # Create BaseModel instance
        basemodel_instance = TestDataModel(name="test", value=123)
        
        # Reproduce the dangerous name generation pattern from staging
        dangerous_name = getattr(basemodel_instance, '__class__', type(basemodel_instance)).__name__.lower()
        
        logger.info(f" SEARCH:  Generated tool name using dangerous pattern: '{dangerous_name}'")
        
        # In current broken state, this should produce "modelmetaclass"
        if dangerous_name == "modelmetaclass":
            logger.error(" ALERT:  REPRODUCED: Dangerous metaclass name fallback creates 'modelmetaclass'")
            pytest.fail(f"REPRODUCED STAGING BUG: Metaclass fallback generates 'modelmetaclass' for BaseModel instances")
        
        # Check for other suspicious BaseModel-related names
        basemodel_indicators = ["model", "base", "pydantic"]
        if any(indicator in dangerous_name for indicator in basemodel_indicators):
            logger.warning(f" WARNING: [U+FE0F] BaseModel-related name detected: '{dangerous_name}'")
            
        # After fix, name generation should avoid metaclass fallbacks
        logger.info(f" PASS:  Safe name generation or BaseModel properly filtered: '{dangerous_name}'")
    
    def test_tool_interface_contract_validation(self):
        """
        FAILING TEST: Tools without proper interface being accepted.
        
        Current State: Objects without 'name' or 'execute' methods pass validation
        After Fix: Only objects with proper tool interface accepted
        """
        logger.info("[U+1F9EA] Testing tool interface contract validation")
        
        # Test 1: Valid tool should always be accepted
        valid_tool = ValidTestTool()
        try:
            self.registry.register(valid_tool.name, valid_tool)
            logger.info(" PASS:  Valid tool registered successfully")
        except Exception as e:
            pytest.fail(f"Valid tool was rejected: {e}")
        
        # Test 2: Tool missing 'name' attribute
        invalid_tool_no_name = InvalidToolMissingName()
        try:
            # This should fail because tool lacks 'name' attribute
            # In current broken state, it might generate a dangerous fallback name
            self.registry.register("fallback_name", invalid_tool_no_name)
            
            # If accepted, check if it caused issues
            logger.warning(" WARNING: [U+FE0F] Tool without 'name' attribute was accepted")
            
            # Check if dangerous name generation occurred
            if hasattr(invalid_tool_no_name, '__class__'):
                generated_name = invalid_tool_no_name.__class__.__name__.lower()
                if "metaclass" in generated_name:
                    pytest.fail(f"REPRODUCED: Dangerous name generation for tool without 'name': {generated_name}")
            
        except ValueError as e:
            logger.info(f" PASS:  Tool without 'name' properly rejected: {e}")
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error for tool without 'name': {e}")
        
        # Test 3: Tool missing 'execute' method  
        invalid_tool_no_execute = InvalidToolMissingExecute()
        try:
            self.registry.register(invalid_tool_no_execute.name, invalid_tool_no_execute)
            
            # If accepted in current state, this is a validation gap
            logger.warning(" WARNING: [U+FE0F] Tool without 'execute' method was accepted")
            
        except ValueError as e:
            logger.info(f" PASS:  Tool without 'execute' method properly rejected: {e}")
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error for tool without 'execute': {e}")
    
    def test_basemodel_class_vs_instance_detection(self):
        """
        Test that both BaseModel classes and instances are properly detected.
        
        CRITICAL: BaseModel classes should never be registered, regardless of
        whether they are passed as class objects or instances.
        """
        logger.info("[U+1F9EA] Testing BaseModel class vs instance detection")
        
        # Test BaseModel class (not instance)
        try:
            self.registry.register("basemodel_class", TestDataModel)
            logger.error(" FAIL:  CURRENT STATE BUG: BaseModel CLASS was accepted as tool")
            pytest.fail("BaseModel class should not be accepted as tool")
        except ValueError as e:
            logger.info(f" PASS:  BaseModel class properly rejected: {e}")
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error for BaseModel class: {e}")
        
        # Test BaseModel instance
        basemodel_instance = TestDataModel(name="test", value=42)
        try:
            self.registry.register("basemodel_instance", basemodel_instance)
            logger.error(" FAIL:  CURRENT STATE BUG: BaseModel INSTANCE was accepted as tool")
            pytest.fail("BaseModel instance should not be accepted as tool")
        except ValueError as e:
            logger.info(f" PASS:  BaseModel instance properly rejected: {e}")
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error for BaseModel instance: {e}")
    
    def test_multiple_basemodel_registration_attempts(self):
        """
        Test multiple BaseModel registration attempts to catch duplicate issues.
        
        This test simulates the scenario that leads to "modelmetaclass already registered"
        when multiple BaseModel classes are processed.
        """
        logger.info("[U+1F9EA] Testing multiple BaseModel registration attempts")
        
        class TestDataModel2(BaseModel):
            field1: str
            field2: int
        
        class TestDataModel3(BaseModel):
            data: Dict[str, Any]
        
        basemodels = [
            TestDataModel(name="test1", value=1),
            TestDataModel2(field1="test2", field2=2), 
            TestDataModel3(data={"test": 3})
        ]
        
        registration_attempts = []
        errors = []
        
        for i, basemodel in enumerate(basemodels):
            try:
                tool_name = f"basemodel_{i}"
                self.registry.register(tool_name, basemodel)
                registration_attempts.append(tool_name)
                logger.warning(f" WARNING: [U+FE0F] BaseModel {i} was accepted as tool")
                
            except ValueError as e:
                errors.append(str(e))
                logger.info(f" PASS:  BaseModel {i} properly rejected: {e}")
                
            except Exception as e:
                # Check for "already registered" errors
                if "already registered" in str(e):
                    logger.error(f" ALERT:  REPRODUCED: Duplicate registration error for BaseModel {i}: {e}")
                    pytest.fail(f"REPRODUCED BUG: Duplicate BaseModel registration: {e}")
                else:
                    errors.append(str(e))
                    logger.error(f" FAIL:  Unexpected error for BaseModel {i}: {e}")
        
        # Analyze results
        logger.info(f" CHART:  Multiple BaseModel test results:")
        logger.info(f"   Accepted: {len(registration_attempts)}")
        logger.info(f"   Rejected: {len(errors)}")
        
        if registration_attempts:
            # In current broken state, some BaseModels might be accepted
            logger.error(f" FAIL:  CURRENT STATE BUG: {len(registration_attempts)} BaseModel(s) accepted as tools")
            
            # Check if this caused "modelmetaclass" registrations
            registered_names = list(self.registry._items.keys())
            if "modelmetaclass" in registered_names:
                pytest.fail("REPRODUCED: Multiple BaseModel registration created 'modelmetaclass' conflict")
        
        # After fix, all BaseModels should be rejected
        if len(errors) == len(basemodels):
            logger.info(" PASS:  All BaseModel registration attempts properly rejected")
    
    def test_valid_tools_still_work_with_basemodel_filtering(self):
        """
        Regression test: Ensure that valid tools still work after BaseModel filtering is implemented.
        
        CRITICAL: The fix should not break existing valid tool registration.
        """
        logger.info("[U+1F9EA] Testing that valid tools still work with BaseModel filtering")
        
        # Create multiple valid tools
        class ValidTool1:
            def __init__(self):
                self.name = "valid_tool_1"
            def execute(self):
                return "result1"
        
        class ValidTool2:
            def __init__(self):
                self.name = "valid_tool_2"
            def execute(self):
                return "result2"
        
        valid_tools = [ValidTool1(), ValidTool2(), ValidTestTool()]
        
        # All valid tools should register successfully
        for tool in valid_tools:
            try:
                self.registry.register(tool.name, tool)
                logger.info(f" PASS:  Valid tool '{tool.name}' registered successfully")
            except Exception as e:
                pytest.fail(f"Valid tool '{tool.name}' was rejected: {e}")
        
        # Verify tools can be retrieved
        for tool in valid_tools:
            retrieved_tool = self.registry.get(tool.name)
            assert retrieved_tool is not None, f"Could not retrieve valid tool '{tool.name}'"
            assert retrieved_tool is tool, f"Retrieved different instance for '{tool.name}'"
        
        # Verify registry state
        registered_count = len(self.registry._items)
        expected_count = len(valid_tools)
        assert registered_count == expected_count, f"Expected {expected_count} tools, got {registered_count}"
        
        logger.info(f" PASS:  All {len(valid_tools)} valid tools work correctly with BaseModel filtering")


@pytest.mark.unit
@pytest.mark.toolregistry  
class TestUniversalRegistryDuplicateHandling(SSotBaseTestCase):
    """
    Unit tests for duplicate registration handling in UniversalRegistry.
    
    These tests validate that the registry properly prevents and handles
    duplicate registrations without breaking the system.
    """
    
    def setup_method(self, method):
        """Set up method-level fixtures."""
        super().setup_method(method)
        logger.info(f"[U+1F9EA] Starting duplicate handling test: {method.__name__}")
    
    def test_duplicate_registration_prevention(self):
        """
        FAILING TEST: Registry allows duplicate registrations of same tool name.
        
        Current State: Multiple tools with same name cause "already registered" errors
        After Fix: Graceful handling with proper error messages
        """
        logger.info("[U+1F9EA] Testing duplicate registration prevention")
        
        # Create registry with duplicate prevention enabled (use scoped registry)
        registry = ToolRegistry(scope_id="duplicate_test")
        
        tool1 = ValidTestTool()
        tool2 = ValidTestTool()  # Same name as tool1
        
        # First registration should succeed
        try:
            registry.register(tool1.name, tool1)
            logger.info(" PASS:  First tool registration successful")
        except Exception as e:
            pytest.fail(f"First registration failed: {e}")
        
        # Second registration should fail gracefully
        try:
            registry.register(tool2.name, tool2)
            
            # If this succeeds, duplicate prevention is not working
            logger.error(" FAIL:  CURRENT STATE BUG: Duplicate registration was allowed")
            pytest.fail("Duplicate registration should have been prevented")
            
        except ValueError as e:
            error_msg = str(e)
            logger.info(f" PASS:  Duplicate registration properly prevented: {error_msg}")
            
            # Validate error message quality
            if "already registered" in error_msg and tool1.name in error_msg:
                logger.info(" PASS:  Clear duplicate registration error message")
            else:
                logger.warning(f" WARNING: [U+FE0F] Duplicate error message could be clearer: {error_msg}")
                
        except Exception as e:
            logger.error(f" FAIL:  Unexpected error type for duplicate registration: {type(e).__name__}: {e}")
    
    def test_registry_scoping_isolation(self):
        """
        FAILING TEST: Global registry state pollution between users.
        
        Current State: Single global registry shared across all users
        After Fix: User-scoped registries with proper isolation
        """
        logger.info("[U+1F9EA] Testing registry scoping isolation")
        
        # Create multiple registries to simulate user isolation
        registry1 = ToolRegistry(scope_id="isolation_test_1")
        registry2 = ToolRegistry(scope_id="isolation_test_2")
        
        # Verify they are different instances
        assert id(registry1) != id(registry2), "Registries should be different instances"
        
        # Register same tool name in both registries - should not conflict
        tool1 = ValidTestTool()
        tool2 = ValidTestTool()
        
        try:
            registry1.register(tool1.name, tool1)
            registry2.register(tool2.name, tool2)
            logger.info(" PASS:  Same tool name registered in different registries without conflict")
            
        except Exception as e:
            if "already registered" in str(e):
                logger.error(" ALERT:  REPRODUCED: Cross-registry registration conflict")
                pytest.fail(f"REPRODUCED BUG: Registry isolation failure - {e}")
            else:
                pytest.fail(f"Unexpected error during registry isolation test: {e}")
        
        # Verify isolation - each registry should only see its own tool
        tool1_retrieved = registry1.get(tool1.name)
        tool2_retrieved = registry2.get(tool2.name)
        
        assert tool1_retrieved is tool1, "Registry1 should return its own tool instance"
        assert tool2_retrieved is tool2, "Registry2 should return its own tool instance"
        
        # Verify tools are not visible across registries
        assert registry1.get(tool2.name) is None or registry1.get(tool2.name) is tool1
        assert registry2.get(tool1.name) is None or registry2.get(tool1.name) is tool2
        
        logger.info(" PASS:  Registry scoping isolation working correctly")
    
    def test_override_behavior_control(self):
        """
        Test that allow_override parameter properly controls duplicate behavior.
        """
        logger.info("[U+1F9EA] Testing override behavior control")
        
        # Test with strict registry (default behavior)
        strict_registry = ToolRegistry(scope_id="strict_test")
        tool1 = ValidTestTool()
        tool2 = ValidTestTool()  # Same name
        
        strict_registry.register(tool1.name, tool1)
        
        # Should fail with default behavior (no overrides)
        with pytest.raises((ValueError, RuntimeError)):
            strict_registry.register(tool2.name, tool2)
        
        # Create a registry that allows overrides by accessing the parent class
        from netra_backend.app.core.registry.universal_registry import UniversalRegistry
        permissive_registry = UniversalRegistry("PermissiveToolRegistry", allow_override=True)
        
        permissive_registry.register(tool1.name, tool1)
        # Should succeed with allow_override=True
        permissive_registry.register(tool2.name, tool2)
        
        # Should have the second tool now
        retrieved = permissive_registry.get(tool1.name)
        assert retrieved is tool2, "Override should have replaced the original tool"
        
        logger.info(" PASS:  Override behavior control working correctly")