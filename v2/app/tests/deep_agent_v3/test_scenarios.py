import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.models_clickhouse import AnalysisRequest

client = TestClient(app)

@pytest.mark.parametrize("scenario_prompt, scenario_name", [
    ("I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.", "cost_reduction_quality_constraint"),
    ("My tools are too slow. I need to reduce the latency by 3x, but I can't spend more money.", "latency_reduction_cost_constraint"),
    ("I'm expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "usage_increase_impact_analysis"),
    ("I need to optimize the 'user_authentication' function. What advanced methods can I use?", "function_optimization"),
    ("I'm considering using the new 'gpt-4o' and 'claude-3-sonnet' models. How effective would they be in my current setup?", "model_effectiveness_analysis"),
    ("I want to audit all uses of KV caching in my system to find optimization opportunities.", "kv_caching_audit"),
    ("I need to reduce costs by 20% and improve latency by 2x. I'm also expecting a 30% increase in usage. What should I do?", "multi_objective_optimization"),
])
def test_deep_agent_v3_scenario(scenario_prompt: str, scenario_name: str):
    run_id = f"test-run-{hash(scenario_prompt)}"
    agent_request = AnalysisRequest(
        user_id="test_user",
        workloads=[{"run_id": run_id, "query": scenario_prompt}],
        query=scenario_prompt
    )
    response = client.post("/api/v3/agent/create", json=agent_request.model_dump())
    assert response.status_code == 202

    import time
    for _ in range(20): # Poll for up to 20 seconds
        response = client.get(f"/api/v3/agent/{run_id}/step")
        assert response.status_code == 200
        if response.json()["status"] == "complete":
            break
        time.sleep(1)
    else:
        pytest.fail("Agent run did not complete in time.")

    final_state = response.json()
    assert final_state["final_report"] is not None
    assert len(final_state["final_report"]) > 0

    response = client.get(f"/api/v3/agent/{run_id}/history")
    assert response.status_code == 200
    history = response.json()
    assert history["is_complete"] is True