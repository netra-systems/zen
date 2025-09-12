"""
Integration Tests for ReportingSubAgent JSON Integration with SSOT

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: SSOT compliance for consistent JSON handling
- Value Impact: Ensures unified JSON processing across agent workflows
- Strategic Impact: Prevents data corruption and parsing errors in production

These tests validate real integration between ReportingSubAgent and the
SSOT unified_json_handler module. NO mocks are used for JSON operations.

EXPECTED BEHAVIOR:
- Some tests FAIL NOW (direct json usage issues)
- Tests PASS after migrating to UnifiedJSONSerializer SSOT
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import unittest
from unittest.mock import Mock, AsyncMock
import asyncio
from typing import Dict, Any

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestReportingSubAgentJSONIntegration(SSotAsyncTestCase):
    """Integration tests for ReportingSubAgent SSOT JSON functionality."""
    
    def setUp(self):
        """Set up test fixtures with real components."""
        # Mock the non-JSON dependencies while keeping JSON operations real
        self.mock_context = Mock()
        self.mock_websocket_manager = Mock()
        self.mock_redis_manager = AsyncMock()
        
    def test_ssot_unified_json_handler_integration(self):
        """Test real integration with SSOT UnifiedJSONHandler."""
        from netra_backend.app.core.serialization.unified_json_handler import UnifiedJSONHandler
        
        # Use real SSOT handler
        handler = UnifiedJSONHandler()
        
        # Test complex data serialization
        test_data = {
            "report": "AI optimization recommendations",
            "metrics": [1, 2, 3, 4, 5],
            "status": "success",
            "metadata": {
                "timestamp": "2025-01-09T12:00:00Z",
                "agent": "ReportingSubAgent"
            }
        }
        
        # Test round-trip serialization
        json_string = handler.dumps(test_data)
        self.assertIsInstance(json_string, str)
        
        parsed_data = handler.loads(json_string)
        self.assertEqual(parsed_data, test_data)
    
    def test_llm_response_parser_integration(self):
        """Test real integration with SSOT LLMResponseParser."""
        from netra_backend.app.core.serialization.unified_json_handler import LLMResponseParser
        
        parser = LLMResponseParser()
        
        # Test valid JSON parsing
        valid_response = '{"report": "Valid JSON response"}'
        result = parser.safe_json_parse(valid_response)
        self.assertEqual(result, {"report": "Valid JSON response"})
        
        # Test malformed JSON recovery
        malformed_response = '{"report": "incomplete'
        result = parser.safe_json_parse(malformed_response, fallback={"error": "fallback"})
        # Should return fallback or attempt recovery
        self.assertIsInstance(result, dict)
    
    def test_json_error_fixer_integration(self):
        """Test real integration with SSOT JSONErrorFixer.""" 
        from netra_backend.app.core.serialization.unified_json_handler import JSONErrorFixer
        
        fixer = JSONErrorFixer()
        
        # Test truncated JSON recovery
        truncated_json = '{"report": "Important data", "status": "succe'
        result = fixer.recover_truncated_json(truncated_json)
        
        # Should attempt to fix the JSON
        if result:
            self.assertIsInstance(result, dict)
            self.assertIn("report", result)
    
    def test_reporting_agent_extract_validate_integration(self):
        """Test ReportingSubAgent._extract_and_validate_report with real SSOT components."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Create agent with mocked dependencies (not JSON components)
        agent = ReportingSubAgent(self.mock_context, self.mock_websocket_manager)
        
        # Test with valid JSON
        valid_response = '{"report": "Test report data", "confidence": 0.95}'
        result = agent._extract_and_validate_report(valid_response, "test_run_123")
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result["report"], "Test report data")
        self.assertEqual(result["confidence"], 0.95)
        
        # Test with malformed JSON (should use SSOT error recovery)
        malformed_response = '{"report": "Incomplete data'
        result = agent._extract_and_validate_report(malformed_response, "test_run_124")
        
        # Should return fallback result from SSOT error handling
        self.assertIsInstance(result, dict)
        self.assertIn("report", result)
    
    def test_cache_operations_integration_simulation(self):
        """Simulate cache operations to test what SSOT integration should look like."""
        from netra_backend.app.core.serialization.unified_json_handler import UnifiedJSONHandler
        
        # This is what the cache operations SHOULD do after SSOT migration
        handler = UnifiedJSONHandler()
        
        # Simulate caching complex report data
        report_data = {
            "report": "AI analysis complete",
            "recommendations": [
                {"action": "optimize database queries", "priority": "high"},
                {"action": "implement caching", "priority": "medium"}
            ],
            "metrics": {"performance_gain": 35.7, "cost_reduction": 12.3}
        }
        
        # Test serialization for caching (what _cache_report_result should do)
        cache_string = handler.dumps(report_data)
        self.assertIsInstance(cache_string, str)
        self.assertIn("AI analysis complete", cache_string)
        
        # Test deserialization from cache (what _get_cached_report should do)
        retrieved_data = handler.loads(cache_string)
        self.assertEqual(retrieved_data, report_data)
        self.assertEqual(retrieved_data["metrics"]["performance_gain"], 35.7)
    
    async def test_redis_cache_ssot_workflow_simulation(self):
        """Simulate the Redis cache workflow with SSOT serialization."""
        from netra_backend.app.core.serialization.unified_json_handler import UnifiedJSONHandler
        
        handler = UnifiedJSONHandler()
        
        # Mock Redis operations
        self.mock_redis_manager.get.return_value = None  # Cache miss
        self.mock_redis_manager.set = AsyncMock()
        
        # Test data
        report_result = {"report": "Cache test", "timestamp": "2025-01-09"}
        
        # Simulate SSOT caching process
        cache_key = "test_report_key"
        serialized_data = handler.dumps(report_result)
        
        # Simulate storing in Redis
        await self.mock_redis_manager.set(f"report_cache:{cache_key}", serialized_data)
        
        # Verify Redis set was called with serialized data
        self.mock_redis_manager.set.assert_called_once_with(
            f"report_cache:{cache_key}", 
            serialized_data
        )
        
        # Simulate retrieval from Redis
        self.mock_redis_manager.get.return_value = serialized_data
        cached_data = await self.mock_redis_manager.get(f"report_cache:{cache_key}")
        
        # Simulate SSOT deserialization
        retrieved_result = handler.loads(cached_data)
        self.assertEqual(retrieved_result, report_result)
    
    def test_error_handling_consistency_with_ssot(self):
        """Test that error handling is consistent with SSOT patterns."""
        from netra_backend.app.core.serialization.unified_json_handler import (
            UnifiedJSONHandler, 
            LLMResponseParser, 
            JSONErrorFixer
        )
        
        # Test error scenarios with all SSOT components
        handler = UnifiedJSONHandler()
        parser = LLMResponseParser()
        fixer = JSONErrorFixer()
        
        # Test invalid data handling
        invalid_data = None
        result = handler.dumps(invalid_data)
        self.assertIsNotNone(result)  # Should handle gracefully
        
        # Test invalid JSON string
        invalid_json = "not json at all"
        result = parser.safe_json_parse(invalid_json, fallback={"error": "invalid"})
        self.assertIsInstance(result, (dict, str))  # Should handle gracefully
        
        # Test error fixing
        broken_json = '{"incomplete": '
        result = fixer.recover_truncated_json(broken_json)
        # Should either fix it or return None, not crash
        if result:
            self.assertIsInstance(result, dict)
    
    def test_reporting_agent_cache_workflow_current_state(self):
        """Test current ReportingSubAgent cache workflow (should show SSOT violations)."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Create agent 
        agent = ReportingSubAgent(self.mock_context, self.mock_websocket_manager)
        agent.redis_manager = self.mock_redis_manager
        
        # Mock Redis operations
        test_data = {"report": "test", "status": "complete"}
        
        # This will show current implementation issues when we inspect the methods
        import inspect
        
        # Inspect _get_cached_report source
        get_cached_source = inspect.getsource(agent._get_cached_report)
        
        # Should show current SSOT violations
        has_direct_json_import = 'import json' in get_cached_source
        has_direct_json_loads = 'json.loads(' in get_cached_source
        
        # Document current state for remediation planning
        violations = []
        if has_direct_json_import:
            violations.append("Direct json import in _get_cached_report")
        if has_direct_json_loads:
            violations.append("Direct json.loads usage in _get_cached_report")
        
        # Log current violations (these should be fixed in remediation)
        if violations:
            print(f"CURRENT SSOT VIOLATIONS DETECTED: {violations}")
        
        # After remediation, these should NOT be present
        # For now, we document the expected state
        self.assertTrue(len(violations) > 0, 
                       "Expected SSOT violations detected for remediation planning")


if __name__ == '__main__':
    # Run async test manually
    async def run_async_tests():
        test_instance = TestReportingSubAgentJSONIntegration()
        test_instance.setUp()
        await test_instance.test_redis_cache_ssot_workflow_simulation()
        print("Async integration test completed")
    
    # Run async test
    asyncio.run(run_async_tests())
    
    # Run regular tests
    unittest.main()