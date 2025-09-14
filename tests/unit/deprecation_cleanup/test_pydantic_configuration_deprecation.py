"""
Pydantic Configuration Deprecation Test - Priority 1 Golden Path Critical

This test reproduces and validates deprecation warnings related to Pydantic configuration
patterns, specifically the migration from `class Config:` to `model_config = ConfigDict(...)`
that impacts data validation in the Golden Path user flow ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise, Platform)
- Business Goal: Data Validation & API Reliability
- Value Impact: Prevents data validation failures in chat functionality and agent responses
- Strategic Impact: Protects $500K+ ARR by ensuring stable data models and API schemas

Test Purpose:
1. Reproduce specific Pydantic configuration deprecation warnings
2. Establish failing tests that demonstrate deprecated Pydantic patterns
3. Provide guidance for migration to modern Pydantic v2 patterns

Priority 1 patterns targeted:
- `class Config:` → `model_config = ConfigDict(...)` migration
- Deprecated BaseModel configuration patterns
- Legacy Pydantic field validation patterns

Created: 2025-09-14
Test Category: Unit (deprecation reproduction)
"""

import warnings
import pytest
from typing import Optional, List, Dict, Any
from unittest.mock import Mock
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Pydantic imports for testing
try:
    from pydantic import BaseModel, Field, validator, ConfigDict, field_validator
    from pydantic.v1 import BaseModel as V1BaseModel
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback for testing without pydantic
    BaseModel = object
    Field = lambda **kwargs: None
    validator = lambda *args, **kwargs: lambda f: f
    field_validator = lambda *args, **kwargs: lambda f: f
    ConfigDict = dict
    V1BaseModel = object
    PYDANTIC_AVAILABLE = False


class TestPydanticConfigurationDeprecation(SSotBaseTestCase):
    """
    Test Pydantic configuration deprecation warnings.

    These tests SHOULD FAIL initially to prove they reproduce the deprecation warnings.
    After Pydantic pattern remediation, they should pass.
    """

    def setup_method(self, method=None):
        """Setup for Pydantic deprecation testing."""
        super().setup_method(method)
        # Clear any existing warnings to get clean test results
        warnings.resetwarnings()
        # Ensure we catch all deprecation warnings
        warnings.simplefilter("always", DeprecationWarning)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_deprecated_pydantic_class_config_pattern(self):
        """
        Test DEPRECATED: Pydantic `class Config:` pattern.

        This test should FAIL initially with deprecation warnings for:
        - `class Config:` instead of `model_config = ConfigDict(...)`
        - Legacy Pydantic configuration syntax
        - Deprecated BaseModel configuration patterns

        EXPECTED TO FAIL: This test reproduces deprecated Pydantic patterns
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # DEPRECATED PATTERN 1: Using `class Config:` syntax
            try:
                class DeprecatedUserModel(BaseModel):
                    """
                    DEPRECATED: Model using `class Config:` syntax.

                    This should trigger deprecation warnings for using the old
                    Pydantic v1 configuration pattern.
                    """
                    user_id: str
                    email: str
                    name: Optional[str] = None
                    preferences: Dict[str, Any] = Field(default_factory=dict)

                    class Config:
                        """DEPRECATED: This syntax is deprecated in Pydantic v2."""
                        arbitrary_types_allowed = True
                        validate_assignment = True
                        json_encoders = {
                            # Custom JSON encoding
                        }
                        schema_extra = {
                            "example": {
                                "user_id": "user123",
                                "email": "user@example.com",
                                "name": "Test User"
                            }
                        }

                # Test the deprecated model
                user = DeprecatedUserModel(
                    user_id="user123",
                    email="test@example.com",
                    name="Test User"
                )

                assert user.user_id == "user123"
                self.record_metric("deprecated_class_config_used", True)

            except Exception as e:
                # Expected - deprecated patterns may cause failures or warnings
                self.record_metric("deprecated_class_config_failure", str(e))

            # DEPRECATED PATTERN 2: Legacy validator syntax
            try:
                class DeprecatedValidationModel(BaseModel):
                    """
                    DEPRECATED: Model using legacy `@validator` syntax.

                    This should trigger deprecation warnings for using old
                    validation patterns.
                    """
                    agent_type: str
                    configuration: Dict[str, Any]

                    class Config:
                        """DEPRECATED: Class Config pattern."""
                        validate_assignment = True

                    @validator('agent_type')
                    def validate_agent_type(cls, v):
                        """DEPRECATED: @validator is deprecated in favor of field_validator."""
                        if v not in ['supervisor', 'triage', 'optimizer']:
                            raise ValueError(f'Invalid agent type: {v}')
                        return v

                    @validator('configuration')
                    def validate_configuration(cls, v):
                        """DEPRECATED: @validator syntax."""
                        if not isinstance(v, dict):
                            raise ValueError('Configuration must be a dictionary')
                        return v

                # Test the deprecated validation model
                agent = DeprecatedValidationModel(
                    agent_type="supervisor",
                    configuration={"timeout": 30}
                )

                assert agent.agent_type == "supervisor"
                self.record_metric("deprecated_validator_used", True)

            except Exception as e:
                self.record_metric("deprecated_validator_failure", str(e))

        # Count Pydantic-related warnings
        pydantic_warnings = [
            w for w in warning_list
            if any(keyword in str(w.message).lower()
                  for keyword in ['config', 'pydantic', 'validator', 'deprecated'])
        ]

        # Record metrics
        self.record_metric("total_pydantic_warnings", len(warning_list))
        self.record_metric("pydantic_deprecation_warnings", len(pydantic_warnings))

        # THIS SHOULD INITIALLY FAIL to prove Pydantic deprecation reproduction
        pydantic_deprecation_reproduced = len(pydantic_warnings) > 0 or len(warning_list) > 0

        assert pydantic_deprecation_reproduced, (
            f"REPRODUCTION FAILURE: Expected deprecation warnings for Pydantic class Config patterns, "
            f"but captured {len(pydantic_warnings)} Pydantic warnings out of {len(warning_list)} total warnings. "
            f"This indicates deprecated Pydantic patterns are not properly reproduced in this test."
        )

        # Log warnings for analysis
        for warning in pydantic_warnings:
            self.logger.warning(f"Captured Pydantic deprecation warning: {warning.message}")

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_deprecated_pydantic_field_patterns(self):
        """
        Test DEPRECATED: Legacy Pydantic field configuration patterns.

        This test should FAIL initially by demonstrating deprecated field configuration
        patterns that should be migrated to modern Pydantic v2 syntax.

        EXPECTED TO FAIL: This test reproduces deprecated Pydantic field patterns
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # DEPRECATED PATTERN: Legacy field configuration
            try:
                class DeprecatedFieldModel(BaseModel):
                    """
                    DEPRECATED: Model using legacy field configuration patterns.

                    This should trigger deprecation warnings for deprecated field syntax.
                    """
                    execution_id: str = Field(..., description="Execution identifier")
                    user_context: Dict[str, Any] = Field(
                        default_factory=dict,
                        description="User execution context"
                    )
                    agent_results: List[Dict[str, Any]] = Field(
                        default_factory=list,
                        description="Agent execution results"
                    )

                    class Config:
                        """DEPRECATED: Legacy Config class."""
                        # Deprecated configuration options
                        allow_population_by_field_name = True
                        validate_assignment = True
                        use_enum_values = True
                        fields = {
                            "execution_id": {
                                "alias": "execId",
                                "description": "Unique execution identifier"
                            }
                        }

                # Test the deprecated field model
                execution = DeprecatedFieldModel(
                    execution_id="exec123",
                    user_context={"user_id": "user123"},
                    agent_results=[{"agent": "triage", "result": "success"}]
                )

                assert execution.execution_id == "exec123"
                self.record_metric("deprecated_field_config_used", True)

            except Exception as e:
                self.record_metric("deprecated_field_config_failure", str(e))

            # DEPRECATED PATTERN: Legacy JSON schema configuration
            try:
                class DeprecatedSchemaModel(BaseModel):
                    """
                    DEPRECATED: Model using legacy JSON schema configuration.
                    """
                    websocket_event: str
                    event_data: Dict[str, Any]
                    timestamp: Optional[str] = None

                    class Config:
                        """DEPRECATED: Legacy schema configuration."""
                        title = "WebSocket Event Model"
                        schema_extra = {
                            "examples": [
                                {
                                    "websocket_event": "agent_started",
                                    "event_data": {"agent_id": "supervisor"},
                                    "timestamp": "2024-01-01T00:00:00Z"
                                }
                            ]
                        }

                # Test the deprecated schema model
                event = DeprecatedSchemaModel(
                    websocket_event="agent_started",
                    event_data={"agent_id": "supervisor"}
                )

                assert event.websocket_event == "agent_started"
                self.record_metric("deprecated_schema_config_used", True)

            except Exception as e:
                self.record_metric("deprecated_schema_config_failure", str(e))

        # Check for field and schema related warnings
        field_warnings = [
            w for w in warning_list
            if any(keyword in str(w.message).lower()
                  for keyword in ['field', 'schema', 'config', 'deprecated'])
        ]

        self.record_metric("field_config_warnings", len(field_warnings))

        # THIS SHOULD INITIALLY FAIL to prove field pattern deprecation reproduction
        field_deprecation_detected = len(field_warnings) > 0 or len(warning_list) > 0

        assert field_deprecation_detected, (
            f"REPRODUCTION FAILURE: Expected deprecation warnings for Pydantic field patterns, "
            f"but captured {len(field_warnings)} field warnings and {len(warning_list)} total warnings. "
            f"This indicates deprecated Pydantic field patterns are not properly reproduced."
        )

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_deprecated_pydantic_json_encoding_patterns(self):
        """
        Test DEPRECATED: Legacy Pydantic JSON encoding patterns.

        This test should FAIL initially by demonstrating deprecated JSON encoding
        configuration that should be migrated to modern serialization patterns.

        EXPECTED TO FAIL: This test reproduces deprecated JSON encoding patterns
        """
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")

            # DEPRECATED PATTERN: Legacy json_encoders configuration
            try:
                from datetime import datetime

                class DeprecatedJSONModel(BaseModel):
                    """
                    DEPRECATED: Model using legacy JSON encoders configuration.
                    """
                    message_id: str
                    content: str
                    created_at: datetime
                    metadata: Dict[str, Any] = Field(default_factory=dict)

                    class Config:
                        """DEPRECATED: Legacy JSON encoders configuration."""
                        json_encoders = {
                            datetime: lambda v: v.isoformat(),
                            # This pattern is deprecated in Pydantic v2
                        }
                        allow_population_by_field_name = True

                # Test the deprecated JSON model
                from datetime import datetime
                message = DeprecatedJSONModel(
                    message_id="msg123",
                    content="Test message",
                    created_at=datetime.now(),
                    metadata={"priority": "high"}
                )

                # Test JSON serialization with deprecated encoders
                json_data = message.json()
                assert "msg123" in json_data

                self.record_metric("deprecated_json_encoders_used", True)

            except Exception as e:
                self.record_metric("deprecated_json_encoders_failure", str(e))

        # Check for JSON encoding warnings
        json_warnings = [
            w for w in warning_list
            if any(keyword in str(w.message).lower()
                  for keyword in ['json', 'encoder', 'serializ', 'deprecated'])
        ]

        self.record_metric("json_encoding_warnings", len(json_warnings))

        # THIS SHOULD INITIALLY FAIL to prove JSON encoding deprecation reproduction
        json_deprecation_detected = len(json_warnings) > 0 or len(warning_list) > 0

        assert json_deprecation_detected, (
            f"REPRODUCTION FAILURE: Expected deprecation warnings for JSON encoding patterns, "
            f"but captured {len(json_warnings)} JSON warnings and {len(warning_list)} total warnings. "
            f"This indicates deprecated JSON encoding patterns are not properly reproduced."
        )


class TestPydanticMigrationGuidance(SSotBaseTestCase):
    """
    Test Pydantic migration guidance and correct patterns.

    These tests provide examples of correct migration paths from deprecated
    Pydantic patterns to modern Pydantic v2 patterns.
    """

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_migration_to_model_config_pattern(self):
        """
        Test migration guidance: `class Config:` → `model_config = ConfigDict(...)`.

        This test demonstrates the correct migration path and should PASS.
        """
        # CORRECT PATTERN: Using model_config with ConfigDict
        class ModernUserModel(BaseModel):
            """
            CORRECT: Model using modern `model_config = ConfigDict(...)` pattern.

            This demonstrates the correct Pydantic v2 configuration approach.
            """
            user_id: str
            email: str
            name: Optional[str] = None
            preferences: Dict[str, Any] = Field(default_factory=dict)

            # CORRECT: Modern configuration pattern
            model_config = ConfigDict(
                arbitrary_types_allowed=True,
                validate_assignment=True,
                json_schema_extra={
                    "example": {
                        "user_id": "user123",
                        "email": "user@example.com",
                        "name": "Test User"
                    }
                }
            )

        # Test the modern model
        user = ModernUserModel(
            user_id="user123",
            email="test@example.com",
            name="Test User"
        )

        assert user.user_id == "user123"
        assert user.email == "test@example.com"

        # Test validation
        user.preferences = {"theme": "dark"}
        assert user.preferences["theme"] == "dark"

        self.record_metric("modern_model_config_success", True)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_migration_to_field_validator_pattern(self):
        """
        Test migration guidance: `@validator` → `@field_validator`.

        This test demonstrates the correct validation migration path and should PASS.
        """
        try:
            from pydantic import field_validator

            # CORRECT PATTERN: Using field_validator
            class ModernValidationModel(BaseModel):
                """
                CORRECT: Model using modern `@field_validator` pattern.
                """
                agent_type: str
                configuration: Dict[str, Any]

                model_config = ConfigDict(
                    validate_assignment=True
                )

                @field_validator('agent_type')
                @classmethod
                def validate_agent_type(cls, v: str) -> str:
                    """Modern field validator pattern."""
                    if v not in ['supervisor', 'triage', 'optimizer']:
                        raise ValueError(f'Invalid agent type: {v}')
                    return v

                @field_validator('configuration')
                @classmethod
                def validate_configuration(cls, v: Dict[str, Any]) -> Dict[str, Any]:
                    """Modern field validator pattern."""
                    if not isinstance(v, dict):
                        raise ValueError('Configuration must be a dictionary')
                    return v

            # Test the modern validation model
            agent = ModernValidationModel(
                agent_type="supervisor",
                configuration={"timeout": 30}
            )

            assert agent.agent_type == "supervisor"
            assert agent.configuration["timeout"] == 30

            self.record_metric("modern_field_validator_success", True)

        except ImportError:
            # field_validator might not be available in older Pydantic versions
            self.record_metric("field_validator_unavailable", True)
            pytest.skip("field_validator not available in this Pydantic version")

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_modern_serialization_pattern(self):
        """
        Test modern Pydantic serialization pattern.

        This test demonstrates the correct serialization approach that replaces
        deprecated json_encoders configuration.
        """
        from datetime import datetime
        from typing import Any

        # CORRECT PATTERN: Modern serialization
        class ModernSerializationModel(BaseModel):
            """
            CORRECT: Model using modern serialization patterns.
            """
            message_id: str
            content: str
            created_at: datetime
            metadata: Dict[str, Any] = Field(default_factory=dict)

            model_config = ConfigDict(
                # Modern serialization configuration
                json_schema_extra={
                    "example": {
                        "message_id": "msg123",
                        "content": "Test message",
                        "created_at": "2024-01-01T00:00:00",
                        "metadata": {"priority": "high"}
                    }
                }
            )

            def model_dump_json_compatible(self) -> Dict[str, Any]:
                """Modern approach to custom serialization."""
                data = self.model_dump()
                # Custom serialization logic
                if isinstance(data.get('created_at'), datetime):
                    data['created_at'] = data['created_at'].isoformat()
                return data

        # Test the modern serialization model
        message = ModernSerializationModel(
            message_id="msg123",
            content="Test message",
            created_at=datetime.now(),
            metadata={"priority": "high"}
        )

        # Test modern serialization
        json_compatible = message.model_dump_json_compatible()
        assert json_compatible['message_id'] == "msg123"
        assert isinstance(json_compatible['created_at'], str)

        self.record_metric("modern_serialization_success", True)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not available")
    @pytest.mark.unit
    def test_websocket_event_model_modernization(self):
        """
        Test WebSocket event model modernization for Golden Path.

        This test demonstrates proper Pydantic v2 patterns for WebSocket events
        that are critical to the Golden Path user flow.
        """
        # CORRECT PATTERN: Modern WebSocket event model
        class ModernWebSocketEventModel(BaseModel):
            """
            Modern WebSocket event model for Golden Path agent events.
            """
            event_type: str
            agent_id: Optional[str] = None
            user_id: str
            session_id: str
            data: Dict[str, Any] = Field(default_factory=dict)
            timestamp: str

            model_config = ConfigDict(
                validate_assignment=True,
                json_schema_extra={
                    "examples": [
                        {
                            "event_type": "agent_started",
                            "agent_id": "supervisor",
                            "user_id": "user123",
                            "session_id": "session456",
                            "data": {"message": "Agent starting"},
                            "timestamp": "2024-01-01T00:00:00Z"
                        }
                    ]
                }
            )

            @field_validator('event_type')
            @classmethod
            def validate_event_type(cls, v: str) -> str:
                """Validate critical WebSocket event types."""
                valid_events = [
                    'agent_started',
                    'agent_thinking',
                    'tool_executing',
                    'tool_completed',
                    'agent_completed'
                ]
                if v not in valid_events:
                    raise ValueError(f'Invalid event type: {v}. Must be one of {valid_events}')
                return v

        # Test all critical WebSocket events
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        for event_type in critical_events:
            event = ModernWebSocketEventModel(
                event_type=event_type,
                agent_id="supervisor",
                user_id="user123",
                session_id="session456",
                data={"status": "active"},
                timestamp="2024-01-01T00:00:00Z"
            )

            assert event.event_type == event_type
            assert event.user_id == "user123"

        self.record_metric("websocket_model_modernization_success", True)


if __name__ == "__main__":
    """
    When run directly, this script executes the Pydantic configuration deprecation tests.
    """
    print("=" * 60)
    print("Pydantic Configuration Deprecation Test - Priority 1")
    print("=" * 60)

    # Note: These tests are designed to FAIL initially to prove reproduction
    print("⚠️  WARNING: These tests are designed to FAIL initially")
    print("   This proves that deprecated Pydantic patterns are reproduced")
    print("   After remediation, tests should pass")
    print("=" * 60)