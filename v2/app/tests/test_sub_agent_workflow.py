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
    
    with client.websocket_connect("/ws/test_run") as websocket:
        websocket.send_json({"type": "start_agent", "payload": analysis_request.model_dump()})
        response = websocket.receive_json()
        assert response["event"] == "agent_started"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_started"
        assert response["data"]["agent"] == "TriageSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_finished"
        assert response["data"]["agent"] == "TriageSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_started"
        assert response["data"]["agent"] == "DataSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_finished"
        assert response["data"]["agent"] == "DataSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_started"
        assert response["data"]["agent"] == "OptimizationsCoreSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_finished"
        assert response["data"]["agent"] == "OptimizationsCoreSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_started"
        assert response["data"]["agent"] == "ActionsToMeetGoalsSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_finished"
        assert response["data"]["agent"] == "ActionsToMeetGoalsSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_started"
        assert response["data"]["agent"] == "ReportingSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_step_finished"
        assert response["data"]["agent"] == "ReportingSubAgent"

        response = websocket.receive_json()
        assert response["event"] == "agent_finished"