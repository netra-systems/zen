"""
Real Services Integration Testing Package

This package contains integration tests that use actual service connections
instead of mocks to validate real-world integration scenarios.

Tests in this package require:
- Real LLM API keys (OpenAI/Anthropic)
- Real PostgreSQL database
- Real Redis instance
- Real auth service connection

Environment Variables Required:
- OPENAI_API_KEY: OpenAI API key for LLM testing
- ANTHROPIC_API_KEY: Anthropic Claude API key for LLM testing  
- DATABASE_URL: PostgreSQL connection string
- REDIS_URL: Redis connection string (default: redis://localhost:6379)
- AUTH_SERVICE_URL: Auth service URL (default: http://localhost:8001)

Run with: pytest -m real_services --tb=short -v
"""

__all__ = ["test_multi_agent_real_services"]