@echo off
echo Running E2E Agent Tests on GCP Staging Environment
echo =================================================

cd /d "C:\GitHub\netra-apex"

set ENVIRONMENT=staging
set NO_DOCKER=1

echo Testing 1: Staging Agent Execution
echo ----------------------------------
python tests\staging\test_staging_agent_execution.py

echo.
echo Testing 2: Staging WebSocket Agent Events
echo ------------------------------------------
python tests\staging\test_staging_websocket_agent_events.py

echo.
echo Testing 3: E2E Agent WebSocket Events Comprehensive
echo --------------------------------------------------
python tests\e2e\test_agent_websocket_events_comprehensive.py

echo.
echo Testing 4: E2E Agent Orchestration Real LLM
echo ------------------------------------------
python tests\e2e\integration\test_agent_orchestration_real_llm.py

echo.
echo All tests completed!
pause