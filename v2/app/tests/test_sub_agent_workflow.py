
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import AnalysisRequest, RequestModel, Settings, Workload, DataSource, TimeRange

@pytest.mark.asyncio
async def test_sub_agent_workflow():
    client = TestClient(app)
    
    analysis_request = AnalysisRequest(
        settings=Settings(debug_mode=True),
        request=RequestModel(
            id="test_run",
            user_id="test_user",
            query="Analyze my data and suggest optimizations.",
            workloads=[
                {
                    "run_id": "test_run",
                    "query": "Sample workload query",
                    "data_source": {"source_table": "my_table"},
                    "time_range": {"start_time": "2025-01-01T00:00:00Z", "end_time": "2025-01-02T00:00:00Z"}
                }
            ]
        )
    )
    
    response = client.post("/api/v3/agent/chat/start_agent", json=analysis_request.model_dump())
    
    assert response.status_code == 200
    
    response_json = response.json()
    agent_names = list(response_json.keys())
    last_agent_name = agent_names[-1]
    last_agent_state = response_json[last_agent_name]

    assert last_agent_state["run_id"] == "test_run"
    assert last_agent_state["current_agent"] == "ReportingSubAgent"
