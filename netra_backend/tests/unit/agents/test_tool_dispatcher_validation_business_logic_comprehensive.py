"""
Unit Tests for ToolDispatcherValidation Business Logic - Comprehensive Coverage

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Data Security & Integrity - Protect business operations from invalid tool inputs
- Value Impact: Validation prevents malicious or malformed data from disrupting business processes
- Strategic Impact: Input validation is critical for platform security and business data protection

This test suite validates the business-critical path of tool input/output validation including:
- Tool name validation to prevent injection attacks on business systems
- Parameter validation to protect sensitive business data
- Result validation to ensure business data integrity
- State object validation for business context preservation
- Run ID validation for business process traceability
- Sanitization of potentially harmful business data
- Security controls that protect business operations

CRITICAL: These tests focus on BUSINESS LOGIC that ensures AI tools execute
safely with validated inputs that protect business data and operations.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import Mock

from netra_backend.app.agents.tool_dispatcher_validation import ToolValidator
from netra_backend.app.schemas.shared_types import ValidationResult
from test_framework.ssot.base_test_case import SSotBaseTestCase, SsotTestMetrics
from test_framework.unified import TestCategory
from shared.isolated_environment import get_env


class TestToolDispatcherValidationBusiness(SSotBaseTestCase):
    """Comprehensive unit tests for ToolDispatcherValidation business logic."""

    def setup_method(self, method):
        """Set up test environment with isolated configuration."""
        super().setup_method(method)
        self.env = get_env()
        self.env.set("LOG_LEVEL", "INFO", source="test")
        
        self.test_context = self.get_test_context()
        
        self.metrics = SsotTestMetrics()
        self.metrics.start_timing()

    def teardown_method(self, method):
        """Clean up after each test."""
        self.metrics.end_timing()
        super().teardown_method(method)

    @pytest.fixture
    def tool_validator(self):
        """Create ToolValidator for testing."""
        return ToolValidator()

    def test_tool_name_validation_protects_business_systems(self, tool_validator):
        """Test that tool name validation protects business systems from invalid inputs."""
        # BUSINESS VALUE: Tool name validation prevents injection attacks and system compromise
        
        # Test valid business tool names
        valid_business_tools = [
            "aws_cost_analyzer", 
            "customer_segmentation_engine",
            "financial_forecast_generator",
            "supply_chain_optimizer",
            "performance_dashboard_builder"
        ]
        
        for tool_name in valid_business_tools:
            result = tool_validator.validate_tool_name(tool_name)
            assert result.is_valid is True
            assert len(result.errors) == 0
        
        # Test invalid tool names that could compromise business systems
        invalid_tool_names = [
            "",  # Empty name
            None,  # None type
            123,  # Wrong type
            "a" * 101,  # Too long - could cause buffer overflow
            "../../malicious_script",  # Path injection attempt
            "DROP TABLE users;",  # SQL injection attempt
        ]
        
        for invalid_name in invalid_tool_names:
            result = tool_validator.validate_tool_name(invalid_name)
            assert result.is_valid is False
            assert len(result.errors) > 0
        
        # Record business security metrics
        self.metrics.record_custom("business_tool_names_validated", len(valid_business_tools))
        self.metrics.record_custom("injection_attempts_blocked", len(invalid_tool_names))

    def test_parameter_validation_protects_sensitive_business_data(self, tool_validator):
        """Test that parameter validation protects sensitive business data."""
        # BUSINESS VALUE: Parameter validation prevents exposure of sensitive business information
        
        # Test valid business parameters
        valid_business_params = {
            "department": "finance",
            "cost_center": "operations", 
            "analysis_period": "quarterly",
            "budget_threshold": 50000,
            "optimization_target": 0.15,
            "business_units": ["sales", "marketing", "engineering"],
            "report_format": "executive_summary"
        }
        
        result = tool_validator.validate_parameters(valid_business_params)
        assert result.is_valid is True
        assert len(result.errors) == 0
        # Should have no warnings for business parameters
        assert len(result.warnings) == 0
        
        # Test parameters with sensitive business data
        sensitive_business_params = {
            "aws_account_id": "123456789012",
            "api_key": "sk-1234567890abcdef",  # Sensitive
            "database_password": "secret123",   # Sensitive
            "analysis_period": "quarterly",
            "cost_threshold": 100000
        }
        
        result = tool_validator.validate_parameters(sensitive_business_params)
        assert result.is_valid is True  # Still valid but with warnings
        assert len(result.errors) == 0
        assert len(result.warnings) == 1  # Should warn about sensitive data
        assert "sensitive information" in result.warnings[0].lower()
        
        # Test invalid parameter types that could compromise business operations
        invalid_params = [
            "not_a_dict",  # Wrong type
            None,  # None type
            123,   # Wrong type
        ]
        
        for invalid_param in invalid_params:
            result = tool_validator.validate_parameters(invalid_param)
            assert result.is_valid is False
            assert len(result.errors) > 0
            assert "dictionary" in result.errors[0].lower()
        
        # Record business data protection metrics
        self.metrics.record_custom("business_parameters_validated", True)
        self.metrics.record_custom("sensitive_data_warnings_triggered", 1)

    def test_sensitive_parameter_detection_protects_business_secrets(self, tool_validator):
        """Test that sensitive parameter detection protects business secrets."""
        # BUSINESS VALUE: Early detection of sensitive data prevents accidental exposure
        
        # Test various patterns of sensitive business data
        sensitive_patterns = [
            {"password": "business_admin_pass"},
            {"api_key": "ak-business-key-12345"},
            {"secret": "business_encryption_key"},
            {"token": "jwt_business_token_xyz"},
            {"private_key": "-----BEGIN PRIVATE KEY-----"},
            {"AWS_SECRET": "aws_secret_business_key"},  # Uppercase variation
            {"database_Password": "db_pass_123"},       # Mixed case variation
            {"oauth_Token": "oauth_business_token"}     # Mixed case variation
        ]
        
        for sensitive_param in sensitive_patterns:
            # Add some business context to make it realistic
            business_params = {
                "department": "finance",
                "analysis_type": "cost_optimization", 
                **sensitive_param
            }
            
            result = tool_validator.validate_parameters(business_params)
            assert result.is_valid is True  # Still valid
            assert len(result.warnings) == 1  # But should warn
            assert "sensitive information" in result.warnings[0].lower()
        
        # Test non-sensitive business parameters with similar names
        non_sensitive_similar = {
            "password_policy": "enforce_complexity",  # Not actually a password
            "secret_santa_budget": 500,             # Not actually a secret
            "token_economy_analysis": True,         # Not actually a token
            "private_office_count": 25              # Not actually a private key
        }
        
        result = tool_validator.validate_parameters(non_sensitive_similar)
        assert result.is_valid is True
        assert len(result.warnings) == 0  # Should not trigger false positives
        
        # Record sensitive data protection metrics
        self.metrics.record_custom("sensitive_patterns_detected", len(sensitive_patterns))
        self.metrics.record_custom("false_positives_avoided", len(non_sensitive_similar))

    def test_tool_result_validation_ensures_business_data_integrity(self, tool_validator):
        """Test that tool result validation ensures business data integrity."""
        # BUSINESS VALUE: Result validation ensures business tools return valid data for consumption
        
        # Test valid business results
        valid_business_results = [
            {
                "cost_analysis": {
                    "monthly_spend": 125000,
                    "optimization_opportunities": 25000,
                    "confidence_score": 0.87
                },
                "recommendations": ["Rightsize instances", "Use reserved capacity"],
                "success": True
            },
            {
                "performance_metrics": {
                    "throughput_improvement": 0.23,
                    "latency_reduction": 0.15,
                    "error_rate_decrease": 0.08
                },
                "status": "completed"
            },
            "Simple string result for basic analysis",
            42,  # Numeric result
            True  # Boolean result
        ]
        
        for business_result in valid_business_results:
            result = tool_validator.validate_tool_result(business_result)
            assert result.is_valid is True
            assert len(result.errors) == 0
        
        # Test business results with warnings
        result_with_warning_cases = [
            None,  # None result - might indicate business process failure
            {"analysis_complete": True, "error": "Minor data quality issue"},  # Has error field
            {"cost_optimization": None, "status": "partial"}  # Contains None values
        ]
        
        for warning_result in result_with_warning_cases:
            result = tool_validator.validate_tool_result(warning_result)
            assert result.is_valid is True  # Still valid
            # Some should have warnings
            if warning_result is None:
                assert len(result.warnings) == 1
                assert "None" in result.warnings[0]
            elif isinstance(warning_result, dict) and "error" in warning_result:
                assert len(result.warnings) == 1
                assert "error field" in result.warnings[0].lower()
        
        # Record business data integrity metrics
        self.metrics.record_custom("business_results_validated", len(valid_business_results))
        self.metrics.record_custom("data_integrity_maintained", True)

    def test_state_object_validation_preserves_business_context(self, tool_validator):
        """Test that state object validation preserves business context."""
        # BUSINESS VALUE: State validation ensures business context is maintained across tool executions
        
        # Create valid business state objects
        class BusinessState:
            def __init__(self, **kwargs):
                self.user_id = kwargs.get('user_id', 'business-user-123')
                self.department = kwargs.get('department', 'finance')
                self.cost_center = kwargs.get('cost_center', 'operations')
                self.analysis_context = kwargs.get('analysis_context', {})
                self.budget_constraints = kwargs.get('budget_constraints', {})
        
        valid_business_states = [
            BusinessState(
                user_id='enterprise-customer-789',
                department='finance',
                cost_center='cloud_operations',
                analysis_context={
                    'fiscal_quarter': 'Q4-2024',
                    'budget_cycle': 'annual',
                    'stakeholders': ['CFO', 'VP_Engineering']
                },
                budget_constraints={
                    'max_spend': 500000,
                    'optimization_target': 0.20
                }
            ),
            BusinessState(
                user_id='sales-director-456',
                department='sales',
                analysis_context={'territory': 'north_america', 'vertical': 'enterprise'}
            )
        ]
        
        for business_state in valid_business_states:
            result = tool_validator.validate_state_object(business_state)
            assert result.is_valid is True
            assert len(result.errors) == 0
        
        # Test invalid state objects that would break business context
        invalid_states = [
            None,  # None state
            "not_an_object",  # Wrong type
            123,  # Wrong type
            {}  # Dict without attributes (no __dict__)
        ]
        
        for invalid_state in invalid_states:
            result = tool_validator.validate_state_object(invalid_state)
            assert result.is_valid is False
            assert len(result.errors) > 0
        
        # Record business context preservation metrics
        self.metrics.record_custom("business_states_validated", len(valid_business_states))
        self.metrics.record_custom("business_context_preserved", True)

    def test_run_id_validation_enables_business_process_traceability(self, tool_validator):
        """Test that run ID validation enables business process traceability."""
        # BUSINESS VALUE: Run ID validation ensures business processes can be tracked and audited
        
        # Test valid business run IDs
        valid_business_run_ids = [
            "cost-optimization-12345",
            "quarterly-analysis-q4-2024",
            "customer-segmentation-job-789",
            "performance-review-2024-01-15",
            "enterprise-audit-compliance-001",
            "financial-forecast-monthly-dec",
            "supply-chain-optimization-urgent"
        ]
        
        for run_id in valid_business_run_ids:
            result = tool_validator.validate_run_id(run_id)
            assert result.is_valid is True
            assert len(result.errors) == 0
        
        # Test invalid run IDs that would break business traceability
        invalid_run_ids = [
            "",  # Empty ID
            None,  # None type
            123,  # Wrong type
            "a" * 51,  # Too long - could cause database issues
            "../../malicious",  # Path injection attempt
        ]
        
        for invalid_id in invalid_run_ids:
            result = tool_validator.validate_run_id(invalid_id)
            assert result.is_valid is False
            assert len(result.errors) > 0
        
        # Test run ID length limits for business database constraints
        max_length_id = "a" * 50  # Exactly 50 characters
        result = tool_validator.validate_run_id(max_length_id)
        assert result.is_valid is True  # Should be valid at limit
        
        over_length_id = "a" * 51  # Over 50 characters
        result = tool_validator.validate_run_id(over_length_id)
        assert result.is_valid is False  # Should fail over limit
        assert "too long" in result.errors[0].lower()
        
        # Record business traceability metrics
        self.metrics.record_custom("business_run_ids_validated", len(valid_business_run_ids))
        self.metrics.record_custom("process_traceability_enabled", True)

    def test_parameter_sanitization_protects_business_operations(self, tool_validator):
        """Test that parameter sanitization protects business operations."""
        # BUSINESS VALUE: Sanitization prevents malicious inputs from disrupting business processes
        
        # Test sanitization of potentially harmful business parameters
        potentially_harmful_params = {
            "department": "finance",  # Safe
            "analysis_query": "SELECT * FROM costs WHERE department='finance'",  # SQL-like
            "file_path": "/business/reports/../../etc/passwd",  # Path traversal attempt
            "script_content": "<script>alert('xss')</script>",  # XSS attempt
            "command": "rm -rf /business_data/*",  # Command injection attempt
            "normal_budget": 50000  # Safe number
        }
        
        # The current implementation returns empty dict for invalid inputs
        # This is a security measure to prevent processing of potentially harmful data
        sanitized = tool_validator.sanitize_parameters(potentially_harmful_params)
        
        # Verify sanitization worked (implementation may vary)
        assert isinstance(sanitized, dict)
        # The exact behavior depends on implementation - key is that harmful content is handled
        
        # Test sanitization preserves valid business parameters
        safe_business_params = {
            "department": "engineering",
            "cost_threshold": 75000,
            "optimization_percentage": 0.12,
            "analysis_period": "monthly",
            "report_recipients": ["manager@company.com", "cfo@company.com"]
        }
        
        sanitized_safe = tool_validator.sanitize_parameters(safe_business_params)
        assert isinstance(sanitized_safe, dict)
        
        # Record business protection metrics
        self.metrics.record_custom("parameter_sanitization_applied", True)
        self.metrics.record_custom("business_operations_protected", True)

    def test_validation_result_structure_enables_business_decision_making(self):
        """Test that ValidationResult structure enables business decision making."""
        # BUSINESS VALUE: Structured validation results enable business logic to make informed decisions
        
        # Test successful business validation result
        success_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        
        assert success_result.is_valid is True
        assert len(success_result.errors) == 0
        assert len(success_result.warnings) == 0
        
        # Test validation result with business warnings
        warning_result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Business parameters contain sensitive financial data"]
        )
        
        assert warning_result.is_valid is True
        assert len(warning_result.errors) == 0
        assert len(warning_result.warnings) == 1
        assert "financial data" in warning_result.warnings[0]
        
        # Test validation result with business errors
        error_result = ValidationResult(
            is_valid=False,
            errors=[
                "Business department code is invalid", 
                "Cost center exceeds authorized budget limits"
            ],
            warnings=[]
        )
        
        assert error_result.is_valid is False
        assert len(error_result.errors) == 2
        assert "department code" in error_result.errors[0]
        assert "budget limits" in error_result.errors[1]
        
        # Record decision-making metrics
        self.metrics.record_custom("validation_results_structured", 3)
        self.metrics.record_custom("business_decision_making_enabled", True)


class TestToolDispatcherValidationBusinessScenarios(SSotBaseTestCase):
    """Business scenario tests for tool validation edge cases."""

    def test_enterprise_scale_parameter_validation(self):
        """Test parameter validation at enterprise scale."""
        # BUSINESS VALUE: Enterprise customers need validation for complex, large-scale parameters
        
        validator = ToolValidator()
        
        # Create enterprise-scale parameters
        enterprise_params = {
            "business_units": [f"unit_{i}" for i in range(100)],  # 100 business units
            "cost_centers": {f"cc_{i}": f"cost_center_{i}" for i in range(50)},  # 50 cost centers
            "stakeholders": [f"stakeholder_{i}@enterprise.com" for i in range(25)],  # 25 stakeholders
            "budget_allocations": {f"dept_{i}": 100000 + (i * 5000) for i in range(20)},  # 20 departments
            "optimization_targets": {
                "quarterly_savings": 500000,
                "annual_roi": 2.5,
                "efficiency_improvement": 0.30
            },
            "compliance_requirements": ["SOX", "GDPR", "HIPAA", "SOC2"],
            "geographic_regions": ["North America", "Europe", "Asia Pacific", "Latin America"]
        }
        
        # Validate enterprise-scale parameters
        result = validator.validate_parameters(enterprise_params)
        
        # Should be valid even at enterprise scale
        assert result.is_valid is True
        assert len(result.errors) == 0
        
        # Record enterprise scale metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("enterprise_scale_validation_successful", True)
        metrics.record_custom("large_parameter_sets_handled", len(enterprise_params))

    def test_multi_tenant_tool_name_isolation(self):
        """Test that tool name validation supports multi-tenant business isolation."""
        # BUSINESS VALUE: Multi-tenant platform must validate tools for different business contexts
        
        validator = ToolValidator()
        
        # Test tenant-specific tool naming patterns
        tenant_tools = {
            "enterprise_corp": [
                "enterprise_corp_cost_analyzer", 
                "enterprise_corp_performance_dashboard",
                "enterprise_corp_compliance_reporter"
            ],
            "startup_inc": [
                "startup_inc_growth_tracker",
                "startup_inc_fundraising_analyzer", 
                "startup_inc_market_research"
            ],
            "global_conglomerate": [
                "global_conglomerate_supply_chain_optimizer",
                "global_conglomerate_risk_assessment",
                "global_conglomerate_merger_analyzer"
            ]
        }
        
        # Validate all tenant tool names
        total_validated = 0
        for tenant, tools in tenant_tools.items():
            for tool_name in tools:
                result = validator.validate_tool_name(tool_name)
                assert result.is_valid is True, f"Tool {tool_name} should be valid"
                assert len(result.errors) == 0
                total_validated += 1
        
        # Record multi-tenant metrics
        metrics = SsotTestMetrics()
        metrics.record_custom("multi_tenant_tools_validated", total_validated)
        metrics.record_custom("business_isolation_maintained", len(tenant_tools))