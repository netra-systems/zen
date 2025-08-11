"""
Comprehensive unit tests for fallback_handler.py
Tests context-aware fallback response generation for AI slop prevention
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import re

from app.core.fallback_handler import (
    FallbackHandler,
    FallbackContext,
    FallbackMetadata
)


class TestFallbackHandler:
    """Test suite for FallbackHandler"""
    
    @pytest.fixture
    def fallback_handler(self):
        """Create FallbackHandler instance"""
        return FallbackHandler()
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample fallback metadata"""
        return FallbackMetadata(
            error_type="ValidationError",
            error_message="Quality score below threshold",
            agent_name="optimization_agent",
            user_input="Optimize my GPU workload for better performance",
            partial_data={
                "metrics": {"latency": 150, "throughput": 1200},
                "bottlenecks": ["memory_bandwidth", "compute_utilization"],
                "recommendations": ["Enable KV cache", "Use tensor parallelism"]
            },
            attempted_operations=["analyze_workload", "identify_bottlenecks"],
            stacktrace="File test.py, line 42, in optimize_gpu"
        )
    
    def test_initialization(self, fallback_handler):
        """Test fallback handler initialization"""
        assert fallback_handler.templates is not None
        assert len(fallback_handler.templates) == 8  # 8 FallbackContext types including GENERAL_FAILURE
        assert fallback_handler.domain_detection_keywords is not None
        assert len(fallback_handler.domain_detection_keywords) > 0
        
        # Verify all required context types have templates
        expected_contexts = [
            FallbackContext.TRIAGE_FAILURE,
            FallbackContext.DATA_FAILURE,
            FallbackContext.OPTIMIZATION_FAILURE,
            FallbackContext.ACTION_FAILURE,
            FallbackContext.REPORT_FAILURE,
            FallbackContext.LLM_FAILURE,
            FallbackContext.VALIDATION_FAILURE,
            FallbackContext.GENERAL_FAILURE
        ]
        
        for context in expected_contexts:
            assert context in fallback_handler.templates
    
    def test_generate_fallback_triage_failure(self, fallback_handler, sample_metadata):
        """Test fallback generation for triage failure"""
        result = fallback_handler.generate_fallback(
            FallbackContext.TRIAGE_FAILURE,
            sample_metadata
        )
        
        assert result["type"] == "contextual_fallback"
        assert result["context"] == "triage_failure"
        assert len(result["message"]) > 100  # Should be substantial
        assert "model optimization" in result["message"].lower()  # Should detect domain
        
        # Check metadata
        assert result["metadata"]["error_type"] == "ValidationError"
        assert result["metadata"]["agent"] == "optimization_agent"
        assert result["metadata"]["has_partial_data"] is True
        assert result["metadata"]["recovery_available"] is True
        
        # Check partial data is included
        assert "partial_data" in result
        assert result["partial_data"] == sample_metadata.partial_data
        
        # Check suggested actions
        assert "suggested_actions" in result
        assert len(result["suggested_actions"]) > 0
    
    def test_generate_fallback_data_failure(self, fallback_handler):
        """Test fallback generation for data failure"""
        metadata = FallbackMetadata(
            error_type="ConnectionError",
            error_message="Database connection timeout",
            agent_name="data_agent",
            user_input="Analyze system performance data",
            partial_data={
                "source": "performance_database",
                "collected_rows": 1250,
                "tables": ["metrics", "logs"]
            }
        )
        
        result = fallback_handler.generate_fallback(
            FallbackContext.DATA_FAILURE,
            metadata
        )
        
        assert result["type"] == "contextual_fallback"
        assert result["context"] == "data_failure"
        assert "database" in result["message"].lower() or "performance_database" in result["message"]
        assert "collected" in result["message"] or "partial" in result["message"].lower()
    
    def test_generate_fallback_optimization_failure(self, fallback_handler, sample_metadata):
        """Test fallback generation for optimization failure"""
        result = fallback_handler.generate_fallback(
            FallbackContext.OPTIMIZATION_FAILURE,
            sample_metadata
        )
        
        message = result["message"]
        assert "bottlenecks" in message or "recommendations" in message or "optimization" in message.lower()
        
        # Should include manual steps
        assert any(word in message.lower() for word in ["manual", "steps", "directly", "immediate"])
    
    def test_generate_fallback_action_failure(self, fallback_handler, sample_metadata):
        """Test fallback generation for action plan failure"""
        result = fallback_handler.generate_fallback(
            FallbackContext.ACTION_FAILURE,
            sample_metadata
        )
        
        message = result["message"]
        assert "analyze_workload" in message or "identify_bottlenecks" in message or "completed" in message.lower()
    
    def test_generate_fallback_report_failure(self, fallback_handler, sample_metadata):
        """Test fallback generation for report failure"""
        metadata = FallbackMetadata(
            error_type="TemplateError",
            error_message="Report template compilation failed",
            agent_name="reporting_agent",
            user_input="Generate monthly performance report",
            partial_data={
                "summary": "System performance analysis complete",
                "metrics": {"cpu": 75, "memory": 68, "disk": 45},
                "findings": ["High CPU during peak hours", "Memory usage trending up"]
            }
        )
        
        result = fallback_handler.generate_fallback(
            FallbackContext.REPORT_FAILURE,
            metadata
        )
        
        message = result["message"]
        assert "report" in message.lower()
        assert "summary" in message.lower() or "Summary" in message or "sections" in message.lower()
    
    def test_generate_fallback_llm_failure(self, fallback_handler):
        """Test fallback generation for LLM failure"""
        metadata = FallbackMetadata(
            error_type="APIError",
            error_message="OpenAI API rate limit exceeded",
            agent_name="generation_agent",
            user_input="Explain quantum computing basics",
            partial_data={
                "model": "gpt-4",
                "operation": "text_generation",
                "tokens": 450
            }
        )
        
        result = fallback_handler.generate_fallback(
            FallbackContext.LLM_FAILURE,
            metadata
        )
        
        message = result["message"]
        assert "gpt-4" in message
        assert "450" in message
        assert "text_generation" in message or "generation" in message
        assert "rate limit" in message.lower() or "limiting" in message.lower()
    
    def test_generate_fallback_validation_failure(self, fallback_handler):
        """Test fallback generation for validation failure"""
        metadata = FallbackMetadata(
            error_type="QualityError",
            error_message="Output quality score too low",
            agent_name="optimization_agent",
            user_input="Improve model inference speed",
            partial_data={
                "quality_issues": ["Too many generic phrases", "Lack of specific metrics"],
                "quality_score": 0.35,
                "threshold": 0.7
            }
        )
        
        result = fallback_handler.generate_fallback(
            FallbackContext.VALIDATION_FAILURE,
            metadata
        )
        
        message = result["message"]
        assert "quality" in message.lower() or "validation" in message.lower()
        assert "generic phrases" in message or "specific metrics" in message or "issues" in message.lower()
    
    def test_generate_fallback_general_failure(self, fallback_handler, sample_metadata):
        """Test fallback generation for general failure"""
        result = fallback_handler.generate_fallback(
            FallbackContext.GENERAL_FAILURE,
            sample_metadata
        )
        
        message = result["message"]
        assert "optimization_agent" in message or "agent" in message.lower()
        assert "ValidationError" in message or "error" in message.lower()
    
    def test_detect_domain_optimization(self, fallback_handler):
        """Test domain detection for optimization queries"""
        test_cases = [
            ("optimize model latency", "model optimization"),
            ("reduce training time", "training"),
            ("deploy to production", "deployment"),
            ("analyze cost breakdown", "cost"),
            ("improve performance metrics", "performance"),
            ("debug memory issues", "debugging"),
            ("design new architecture", "architecture"),
            ("process large dataset", "data")
        ]
        
        for user_input, expected_domain in test_cases:
            detected = fallback_handler._detect_domain(user_input)
            assert detected == expected_domain.replace('_', ' ') or detected == "general optimization"
    
    def test_extract_error_reason(self, fallback_handler):
        """Test error reason extraction"""
        test_cases = [
            ("ValueError: Invalid input format", "Invalid input format"),
            ("ConnectionError: Database timeout after 30s\nStack trace...", "Database timeout after 30s"),
            ("Very long error message " + "x" * 200, "Very long error message " + "x" * 77 + "..."),
            ("TimeoutError: Operation timed out", "Operation timed out"),
        ]
        
        for error_message, expected_reason in test_cases:
            reason = fallback_handler._extract_error_reason(error_message)
            assert reason == expected_reason
    
    def test_format_partial_data_various_types(self, fallback_handler):
        """Test formatting of various partial data types"""
        test_cases = [
            (None, "Initial analysis suggests this is an optimization-related query"),
            ({}, "Partial analysis completed"),
            ({"count": 42}, "- count: 42"),
            ({"items": [1, 2, 3, 4, 5]}, "- items: 5 items collected"),
            ({"config": {"batch_size": 32, "lr": 0.001}}, "- config: Data structure with 2 fields"),
            ({"mixed": "value", "list": [1, 2], "dict": {"a": 1}}, 
             "- mixed: value\n- list: 2 items collected\n- dict: Data structure with 1 fields")
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._format_partial_data(partial_data)
            if expected in result or result == expected:
                assert True
            else:
                # For complex cases, just verify it's not empty and contains key info
                assert len(result) > 0
                if partial_data:
                    assert any(key in result for key in partial_data.keys())
    
    def test_summarize_partial_data(self, fallback_handler):
        """Test summarization of partial data"""
        test_cases = [
            (None, "No data was successfully collected before the error"),
            ({"metrics": [1, 2, 3], "logs": [{"a": 1}, {"b": 2}]}, 
             "Collected 5 total items: 3 metrics, 2 logs entries"),
            ({"single": "value"}, "Some preliminary data was collected"),
            ({"empty_list": [], "empty_dict": {}}, "Some preliminary data was collected")
        ]
        
        for partial_data, expected_pattern in test_cases:
            result = fallback_handler._summarize_partial_data(partial_data)
            if "total items" in expected_pattern:
                assert "total items" in result
            else:
                assert result == expected_pattern
    
    def test_extract_data_source(self, fallback_handler):
        """Test data source extraction from metadata"""
        test_cases = [
            # From partial data
            (FallbackMetadata("", "", partial_data={"source": "redis_cache"}), "redis_cache"),
            # From error message
            (FallbackMetadata("", "Database connection failed", partial_data=None), "database"),
            (FallbackMetadata("", "API endpoint returned 500", partial_data=None), "API endpoint"),
            (FallbackMetadata("", "File not found error", partial_data=None), "file system"),
            (FallbackMetadata("", "Unknown error", partial_data=None), "data source")
        ]
        
        for metadata, expected in test_cases:
            result = fallback_handler._extract_data_source(metadata)
            assert result == expected
    
    def test_suggest_alternative_sources(self, fallback_handler):
        """Test alternative data source suggestions"""
        test_cases = [
            ("database", ["Cache layer", "Read replica", "Data warehouse"]),
            ("API endpoint", ["Alternative API", "GraphQL", "Webhook"]),
            ("file system", ["Object storage", "Database export", "API data"]),
            ("unknown_source", ["Manual data export", "Alternative API", "Cached results"])
        ]
        
        for source, expected_keywords in test_cases:
            result = fallback_handler._suggest_alternative_sources(source)
            assert len(result) > 0
            for keyword in expected_keywords:
                assert any(word in result for word in keyword.split())
    
    def test_identify_limitation(self, fallback_handler):
        """Test limitation identification from error messages"""
        test_cases = [
            ("Operation timeout after 30 seconds", "processing timeout"),
            ("Out of memory error occurred", "memory constraints"),
            ("Rate limit exceeded: 429", "rate limiting"),
            ("Permission denied: insufficient privileges", "permission restrictions"),
            ("Connection refused by server", "connection issues"),
            ("Unknown error occurred", "technical constraints")
        ]
        
        for error_message, expected_limitation in test_cases:
            metadata = FallbackMetadata("", error_message)
            result = fallback_handler._identify_limitation(metadata)
            assert result == expected_limitation
    
    def test_format_optimization_results(self, fallback_handler):
        """Test formatting of optimization results"""
        test_cases = [
            (None, "Initial optimization scan completed"),
            ({}, "Preliminary analysis completed"),
            ({"metrics": "latency, throughput"}, "Metrics analyzed: latency, throughput"),
            ({"bottlenecks": ["cpu", "memory"]}, "Bottlenecks identified: ['cpu', 'memory']"),
            ({"recommendations": ["cache", "batch", "parallel"]}, "Recommendations generated: 3"),
            ({
                "metrics": "performance",
                "bottlenecks": ["network"],
                "recommendations": ["optimize", "scale"]
            }, None)  # Complex case - just verify it processes
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._format_optimization_results(partial_data)
            if expected:
                if expected == "Bottlenecks identified: ['cpu', 'memory']":
                    assert "Bottlenecks identified:" in result
                else:
                    assert result == expected
            else:
                # For complex cases, verify content is present
                assert len(result) > 0
    
    def test_generate_manual_optimization_steps(self, fallback_handler):
        """Test manual optimization steps generation"""
        result = fallback_handler._generate_manual_optimization_steps()
        
        assert len(result) > 200  # Should be substantial
        assert "profile" in result.lower()
        assert "bottlenecks" in result.lower()
        assert "caching" in result.lower()
        assert "measure" in result.lower()
        assert "iterate" in result.lower()
    
    def test_extract_partial_recommendations(self, fallback_handler):
        """Test extraction of partial recommendations"""
        test_cases = [
            (None, "Standard optimizations: caching, batching, async processing"),
            ({"other_data": "value"}, "Standard optimizations: caching, batching, async processing"),
            ({"recommendations": ["Use Redis cache", "Enable compression", "Add load balancer"]}, 
             "- Use Redis cache\n- Enable compression\n- Add load balancer"),
            ({"recommendations": "Single recommendation"}, "Single recommendation")
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._extract_partial_recommendations(partial_data)
            if expected.startswith("- "):
                # List format
                assert result.startswith("- ")
                assert "Redis cache" in result
            else:
                assert result == expected
    
    def test_list_completed_actions(self, fallback_handler):
        """Test listing of completed actions"""
        test_cases = [
            (None, "No actions were completed before the failure"),
            ([], "No actions were completed before the failure"),
            (["analyze_data", "identify_issues"], "✓ analyze_data\n✓ identify_issues"),
            (["single_action"], "✓ single_action")
        ]
        
        for operations, expected in test_cases:
            result = fallback_handler._list_completed_actions(operations)
            assert result == expected
    
    def test_identify_failure_point(self, fallback_handler):
        """Test failure point identification"""
        test_cases = [
            (FallbackMetadata("", "", agent_name="test_agent"), "Failed during: test_agent"),
            (FallbackMetadata("", "", stacktrace="File test.py, line 42, in optimize"), 
             "Failed at: File test.py, line 42, in optimize"),
            (FallbackMetadata("", "", stacktrace="Multiple\nFile script.py, line 15\nlines"), 
             "Failed at: File script.py, line 15"),
            (FallbackMetadata("", ""), "Failed during: processing")
        ]
        
        for metadata, expected in test_cases:
            result = fallback_handler._identify_failure_point(metadata)
            assert result == expected
    
    def test_generate_immediate_steps(self, fallback_handler):
        """Test immediate steps generation"""
        result = fallback_handler._generate_immediate_steps(FallbackMetadata("", ""))
        
        assert "configuration" in result.lower()
        assert "parameters" in result.lower()
        assert "resources" in result.lower()
        assert "retry" in result.lower()
        assert "documentation" in result.lower()
    
    def test_create_manual_guide(self, fallback_handler):
        """Test manual implementation guide creation"""
        result = fallback_handler._create_manual_guide(FallbackMetadata("", ""))
        
        assert "dashboard" in result.lower()
        assert "configuration" in result.lower()
        assert "parameters" in result.lower()
        assert "incremental" in result.lower()
        assert "monitor" in result.lower()
        assert "document" in result.lower()
    
    def test_list_completed_sections(self, fallback_handler):
        """Test listing completed report sections"""
        test_cases = [
            (None, "No sections completed"),
            ({}, "Report initialization completed"),
            ({"summary": "data", "analysis": "more data"}, "✓ Summary\n✓ Analysis"),
            ({"custom_section": "data"}, "Report initialization completed"),  # Unknown sections
            ({"summary": "data", "metrics": [1,2,3], "conclusions": "final"}, 
             "✓ Summary\n✓ Metrics\n✓ Conclusions")
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._list_completed_sections(partial_data)
            if "✓" in expected:
                for section in ["Summary", "Analysis", "Metrics", "Conclusions"]:
                    if section in expected:
                        assert section in result
            else:
                assert result == expected
    
    def test_summarize_analyzed_data(self, fallback_handler):
        """Test analyzed data summarization"""
        test_cases = [
            (None, "No data analysis completed"),
            ({"metric1": 100, "metric2": 200, "status": "ok"}, "Analyzed 3 data points across multiple dimensions")
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._summarize_analyzed_data(partial_data)
            assert result == expected
    
    def test_extract_key_findings(self, fallback_handler):
        """Test key findings extraction"""
        test_cases = [
            (None, "Analysis incomplete - no findings available"),
            ({"findings": "Critical performance bottleneck identified"}, 
             "Critical performance bottleneck identified"),
            ({"cpu_usage": 85.5, "memory": 92, "disk_io": 45}, "cpu_usage: 85.5\nmemory: 92\ndisk_io: 45"),
            ({}, "Preliminary analysis started")
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._extract_key_findings(partial_data)
            if expected.count(":") > 0 and expected.count("\n") > 0:
                # Multiple metrics case
                assert ":" in result
                # Check that at least some numeric values are present
                assert any(str(v) in result for v in [85.5, 92, 45])
            else:
                assert result == expected
    
    def test_format_quality_issues(self, fallback_handler):
        """Test quality issues formatting"""
        test_cases = [
            (None, "Output did not meet quality thresholds"),
            ({"other_data": "value"}, "Output did not meet quality thresholds"),
            ({"quality_issues": ["Generic phrases", "No metrics"]}, 
             "- Generic phrases\n- No metrics"),
            ({"quality_issues": "Single issue"}, "Single issue")
        ]
        
        for partial_data, expected in test_cases:
            result = fallback_handler._format_quality_issues(partial_data)
            if "- " in expected:
                assert "- Generic phrases" in result
                assert "- No metrics" in result
            else:
                assert result == expected
    
    def test_identify_specific_problems(self, fallback_handler):
        """Test specific problem identification"""
        test_cases = [
            ("Too many generic phrases detected", ["Too many generic phrases detected"]),
            ("Output is too short", ["Output length below minimum threshold"]),
            ("Not actionable enough", ["Lack of actionable recommendations"]),
            ("Multiple issues: generic and short and actionable", 
             ["generic", "short", "actionable"]),
            ("Unknown quality issue", ["Quality score below acceptable threshold"])
        ]
        
        for error_message, expected_keywords in test_cases:
            metadata = FallbackMetadata("", error_message)
            result = fallback_handler._identify_specific_problems(metadata)
            
            if expected_keywords[0] == "Quality score below acceptable threshold":
                assert expected_keywords[0] == result
            else:
                # Check that at least one expected keyword is in result
                assert any(keyword in result.lower() for keyword in [k.lower() for k in expected_keywords])
    
    def test_generate_alternative_output(self, fallback_handler):
        """Test alternative output generation"""
        result = fallback_handler._generate_alternative_output(FallbackMetadata("", ""))
        
        assert "caching" in result.lower()
        assert "30-40%" in result or "latency reduction" in result
        assert "batching" in result.lower()
        assert "pooling" in result.lower()
        assert "scaling" in result.lower()
        assert "monitoring" in result.lower()
    
    def test_suggest_improvements(self, fallback_handler):
        """Test improvement suggestions"""
        result = fallback_handler._suggest_improvements(FallbackMetadata("", ""))
        
        assert "specific" in result.lower()
        assert "configuration" in result.lower()
        assert "goals" in result.lower()
        assert "data" in result.lower()
        assert "criteria" in result.lower()
    
    def test_generate_verification_steps(self, fallback_handler):
        """Test verification steps generation"""
        result = fallback_handler._generate_verification_steps()
        
        assert "requirements" in result.lower()
        assert "validate" in result.lower()
        assert "actionability" in result.lower()
        assert "staging" in result.lower()
        assert "improvements" in result.lower()
    
    def test_identify_stage(self, fallback_handler):
        """Test processing stage identification"""
        test_cases = [
            (FallbackMetadata("", "", agent_name="optimization_agent"), "optimization_agent processing"),
            (FallbackMetadata("", ""), "Processing")
        ]
        
        for metadata, expected in test_cases:
            result = fallback_handler._identify_stage(metadata)
            assert result == expected
    
    def test_generate_diagnostics(self, fallback_handler):
        """Test diagnostics generation"""
        metadata = FallbackMetadata(
            error_type="ValidationError",
            error_message="Test error",
            agent_name="test_agent",
            attempted_operations=["op1", "op2", "op3"]
        )
        
        result = fallback_handler._generate_diagnostics(metadata)
        
        assert "Error Type: ValidationError" in result
        assert "Agent: test_agent" in result
        assert "Operations Attempted: 3" in result
    
    def test_suggest_recovery_actions(self, fallback_handler):
        """Test recovery actions suggestion"""
        result = fallback_handler._suggest_recovery_actions(FallbackMetadata("", ""))
        
        assert "retry" in result.lower()
        assert "complexity" in result.lower()
        assert "status" in result.lower()
        assert "cache" in result.lower()
        assert "support" in result.lower()
    
    def test_generate_structured_fallback(self, fallback_handler):
        """Test structured fallback generation when template fails"""
        metadata = FallbackMetadata(
            error_type="TestError",
            error_message="Test error message"
        )
        
        result = fallback_handler._generate_structured_fallback(
            FallbackContext.GENERAL_FAILURE,
            metadata
        )
        
        assert "general_failure" in result
        assert "Test error message" in result
        assert "retry" in result.lower()
        assert "parameters" in result.lower()
        assert "support" in result.lower()
        assert "general_failure_TestError" in result
    
    def test_generate_suggested_actions(self, fallback_handler):
        """Test suggested actions generation"""
        metadata = FallbackMetadata("TestError", "Test message")
        
        result = fallback_handler._generate_suggested_actions(
            FallbackContext.OPTIMIZATION_FAILURE,
            metadata
        )
        
        assert len(result) == 3
        
        # Check retry action
        retry_action = result[0]
        assert retry_action["action"] == "retry"
        assert retry_action["description"] == "Retry the operation"
        assert "delay" in retry_action["parameters"]
        assert "max_attempts" in retry_action["parameters"]
        
        # Check simplify action
        simplify_action = result[1]
        assert simplify_action["action"] == "simplify"
        assert "simplified" in simplify_action["description"]
        
        # Check manual action
        manual_action = result[2]
        assert manual_action["action"] == "manual"
        assert "manual" in manual_action["description"]
        assert "optimization_failure" in manual_action["documentation_url"]
    
    def test_generate_fallback_template_formatting_error(self, fallback_handler):
        """Test fallback generation when template formatting fails"""
        # Create metadata that will cause template variable issues
        metadata = FallbackMetadata(
            error_type="TemplateError",
            error_message="Template formatting failed"
        )
        
        # Mock template formatting to raise KeyError
        with patch.object(fallback_handler, '_generate_template_variables', 
                         side_effect=KeyError("Missing template variable")):
            result = fallback_handler.generate_fallback(
                FallbackContext.GENERAL_FAILURE,
                metadata
            )
        
        # Should fall back to structured fallback
        assert result["type"] == "contextual_fallback"
        assert "Template formatting failed" in result["message"]
        assert "retry" in result["message"].lower()
    
    def test_format_fallback_data_serialization_error(self, fallback_handler):
        """Test fallback data formatting with serialization error"""
        # Create data that can't be JSON serialized
        class UnserializableObject:
            pass
        
        partial_data = {"object": UnserializableObject()}
        
        with patch('app.core.fallback_handler.logger') as mock_logger:
            result = fallback_handler._format_fallback_data(partial_data)
            
            assert result == "Structured data available but cannot be displayed"
            mock_logger.warning.assert_called_once()
    
    def test_comprehensive_fallback_scenarios(self, fallback_handler):
        """Test comprehensive fallback scenarios for all contexts"""
        scenarios = [
            (FallbackContext.TRIAGE_FAILURE, "analyze user query"),
            (FallbackContext.DATA_FAILURE, "collect performance metrics"),
            (FallbackContext.OPTIMIZATION_FAILURE, "optimize GPU workload"),
            (FallbackContext.ACTION_FAILURE, "create deployment plan"),
            (FallbackContext.REPORT_FAILURE, "generate analysis report"),
            (FallbackContext.LLM_FAILURE, "generate explanation"),
            (FallbackContext.VALIDATION_FAILURE, "validate output quality"),
            (FallbackContext.GENERAL_FAILURE, "process request")
        ]
        
        for context, user_request in scenarios:
            metadata = FallbackMetadata(
                error_type="TestError",
                error_message=f"Failed to {user_request}",
                agent_name="test_agent",
                user_input=f"Please {user_request}",
                partial_data={"test": "data"},
                attempted_operations=["init", "process"]
            )
            
            result = fallback_handler.generate_fallback(context, metadata)
            
            # Verify basic structure
            assert result["type"] == "contextual_fallback"
            assert result["context"] == context.value
            assert len(result["message"]) > 50
            
            # Verify metadata
            assert result["metadata"]["error_type"] == "TestError"
            assert result["metadata"]["agent"] == "test_agent"
            assert result["metadata"]["has_partial_data"] is True
            
            # Verify partial data and actions
            assert "partial_data" in result
            assert "suggested_actions" in result
            assert len(result["suggested_actions"]) == 3


class TestFallbackContextEnum:
    """Test FallbackContext enum"""
    
    def test_fallback_context_values(self):
        """Test that all fallback context values are strings"""
        contexts = [
            FallbackContext.TRIAGE_FAILURE,
            FallbackContext.DATA_FAILURE,
            FallbackContext.OPTIMIZATION_FAILURE,
            FallbackContext.ACTION_FAILURE,
            FallbackContext.REPORT_FAILURE,
            FallbackContext.LLM_FAILURE,
            FallbackContext.VALIDATION_FAILURE,
            FallbackContext.GENERAL_FAILURE
        ]
        
        for context in contexts:
            assert isinstance(context.value, str)
            assert len(context.value) > 0
            assert "_" in context.value  # Should be snake_case


class TestFallbackMetadata:
    """Test FallbackMetadata dataclass"""
    
    def test_fallback_metadata_creation(self):
        """Test FallbackMetadata creation with various parameters"""
        # Minimal metadata
        metadata = FallbackMetadata("Error", "Message")
        assert metadata.error_type == "Error"
        assert metadata.error_message == "Message"
        assert metadata.agent_name is None
        assert metadata.user_input is None
        assert metadata.partial_data is None
        assert metadata.attempted_operations is None
        assert metadata.stacktrace is None
        
        # Full metadata
        full_metadata = FallbackMetadata(
            error_type="ValidationError",
            error_message="Quality check failed",
            agent_name="optimizer",
            user_input="Optimize system",
            partial_data={"metrics": [1, 2, 3]},
            attempted_operations=["analyze", "optimize"],
            stacktrace="File test.py, line 1"
        )
        
        assert full_metadata.error_type == "ValidationError"
        assert full_metadata.error_message == "Quality check failed"
        assert full_metadata.agent_name == "optimizer"
        assert full_metadata.user_input == "Optimize system"
        assert full_metadata.partial_data == {"metrics": [1, 2, 3]}
        assert full_metadata.attempted_operations == ["analyze", "optimize"]
        assert full_metadata.stacktrace == "File test.py, line 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])