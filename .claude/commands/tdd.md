---
allowed-tools: ["Task", "Bash", "Read", "Write", "Edit", "TodoWrite"]
description: "Execute complete TDD workflow with GCP staging environment - NO MOCKS ALLOWED"
argument-hint: "<feature-name> <module-name>"
---

# Test-Driven Development (TDD) with GCP Staging Services

## 🚨 CRITICAL: NO MOCKS ALLOWED - REAL GCP SERVICES ONLY

Follow TDD strategy for feature **$1** in module **$2** using ONLY real GCP staging services, APIs, and agents.

**MANDATORY REQUIREMENTS:**
- ✅ Use REAL GCP Cloud SQL (PostgreSQL)
- ✅ Use REAL GCP Memorystore (Redis)
- ✅ Use REAL ClickHouse Cloud
- ✅ Use REAL LLMs (Gemini API, no mocks)
- ✅ Use REAL WebSocket connections via Cloud Run
- ✅ Use REAL authentication services on staging.netrasystems.ai
- ❌ NO mock implementations
- ❌ NO stub services
- ❌ NO fake APIs
- ❌ NO Docker local services

## Process with Agent Spawning:

### 1. Write Tests First (Red Phase)
Spawn a subagent to write REAL integration tests:
```
Task: Write comprehensive integration tests for $1 in $2
- Create test file: tests/$2/test_$1.py
- Test against REAL GCP staging services (staging.netrasystems.ai)
- Cover actual API endpoints, Cloud SQL operations, agent executions
- Add extensive logging: logger.debug() after EVERY operation
- Tests must use real staging credentials and connections
- Verify with: python tests/unified_test_runner.py --env staging --real-services --real-llm
```

**SPAWN REVIEWER:** Review tests for real GCP staging service integration

### 2. Verify Test Failure
Spawn a subagent to verify tests fail against real staging system:
```
Task: Run tests and verify they fail correctly
- Validate GCP staging services are healthy
- Run: python tests/unified_test_runner.py --env staging --real-services --real-llm --category $2
- Document actual error messages from real GCP staging services
- Confirm failures indicate missing real functionality
```

**SPAWN REVIEWER:** Verify failure analysis is accurate

### 3. Commit Tests
Spawn a subagent to commit real integration tests:
```
Task: Commit comprehensive test suite
- Ensure tests connect to real GCP staging services
- Verify staging environment dependencies documented
- Commit message: "test($2): add real GCP staging integration tests for $1 - NO MOCKS"
```

**SPAWN REVIEWER:** Review test quality and real GCP staging service usage

### 4. Implement Feature (Green Phase)
Spawn a subagent to implement against real staging services:
```
Task: Implement $1 to pass real GCP staging integration tests
- Write code that works with REAL Cloud SQL databases
- Implement REAL API endpoints on staging.netrasystems.ai
- Create REAL agent workflows with staging WebSocket
- Test frequently: python tests/unified_test_runner.py --env staging --real-services
- NO changing tests, only implementation
```

**SPAWN REVIEWER:** Verify implementation uses real GCP staging services correctly

### 5. Verify and Refactor
Spawn a subagent for production-ready refactoring:
```
Task: Refactor while maintaining real GCP staging service integration
- Test with production-like data volumes on Cloud SQL
- Verify performance with real Cloud SQL queries
- Check real WebSocket event propagation via Cloud Run
- Run: python tests/unified_test_runner.py --env staging --real-services --categories smoke unit integration api
```

**SPAWN REVIEWER:** Ensure refactoring maintains real GCP staging service compatibility

### 6. Final Validation and Commit
```
Task: Final validation with all real GCP staging services
- Run full test suite with real LLM on staging
- Verify staging environment compatibility with production patterns
- Commit message: "feat($2): implement $1 with real GCP staging service integration"
```

## Pre-execution Checklist:

!echo "🔍 Checking GCP staging services..."
!curl -s --fail -H "X-Staging-Test: true" https://staging.netrasystems.ai/health && echo "✅ Backend staging health OK" || echo "❌ Backend staging health FAILED"
!curl -s --fail -H "X-Staging-Test: true" https://staging.netrasystems.ai/auth/health && echo "✅ Auth staging health OK" || echo "❌ Auth staging health FAILED"
!echo "🔍 Checking WebSocket endpoint..."
!curl -s --fail -H "X-Staging-Test: true" https://api-staging.netrasystems.ai/health && echo "✅ WebSocket staging health OK" || echo "❌ WebSocket staging health FAILED"
!echo "🔍 Checking API keys for staging..."
!python -c "import os; print('✅ Gemini API' if os.getenv('GEMINI_API_KEY') else '❌ Missing GEMINI_API_KEY')"
!echo "🔍 Validating staging configuration..."
!python -c "from tests.e2e.staging.staging_test_config import validate_staging_coordination; result = validate_staging_coordination(); print('✅ All staging services ready' if all(result.values()) else f'❌ Staging issues: {[k for k,v in result.items() if not v]}')"

## Execution with Real GCP Staging Services:

!python tests/unified_test_runner.py --env staging --real-services --real-llm --category ${2:-integration}

## FORBIDDEN PRACTICES:
- ❌ Mock objects (MagicMock, Mock, etc.)
- ❌ Fake database connections
- ❌ Stubbed API responses
- ❌ Simulated WebSocket events
- ❌ Test-only implementations
- ❌ In-memory databases for testing
- ❌ Docker local services (use GCP staging instead)
- ❌ Local PostgreSQL (use Cloud SQL instead)

## REQUIRED PRACTICES:
- ✅ GCP Cloud Run services on staging.netrasystems.ai
- ✅ Real Cloud SQL (PostgreSQL) with actual schemas
- ✅ Real GCP Memorystore (Redis) with actual data structures
- ✅ Real ClickHouse Cloud for analytics
- ✅ Real Gemini API calls
- ✅ Real WebSocket connections via Cloud Run
- ✅ Real authentication flows via staging environment
- ✅ Environment-specific configuration through staging config