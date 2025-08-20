"""Core Tests - Split from test_websocket_resilience_integration.py"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Dict, Any
from app.routes.websocket_enhanced import (
from app.websocket.unified.manager import UnifiedWebSocketManager
from app.core.websocket_cors import WebSocketCORSHandler

    def test_cors_handler_edge_case_origins(self):
        """Test CORS handler with edge case origin formats."""
        handler = WebSocketCORSHandler(
            allowed_origins=["https://*.netra.ai"], 
            environment="production"
        )
        
        edge_case_origins = [
            "",  # Empty origin
            " ",  # Whitespace only
            "https://",  # Incomplete URL
            "invalid-url",  # Invalid format
            "https://sub.domain.netra.ai.malicious.com",  # Domain spoofing attempt
            "https://netra.ai:443",  # With default HTTPS port
            "https://NETRA.AI",  # Different case
        ]
        
        # Should handle all edge cases without crashing
        for origin in edge_case_origins:
            result = handler.is_origin_allowed(origin)
            assert isinstance(result, bool)  # Should return boolean, not crash

    def test_error_logging_production_readiness(self):
        """Test that error logging is appropriate for production monitoring."""
        handler = WebSocketCORSHandler(environment="production")
        
        with patch('app.core.websocket_cors.logger') as mock_logger:
            # Generate security violation
            handler.is_origin_allowed("http://malicious.com")
            
            # Should log security violations for monitoring
            mock_logger.warning.assert_called()
            log_call = mock_logger.warning.call_args[0][0]
            assert "security violation" in log_call.lower()

    def test_cors_validation_performance(self):
        """Test CORS validation performance under high load."""
        handler = WebSocketCORSHandler(environment="production")
        
        # Test many different origins
        test_origins = [
            "https://netra.ai",
            "http://malicious.com",
            "https://app.netra.ai",
            "chrome-extension://fake",
            "http://192.168.1.1"
        ] * 200  # 1000 total checks
        
        start_time = time.time()
        
        results = []
        for origin in test_origins:
            result = handler.is_origin_allowed(origin)
            results.append(result)
        
        validation_time = time.time() - start_time
        
        # Should complete validation quickly
        assert validation_time < 2.0  # Less than 2 seconds for 1000 validations
        
        # Should have correct results
        legitimate_count = sum(1 for origin in test_origins if "netra.ai" in origin)
        legitimate_results = sum(1 for i, origin in enumerate(test_origins) 
                               if "netra.ai" in origin and results[i])
        
        assert legitimate_results == legitimate_count

    def test_cors_handler_edge_case_origins(self):
        """Test CORS handler with edge case origin formats."""
        handler = WebSocketCORSHandler(
            allowed_origins=["https://*.netra.ai"], 
            environment="production"
        )
        
        edge_case_origins = [
            "",  # Empty origin
            " ",  # Whitespace only
            "https://",  # Incomplete URL
            "invalid-url",  # Invalid format
            "https://sub.domain.netra.ai.malicious.com",  # Domain spoofing attempt
            "https://netra.ai:443",  # With default HTTPS port
            "https://NETRA.AI",  # Different case
        ]
        
        # Should handle all edge cases without crashing
        for origin in edge_case_origins:
            result = handler.is_origin_allowed(origin)
            assert isinstance(result, bool)  # Should return boolean, not crash
