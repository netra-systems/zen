import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.db.models_clickhouse import AnalysisRequest, Settings, RequestModel, Workload, DataSource, TimeRange
from app.llm.llm_manager import LLMManager
from app.config import settings

# Initialize the LLMManager and add it to the app state for testing
llm_manager = LLMManager(settings)
app.state.llm_manager = llm_manager

client = TestClient(app)

@pytest.mark.parametrize("prompt", [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?"
])
def test_apex_optimizer_agent(prompt: str):
    analysis_request = AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(
            user_id="test_user",
            query=prompt,
            workloads=[
                Workload(
                    run_id="test_run",
                    query=prompt,
                    data_source=DataSource(source_table="test_table"),
                    time_range=TimeRange(start_time="2025-01-01T00:00:00Z", end_time="2025-01-02T00:00:00Z")
                )
            ]
        )
    )
    response = client.post("/api/v3/apex/chat/start_agent", json=analysis_request.dict())
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert isinstance(run_id, str)

    with client.websocket_connect(f"/ws/{run_id}") as websocket:
        try:
            time.sleep(35) # Allow even more time for the websocket to connect and receive the message
            data = websocket.receive_text()
            assert isinstance(data, str)
        finally:
            websocket.close()