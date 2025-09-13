"""Test Helpers for Example Message Tests



Common utilities and fixtures for example message testing.

Reduces code duplication across test files.



Business Value: Improves test maintainability and consistency

"""



from datetime import datetime, timezone

from typing import Any, Dict

from uuid import uuid4





def create_example_message_request(

    content: str,

    category: str = "cost-optimization",

    complexity: str = "basic",

    user_id: str = None,

    business_value: str = "conversion"

) -> Dict[str, Any]:

    """Create standard example message request"""

    if user_id is None:

        user_id = f"test_user_{uuid4()}"

    

    return {

        "content": content,

        "example_message_id": str(uuid4()),

        "example_message_metadata": {

            "title": "Test Message",

            "category": category,

            "complexity": complexity,

            "businessValue": business_value,

            "estimatedTime": "2 minutes"

        },

        "user_id": user_id,

        "timestamp": int(datetime.now(timezone.utc).timestamp())

    }





def create_thread_data(user_id: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:

    """Create standard thread data for testing"""

    base_metadata = {"user_id": user_id, "type": "example_message"}

    if metadata:

        base_metadata.update(metadata)

    

    return {

        "id": str(uuid4()),

        "created_at": int(datetime.now(timezone.utc).timestamp()),

        "metadata_": base_metadata

    }





def create_message_data(

    thread_id: str,

    content: str,

    role: str = "user",

    metadata: Dict[str, Any] = None

) -> Dict[str, Any]:

    """Create standard message data for testing"""

    return {

        "id": str(uuid4()),

        "thread_id": thread_id,

        "role": role,

        "content": [{"type": "text", "text": content}],

        "created_at": int(datetime.now(timezone.utc).timestamp()),

        "metadata_": metadata or {}

    }





def assert_valid_response(response):

    """Assert response has valid structure"""

    assert response is not None

    assert hasattr(response, "status")

    assert hasattr(response, "message_id")

    assert response.status in ["completed", "error"]





def assert_completed_response(response):

    """Assert response completed successfully"""

    assert_valid_response(response)

    assert response.status == "completed"

    assert response.processing_time_ms is not None

    assert response.processing_time_ms > 0





def assert_error_response(response):

    """Assert response indicates error"""

    assert_valid_response(response)

    assert response.status == "error"

    assert response.error is not None





# Common test prompts for reuse

BASIC_COST_OPTIMIZATION = "I need to reduce costs while maintaining quality"

LATENCY_OPTIMIZATION = "My tools are too slow, need 3x improvement"

SCALING_ANALYSIS = "50% usage increase impact on costs and limits"

MODEL_SELECTION = "Evaluate gpt-4o and claude-3-sonnet effectiveness"

