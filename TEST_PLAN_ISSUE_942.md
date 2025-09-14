# 🚀 TEST PLAN: Issue #942 - Pydantic DataAnalysisResponse Validation Errors

## Executive Summary

**Issue:** Schema migration debt causing 6/7 ActionsAgent tests to fail due to Pydantic validation errors in DataAnalysisResponse  
**Root Cause:** Legacy field names in test data vs SSOT schema field names  
**Business Impact:** $500K+ ARR Golden Path WebSocket events and agent execution at risk  
**Test Strategy:** Create failing tests first, then passing tests to validate fixes

## Schema Analysis

### SSOT Schema (Correct)
Location: `/netra_backend/app/schemas/shared_types.py`
```python
class DataAnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    results: Dict[str, Any]
    metrics: PerformanceMetrics  
    created_at: float
    completed_at: Optional[float] = None
```

### Legacy Schema (Incorrect) 
Location: `/netra_backend/app/agents/data_sub_agent/models.py`
```python
class DataAnalysisResponse(BaseModel):
    analysis_type: str = "legacy_stub"
    results: Dict[str, Any] = {}
    metrics: Dict[str, float] = {}
    summary: str = "Legacy stub response"
```

### Test Field Violations
Tests are using non-existent fields:
- ❌ `query` (not in SSOT schema)
- ❌ `insights` (not in SSOT schema) 
- ❌ `recommendations` (not in SSOT schema)
- ✅ `results` (exists in SSOT)

## Test Plan Structure

### Phase 1: FAILING Tests (Reproduce Current State)
**Purpose:** Document current broken state and validate test infrastructure

#### Test 1.1: Unit Test - Schema Validation Failures
**File:** `/netra_backend/tests/unit/test_data_analysis_response_schema_violations.py`
**Type:** Unit Test (No Docker Required)
**Expected:** FAIL - Validates current broken state

```python
"""FAILING tests that reproduce Issue #942 Pydantic validation errors."""

import pytest
from pydantic import ValidationError
from netra_backend.app.schemas.shared_types import DataAnalysisResponse, PerformanceMetrics


class TestDataAnalysisResponseSchemaViolations:
    """These tests MUST FAIL - they reproduce the current broken state."""
    
    def test_legacy_field_names_cause_validation_error(self):
        """FAILING TEST: Legacy field names should cause ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            # This is how tests currently try to create DataAnalysisResponse
            DataAnalysisResponse(
                query="test query",  # ❌ Not in SSOT schema
                insights={"insight": "test"},  # ❌ Not in SSOT schema  
                recommendations=["rec1", "rec2"],  # ❌ Not in SSOT schema
                results=[{"test": "data"}]  # ✅ Valid field
            )
        
        # Validate that specific fields are missing
        error_details = str(exc_info.value)
        assert "analysis_id" in error_details
        assert "status" in error_details
        assert "metrics" in error_details
        assert "created_at" in error_details
    
    def test_missing_required_fields_validation_error(self):
        """FAILING TEST: Missing required SSOT fields should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            # Missing all required SSOT fields
            DataAnalysisResponse(
                results={"some": "data"}  # Only providing one valid field
            )
        
        error_details = str(exc_info.value)
        assert "analysis_id" in error_details or "field required" in error_details
        assert "status" in error_details or "field required" in error_details
        
    def test_incorrect_metrics_type_validation_error(self):
        """FAILING TEST: Wrong metrics type should cause ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DataAnalysisResponse(
                analysis_id="test_123",
                status="completed", 
                results={"test": "data"},
                metrics={"response_time": 100.0},  # ❌ Dict instead of PerformanceMetrics
                created_at=1642780800.0
            )
        
        error_details = str(exc_info.value)
        assert "PerformanceMetrics" in error_details or "type" in error_details
```

#### Test 1.2: Integration Test - ActionsAgent State Validation
**File:** `/netra_backend/tests/integration/test_actions_agent_schema_violations.py`
**Type:** Integration Test (No Docker Required)
**Expected:** FAIL - Reproduces actual test failures

```python
"""FAILING integration tests reproducing ActionsAgent schema violations."""

import pytest
from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.schemas.shared_types import DataAnalysisResponse
from pydantic import ValidationError


class TestActionsAgentSchemaViolations:
    """Integration tests that reproduce current ActionsAgent failures."""
    
    def test_deep_agent_state_with_invalid_data_result_fails(self):
        """FAILING TEST: DeepAgentState with invalid DataAnalysisResponse should fail."""
        with pytest.raises(ValidationError):
            # This mimics how current tests create state - should fail
            DeepAgentState(
                user_request="Test request",
                data_result=DataAnalysisResponse(
                    query="test query",  # ❌ Legacy field
                    results=[{"test": "data"}],
                    insights={"insight": "test insight"},  # ❌ Legacy field
                    recommendations=["test recommendation"]  # ❌ Legacy field
                )
            )
    
    def test_websocket_event_serialization_with_invalid_schema_fails(self):
        """FAILING TEST: WebSocket events with invalid schema should fail serialization.""" 
        # Simulate WebSocket event creation with invalid data
        invalid_data = {
            "query": "test query",
            "insights": {"test": "insight"},
            "recommendations": ["rec1"],
            "results": {"data": "test"}
        }
        
        with pytest.raises(ValidationError):
            # WebSocket events must serialize valid schemas
            DataAnalysisResponse.model_validate(invalid_data)
```

### Phase 2: PASSING Tests (Target State)
**Purpose:** Validate fixes and ensure schema compliance

#### Test 2.1: Unit Test - SSOT Schema Validation
**File:** `/netra_backend/tests/unit/test_data_analysis_response_ssot_schema.py`
**Type:** Unit Test (No Docker Required)
**Expected:** PASS - Validates SSOT schema works correctly

```python
"""PASSING tests that validate SSOT DataAnalysisResponse schema."""

import time
from netra_backend.app.schemas.shared_types import DataAnalysisResponse, PerformanceMetrics


class TestDataAnalysisResponseSSOTSchema:
    """These tests validate the correct SSOT schema usage."""
    
    def test_valid_ssot_schema_creation_succeeds(self):
        """PASSING TEST: Valid SSOT schema should create successfully."""
        # Create with proper SSOT field names
        response = DataAnalysisResponse(
            analysis_id="analysis_123",
            status="completed",
            results={"insights": ["insight1", "insight2"], "recommendations": ["rec1", "rec2"]},
            metrics=PerformanceMetrics(duration_ms=250.0),
            created_at=time.time()
        )
        
        assert response.analysis_id == "analysis_123"
        assert response.status == "completed"
        assert "insights" in response.results
        assert "recommendations" in response.results
        assert response.metrics.duration_ms == 250.0
        assert response.created_at > 0
    
    def test_optional_completed_at_field(self):
        """PASSING TEST: Optional completed_at field should work correctly."""
        # Test without completed_at
        response = DataAnalysisResponse(
            analysis_id="test_id",
            status="running", 
            results={},
            metrics=PerformanceMetrics(duration_ms=100.0),
            created_at=time.time()
        )
        assert response.completed_at is None
        
        # Test with completed_at
        response.completed_at = time.time()
        assert response.completed_at is not None
    
    def test_serialization_and_deserialization(self):
        """PASSING TEST: Schema should serialize/deserialize correctly."""
        original = DataAnalysisResponse(
            analysis_id="ser_test_123",
            status="completed",
            results={"data": {"key": "value"}},
            metrics=PerformanceMetrics(duration_ms=300.0, memory_usage_mb=128.5),
            created_at=1642780800.0,
            completed_at=1642780850.0
        )
        
        # Serialize to dict
        data = original.model_dump()
        
        # Deserialize back
        restored = DataAnalysisResponse.model_validate(data)
        
        assert restored.analysis_id == original.analysis_id
        assert restored.status == original.status
        assert restored.results == original.results
        assert restored.metrics.duration_ms == original.metrics.duration_ms
        assert restored.created_at == original.created_at
        assert restored.completed_at == original.completed_at
```

#### Test 2.2: Integration Test - WebSocket Event Schema Compliance
**File:** `/netra_backend/tests/integration/test_websocket_data_analysis_response_schema.py`
**Type:** Integration Test (No Docker Required)
**Expected:** PASS - Validates WebSocket events use correct schema

```python
"""Integration tests for WebSocket events with correct DataAnalysisResponse schema."""

import json
import time
from unittest.mock import AsyncMock
from netra_backend.app.schemas.shared_types import DataAnalysisResponse, PerformanceMetrics
from netra_backend.app.websocket_core.manager import UnifiedWebSocketManager


class TestWebSocketDataAnalysisResponseSchema:
    """Integration tests for WebSocket events with SSOT schema."""
    
    async def test_websocket_agent_completed_event_with_valid_schema(self):
        """PASSING TEST: WebSocket agent_completed event should serialize valid schema.""" 
        # Create valid SSOT DataAnalysisResponse
        valid_response = DataAnalysisResponse(
            analysis_id="ws_test_123",
            status="completed",
            results={
                "insights": ["Cost optimization opportunity identified", "Performance bottleneck detected"],
                "recommendations": ["Implement caching", "Optimize database queries"]
            },
            metrics=PerformanceMetrics(
                duration_ms=1250.0,
                memory_usage_mb=256.0,
                cpu_usage_percent=45.0
            ),
            created_at=time.time(),
            completed_at=time.time()
        )
        
        # Mock WebSocket manager
        ws_manager = UnifiedWebSocketManager()
        ws_manager.send_agent_event = AsyncMock()
        
        # Simulate sending agent_completed event
        event_data = {
            "event_type": "agent_completed",
            "agent_name": "ActionsToMeetGoalsSubAgent", 
            "data_result": valid_response.model_dump(),
            "run_id": "test_run_123",
            "user_id": "user_456"
        }
        
        await ws_manager.send_agent_event("user_456", "test_run_123", event_data)
        
        # Verify event was sent and data is serializable
        ws_manager.send_agent_event.assert_called_once()
        call_args = ws_manager.send_agent_event.call_args[0]
        
        # Validate the event data contains proper SSOT fields
        event_json = json.dumps(call_args[2])  # Should not raise serialization error
        event_dict = json.loads(event_json)
        
        data_result = event_dict["data_result"]
        assert "analysis_id" in data_result
        assert "status" in data_result
        assert "results" in data_result
        assert "metrics" in data_result
        assert "created_at" in data_result
    
    async def test_websocket_tool_completed_event_schema_validation(self):
        """PASSING TEST: WebSocket tool_completed event should validate data schemas."""
        valid_response = DataAnalysisResponse(
            analysis_id="tool_test_789",
            status="completed",
            results={"analysis_summary": "Performance analysis completed successfully"},
            metrics=PerformanceMetrics(duration_ms=800.0),
            created_at=time.time()
        )
        
        # Verify the response can be included in tool_completed events
        tool_event = {
            "event_type": "tool_completed",
            "tool_name": "data_analyzer",
            "result": valid_response.model_dump(),
            "execution_time_ms": 800.0
        }
        
        # Should serialize without errors  
        event_json = json.dumps(tool_event)
        reconstructed = json.loads(event_json)
        
        # Validate reconstructed data can recreate valid schema
        result_data = reconstructed["result"] 
        recreated_response = DataAnalysisResponse.model_validate(result_data)
        
        assert recreated_response.analysis_id == "tool_test_789"
        assert recreated_response.status == "completed"
```

#### Test 2.3: E2E Test - Golden Path WebSocket Events
**File:** `/netra_backend/tests/e2e/test_golden_path_data_analysis_response.py`
**Type:** E2E Test (No Docker - Staging Environment)
**Expected:** PASS - Validates complete Golden Path functionality

```python
"""E2E tests for Golden Path with corrected DataAnalysisResponse schema."""

import asyncio
import time
from test_framework.ssot.websocket_test_utility import SSotWebSocketTestUtility
from netra_backend.app.schemas.shared_types import DataAnalysisResponse, PerformanceMetrics


class TestGoldenPathDataAnalysisResponse:
    """E2E tests for Golden Path user flow with correct schema."""
    
    async def test_complete_agent_execution_with_valid_data_analysis_response(self):
        """PASSING TEST: Complete agent execution should use valid DataAnalysisResponse schema."""
        ws_utility = SSotWebSocketTestUtility()
        
        # Simulate complete Golden Path execution
        async with ws_utility.create_test_connection() as connection:
            # Send user message that triggers ActionsToMeetGoalsSubAgent
            user_message = {
                "type": "user_message",
                "content": "Help me optimize our cloud infrastructure costs",
                "user_id": "test_user_golden_path"
            }
            
            await connection.send_message(user_message)
            
            # Wait for and validate all 5 Golden Path WebSocket events
            events = await connection.collect_events(
                expected_events=[
                    "agent_started",
                    "agent_thinking", 
                    "tool_executing",
                    "tool_completed",
                    "agent_completed"
                ],
                timeout_seconds=30
            )
            
            # Validate agent_completed event has valid DataAnalysisResponse
            agent_completed = next(e for e in events if e["event_type"] == "agent_completed")
            
            # Verify data_result follows SSOT schema
            data_result = agent_completed.get("data_result", {})
            
            # Should be able to create valid DataAnalysisResponse from event data
            validated_response = DataAnalysisResponse.model_validate(data_result)
            
            # Verify SSOT fields are present and valid
            assert validated_response.analysis_id is not None
            assert validated_response.status in ["completed", "running", "error"]
            assert isinstance(validated_response.results, dict)
            assert isinstance(validated_response.metrics, PerformanceMetrics)
            assert validated_response.created_at > 0
    
    async def test_websocket_event_schema_consistency_across_all_events(self):
        """PASSING TEST: All WebSocket events should maintain schema consistency."""
        ws_utility = SSotWebSocketTestUtility()
        
        async with ws_utility.create_test_connection() as connection:
            # Trigger agent execution
            await connection.send_message({
                "type": "user_message",
                "content": "Analyze our system performance metrics",
                "user_id": "test_schema_consistency"
            })
            
            # Collect all events
            all_events = await connection.collect_events(timeout_seconds=25)
            
            # Find events that contain DataAnalysisResponse data
            data_analysis_events = [
                event for event in all_events 
                if "data_result" in event and isinstance(event["data_result"], dict)
            ]
            
            # Validate each event's DataAnalysisResponse follows SSOT schema
            for event in data_analysis_events:
                data_result = event["data_result"]
                
                # Should not raise ValidationError
                try:
                    DataAnalysisResponse.model_validate(data_result)
                except Exception as e:
                    pytest.fail(f"Event {event['event_type']} contains invalid DataAnalysisResponse: {e}")
```

## Test Execution Strategy

### Phase 1: Validate Failing Tests
```bash
# Run failing tests to confirm they reproduce the issue
python -m pytest netra_backend/tests/unit/test_data_analysis_response_schema_violations.py -v
python -m pytest netra_backend/tests/integration/test_actions_agent_schema_violations.py -v

# Expected Result: All tests should FAIL with ValidationError
```

### Phase 2: Implement Schema Fixes
1. Update all test files to use SSOT field names
2. Replace legacy `DataAnalysisResponse` imports with SSOT version
3. Migrate field mappings: `query` → `results`, `insights` → `results`, `recommendations` → `results`

### Phase 3: Validate Passing Tests  
```bash
# Run passing tests to confirm fixes work
python -m pytest netra_backend/tests/unit/test_data_analysis_response_ssot_schema.py -v
python -m pytest netra_backend/tests/integration/test_websocket_data_analysis_response_schema.py -v
python -m pytest netra_backend/tests/e2e/test_golden_path_data_analysis_response.py -v

# Expected Result: All tests should PASS
```

### Phase 4: Regression Testing
```bash
# Run original failing tests to confirm they now pass
python -m pytest netra_backend/tests/unit/test_actions_to_meet_goals_agent_state.py -v
python -m pytest netra_backend/tests/unit/test_actions_to_meet_goals_execution_failure.py -v

# Run mission critical tests
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Success Criteria

✅ **Phase 1 Complete:** All failing tests reproduce current ValidationError issues  
✅ **Phase 2 Complete:** Schema fixes implemented across all affected files  
✅ **Phase 3 Complete:** All passing tests validate SSOT schema compliance  
✅ **Phase 4 Complete:** Original 6/7 ActionsAgent tests now pass  
✅ **Golden Path Validated:** All 5 WebSocket events work with correct schema  
✅ **Business Value Protected:** $500K+ ARR functionality operational  

## Risk Mitigation

- **No Docker Required:** All tests run without Docker infrastructure dependencies
- **Real Service Integration:** Integration tests use real WebSocket connections where possible  
- **Incremental Validation:** Each phase validates previous phase success
- **Rollback Plan:** Keep legacy schema files until full migration verified
- **SSOT Compliance:** All new tests follow established SSOT patterns

## Business Value Protection

- **Golden Path Priority:** Ensures end-to-end user chat experience works correctly
- **WebSocket Events:** Validates all 5 mission-critical events function properly
- **Agent Execution:** Confirms ActionsToMeetGoalsSubAgent delivers value to users
- **Schema Consistency:** Prevents future regression issues in data serialization
- **Test Coverage:** Comprehensive validation of schema migration ensures stability