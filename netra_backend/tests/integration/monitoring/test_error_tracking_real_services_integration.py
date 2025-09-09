"""
Test Error Tracking Real Services Integration

CRITICAL REQUIREMENTS:
- Tests real error tracking and alerting systems
- Validates error aggregation, classification, notification
- Uses real error tracking services, NO MOCKS
"""

import pytest
import asyncio
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env

from netra_backend.app.services.monitoring.error_tracker import ErrorTracker


class TestErrorTrackingRealServicesIntegration(SSotBaseTestCase):
    """Test error tracking with real services"""
    
    def setup_method(self):
        """Set up test environment"""
        super().setup_method() if hasattr(super(), 'setup_method') else None
        self.env = get_env()
        self.test_prefix = f"error_{uuid.uuid4().hex[:8]}"
        self.error_tracker = ErrorTracker()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_capture_and_aggregation(self):
        """Test error capture and aggregation"""
        # Generate test errors
        test_errors = [
            {"type": "ValueError", "message": "Invalid input", "severity": "medium"},
            {"type": "ConnectionError", "message": "Database timeout", "severity": "high"},
            {"type": "ValidationError", "message": "Missing field", "severity": "low"}
        ]
        
        for error in test_errors:
            await self.error_tracker.capture_error(
                error_type=error["type"],
                message=error["message"],
                severity=error["severity"],
                test_prefix=self.test_prefix
            )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Verify error aggregation
        error_stats = await self.error_tracker.get_error_statistics(self.test_prefix)
        assert error_stats.total_errors >= len(test_errors)
        assert error_stats.error_types_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])