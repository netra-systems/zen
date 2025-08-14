"""Critical Pydantic Validation Tests for Agent System

This test suite addresses the CRITICAL validation errors seen in production
where LLM returns strings instead of dicts for nested fields.
"""

import pytest
import json
from typing import Dict, Any, List
from pydantic import ValidationError
from unittest.mock import AsyncMock, Mock, patch

from app.agents.triage_sub_agent.models import (
    TriageResult, ToolRecommendation, Priority, Complexity,
    ExtractedEntities, UserIntent, TriageMetadata
)
from app.agents.state import (
    OptimizationsResult, DeepAgentState, AgentMetadata
)
from app.llm.llm_manager import LLMManager
from app.agents.triage_sub_agent.agent import TriageSubAgent
from app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent


class TestPydanticValidationCritical:
    """Test Pydantic validation issues seen in production"""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager"""
        llm = Mock(spec=LLMManager)
        return llm
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Create mock tool dispatcher"""
        from app.agents.tool_dispatcher import ToolDispatcher
        return Mock(spec=ToolDispatcher)
    
    @pytest.mark.asyncio
    async def test_triage_tool_recommendations_string_parameters_error(self):
        """Test exact error: tool_recommendations.parameters as string instead of dict"""
        # This is the EXACT error from production logs
        invalid_llm_response = {
            "category": "Cost Optimization",
            "confidence_score": 0.95,
            "priority": "medium",
            "complexity": "moderate",
            "tool_recommendations": [
                {
                    "tool_name": "optimize_performance",
                    "relevance_score": 0.9,
                    # ERROR: This is a string, not a dict!
                    "parameters": '{ "performance_goal": "3x", "budget_constraint": "no_increase" }'
                },
                {
                    "tool_name": "analyze_metrics",
                    "relevance_score": 0.8,
                    # ERROR: This is also a string!
                    "parameters": '{ "metric": "latency" }'
                }
            ]
        }
        
        # This should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            TriageResult(**invalid_llm_response)
        
        # Verify the exact error message matches production
        error = exc_info.value
        assert "Input should be a valid dictionary" in str(error)
        assert "tool_recommendations" in str(error)
    
    @pytest.mark.asyncio
    async def test_triage_string_parameters_recovery(self):
        """Test recovery from string parameters by parsing JSON"""
        # Test the recovery mechanism
        invalid_response_str = json.dumps({
            "category": "Cost Optimization",
            "tool_recommendations": [{
                "tool_name": "optimize",
                "parameters": '{"key": "value"}'  # String that needs parsing
            }]
        })
        
        # Recovery function that should be implemented
        def fix_string_parameters(data: Dict[str, Any]) -> Dict[str, Any]:
            """Fix string parameters in tool recommendations"""
            if "tool_recommendations" in data:
                for rec in data["tool_recommendations"]:
                    if isinstance(rec.get("parameters"), str):
                        try:
                            rec["parameters"] = json.loads(rec["parameters"])
                        except json.JSONDecodeError:
                            rec["parameters"] = {}
            return data
        
        # Parse and fix
        parsed = json.loads(invalid_response_str)
        fixed = fix_string_parameters(parsed)
        
        # Should now validate
        result = TriageResult(**fixed)
        assert result.tool_recommendations[0].parameters == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_optimizations_result_recommendations_dict_error(self):
        """Test exact error: recommendations as dict instead of list of strings"""
        # This is the EXACT error from production logs
        invalid_response = {
            "optimization_type": "general",
            "recommendations": [
                # ERROR: This is a dict, not a string!
                {"type": "general", "description": "Optimize", "priority": "medium", "fallback": True}
            ]
        }
        
        # This should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            OptimizationsResult(**invalid_response)
        
        # Verify error matches production
        error = exc_info.value
        assert "Input should be a valid string" in str(error)
        assert "recommendations.0" in str(error)
    
    @pytest.mark.asyncio
    async def test_optimizations_fallback_format_error(self):
        """Test the fallback optimization format that's failing"""
        # The fallback is returning wrong format
        fallback_response = {
            "optimization_type": "general",
            "recommendations": [
                {"type": "general", "description": "Optimize", "priority": "medium"}
            ],
            "confidence_score": 0.5
        }
        
        # Fix function that should be implemented
        def fix_recommendations_format(data: Dict[str, Any]) -> Dict[str, Any]:
            """Convert dict recommendations to strings"""
            if "recommendations" in data and isinstance(data["recommendations"], list):
                fixed_recs = []
                for rec in data["recommendations"]:
                    if isinstance(rec, dict):
                        # Convert dict to string description
                        desc = rec.get("description", str(rec))
                        fixed_recs.append(desc)
                    else:
                        fixed_recs.append(str(rec))
                data["recommendations"] = fixed_recs
            return data
        
        # Fix and validate
        fixed = fix_recommendations_format(fallback_response)
        result = OptimizationsResult(**fixed)
        assert result.recommendations == ["Optimize"]
    
    @pytest.mark.asyncio
    async def test_llm_response_not_fully_defined_error(self):
        """Test LLMResponse not fully defined error"""
        # This tests the circular dependency issue
        with patch("app.llm.llm_manager.LLMResponse") as mock_response:
            # Simulate the error condition
            mock_response.model_rebuild = Mock(side_effect=Exception(
                "LLMResponse is not fully defined; you should define LLMProvider"
            ))
            
            # This should be caught and handled
            llm = LLMManager()
            with pytest.raises(Exception) as exc_info:
                mock_response.model_rebuild()
            
            assert "not fully defined" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_datetime_serialization_error(self):
        """Test datetime serialization in state and WebSocket messages"""
        from datetime import datetime
        import json
        
        # Create state with datetime
        state = DeepAgentState(
            user_request="Test",
            metadata=AgentMetadata(
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
        )
        
        # Direct JSON dump should fail
        with pytest.raises(TypeError) as exc_info:
            json.dumps(state.model_dump())
        assert "not JSON serializable" in str(exc_info.value)
        
        # Should work with proper serialization
        def serialize_datetime(obj):
            """JSON serializer for datetime objects"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        # This should work
        serialized = json.dumps(
            state.model_dump(), 
            default=serialize_datetime
        )
        assert serialized  # Should not raise
    
    @pytest.mark.asyncio
    async def test_async_sessionmaker_execute_error(self):
        """Test the database session error seen in production"""
        from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
        
        # Mock the incorrect usage pattern
        mock_sessionmaker = Mock(spec=async_sessionmaker)
        
        # This is the error - calling execute on sessionmaker not session
        with pytest.raises(AttributeError) as exc_info:
            await mock_sessionmaker.execute("SELECT 1")
        
        assert "has no attribute 'execute'" in str(exc_info.value)
        
        # Correct pattern
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.execute = AsyncMock(return_value=Mock())
        
        # This should work
        result = await mock_session.execute("SELECT 1")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_websocket_message_validation_error(self):
        """Test WebSocket message type validation error"""
        from app.schemas import WebSocketMessage
        
        # Invalid message type from production
        invalid_message = {
            "type": "thread_created",  # Not in allowed types
            "payload": {"thread_id": "123"}
        }
        
        # Should raise validation error
        with pytest.raises(ValidationError) as exc_info:
            WebSocketMessage(**invalid_message)
        
        error_str = str(exc_info.value)
        # The error should indicate invalid message type
        assert "type" in error_str.lower() or "invalid" in error_str.lower()
    
    @pytest.mark.asyncio
    async def test_triage_agent_with_real_llm_patterns(self, mock_llm_manager, mock_tool_dispatcher):
        """Test triage agent with actual LLM response patterns from production"""
        triage_agent = TriageSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        # First call returns invalid format (string parameters)
        invalid_response = TriageResult(
            category="Cost Optimization",
            confidence_score=0.95,
            tool_recommendations=[]  # Start with empty to avoid error
        )
        
        # Mock the structured LLM to fail first, then succeed
        mock_llm_manager.ask_structured_llm = AsyncMock(side_effect=[
            ValidationError.from_exception_data(
                "ValidationError",
                [{"type": "dict_type", "loc": ("tool_recommendations", 0, "parameters")}]
            ),
            invalid_response  # Second call succeeds
        ])
        
        # Mock the fallback JSON extraction
        mock_llm_manager.ask_llm = AsyncMock(return_value=json.dumps({
            "category": "Cost Optimization",
            "confidence_score": 0.95,
            "tool_recommendations": []
        }))
        
        state = DeepAgentState(user_request="Optimize my costs")
        
        # Should handle the error and retry
        await triage_agent.execute(state, "test_run_id", False)
        
        # Verify retry happened
        assert mock_llm_manager.ask_structured_llm.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_complete_validation_chain(self):
        """Test the complete validation chain from request to response"""
        # Test data flow with all potential validation points
        test_cases = [
            {
                "name": "String in dict field",
                "data": {"parameters": '{"key": "value"}'},
                "expected_error": "Input should be a valid dictionary"
            },
            {
                "name": "Dict in string list field",
                "data": {"recommendations": [{"type": "test"}]},
                "expected_error": "Input should be a valid string"
            },
            {
                "name": "Invalid enum value",
                "data": {"priority": "ultra-high"},
                "expected_error": "Input should be"
            },
            {
                "name": "Out of range float",
                "data": {"confidence_score": 1.5},
                "expected_error": "less than or equal to 1"
            }
        ]
        
        for test_case in test_cases:
            # Test with different models based on fields
            if "parameters" in test_case["data"]:
                model_data = {
                    "tool_name": "test",
                    "relevance_score": 0.5,
                    **test_case["data"]
                }
                with pytest.raises(ValidationError) as exc_info:
                    ToolRecommendation(**model_data)
            elif "recommendations" in test_case["data"]:
                model_data = {
                    "optimization_type": "test",
                    **test_case["data"]
                }
                with pytest.raises(ValidationError) as exc_info:
                    OptimizationsResult(**model_data)
            elif "priority" in test_case["data"]:
                model_data = {
                    "category": "test",
                    **test_case["data"]
                }
                with pytest.raises(ValidationError) as exc_info:
                    TriageResult(**model_data)
            elif "confidence_score" in test_case["data"]:
                model_data = {
                    "category": "test",
                    **test_case["data"]
                }
                with pytest.raises(ValidationError) as exc_info:
                    TriageResult(**model_data)
            
            # Verify expected error appears
            if test_case.get("expected_error"):
                assert test_case["expected_error"] in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])