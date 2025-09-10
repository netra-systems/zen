"""
Unit Tests for ReportingSubAgent SSOT JSON Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: SSOT compliance for consistent JSON handling
- Value Impact: Prevents JSON parsing inconsistencies in agent workflows
- Strategic Impact: Unified error handling and serialization across platform

These tests validate the SSOT JSON handling integration in ReportingSubAgent.
Tests use mocks for isolated unit testing.

EXPECTED BEHAVIOR:
- Tests FAIL NOW (methods use direct json.loads/dumps)
- Tests PASS after migrating to UnifiedJSONSerializer
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import Dict, Any

# Add project root to path for imports
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TestReportingSubAgentSSOTJSON(unittest.TestCase):
    """Unit tests for ReportingSubAgent SSOT JSON integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the dependencies to isolate JSON testing
        self.mock_context = Mock()
        self.mock_websocket_manager = Mock()
        self.mock_redis_manager = Mock()
        
    @patch('netra_backend.app.agents.reporting_sub_agent.LLMResponseParser')
    @patch('netra_backend.app.agents.reporting_sub_agent.JSONErrorFixer')
    def test_extract_and_validate_report_uses_ssot_parser(self, mock_json_fixer, mock_llm_parser):
        """Test that _extract_and_validate_report uses SSOT LLMResponseParser."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Create agent instance
        agent = ReportingSubAgent(self.mock_context, self.mock_websocket_manager)
        
        # Mock the SSOT parser behavior
        mock_parser_instance = Mock()
        mock_llm_parser.return_value = mock_parser_instance
        mock_parser_instance.safe_json_parse.return_value = {"report": "test report"}
        
        # Test LLM response parsing
        test_response = '{"report": "test report"}'
        result = agent._extract_and_validate_report(test_response, "test_run_id")
        
        # Verify SSOT parser was used
        mock_llm_parser.assert_called_once()
        mock_parser_instance.safe_json_parse.assert_called_once_with(test_response)
        self.assertEqual(result, {"report": "test report"})
    
    @patch('netra_backend.app.agents.reporting_sub_agent.json.loads')
    def test_get_cached_report_should_use_ssot_serializer(self, mock_json_loads):
        """CRITICAL: Test that _get_cached_report should NOT use direct json.loads.
        
        EXPECTED: FAIL NOW - uses json.loads directly
        EXPECTED: PASS AFTER - uses UnifiedJSONSerializer.safe_loads
        """
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Create agent instance
        agent = ReportingSubAgent(self.mock_context, self.mock_websocket_manager)
        agent.redis_manager = self.mock_redis_manager
        
        # Mock Redis returning cached data
        cached_data = '{"report": "cached report"}'
        self.mock_redis_manager.get = Mock(return_value=cached_data)
        
        # Mock json.loads to track if it's called (SHOULD NOT BE)
        mock_json_loads.return_value = {"report": "cached report"}
        
        # This will fail because the method currently uses json.loads
        import asyncio
        result = asyncio.run(agent._get_cached_report("test_key"))
        
        # THIS ASSERTION WILL FAIL - proving SSOT violation
        mock_json_loads.assert_not_called()  # Should NOT call json.loads
        
    def test_get_cached_report_should_import_ssot_serializer(self):
        """Test that _get_cached_report method should import UnifiedJSONSerializer."""
        import inspect
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Get source code of the method
        method_source = inspect.getsource(ReportingSubAgent._get_cached_report)
        
        # Check for SSOT import usage (should be present after remediation)
        self.assertNotIn('import json', method_source, 
                        "SSOT VIOLATION: _get_cached_report should not import json directly")
        
        # After remediation, should import SSOT serializer
        # This will fail NOW but pass after remediation
        self.assertIn('UnifiedJSONSerializer', method_source,
                     "Missing SSOT import: Should use UnifiedJSONSerializer.safe_loads()")
    
    @patch('netra_backend.app.agents.reporting_sub_agent.json.dumps')  
    def test_cache_report_result_should_use_ssot_serializer(self, mock_json_dumps):
        """CRITICAL: Test that _cache_report_result should NOT use direct json.dumps.
        
        EXPECTED: FAIL NOW - uses json.dumps directly  
        EXPECTED: PASS AFTER - uses UnifiedJSONSerializer.safe_dumps
        """
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Create agent instance
        agent = ReportingSubAgent(self.mock_context, self.mock_websocket_manager)
        agent.redis_manager = self.mock_redis_manager
        
        # Mock Redis set operation
        self.mock_redis_manager.set = Mock()
        
        # Mock json.dumps to track if it's called (SHOULD NOT BE)
        mock_json_dumps.return_value = '{"report": "test"}'
        
        # Test data to cache
        test_result = {"report": "test report", "status": "success"}
        
        # This will fail because the method currently uses json.dumps
        import asyncio
        asyncio.run(agent._cache_report_result("test_key", test_result))
        
        # THIS ASSERTION WILL FAIL - proving SSOT violation
        mock_json_dumps.assert_not_called()  # Should NOT call json.dumps
    
    def test_cache_report_result_should_import_ssot_serializer(self):
        """Test that _cache_report_result method should import UnifiedJSONSerializer."""
        import inspect
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Get source code of the method
        method_source = inspect.getsource(ReportingSubAgent._cache_report_result)
        
        # Check for SSOT import usage (should be present after remediation)
        self.assertNotIn('json.dumps', method_source,
                        "SSOT VIOLATION: _cache_report_result should not use json.dumps directly")
        
        # After remediation, should use SSOT serializer  
        # This will fail NOW but pass after remediation
        self.assertIn('UnifiedJSONSerializer', method_source,
                     "Missing SSOT import: Should use UnifiedJSONSerializer.safe_dumps()")
    
    def test_unified_json_serializer_available(self):
        """Test that UnifiedJSONSerializer is available from SSOT module."""
        try:
            from netra_backend.app.core.serialization.unified_json_handler import UnifiedJSONSerializer
            
            # Test basic functionality
            serializer = UnifiedJSONSerializer()
            
            # Test safe_dumps method exists
            self.assertTrue(hasattr(serializer, 'safe_dumps'), 
                          "UnifiedJSONSerializer missing safe_dumps method")
            
            # Test safe_loads method exists  
            self.assertTrue(hasattr(serializer, 'safe_loads'),
                          "UnifiedJSONSerializer missing safe_loads method")
            
        except ImportError as e:
            self.fail(f"Cannot import UnifiedJSONSerializer from SSOT module: {e}")
    
    def test_ssot_json_serializer_functionality(self):
        """Test SSOT UnifiedJSONSerializer basic functionality."""
        from netra_backend.app.core.serialization.unified_json_handler import UnifiedJSONSerializer
        
        serializer = UnifiedJSONSerializer()
        
        # Test data
        test_data = {"report": "test report", "status": "success", "count": 42}
        
        # Test safe_dumps
        json_string = serializer.safe_dumps(test_data)
        self.assertIsInstance(json_string, str)
        self.assertIn("test report", json_string)
        
        # Test safe_loads
        parsed_data = serializer.safe_loads(json_string)
        self.assertEqual(parsed_data, test_data)
    
    def test_reporting_agent_llm_response_parsing_uses_ssot(self):
        """Test that LLM response parsing uses SSOT patterns correctly."""
        from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
        
        # Create agent instance
        agent = ReportingSubAgent(self.mock_context, self.mock_websocket_manager)
        
        # Test malformed JSON recovery uses SSOT JSONErrorFixer
        malformed_json = '{"report": "incomplete'  # Missing closing brace
        
        # This should use SSOT error recovery
        result = agent._extract_and_validate_report(malformed_json, "test_run")
        
        # Should return fallback result from SSOT error handling
        self.assertIsInstance(result, dict)
        self.assertIn("report", result)


if __name__ == '__main__':
    unittest.main()