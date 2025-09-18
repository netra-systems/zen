# Testing Guide for Netra Adaptive Workflow

**System Health Score: 95% (EXCELLENT)** | **Last Updated: 2025-09-14** | **Issue #1116 COMPLETE: SSOT Factory Migration**

## Quick Start

The `test_adaptive_workflow.py` script provides a comprehensive test suite for the adaptive workflow system.

### Prerequisites

1. **Install Dependencies:**
   ```bash
   pip install rich requests pytest
   ```

2. **Ensure Docker is Running:**
   ```bash
   docker --version  # Should show Docker version
   ```

## Running Tests

### Full Test Suite (Recommended)
Runs all tests including services check, authentication, workflow scenarios, and integration tests:
```bash
python test_adaptive_workflow.py
```

### Quick Test
Tests only the workflow scenarios (faster):
```bash
python test_adaptive_workflow.py --quick
```

### Without Authentication
For testing without auth service (development only):
```bash
python test_adaptive_workflow.py --no-auth
```
Note: Requires `AUTH_SERVICE_ENABLED=false` in your environment.

### Integration Tests Only
Run only the pytest integration tests:
```bash
python test_adaptive_workflow.py --integration
```

## Test Scenarios

The test suite validates three adaptive workflow scenarios:

1. **Sufficient Data**: Full optimization workflow with all agents
   - User provides comprehensive metrics (requests, latency, costs)
   - System runs: triage → optimization → data → actions → reporting

2. **Partial Data**: Modified workflow with data collection
   - User provides some information but missing key metrics
   - System adapts by including data_helper agent

3. **Insufficient Data**: Minimal workflow for data gathering
   - User provides minimal information
   - System focuses on understanding needs and collecting data

## Authentication

### Interactive Authentication (NEW!)
The test script now prompts for credentials interactively:

1. **Run the test:**
   ```bash
   python test_adaptive_workflow.py
   ```

2. **When prompted:**
   - Press Enter to use default test account (test@netrasystems.ai)
   - Or enter your own email and password
   - If the account doesn't exist, you'll be offered to create it

3. **Non-interactive mode:**
   ```bash
   python test_adaptive_workflow.py --non-interactive
   ```
   Uses default credentials without prompting.

### Default Test Credentials
- **Email**: test@netrasystems.ai
- **Password**: TestPassword123!

### Authentication Flow
The test script:
1. Prompts for credentials (or uses defaults)
2. Attempts to login
3. If login fails, offers to create the account
4. After account creation, automatically logs in
5. Uses the token for all API requests

### Disabling Authentication
For quick local testing without auth:
```bash
export AUTH_SERVICE_ENABLED=false
python test_adaptive_workflow.py --no-auth
```

## Troubleshooting

### Services Not Running
The test script automatically starts required services. If issues persist:
```bash
# Manually start services
docker-compose up -d backend auth postgres redis clickhouse

# Check service status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs auth
```

### Authentication Failures
1. Ensure auth service is running: `docker-compose ps auth`
2. Check auth service logs: `docker-compose logs auth`
3. Try recreating test user: Script auto-creates if missing
4. Or disable auth: `export AUTH_SERVICE_ENABLED=false`

### Test Failures
1. Check service health: `docker-compose ps`
2. Review logs: `docker-compose logs backend --tail=50`
3. Run integration tests directly: `pytest netra_backend/tests/integration/test_adaptive_workflow.py -v`

## Manual API Testing

### With Authentication
```python
import requests

# Login
response = requests.post(
    "http://localhost:8081/auth/login",
    json={"email": "test@netrasystems.ai", "password": "TestPassword123!"}
)
token = response.json()["access_token"]

# Create thread
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/api/threads",
    json={"user_prompt": "Help me optimize my AI workload"},
    headers=headers
)
print(response.json())
```

### Without Authentication (Dev Only)
```bash
export AUTH_SERVICE_ENABLED=false
curl -X POST http://localhost:8000/api/threads \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "Help me optimize my AI workload"}'
```

## Understanding Results

A successful test run shows:
- ✅ All required services running
- ✅ Authentication successful
- ✅ Thread creation for each scenario
- ✅ Integration tests passing

The adaptive workflow ensures users get optimal recommendations based on available data, gracefully handling missing information through intelligent agent orchestration.