
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# --- Test Scenarios ---

@pytest.mark.parametrize("scenario_prompt", [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
    "My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.",
    "I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?",
    "I need to optimize the 'user_authentication' function. What advanced methods can I use?",
    "I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?",
    "I want to audit all uses of KV caching in my system to find optimization opportunities.",
    "I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?",
])
def test_deep_agent_scenario(scenario_prompt: str):
    # Step 1: Generate synthetic data
    data_gen_params = {
        "num_traces": 100,
        "num_users": 10,
        "error_rate": 0.1,
        "event_types": ["search", "login"],
        "source_table": "default.content_corpus",
        "destination_table": "default.synthetic_data",
    }
    response = client.post("/api/v3/generation/synthetic_data", json=data_gen_params)
    assert response.status_code == 202

    # Step 2: Create and start the agent run
    run_id = f"test-run-{hash(scenario_prompt)}"
    agent_request = {
        "run_id": run_id,
        "query": scenario_prompt,
        "data_source": {
            "source_table": "default.synthetic_data",
            "filters": {},
        },
        "time_range": {
            "start_time": "2025-08-03T00:00:00Z",
            "end_time": "2025-08-04T00:00:00Z",
        },
    }
    response = client.post("/api/v3/agent/create", json=agent_request)
    assert response.status_code == 202

    # Step 3: Poll for completion
    import time
    for _ in range(20): # Poll for up to 20 seconds
        response = client.get(f"/api/v3/agent/{run_id}/step")
        assert response.status_code == 200
        if response.json()["status"] == "complete":
            break
        time.sleep(1)
    else:
        pytest.fail("Agent run did not complete in time.")

    # Step 4: Verify the final report
    final_state = response.json()
    assert final_state["final_report"] is not None
    assert len(final_state["final_report"]) > 0

    # Step 5: Verify the history
    response = client.get(f"/api/v3/agent/{run_id}/history")
    assert response.status_code == 200
    history = response.json()
    assert history["is_complete"] is True
    assert "raw_logs" in history["history"]
    assert "patterns" in history["history"]
    assert "policies" in history["history"]
