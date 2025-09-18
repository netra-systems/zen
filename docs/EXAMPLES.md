# ZEN Examples

Common use cases and configuration examples for ZEN.

## Code Review Workflow

Run multiple code review tasks in parallel:

```json
{
  "instances": [
    {
      "name": "security-review",
      "command": "/security-audit",
      "description": "Security vulnerability scan"
    },
    {
      "name": "performance-review",
      "command": "/performance-audit",
      "description": "Performance optimization analysis"
    },
    {
      "name": "code-quality",
      "command": "/code-quality-check",
      "description": "Code quality and style review"
    }
  ]
}
```

```bash
python zen_orchestrator.py --config code_review.json --overall-token-budget 75000
```

## Documentation Generation

Generate multiple documentation types:

```json
{
  "instances": [
    {
      "name": "api-docs",
      "command": "/generate-api-docs",
      "description": "Generate API documentation"
    },
    {
      "name": "user-guide",
      "command": "/generate-user-guide",
      "description": "Create user documentation"
    },
    {
      "name": "dev-guide",
      "command": "/generate-dev-guide",
      "description": "Developer setup guide"
    }
  ]
}
```

## Testing Suite

Run comprehensive testing in parallel:

```json
{
  "instances": [
    {
      "name": "unit-tests",
      "command": "/run-unit-tests",
      "description": "Execute unit test suite"
    },
    {
      "name": "integration-tests",
      "command": "/run-integration-tests",
      "description": "Run integration tests"
    },
    {
      "name": "e2e-tests",
      "command": "/run-e2e-tests",
      "description": "End-to-end testing"
    }
  ]
}
```

## Development Workflow

Complete development tasks:

```json
{
  "instances": [
    {
      "name": "feature-impl",
      "command": "/implement-feature --feature=user-auth",
      "description": "Implement user authentication"
    },
    {
      "name": "test-coverage",
      "command": "/improve-test-coverage",
      "description": "Enhance test coverage"
    },
    {
      "name": "refactor-db",
      "command": "/refactor-database-layer",
      "description": "Optimize database layer"
    }
  ]
}
```

With command-specific budgets:
```bash
python zen_orchestrator.py \
  --config development.json \
  --command-budget "/implement-feature=40000,/improve-test-coverage=20000,/refactor-database-layer=30000"
```

## Monitoring Example

ZEN provides real-time monitoring:

```
╔═══ STATUS REPORT [14:25:10] ═══╗
║ Total: 3 instances
║ Running: 2, Completed: 1, Failed: 0, Pending: 0
║ Tokens: 45.2K total, 12.3K cached | Tools: 23
║ 💰 Cost: $0.0912 total | Pricing: Claude compliant
║
║ TOKEN BUDGET STATUS |
║ Overall: [████████████--------] 60% 45.2K/75.0K
║
║  Status   Name           Duration   Tokens   Tools
║  ──────── ────────────── ────────── ──────── ──────
║  ✅        security       2m15s      18.5K    8
║  🏃        performance    1m42s      15.2K    7
║  🏃        code-quality   1m18s      11.5K    8
╚════════════════════════════════╝
```