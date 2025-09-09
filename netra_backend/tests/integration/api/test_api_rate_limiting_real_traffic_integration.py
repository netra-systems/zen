"""
Test API Rate Limiting Real Traffic Integration

Business Value Justification (BVJ):
- Segment: All customer segments (fair usage enforcement)
- Business Goal: Prevent service abuse while ensuring fair access
- Value Impact: Rate limiting protects service quality for all customers
- Strategic Impact: Enables tiered pricing models and prevents resource exhaustion

CRITICAL REQUIREMENTS:
- Tests real rate limiting with actual HTTP traffic
- Validates tier-based limits and throttling mechanisms
- Uses real API endpoints and traffic patterns, NO MOCKS
- Ensures rate limiting accuracy under load
"""

import pytest
import asyncio
import httpx
import time
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

from netra_backend.app.services.rate_limiting.api_rate_limiter import APIRateLimiter


class TestAPIRateLimitingRealTrafficIntegration(SSotBaseTestCase):
    """Test API rate limiting with real HTTP traffic"""
    
    def setup_method(self):
        """Set up test environment"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.test_prefix = f"rate_limit_{uuid.uuid4().hex[:8]}"
        self.rate_limiter = APIRateLimiter()
        self.backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tier_based_rate_limiting_with_real_requests(self):
        """Test tier-based rate limiting with real HTTP requests"""
        # Configure rate limits for different tiers
        rate_configs = {
            "free": {"requests_per_minute": 10, "burst_limit": 5},
            "mid": {"requests_per_minute": 50, "burst_limit": 15},
            "enterprise": {"requests_per_minute": 200, "burst_limit": 50}
        }
        
        await self.rate_limiter.configure_limits(rate_configs, test_prefix=self.test_prefix)
        
        # Test each tier
        for tier, config in rate_configs.items():
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Make requests up to burst limit
                responses = []
                
                for i in range(config["burst_limit"] + 3):  # Exceed burst by 3
                    try:
                        response = await client.get(
                            f"{self.backend_url}/health",
                            headers={"X-User-Tier": tier, "X-Test-ID": self.test_prefix}
                        )
                        responses.append({"status": response.status_code, "headers": dict(response.headers)})
                    except Exception as e:
                        responses.append({"status": 0, "error": str(e)})
                    
                    await asyncio.sleep(0.1)
                
                # Validate rate limiting behavior
                successful_requests = [r for r in responses if r.get("status") == 200]
                rate_limited_requests = [r for r in responses if r.get("status") == 429]
                
                # Should allow requests up to burst limit
                assert len(successful_requests) >= config["burst_limit"]
                
                # Should rate limit excess requests
                if len(responses) > config["burst_limit"]:
                    assert len(rate_limited_requests) > 0, f"No rate limiting for {tier} tier"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])