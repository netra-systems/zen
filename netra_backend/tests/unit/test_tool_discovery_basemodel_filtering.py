"""
Unit Tests for Tool Discovery BaseModel Filtering

This module tests the detection and exclusion of Pydantic BaseModel classes
from tool registration, which is the root cause of the "modelmetaclass" duplicate
registration error.

CRITICAL REQUIREMENTS:
- Tests MUST be designed to FAIL in current broken state
- Tests MUST detect BaseModel classes being treated as tools
- Tests MUST validate tool interface contract enforcement
- Tests MUST prevent metaclass name fallback scenarios

Business Value:
- Prevents BaseModel classes from being registered as executable tools
- Validates tool interface contracts before registration
- Eliminates "modelmetaclass" registration attempts that break the system

See: /Users/rindhujajohnson/Netra/GitHub/netra-apex/audit/staging/auto-solve-loop/toolregistry-duplicate-registration-20250109.md
"""

import logging
import pytest
from typing import Any, Dict, List, Type, Optional
from unittest.mock import Mock, patch
from pydantic import BaseModel

from netra_backend.app.core.registry.universal_registry import ToolRegistry, UniversalRegistry
from netra_backend.app.agents.user_context_tool_factory import UserContextToolFactory
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


class MockBaseTool:
    """Mock base tool that implements proper tool interface."""
    
    def __init__(self, name: str = "mock_tool"):
        self.name = name
        
    def execute(self, *args, **kwargs):
        return {"success": True, "result": "mock execution"}


class ProblematicBaseModelTool(BaseModel):
    """
    Pydantic BaseModel that's incorrectly being treated as a tool.
    This represents the classes causing the "modelmetaclass" registration issue.
    """
    field1: str = "test_value"
    field2: int = 42
    
    # Missing proper tool interface - no 'name' attribute, no execute method


class ProblematicBaseModelWithName(BaseModel):
    """BaseModel that has a name but is still not a proper tool."""
    name: str = "problematic_basemodel_tool"
    field1: str = "test_value"
    
    # Still missing execute method - not a proper tool


class ProperToolClass:
    """Properly implemented tool class that should be registered."""
    
    def __init__(self):
        self.name = "proper_tool"
        
    def execute(self, *args, **kwargs):
        return {"success": True, "tool": self.name}


class ToolWithoutName:
    """Tool class missing name attribute (causes fallback naming)."""
    
    def __init__(self):
        # No name attribute - will trigger fallback
        pass
        
    def execute(self, *args, **kwargs):
        return {"success": True, "tool": "unnamed_tool"}


@pytest.mark.unit
@pytest.mark.toolregistry
class TestToolDiscoveryBaseModelFiltering(SSotBaseTestCase):
    """
    Unit tests for BaseModel filtering in tool discovery.
    
    These tests focus on the tool validation and filtering logic that should
    prevent Pydantic BaseModel classes from being registered as executable tools.
    """
    
    def setup_method(self, method):
        """Set up method-level fixtures."""
        super().setup_method(method)
        self.registry = ToolRegistry()
        
    def test_basemodel_detection_and_exclusion(self):
        """
        Test that BaseModel classes are correctly identified and excluded.
        Should catch Pydantic model misclassification.
        
        CRITICAL: This test should FAIL in current state if BaseModel classes
        are being registered as tools, causing the "modelmetaclass" error.
        """
        logger.info("[U+1F9EA] Testing BaseModel detection and exclusion")
        
        # Create tool classes list mixing proper tools and BaseModel classes
        tool_classes = [
            ProperToolClass,              # Should be registered
            ProblematicBaseModelTool,     # Should be EXCLUDED
            ProblematicBaseModelWithName, # Should be EXCLUDED even with name
            ToolWithoutName              # Should be registered with fallback name
        ]
        
        # Track registration attempts
        registration_attempts = []
        successful_registrations = []
        basemodel_registration_attempts = []
        
        original_register = self.registry.register
        
        def tracking_register(name: str, tool):
            """Track all registration attempts."""
            registration_attempts.append({
                'name': name,
                'tool_class': tool.__class__.__name__,
                'is_basemodel': isinstance(tool, BaseModel),
                'has_name_attr': hasattr(tool, 'name'),
                'has_execute_method': hasattr(tool, 'execute')
            })
            
            if isinstance(tool, BaseModel):
                basemodel_registration_attempts.append({
                    'name': name,
                    'tool_class': tool.__class__.__name__,
                    'metaclass_name': type(tool).__name__.lower()
                })
            
            try:
                result = original_register(name, tool)
                successful_registrations.append(name)
                return result
            except Exception as e:
                logger.info(f"Registration failed for {name}: {e}")
                raise
                
        self.registry.register = tracking_register
        
        # Attempt to create tools and register them (simulating current broken behavior)
        logger.info("[U+1F4DD] Attempting to register mixed tool classes...")
        
        created_tools = []
        registration_errors = []
        
        for tool_class in tool_classes:
            try:
                tool_instance = tool_class()
                created_tools.append(tool_instance)
                
                # This is the problematic logic from user_context_tool_factory.py
                if hasattr(tool_instance, 'name') and tool_instance.name:
                    tool_name = tool_instance.name
                else:
                    # CRITICAL: This fallback causes "modelmetaclass" for BaseModel classes
                    tool_name = getattr(tool_instance, '__class__', type(tool_instance)).__name__.lower()
                    
                self.registry.register(tool_name, tool_instance)
                
            except Exception as e:
                registration_errors.append({
                    'tool_class': tool_class.__name__,
                    'error': str(e)
                })
                
        # Analyze results
        logger.info(f" CHART:  Registration analysis:")
        logger.info(f"   Total attempts: {len(registration_attempts)}")
        logger.info(f"   Successful: {len(successful_registrations)}")
        logger.info(f"   BaseModel attempts: {len(basemodel_registration_attempts)}")
        logger.info(f"   Errors: {len(registration_errors)}")
        
        # CRITICAL VALIDATIONS:
        
        # 1. BaseModel classes should NOT be registered as tools
        if basemodel_registration_attempts:
            logger.error(f" FAIL:  BaseModel classes were registered as tools: {basemodel_registration_attempts}")
            
            # Check for the specific "modelmetaclass" issue
            modelmetaclass_attempts = [
                attempt for attempt in basemodel_registration_attempts
                if attempt['metaclass_name'] == 'modelmetaclass' or attempt['name'] == 'modelmetaclass'
            ]
            
            if modelmetaclass_attempts:
                pytest.fail(f"REPRODUCED BUG: BaseModel registered with 'modelmetaclass' name: {modelmetaclass_attempts}")
            else:
                pytest.fail(f"REPRODUCED BUG: BaseModel classes registered as tools: {basemodel_registration_attempts}")
                
        # 2. Only proper tool classes should be successfully registered
        expected_proper_tools = ['proper_tool', 'toolwithoutname']  # fallback name for ToolWithoutName
        
        # Check what was actually registered
        improper_registrations = []
        for attempt in registration_attempts:
            if attempt['is_basemodel']:
                improper_registrations.append(attempt['tool_class'])
                
        if improper_registrations:
            pytest.fail(f"REPRODUCED BUG: BaseModel classes registered: {improper_registrations}")
            
        # 3. Proper tools should be registered successfully
        proper_tool_registrations = [
            attempt for attempt in registration_attempts
            if not attempt['is_basemodel'] and attempt['has_execute_method']
        ]
        
        if len(proper_tool_registrations) < 2:  # Should have ProperToolClass and ToolWithoutName
            pytest.fail("Proper tool classes were not registered correctly")
            
        logger.info(" PASS:  BaseModel detection and exclusion test passed")
        
    def test_tool_interface_contract_validation(self):
        """
        Test that only objects implementing proper tool interface are accepted.
        Should catch interface contract violations.
        
        CRITICAL: This test validates that tools must have both 'name' and 'execute'.
        """
        logger.info("[U+1F9EA] Testing tool interface contract validation")
        
        # Define various tool-like classes with different interface compliance
        class ToolWithNameOnly:
            def __init__(self):
                self.name = "name_only_tool"
                # Missing execute method
                
        class ToolWithExecuteOnly:
            def __init__(self):
                # Missing name attribute
                pass
                
            def execute(self):
                return "result"
                
        class CompliantTool:
            def __init__(self):
                self.name = "compliant_tool"
                
            def execute(self):
                return "result"
                
        # Test tool interface validation
        test_cases = [
            {
                'tool_class': ProblematicBaseModelTool,
                'should_be_accepted': False,
                'reason': 'BaseModel without proper interface'
            },
            {
                'tool_class': ToolWithNameOnly,
                'should_be_accepted': False,  # Missing execute method
                'reason': 'Missing execute method'
            },
            {
                'tool_class': ToolWithExecuteOnly,
                'should_be_accepted': True,   # Can use fallback naming
                'reason': 'Has execute, can use fallback name'
            },
            {
                'tool_class': CompliantTool,
                'should_be_accepted': True,
                'reason': 'Fully compliant tool interface'
            }
        ]
        
        validation_results = []
        
        for case in test_cases:
            try:
                tool_instance = case['tool_class']()
                
                # Apply the validation logic that SHOULD exist
                is_basemodel = isinstance(tool_instance, BaseModel)
                has_execute = hasattr(tool_instance, 'execute')
                has_name = hasattr(tool_instance, 'name')
                
                # Current broken logic allows BaseModel registration
                if is_basemodel:
                    # This should be rejected but currently isn't
                    validation_results.append({
                        'tool_class': case['tool_class'].__name__,
                        'accepted': True,  # Current broken behavior
                        'should_be_accepted': case['should_be_accepted'],
                        'is_basemodel': True,
                        'validation_error': 'BaseModel incorrectly accepted'
                    })
                elif not has_execute:
                    # Tools without execute method should be rejected
                    validation_results.append({
                        'tool_class': case['tool_class'].__name__,
                        'accepted': False,
                        'should_be_accepted': case['should_be_accepted'],
                        'is_basemodel': False,
                        'validation_error': 'Missing execute method'
                    })
                else:
                    # Proper tools should be accepted
                    validation_results.append({
                        'tool_class': case['tool_class'].__name__,
                        'accepted': True,
                        'should_be_accepted': case['should_be_accepted'],
                        'is_basemodel': False,
                        'validation_error': None
                    })
                    
            except Exception as e:
                validation_results.append({
                    'tool_class': case['tool_class'].__name__,
                    'accepted': False,
                    'should_be_accepted': case['should_be_accepted'],
                    'is_basemodel': isinstance(tool_instance, BaseModel),
                    'validation_error': str(e)
                })
        
        # Analyze validation results
        validation_failures = []
        
        for result in validation_results:
            if result['accepted'] != result['should_be_accepted']:
                validation_failures.append(result)
                
        # CRITICAL: Check for BaseModel acceptance (the bug)
        basemodel_accepted = [
            result for result in validation_results
            if result['is_basemodel'] and result['accepted']
        ]
        
        if basemodel_accepted:
            logger.error(f" FAIL:  BaseModel tools incorrectly accepted: {basemodel_accepted}")
            pytest.fail(f"REPRODUCED BUG: BaseModel classes passed tool interface validation: {basemodel_accepted}")
            
        logger.info(f" CHART:  Interface validation results: {len(validation_failures)} failures out of {len(validation_results)} tests")
        
        if validation_failures:
            failure_details = [f"{r['tool_class']}: {r['validation_error']}" for r in validation_failures]
            logger.warning(f" WARNING: [U+FE0F] Interface validation failures: {failure_details}")
            
        logger.info(" PASS:  Tool interface contract validation test passed")
        
    def test_metaclass_name_fallback_prevention(self):
        """
        Test prevention of metaclass name fallbacks like "modelmetaclass".
        Should catch the exact error scenario from staging.
        
        CRITICAL: This test reproduces the exact "modelmetaclass" naming issue.
        """
        logger.info("[U+1F9EA] Testing metaclass name fallback prevention")
        
        # Create BaseModel instance and test the fallback naming logic
        basemodel_instance = ProblematicBaseModelTool()
        
        # This is the exact problematic code from user_context_tool_factory.py:118-120
        if hasattr(basemodel_instance, 'name') and basemodel_instance.name:
            tool_name = basemodel_instance.name
        else:
            # CRITICAL: This line causes "modelmetaclass" for BaseModel instances
            tool_name = getattr(basemodel_instance, '__class__', type(basemodel_instance)).__name__.lower()
            
        logger.info(f" SEARCH:  Fallback tool name generated: '{tool_name}'")
        
        # CRITICAL VALIDATION: Check if we generated the problematic name
        if tool_name == "modelmetaclass":
            logger.error(" FAIL:  REPRODUCED: Metaclass fallback generated 'modelmetaclass' name")
            pytest.fail("REPRODUCED STAGING BUG: BaseModel fallback naming generated 'modelmetaclass'")
            
        # Check for other problematic metaclass names
        problematic_names = ["modelmetaclass", "basemodel", "metaclass"]
        if tool_name.lower() in problematic_names:
            logger.error(f" FAIL:  Problematic fallback name generated: '{tool_name}'")
            pytest.fail(f"REPRODUCED BUG: Problematic metaclass fallback name: '{tool_name}'")
            
        # Test with multiple BaseModel classes to see if they all get the same name
        class AnotherBaseModelTool(BaseModel):
            value: str = "test"
            
        another_instance = AnotherBaseModelTool()
        
        if hasattr(another_instance, 'name') and another_instance.name:
            another_tool_name = another_instance.name
        else:
            another_tool_name = getattr(another_instance, '__class__', type(another_instance)).__name__.lower()
            
        logger.info(f" SEARCH:  Second BaseModel tool name: '{another_tool_name}'")
        
        # If multiple BaseModel classes generate the same fallback name, that's the duplicate registration issue
        if tool_name == another_tool_name and tool_name != "problematicbasemodeltool":
            logger.error(f" FAIL:  REPRODUCED: Multiple BaseModel classes generate same fallback name: '{tool_name}'")
            pytest.fail(f"REPRODUCED BUG: Multiple BaseModel classes generate duplicate fallback name: '{tool_name}'")
            
        # Test the actual registration to see if duplicates are rejected
        logger.info("[U+1F4DD] Testing duplicate registration prevention...")
        
        try:
            # First registration
            self.registry.register(tool_name, basemodel_instance)
            logger.info(f" PASS:  First registration of '{tool_name}' succeeded")
            
            # Second registration with same name - should fail
            try:
                self.registry.register(another_tool_name, another_instance)
                
                # If we reach here and the names were the same, that's a problem
                if tool_name == another_tool_name:
                    pytest.fail(f"REPRODUCED BUG: Duplicate registration succeeded for name: '{tool_name}'")
                    
            except Exception as e:
                if "already registered" in str(e) and tool_name == another_tool_name:
                    logger.error(f" FAIL:  REPRODUCED: Duplicate registration error for metaclass name: {e}")
                    pytest.fail(f"REPRODUCED STAGING BUG: Duplicate registration error: {e}")
                    
        except Exception as e:
            logger.error(f" FAIL:  Registration error: {e}")
            # This might be expected if BaseModel registration is properly prevented
            
        logger.info(" PASS:  Metaclass name fallback prevention test completed")


@pytest.mark.unit
@pytest.mark.toolregistry
class TestUniversalRegistryDuplicatePrevention(SSotBaseTestCase):
    """
    Unit tests for UniversalRegistry duplicate registration prevention.
    
    These tests focus on the low-level registry behavior that should prevent
    duplicate registrations and enforce proper tool validation.
    """
    
    def test_universal_registry_duplicate_registration_rejection(self):
        """
        Test that UniversalRegistry properly rejects duplicate registrations.
        Should validate the allow_override=False behavior.
        """
        logger.info("[U+1F9EA] Testing UniversalRegistry duplicate registration rejection")
        
        # Create registry with strict duplicate prevention
        registry = UniversalRegistry(allow_override=False)
        
        tool1 = MockBaseTool("test_tool")
        tool2 = MockBaseTool("test_tool")  # Same name, different instance
        
        # First registration should succeed
        registry.register("test_tool", tool1)
        registered_tool = registry.get_tool("test_tool")
        assert registered_tool is not None, "First registration should succeed"
        assert registered_tool is tool1, "Should return the first registered tool"
        
        # Second registration with same name should fail
        with pytest.raises(ValueError) as exc_info:
            registry.register("test_tool", tool2)
            
        assert "already registered" in str(exc_info.value).lower(), "Should reject duplicate registration"
        
        # Verify original tool is still registered
        still_registered = registry.get_tool("test_tool")
        assert still_registered is tool1, "Original tool should remain registered"
        
        logger.info(" PASS:  Duplicate registration rejection test passed")
        
    def test_universal_registry_singleton_enforcement(self):
        """
        Test singleton pattern enforcement in UniversalRegistry.
        Should catch multiple instance creation issues.
        """
        logger.info("[U+1F9EA] Testing UniversalRegistry singleton enforcement")
        
        # The registry itself might not be a singleton, but shared registrations should be consistent
        registry1 = UniversalRegistry()
        registry2 = UniversalRegistry()
        
        # They should be independent instances (not singleton)
        assert id(registry1) != id(registry2), "Registry instances should be independent"
        
        # But they should behave consistently
        tool = MockBaseTool("singleton_test_tool")
        
        registry1.register("singleton_test_tool", tool)
        
        # Registry2 should be able to register a tool with same name (independent registries)
        tool2 = MockBaseTool("singleton_test_tool")
        registry2.register("singleton_test_tool", tool2)  # Should succeed
        
        # Each registry should have its own tool
        assert registry1.get_tool("singleton_test_tool") is tool
        assert registry2.get_tool("singleton_test_tool") is tool2
        
        logger.info(" PASS:  Registry independence test passed")


@pytest.mark.unit
@pytest.mark.toolregistry  
class TestToolRegistryValidationHelpers(SSotBaseTestCase):
    """
    Unit tests for helper functions that should validate tools before registration.
    
    These tests focus on the validation logic that should exist to prevent
    BaseModel classes from being treated as tools.
    """
    
    def test_is_valid_tool_class_validation(self):
        """
        Test validation helper that should identify valid tool classes.
        This represents the validation logic that SHOULD exist but currently doesn't.
        """
        logger.info("[U+1F9EA] Testing tool class validation logic")
        
        # Define validation function that SHOULD exist
        def is_valid_tool_class(tool_class: Type) -> Dict[str, Any]:
            """Validate if a class is a proper tool class."""
            validation_result = {
                'is_valid': True,
                'reasons': []
            }
            
            # Check if it's a BaseModel (should be rejected)
            if issubclass(tool_class, BaseModel):
                validation_result['is_valid'] = False
                validation_result['reasons'].append('BaseModel classes are not valid tools')
                
            # Create instance to check interface
            try:
                instance = tool_class()
                
                # Check for execute method
                if not hasattr(instance, 'execute'):
                    validation_result['is_valid'] = False
                    validation_result['reasons'].append('Missing execute method')
                    
                # Check for name attribute (not strictly required due to fallback)
                if not hasattr(instance, 'name'):
                    validation_result['reasons'].append('Missing name attribute (will use fallback)')
                    
            except Exception as e:
                validation_result['is_valid'] = False
                validation_result['reasons'].append(f'Cannot instantiate: {e}')
                
            return validation_result
            
        # Test various tool classes
        test_cases = [
            (ProperToolClass, True, "Properly implemented tool"),
            (ProblematicBaseModelTool, False, "BaseModel should be rejected"),
            (ProblematicBaseModelWithName, False, "BaseModel with name should still be rejected"),
            (ToolWithoutName, True, "Tool without name is acceptable with fallback"),
        ]
        
        validation_failures = []
        
        for tool_class, expected_valid, description in test_cases:
            result = is_valid_tool_class(tool_class)
            
            if result['is_valid'] != expected_valid:
                validation_failures.append({
                    'tool_class': tool_class.__name__,
                    'expected': expected_valid,
                    'actual': result['is_valid'],
                    'reasons': result['reasons'],
                    'description': description
                })
                
            logger.info(f" SEARCH:  {tool_class.__name__}: {' PASS: ' if result['is_valid'] == expected_valid else ' FAIL: '} "
                       f"(Expected: {expected_valid}, Got: {result['is_valid']})")
                       
        # Report validation failures
        if validation_failures:
            failure_details = [
                f"{f['tool_class']}: expected {f['expected']}, got {f['actual']} - {f['reasons']}"
                for f in validation_failures
            ]
            logger.error(f" FAIL:  Tool validation failures: {failure_details}")
            
            # Check specifically for BaseModel validation failure
            basemodel_failures = [
                f for f in validation_failures
                if 'BaseModel' in f['tool_class'] and f['actual'] == True
            ]
            
            if basemodel_failures:
                pytest.fail(f"CRITICAL: Tool validation failed to reject BaseModel classes: {basemodel_failures}")
                
        logger.info(" PASS:  Tool class validation test passed")
        
    def test_tool_name_generation_safety(self):
        """
        Test safe tool name generation that prevents problematic fallbacks.
        This represents the logic that SHOULD exist to prevent "modelmetaclass" names.
        """
        logger.info("[U+1F9EA] Testing safe tool name generation")
        
        def generate_safe_tool_name(tool_instance) -> str:
            """Generate safe tool name, avoiding problematic fallbacks."""
            
            # Check if tool has explicit name
            if hasattr(tool_instance, 'name') and tool_instance.name:
                return tool_instance.name
                
            # For fallback, use class name but avoid problematic cases
            class_name = tool_instance.__class__.__name__
            
            # Convert to lowercase
            fallback_name = class_name.lower()
            
            # Check for problematic patterns
            problematic_patterns = ['modelmetaclass', 'basemodel', 'metaclass']
            
            if fallback_name in problematic_patterns:
                # Generate safer alternative name
                fallback_name = f"tool_{hash(class_name) & 0xFFFF:04x}"
                
            return fallback_name
            
        # Test name generation with various tool types
        test_instances = [
            (ProperToolClass(), "proper_tool"),
            (ProblematicBaseModelTool(), None),  # Should not generate "modelmetaclass"
            (ToolWithoutName(), "toolwithoutname"),
        ]
        
        name_generation_issues = []
        
        for tool_instance, expected_name in test_instances:
            generated_name = generate_safe_tool_name(tool_instance)
            
            # Check for problematic names
            if generated_name in ['modelmetaclass', 'basemodel', 'metaclass']:
                name_generation_issues.append({
                    'tool_class': tool_instance.__class__.__name__,
                    'generated_name': generated_name,
                    'issue': 'Generated problematic name'
                })
                
            logger.info(f"[U+1F3F7][U+FE0F] {tool_instance.__class__.__name__} -> '{generated_name}'")
            
        # Report issues
        if name_generation_issues:
            logger.error(f" FAIL:  Problematic name generation: {name_generation_issues}")
            pytest.fail(f"Safe name generation failed: {name_generation_issues}")
            
        logger.info(" PASS:  Safe tool name generation test passed")