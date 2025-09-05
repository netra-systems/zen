---
allowed-tools: ["Bash"]
description: "Run tests with real services and LLM"
argument-hint: "[category]"
---

# 🧪 Real Service Testing

Execute tests against real databases, APIs, and LLMs - **NO MOCKS ALLOWED**.

## Test Configuration
- **Category:** ${1:-integration}
- **Services:** Real PostgreSQL, Redis, ClickHouse
- **LLM:** Real Gemini API
- **Mode:** Production-like testing

## Execution Steps

### 1. Ensure Docker Services Running
!echo "⚠️  Ensuring Docker services are running..."
!docker compose up -d

### 2. Execute Tests with Real Services
!echo "🧪 Running tests with real services..."
!python tests/unified_test_runner.py --real-services --real-llm --category ${1:-integration}

## Available Categories
- `unit` - Unit tests with real dependencies
- `integration` - Service integration tests
- `e2e` - End-to-end user flows
- `smoke` - Quick validation tests
- `api` - API endpoint tests

## Usage Examples
- `/test-real` - Run integration tests (default)
- `/test-real e2e` - Run end-to-end tests
- `/test-real smoke` - Quick smoke tests