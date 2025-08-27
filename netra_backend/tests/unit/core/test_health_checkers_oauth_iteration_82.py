"""OAuth Health Checker Tests - Iteration 82"""
import pytest
from netra_backend.app.core.health_checkers import HealthChecker

class TestOAuthHealthCheckersIteration82:
    @pytest.fixture
    def health_checker(self):
        return HealthChecker()

    @pytest.mark.asyncio
    async def test_oauth_provider_response_format_iteration_82(self, health_checker):
        """Test OAuth provider response format - Iteration 82."""
        result = await health_checker.check_oauth_providers()
        assert isinstance(result, dict)
        assert "healthy" in result
        assert "latency_ms" in result
        assert isinstance(result["healthy"], bool)
        assert isinstance(result["latency_ms"], (int, float))
        assert result["latency_ms"] >= 0
