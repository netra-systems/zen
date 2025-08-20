"""Performance Tests - Split from test_websocket_resilience_integration.py"""

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
