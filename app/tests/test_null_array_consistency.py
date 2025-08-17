"""Null Handling and Array Consistency Tests.

Tests null vs undefined handling and array type consistency patterns
across the frontend-backend interface.
"""

import json
import pytest
from typing import Dict, Any

# Import schemas for testing
from app.schemas.registry import Message, MessageType, StartAgentPayload
from app.schemas.Request import RequestModel

# Import test data
from app.tests.frontend_data_mocks import FrontendDataMocks


class TestNullUndefinedHandling:
    """Test handling of null vs undefined fields."""
    
    def test_explicit_none_handling(self) -> None:
        """Test explicit None value handling."""
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None
        )
        
        json_data = payload.model_dump()
        assert "thread_id" in json_data
        assert json_data["thread_id"] is None
    
    def test_exclude_none_behavior(self) -> None:
        """Test exclude_none serialization behavior."""
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None
        )
        
        json_data_with_none = payload.model_dump()
        json_data_no_none = payload.model_dump(exclude_none=True)
        
        assert "thread_id" in json_data_with_none
        assert "thread_id" not in json_data_no_none
    
    def test_optional_field_omission(self) -> None:
        """Test omitted optional fields."""
        minimal_data = FrontendDataMocks.minimal_start_agent_payload()
        
        payload = StartAgentPayload(**minimal_data)
        json_data = payload.model_dump(exclude_none=True)
        
        assert "query" in json_data
        assert "user_id" in json_data
        assert "thread_id" not in json_data
        assert "context" not in json_data
    
    def test_nested_none_handling(self) -> None:
        """Test None handling in nested structures."""
        workloads_data = [{
            "run_id": "run123",
            "query": "test",
            "data_source": {
                "source_table": "logs",
                "filters": None
            },
            "time_range": {
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-02T00:00:00Z"
            }
        }]
        
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=workloads_data
        )
        
        json_data = request.model_dump()
        assert json_data["workloads"][0]["data_source"]["filters"] is None
    
    def test_partial_object_with_nulls(self) -> None:
        """Test partial objects with explicit null fields."""
        partial_data = {
            "query": "Test query",
            "user_id": "user123",
            "thread_id": None,
            "context": {
                "session_id": "session123",
                "metadata": None
            }
        }
        
        payload = StartAgentPayload(**partial_data)
        json_data = payload.model_dump()
        
        assert json_data["thread_id"] is None
        assert json_data["context"]["metadata"] is None
    
    def test_conditional_null_exclusion(self) -> None:
        """Test conditional null field exclusion."""
        payload = StartAgentPayload(
            query="Test",
            user_id="user123",
            thread_id=None,
            context=None
        )
        
        # Include nulls
        with_nulls = payload.model_dump(exclude_none=False)
        assert with_nulls["thread_id"] is None
        assert with_nulls["context"] is None
        
        # Exclude nulls
        without_nulls = payload.model_dump(exclude_none=True)
        assert "thread_id" not in without_nulls
        assert "context" not in without_nulls
    
    def test_nested_null_propagation(self) -> None:
        """Test null value propagation in nested objects."""
        nested_structure = {
            "level1": {
                "level2": {
                    "value": None,
                    "array": [None, "value", None]
                },
                "other_field": "present"
            }
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Nested null test",
            metadata=nested_structure
        )
        
        json_data = message.model_dump()
        level2 = json_data["metadata"]["level1"]["level2"]
        assert level2["value"] is None
        assert level2["array"][0] is None
        assert level2["array"][2] is None


class TestArrayTypeConsistency:
    """Test array type handling consistency."""
    
    def test_simple_array_serialization(self) -> None:
        """Test simple array serialization."""
        workloads_data = FrontendDataMocks.workloads_array_data()
        
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=workloads_data
        )
        
        json_data = request.model_dump()
        assert isinstance(json_data["workloads"], list)
        assert len(json_data["workloads"]) == 3
    
    def test_empty_array_handling(self) -> None:
        """Test empty array handling."""
        request = RequestModel(
            user_id="user123",
            query="Test",
            workloads=[]
        )
        
        json_data = request.model_dump()
        assert isinstance(json_data["workloads"], list)
        assert len(json_data["workloads"]) == 0
    
    def test_nested_array_structures(self) -> None:
        """Test nested array structures."""
        complex_result = {
            "recommendations": [
                {"action": "scale_up", "tags": ["performance", "cost"]},
                {"action": "optimize", "tags": ["efficiency"]}
            ],
            "metrics_history": [
                [10, 20, 30],  # CPU usage over time
                [5, 15, 25]    # Memory usage over time
            ]
        }
        
        json_str = json.dumps(complex_result)
        parsed = json.loads(json_str)
        
        assert len(parsed["recommendations"]) == 2
        assert len(parsed["metrics_history"][0]) == 3
        assert "performance" in parsed["recommendations"][0]["tags"]
    
    def test_array_of_mixed_types(self) -> None:
        """Test arrays containing mixed types."""
        mixed_metadata = {
            "values": ["string", 42, True, None, {"key": "value"}],
            "nested_arrays": [[1, 2], ["a", "b"], [True, False]]
        }
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Mixed array test",
            metadata=mixed_metadata
        )
        
        json_data = message.model_dump()
        values = json_data["metadata"]["values"]
        
        assert values[0] == "string"
        assert values[1] == 42
        assert values[2] is True
        assert values[3] is None
        assert isinstance(values[4], dict)
    
    def test_array_bounds_and_indexing(self) -> None:
        """Test array bounds and indexing consistency."""
        large_array = [f"item_{i}" for i in range(100)]
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Large array test",
            metadata={"items": large_array}
        )
        
        json_data = message.model_dump()
        items = json_data["metadata"]["items"]
        
        assert len(items) == 100
        assert items[0] == "item_0"
        assert items[99] == "item_99"
    
    def test_sparse_array_handling(self) -> None:
        """Test sparse array handling with None values."""
        sparse_array = ["value1", None, "value3", None, "value5"]
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Sparse array test",
            metadata={"sparse_data": sparse_array}
        )
        
        json_data = message.model_dump()
        sparse_data = json_data["metadata"]["sparse_data"]
        
        assert len(sparse_data) == 5
        assert sparse_data[0] == "value1"
        assert sparse_data[1] is None
        assert sparse_data[2] == "value3"
        assert sparse_data[3] is None
        assert sparse_data[4] == "value5"
    
    def test_array_serialization_performance(self) -> None:
        """Test array serialization with large datasets."""
        # Create a reasonably large array to test performance
        large_dataset = [
            {
                "id": i,
                "name": f"item_{i}",
                "values": [j for j in range(10)],
                "metadata": {"category": i % 5}
            }
            for i in range(50)
        ]
        
        message = Message(
            id="msg123",
            type=MessageType.SYSTEM,
            content="Performance test",
            metadata={"dataset": large_dataset}
        )
        
        json_data = message.model_dump()
        dataset = json_data["metadata"]["dataset"]
        
        assert len(dataset) == 50
        assert dataset[0]["id"] == 0
        assert dataset[49]["id"] == 49
        assert len(dataset[0]["values"]) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])