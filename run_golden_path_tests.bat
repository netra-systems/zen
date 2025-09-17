@echo off
cd /c/netra-apex

echo ===== Running Agent Golden Path Tests =====
python -m pytest tests/integration/agent_golden_path/ -v --tb=short -x

echo.
echo ===== Running Issue 1142 Test =====
python -m pytest tests/integration/agents/test_issue_1142_golden_path_startup_contamination.py -v --tb=short -x

echo.
echo ===== Running Config SSOT Golden Path Protection Test =====
python -m pytest tests/integration/config_ssot/test_config_golden_path_protection.py -v --tb=short -x

echo.
echo ===== Running Golden Path Auth Failure Reproduction Test =====
python -m pytest tests/integration/config_ssot/test_golden_path_auth_failure_reproduction.py -v --tb=short -x

echo.
echo ===== All Golden Path Tests Complete =====