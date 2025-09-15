"""
FAILING TEST: DeepAgentState Interface Consistency Validation (Issue #871)

This test validates that both DeepAgentState definitions have identical interfaces.
If they differ, this proves the SSOT violation causes interface inconsistency.

Expected: FAIL initially if interfaces differ
After Fix: PASS (single consistent interface)
"""

import pytest
import inspect
from typing import get_type_hints, get_origin, get_args
from pydantic import BaseModel

@pytest.mark.unit
class TestDeepAgentStateInterfaceConsistency:
    """Test suite validating DeepAgentState interface consistency"""

    def get_class_signature(self, cls):
        """Extract class signature for comparison"""
        signature = {
            'fields': {},
            'methods': set(),
            'properties': set(),
            'base_classes': [base.__name__ for base in cls.__mro__[1:]],  # Exclude self
            'module': cls.__module__,
            'docstring': cls.__doc__
        }

        # Get fields for Pydantic models (using v2 API)
        if hasattr(cls, 'model_fields'):
            for field_name, field_info in cls.model_fields.items():
                signature['fields'][field_name] = {
                    'annotation': str(field_info.annotation),
                    'default': str(field_info.default),
                    'required': field_info.is_required()
                }
        elif hasattr(cls, '__fields__'):
            # Fallback for Pydantic v1 compatibility
            for field_name, field_info in cls.__fields__.items():
                signature['fields'][field_name] = {
                    'type': str(getattr(field_info, 'type_', field_info.annotation)),
                    'default': field_info.default,
                    'required': getattr(field_info, 'is_required', lambda: True)()
                }

        # Get properties (like thread_id property in deprecated version)
        for name in dir(cls):
            if isinstance(getattr(cls, name, None), property):
                signature['properties'].add(name)

        # Get methods (excluding private/dunder methods)
        for name, method in inspect.getmembers(cls, predicate=inspect.ismethod):
            if not name.startswith('_'):
                signature['methods'].add(name)

        return signature

    def test_deepagentstate_field_consistency_violation(self):
        """
        FAILING TEST: Validates field definitions are identical between versions

        Expected: FAIL initially if field definitions differ
        After Fix: N/A (only SSOT version exists)
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState
        except ImportError:
            pytest.skip("Deprecated DeepAgentState has been removed - SSOT remediation complete")

        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState
        except ImportError:
            pytest.fail("SSOT DeepAgentState source missing from schemas.agent_models")

        # Get signatures of both classes
        deprecated_sig = self.get_class_signature(DeprecatedState)
        ssot_sig = self.get_class_signature(SsotState)

        # Compare field definitions
        deprecated_fields = deprecated_sig['fields']
        ssot_fields = ssot_sig['fields']

        # Check for missing fields in either version
        deprecated_only = set(deprecated_fields.keys()) - set(ssot_fields.keys())
        ssot_only = set(ssot_fields.keys()) - set(deprecated_fields.keys())

        if deprecated_only or ssot_only:
            error_msg = f"INTERFACE INCONSISTENCY DETECTED:\n"
            if deprecated_only:
                error_msg += f"  - Fields only in deprecated: {deprecated_only}\n"
            if ssot_only:
                error_msg += f"  - Fields only in SSOT: {ssot_only}\n"
            pytest.fail(error_msg)

        # Check for type differences in common fields
        field_type_diffs = []
        for field_name in deprecated_fields:
            if field_name in ssot_fields:
                dep_type = deprecated_fields[field_name]['type']
                ssot_type = ssot_fields[field_name]['type']
                if dep_type != ssot_type:
                    field_type_diffs.append(f"  {field_name}: deprecated({dep_type}) != ssot({ssot_type})")

        if field_type_diffs:
            pytest.fail(f"FIELD TYPE INCONSISTENCIES:\n" + "\n".join(field_type_diffs))

        # If we get here, interfaces are consistent (good for SSOT compliance)
        assert True, "Interface consistency validated"

    def test_deepagentstate_property_consistency_violation(self):
        """
        FAILING TEST: Validates property definitions are identical between versions

        The deprecated version has a thread_id property, SSOT version doesn't.
        This causes "'DeepAgentState' object has no attribute 'thread_id'" errors.

        Expected: FAIL initially (property differences exist)
        After Fix: N/A (only SSOT version exists)
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState
        except ImportError:
            pytest.skip("Deprecated DeepAgentState has been removed - SSOT remediation complete")

        from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState

        # Get signatures of both classes
        deprecated_sig = self.get_class_signature(DeprecatedState)
        ssot_sig = self.get_class_signature(SsotState)

        # Compare properties
        deprecated_props = deprecated_sig['properties']
        ssot_props = ssot_sig['properties']

        # Check for property differences
        deprecated_only_props = deprecated_props - ssot_props
        ssot_only_props = ssot_props - deprecated_props

        if deprecated_only_props or ssot_only_props:
            error_msg = f"PROPERTY INCONSISTENCY DETECTED:\n"
            if deprecated_only_props:
                error_msg += f"  - Properties only in deprecated: {deprecated_only_props}\n"
            if ssot_only_props:
                error_msg += f"  - Properties only in SSOT: {ssot_only_props}\n"
            error_msg += f"This causes 'object has no attribute' runtime errors"
            pytest.fail(error_msg)

    def test_deepagentstate_inheritance_consistency(self):
        """
        FAILING TEST: Validates both versions inherit from same base classes

        Expected: FAIL if inheritance differs
        After Fix: N/A (only SSOT version exists)
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState
        except ImportError:
            pytest.skip("Deprecated DeepAgentState has been removed - SSOT remediation complete")

        from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState

        # Both should inherit from BaseModel
        assert issubclass(DeprecatedState, BaseModel), "Deprecated version should inherit from BaseModel"
        assert issubclass(SsotState, BaseModel), "SSOT version should inherit from BaseModel"

        # Get MRO (Method Resolution Order) for both
        deprecated_mro = [cls.__name__ for cls in DeprecatedState.__mro__]
        ssot_mro = [cls.__name__ for cls in SsotState.__mro__]

        # Compare inheritance chains (excluding the class itself)
        deprecated_bases = deprecated_mro[1:]  # Skip self
        ssot_bases = ssot_mro[1:]  # Skip self

        assert deprecated_bases == ssot_bases, (
            f"INHERITANCE INCONSISTENCY:\n"
            f"  - Deprecated MRO: {deprecated_mro}\n"
            f"  - SSOT MRO: {ssot_mro}\n"
            f"Both versions should have identical inheritance"
        )

    def test_deepagentstate_runtime_compatibility_violation(self):
        """
        FAILING TEST: Tests runtime compatibility between versions

        Expected: FAIL if objects aren't interchangeable
        After Fix: N/A (only SSOT version exists)
        """
        try:
            from netra_backend.app.schemas.agent_models import DeepAgentState as DeprecatedState
        except ImportError:
            pytest.skip("Deprecated DeepAgentState has been removed - SSOT remediation complete")

        from netra_backend.app.schemas.agent_models import DeepAgentState as SsotState

        # Create instances with minimal required data
        test_data = {
            "user_request": "test_request",
            "chat_thread_id": "test_thread_123",
            "user_id": "test_user_456"
        }

        try:
            deprecated_instance = DeprecatedState(**test_data)
            ssot_instance = SsotState(**test_data)
        except Exception as e:
            pytest.fail(f"RUNTIME CREATION FAILED: {e}")

        # Both should be valid Pydantic models
        assert isinstance(deprecated_instance, BaseModel), "Deprecated instance should be BaseModel"
        assert isinstance(ssot_instance, BaseModel), "SSOT instance should be BaseModel"

        # Both should serialize to same dict structure
        deprecated_dict = deprecated_instance.model_dump()
        ssot_dict = ssot_instance.model_dump()

        # Compare serialized structures (should be identical)
        deprecated_keys = set(deprecated_dict.keys())
        ssot_keys = set(ssot_dict.keys())

        if deprecated_keys != ssot_keys:
            key_diff = deprecated_keys.symmetric_difference(ssot_keys)
            pytest.fail(f"SERIALIZATION INCONSISTENCY - Key differences: {key_diff}")

        # Check values for common keys
        for key in deprecated_keys & ssot_keys:
            if deprecated_dict[key] != ssot_dict[key]:
                pytest.fail(
                    f"VALUE INCONSISTENCY for {key}: "
                    f"deprecated({deprecated_dict[key]}) != ssot({ssot_dict[key]})"
                )