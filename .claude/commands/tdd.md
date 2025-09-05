---
allowed-tools: ["Task", "Bash", "Read", "Write", "Edit", "TodoWrite"]
description: "Execute complete TDD workflow with REAL services - NO MOCKS ALLOWED"
argument-hint: "<feature-name> <module-name>"
---

# Test-Driven Development (TDD) with REAL Services

## 🚨 CRITICAL: NO MOCKS ALLOWED - REAL EVERYTHING

Follow TDD strategy for feature **$1** in module **$2** using ONLY real services, APIs, and agents.

**MANDATORY REQUIREMENTS:**
- ✅ Use REAL databases (PostgreSQL, Redis, ClickHouse)
- ✅ Use REAL LLMs (Gemini API, no mocks)
- ✅ Use REAL WebSocket connections
- ✅ Use REAL authentication services
- ❌ NO mock implementations
- ❌ NO stub services
- ❌ NO fake APIs

## Process with Agent Spawning:

### 1. Write Tests First (Red Phase)
Spawn a subagent to write REAL integration tests:
```
Task: Write comprehensive integration tests for $1 in $2
- Create test file: tests/$2/test_$1.py
- Test against REAL services (Docker must be running)
- Cover actual API endpoints, database operations, agent executions
- Add extensive logging: logger.debug() after EVERY operation
- Tests must use real credentials and connections
- Verify with: python tests/unified_test_runner.py --real-services --real-llm
```

**SPAWN REVIEWER:** Review tests for real service integration

### 2. Verify Test Failure
Spawn a subagent to verify tests fail against real system:
```
Task: Run tests and verify they fail correctly
- Start Docker services: docker compose up -d
- Run: python tests/unified_test_runner.py --real-services --real-llm --category $2
- Document actual error messages from real services
- Confirm failures indicate missing real functionality
```

**SPAWN REVIEWER:** Verify failure analysis is accurate

### 3. Commit Tests
Spawn a subagent to commit real integration tests:
```
Task: Commit comprehensive test suite
- Ensure tests connect to real services
- Verify Docker dependencies documented
- Commit message: "test($2): add real integration tests for $1 - NO MOCKS"
```

**SPAWN REVIEWER:** Review test quality and real service usage

### 4. Implement Feature (Green Phase)
Spawn a subagent to implement against real services:
```
Task: Implement $1 to pass real integration tests
- Write code that works with REAL databases
- Implement REAL API endpoints
- Create REAL agent workflows
- Test frequently: python tests/unified_test_runner.py --real-services
- NO changing tests, only implementation
```

**SPAWN REVIEWER:** Verify implementation uses real services correctly

### 5. Verify and Refactor
Spawn a subagent for production-ready refactoring:
```
Task: Refactor while maintaining real service integration
- Test with production-like data volumes
- Verify performance with real database queries
- Check real WebSocket event propagation
- Run: python tests/unified_test_runner.py --real-services --categories smoke unit integration api
```

**SPAWN REVIEWER:** Ensure refactoring maintains real service compatibility

### 6. Final Validation and Commit
```
Task: Final validation with all real services
- Run full test suite with real LLM
- Verify staging environment compatibility
- Commit message: "feat($2): implement $1 with real service integration"
```

## Pre-execution Checklist:

!echo "🔍 Checking Docker services..."
!docker compose ps
!echo "🔍 Checking database connections..."
!docker compose exec -T dev-postgres pg_isready -U netra
!docker compose exec -T dev-redis redis-cli ping
!echo "🔍 Checking API keys..."
!python -c "import os; print('✅ Gemini API' if os.getenv('GEMINI_API_KEY') else '❌ Missing GEMINI_API_KEY')"

## Execution with Real Services:

!python tests/unified_test_runner.py --real-services --real-llm --env development --category ${2:-integration}

## FORBIDDEN PRACTICES:
- ❌ Mock objects (MagicMock, Mock, etc.)
- ❌ Fake database connections
- ❌ Stubbed API responses
- ❌ Simulated WebSocket events
- ❌ Test-only implementations
- ❌ In-memory databases for testing

## REQUIRED PRACTICES:
- ✅ Docker Compose for real services
- ✅ Real PostgreSQL with actual schemas
- ✅ Real Redis with actual data structures
- ✅ Real ClickHouse for analytics
- ✅ Real Gemini API calls
- ✅ Real WebSocket connections
- ✅ Real authentication flows