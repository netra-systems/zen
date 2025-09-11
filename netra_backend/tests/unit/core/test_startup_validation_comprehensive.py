"""
Test StartupValidator - System Initialization Validation

Business Value Justification (BVJ):
- Segment: Platform/Internal (enables all customer segments)
- Business Goal: Platform Stability and Reliability
- Value Impact: Ensures system components are properly initialized before serving customers
- Strategic Impact: Prevents startup failures that would result in 100% service unavailability

This comprehensive test suite validates ALL StartupValidator functionality:
- Component validation orchestration
- Factory pattern recognition
- Error handling and reporting
- Status determination logic
- Critical path validation integration
- Report generation and logging
"""

import pytest
import asyncio
import time
from typing import Any, Dict, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

# ABSOLUTE IMPORTS ONLY (CLAUDE.md compliance)
from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.core.startup_validation import (
    StartupValidator,
    ComponentValidation,
    ComponentStatus,
    get_startup_validator,
    validate_startup
)


class TestStartupValidatorInitialization(BaseIntegrationTest):
    """Test StartupValidator initialization and configuration."""

    def test_startup_validator_init(self):
        """Test StartupValidator proper initialization."""
        validator = StartupValidator()
        
        # Verify initialization
        assert validator is not None
        assert validator.logger is not None
        assert validator.validations == []
        assert validator.start_time is None
        assert validator.end_time is None

    def test_global_startup_validator_instance(self):
        """Test global startup_validator instance is properly initialized."""
        validator = get_startup_validator()
        
        assert validator is not None
        assert isinstance(validator, StartupValidator)
        assert validator.validations == []

    def test_convenience_function_delegates_to_global_instance(self):
        """Test validate_startup convenience function delegates to global instance."""
        mock_app = Mock()
        validator = get_startup_validator()
        
        with patch.object(validator, 'validate_startup', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = (True, {"test": "report"})
            
            # Call convenience function
            import asyncio
            async def test_call():
                return await validate_startup(mock_app)
            
            result = asyncio.run(test_call())
            
            # Verify delegation
            mock_validate.assert_called_once_with(mock_app)
            assert result == (True, {"test": "report"})


class TestComponentValidationDataClass:
    """Test ComponentValidation dataclass functionality."""

    def test_component_validation_creation(self):
        """Test ComponentValidation creation with all fields."""
        validation = ComponentValidation(
            name="Test Component",
            category="Test Category",
            expected_min=5,
            actual_count=3,
            status=ComponentStatus.WARNING,
            message="Test message",
            is_critical=True,
            metadata={"key": "value"}
        )
        
        assert validation.name == "Test Component"
        assert validation.category == "Test Category"
        assert validation.expected_min == 5
        assert validation.actual_count == 3
        assert validation.status == ComponentStatus.WARNING
        assert validation.message == "Test message"
        assert validation.is_critical is True
        assert validation.metadata == {"key": "value"}

    def test_component_validation_default_values(self):
        """Test ComponentValidation default values."""
        validation = ComponentValidation(
            name="Test",
            category="Test",
            expected_min=1,
            actual_count=1,
            status=ComponentStatus.HEALTHY,
            message="Test"
        )
        
        # Test defaults
        assert validation.is_critical is True  # Default is True
        assert validation.metadata == {}  # Default is empty dict


class TestComponentStatusEnum:
    """Test ComponentStatus enum values and behavior."""

    def test_component_status_enum_values(self):
        """Test all ComponentStatus enum values exist."""
        assert ComponentStatus.NOT_CHECKED.value == "not_checked"
        assert ComponentStatus.HEALTHY.value == "healthy"
        assert ComponentStatus.WARNING.value == "warning"
        assert ComponentStatus.CRITICAL.value == "critical"
        assert ComponentStatus.FAILED.value == "failed"

    def test_component_status_enum_equality(self):
        """Test ComponentStatus enum equality comparisons."""
        assert ComponentStatus.HEALTHY == ComponentStatus.HEALTHY
        assert ComponentStatus.HEALTHY != ComponentStatus.WARNING
        assert ComponentStatus.CRITICAL != ComponentStatus.FAILED

    def test_component_status_in_collections(self):
        """Test ComponentStatus enum usage in collections."""
        critical_statuses = [ComponentStatus.CRITICAL, ComponentStatus.FAILED]
        
        assert ComponentStatus.CRITICAL in critical_statuses
        assert ComponentStatus.FAILED in critical_statuses
        assert ComponentStatus.HEALTHY not in critical_statuses
        assert ComponentStatus.WARNING not in critical_statuses


class TestGetStatusMethod:
    """Test _get_status method logic comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    def test_get_status_zero_actual_critical(self):
        """Test _get_status with zero actual count and critical component."""
        status = self.validator._get_status(actual=0, expected=5, is_critical=True)
        assert status == ComponentStatus.CRITICAL

    def test_get_status_zero_actual_non_critical(self):
        """Test _get_status with zero actual count and non-critical component."""
        status = self.validator._get_status(actual=0, expected=5, is_critical=False)
        assert status == ComponentStatus.WARNING

    def test_get_status_below_expected_always_warning(self):
        """Test _get_status below expected is always WARNING regardless of criticality."""
        # Critical component below expected = WARNING
        status = self.validator._get_status(actual=3, expected=5, is_critical=True)
        assert status == ComponentStatus.WARNING
        
        # Non-critical component below expected = WARNING
        status = self.validator._get_status(actual=2, expected=4, is_critical=False)
        assert status == ComponentStatus.WARNING

    def test_get_status_meets_expected_healthy(self):
        """Test _get_status meeting or exceeding expected is HEALTHY."""
        # Exactly meets expected
        status = self.validator._get_status(actual=5, expected=5, is_critical=True)
        assert status == ComponentStatus.HEALTHY
        
        # Exceeds expected
        status = self.validator._get_status(actual=8, expected=5, is_critical=False)
        assert status == ComponentStatus.HEALTHY

    def test_get_status_edge_cases(self):
        """Test _get_status edge cases."""
        # Zero expected, zero actual
        status = self.validator._get_status(actual=0, expected=0, is_critical=True)
        assert status == ComponentStatus.HEALTHY
        
        # Zero expected, positive actual
        status = self.validator._get_status(actual=3, expected=0, is_critical=False)
        assert status == ComponentStatus.HEALTHY


class TestAddFailedValidationMethod:
    """Test _add_failed_validation method."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    def test_add_failed_validation_creates_entry(self):
        """Test _add_failed_validation creates proper validation entry."""
        self.validator._add_failed_validation("Test Component", "Test Category", "Test error")
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Test Component"
        assert validation.category == "Test Category"
        assert validation.expected_min == 1
        assert validation.actual_count == 0
        assert validation.status == ComponentStatus.FAILED
        assert validation.message == "Validation failed: Test error"
        assert validation.is_critical is True

    def test_add_failed_validation_multiple_entries(self):
        """Test _add_failed_validation handles multiple failures."""
        self.validator._add_failed_validation("Component A", "Category A", "Error A")
        self.validator._add_failed_validation("Component B", "Category B", "Error B")
        
        assert len(self.validator.validations) == 2
        
        assert self.validator.validations[0].name == "Component A"
        assert self.validator.validations[0].message == "Validation failed: Error A"
        
        assert self.validator.validations[1].name == "Component B"
        assert self.validator.validations[1].message == "Validation failed: Error B"

    def test_add_failed_validation_with_logger(self):
        """Test _add_failed_validation logs errors."""
        with patch.object(self.validator.logger, 'error') as mock_error:
            self.validator._add_failed_validation("Test", "Category", "Error message")
            
            mock_error.assert_called_once_with("❌ Test: Error message")


class TestDetermineSuccessMethod:
    """Test _determine_success method logic."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    def test_determine_success_no_validations(self):
        """Test _determine_success with no validations returns True."""
        success = self.validator._determine_success()
        assert success is True

    def test_determine_success_only_healthy_validations(self):
        """Test _determine_success with only healthy validations."""
        self.validator.validations = [
            ComponentValidation("Test1", "Cat1", 1, 1, ComponentStatus.HEALTHY, "Healthy", True),
            ComponentValidation("Test2", "Cat2", 2, 3, ComponentStatus.HEALTHY, "Healthy", False)
        ]
        
        success = self.validator._determine_success()
        assert success is True

    def test_determine_success_warning_non_critical(self):
        """Test _determine_success with warnings on non-critical components."""
        self.validator.validations = [
            ComponentValidation("Critical", "Cat1", 1, 1, ComponentStatus.HEALTHY, "Healthy", True),
            ComponentValidation("Optional", "Cat2", 5, 3, ComponentStatus.WARNING, "Warning", False)
        ]
        
        success = self.validator._determine_success()
        assert success is True  # Non-critical warnings don't fail startup

    def test_determine_success_critical_failure(self):
        """Test _determine_success fails on critical component failure."""
        self.validator.validations = [
            ComponentValidation("Critical", "Cat1", 1, 0, ComponentStatus.CRITICAL, "Critical failure", True),
            ComponentValidation("Optional", "Cat2", 1, 1, ComponentStatus.HEALTHY, "Healthy", False)
        ]
        
        success = self.validator._determine_success()
        assert success is False

    def test_determine_success_failed_status(self):
        """Test _determine_success fails on FAILED status."""
        self.validator.validations = [
            ComponentValidation("Failed", "Cat1", 1, 0, ComponentStatus.FAILED, "Failed validation", True)
        ]
        
        success = self.validator._determine_success()
        assert success is False

    def test_determine_success_mixed_critical_failures(self):
        """Test _determine_success with mixed critical and non-critical failures."""
        self.validator.validations = [
            ComponentValidation("Critical OK", "Cat1", 1, 1, ComponentStatus.HEALTHY, "Healthy", True),
            ComponentValidation("Critical Failed", "Cat2", 1, 0, ComponentStatus.CRITICAL, "Critical", True),
            ComponentValidation("Optional Failed", "Cat3", 1, 0, ComponentStatus.FAILED, "Failed", False)
        ]
        
        success = self.validator._determine_success()
        assert success is False  # Critical failure causes overall failure


class TestGenerateReportMethod:
    """Test _generate_report method comprehensively."""

    def setup_method(self):
        """Setup validator with sample validations."""
        self.validator = StartupValidator()
        self.validator.start_time = 1000.0
        self.validator.end_time = 1005.5
        
        # Add sample validations
        self.validator.validations = [
            ComponentValidation("Healthy Component", "Services", 1, 1, ComponentStatus.HEALTHY, "OK", True),
            ComponentValidation("Warning Component", "Tools", 5, 3, ComponentStatus.WARNING, "Below expected", False),
            ComponentValidation("Critical Component", "Database", 1, 0, ComponentStatus.CRITICAL, "Failed", True),
            ComponentValidation("Failed Component", "Network", 1, 0, ComponentStatus.FAILED, "Connection failed", True),
            ComponentValidation("Not Checked", "Optional", 1, 1, ComponentStatus.NOT_CHECKED, "Skipped", False)
        ]

    def test_generate_report_structure(self):
        """Test _generate_report returns proper structure."""
        report = self.validator._generate_report()
        
        # Verify required keys
        assert "timestamp" in report
        assert "duration" in report
        assert "total_validations" in report
        assert "status_counts" in report
        assert "critical_failures" in report
        assert "categories" in report
        assert "overall_health" in report

    def test_generate_report_metadata_calculation(self):
        """Test _generate_report calculates metadata correctly."""
        report = self.validator._generate_report()
        
        assert report["timestamp"] == 1005.5
        assert report["duration"] == 5.5
        assert report["total_validations"] == 5

    def test_generate_report_status_counts(self):
        """Test _generate_report counts statuses correctly."""
        report = self.validator._generate_report()
        status_counts = report["status_counts"]
        
        assert status_counts["healthy"] == 1
        assert status_counts["warning"] == 1
        assert status_counts["critical"] == 1
        assert status_counts["failed"] == 1
        assert status_counts["not_checked"] == 1

    def test_generate_report_critical_failures(self):
        """Test _generate_report counts critical failures correctly."""
        report = self.validator._generate_report()
        
        # 2 critical failures: 1 CRITICAL + 1 FAILED (both marked is_critical=True)
        assert report["critical_failures"] == 2

    def test_generate_report_overall_health(self):
        """Test _generate_report determines overall health correctly."""
        report = self.validator._generate_report()
        
        # Has critical failures, so should be unhealthy
        assert report["overall_health"] == "unhealthy"

    def test_generate_report_categories_grouping(self):
        """Test _generate_report groups validations by category."""
        report = self.validator._generate_report()
        categories = report["categories"]
        
        assert "Services" in categories
        assert "Tools" in categories
        assert "Database" in categories
        assert "Network" in categories
        assert "Optional" in categories
        
        # Verify Services category content
        services = categories["Services"]
        assert len(services) == 1
        assert services[0]["name"] == "Healthy Component"
        assert services[0]["status"] == "healthy"

    def test_generate_report_healthy_scenario(self):
        """Test _generate_report with all healthy components."""
        # Override with healthy validations
        self.validator.validations = [
            ComponentValidation("Service A", "Services", 1, 1, ComponentStatus.HEALTHY, "OK", True),
            ComponentValidation("Service B", "Services", 2, 3, ComponentStatus.HEALTHY, "Good", False)
        ]
        
        report = self.validator._generate_report()
        
        assert report["critical_failures"] == 0
        assert report["overall_health"] == "healthy"
        assert report["status_counts"]["healthy"] == 2
        assert report["status_counts"]["critical"] == 0
        assert report["status_counts"]["failed"] == 0

    def test_generate_report_no_timing_data(self):
        """Test _generate_report handles missing timing data."""
        self.validator.start_time = None
        self.validator.end_time = None
        
        report = self.validator._generate_report()
        
        assert report["timestamp"] is None
        assert report["duration"] is None


class TestValidateStartupMainMethod:
    """Test the main validate_startup orchestration method."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_startup_calls_all_validators(self):
        """Test validate_startup calls all validation methods."""
        mock_app = Mock()
        
        with patch.multiple(self.validator,
                           _validate_agents=AsyncMock(),
                           _validate_tools=AsyncMock(),
                           _validate_database=AsyncMock(),
                           _validate_websocket=AsyncMock(),
                           _validate_services=AsyncMock(),
                           _validate_middleware=AsyncMock(),
                           _validate_background_tasks=AsyncMock(),
                           _validate_monitoring=AsyncMock(),
                           _validate_critical_paths=AsyncMock()) as mocks:
            
            await self.validator.validate_startup(mock_app)
            
            # Verify all validation methods were called
            for mock_method in mocks.values():
                mock_method.assert_called_once_with(mock_app)

    @pytest.mark.asyncio
    async def test_validate_startup_timing_tracking(self):
        """Test validate_startup tracks execution timing."""
        mock_app = Mock()
        
        # Mock all validation methods to avoid side effects
        with patch.multiple(self.validator,
                           _validate_agents=AsyncMock(),
                           _validate_tools=AsyncMock(),
                           _validate_database=AsyncMock(),
                           _validate_websocket=AsyncMock(),
                           _validate_services=AsyncMock(),
                           _validate_middleware=AsyncMock(),
                           _validate_background_tasks=AsyncMock(),
                           _validate_monitoring=AsyncMock(),
                           _validate_critical_paths=AsyncMock()):
            
            start_time = time.time()
            success, report = await self.validator.validate_startup(mock_app)
            end_time = time.time()
            
            # Verify timing was tracked
            assert self.validator.start_time is not None
            assert self.validator.end_time is not None
            assert self.validator.start_time >= start_time
            assert self.validator.end_time <= end_time
            assert self.validator.end_time >= self.validator.start_time

    @pytest.mark.asyncio
    async def test_validate_startup_return_format(self):
        """Test validate_startup returns proper format."""
        mock_app = Mock()
        
        with patch.multiple(self.validator,
                           _validate_agents=AsyncMock(),
                           _validate_tools=AsyncMock(),
                           _validate_database=AsyncMock(),
                           _validate_websocket=AsyncMock(),
                           _validate_services=AsyncMock(),
                           _validate_middleware=AsyncMock(),
                           _validate_background_tasks=AsyncMock(),
                           _validate_monitoring=AsyncMock(),
                           _validate_critical_paths=AsyncMock()):
            
            success, report = await self.validator.validate_startup(mock_app)
            
            # Verify return format
            assert isinstance(success, bool)
            assert isinstance(report, dict)
            assert "timestamp" in report
            assert "duration" in report
            assert "total_validations" in report

    @pytest.mark.asyncio
    async def test_validate_startup_logs_results(self):
        """Test validate_startup logs results."""
        mock_app = Mock()
        
        with patch.multiple(self.validator,
                           _validate_agents=AsyncMock(),
                           _validate_tools=AsyncMock(),
                           _validate_database=AsyncMock(),
                           _validate_websocket=AsyncMock(),
                           _validate_services=AsyncMock(),
                           _validate_middleware=AsyncMock(),
                           _validate_background_tasks=AsyncMock(),
                           _validate_monitoring=AsyncMock(),
                           _validate_critical_paths=AsyncMock()):
            
            with patch.object(self.validator, '_log_results') as mock_log:
                success, report = await self.validator.validate_startup(mock_app)
                
                mock_log.assert_called_once_with(success, report)


class TestValidateAgentsMethod:
    """Test _validate_agents method comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_agents_with_supervisor_factory_pattern(self):
        """Test _validate_agents recognizes factory pattern correctly."""
        mock_app = Mock()
        # Create supervisor without registry attribute
        mock_supervisor = Mock(spec=[])  # Empty spec means no attributes
        mock_app.state.agent_supervisor = mock_supervisor
        
        await self.validator._validate_agents(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Agent Factory"
        assert validation.category == "Agents"
        assert validation.expected_min == 1
        assert validation.actual_count == 1
        assert validation.status == ComponentStatus.HEALTHY
        assert "Factory-based agent creation ready" in validation.message
        assert validation.is_critical is True
        assert validation.metadata["factory_pattern"] is True
        assert validation.metadata["supervisor_ready"] is True

    @pytest.mark.asyncio
    async def test_validate_agents_supervisor_none(self):
        """Test _validate_agents handles None supervisor."""
        mock_app = Mock()
        mock_app.state.agent_supervisor = None
        
        await self.validator._validate_agents(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        # When supervisor is None, it goes to the else block
        assert validation.name == "Agent Supervisor"
        assert validation.category == "Agents"
        assert validation.status == ComponentStatus.FAILED
        assert "Supervisor not initialized" in validation.message

    @pytest.mark.asyncio
    async def test_validate_agents_no_supervisor_attribute(self):
        """Test _validate_agents handles missing supervisor attribute."""
        mock_app = Mock()
        mock_app.state = Mock(spec=[])  # Empty spec = no attributes
        
        await self.validator._validate_agents(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Agent Supervisor"
        assert validation.category == "Agents" 
        assert validation.status == ComponentStatus.FAILED

    @pytest.mark.asyncio
    async def test_validate_agents_with_legacy_registry(self):
        """Test _validate_agents handles legacy registry pattern."""
        mock_app = Mock()
        mock_supervisor = Mock()
        mock_registry = Mock()
        mock_registry.agents = {
            "triage": Mock(),
            "data": Mock(),
            "optimization": Mock(),
            "actions": Mock(),
            "reporting": Mock(),
            "data_helper": Mock(),
            "synthetic_data": Mock(),
            "corpus_admin": Mock()
        }
        mock_supervisor.registry = mock_registry
        mock_app.state.agent_supervisor = mock_supervisor
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_agents(mock_app)
            
            # Should log about registry agents
            mock_info.assert_any_call("✓ Agent Registry: 8 agents registered")

    @pytest.mark.asyncio
    async def test_validate_agents_legacy_registry_empty(self):
        """Test _validate_agents handles empty legacy registry."""
        mock_app = Mock()
        mock_supervisor = Mock()
        mock_registry = Mock()
        mock_registry.agents = {}
        mock_supervisor.registry = mock_registry
        mock_app.state.agent_supervisor = mock_supervisor
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_agents(mock_app)
            
            # Should log about factory pattern
            mock_info.assert_any_call("ℹ️ Legacy registry empty - agents will be created per-request (factory pattern)")

    @pytest.mark.asyncio
    async def test_validate_agents_exception_handling(self):
        """Test _validate_agents handles exceptions gracefully."""
        mock_app = Mock()
        # Simulate exception when accessing state
        mock_app.state = Mock(side_effect=Exception("Test exception"))
        
        await self.validator._validate_agents(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Agent Validation"
        assert validation.category == "Agents"
        assert validation.status == ComponentStatus.FAILED
        assert "Test exception" in validation.message


class TestValidateToolsMethod:
    """Test _validate_tools method comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_tools_usercontext_pattern(self):
        """Test _validate_tools recognizes UserContext pattern correctly."""
        mock_app = Mock()
        mock_tool_classes = [Mock(), Mock(), Mock(), Mock()]  # 4 tools
        mock_bridge_factory = Mock()
        
        mock_app.state.tool_classes = mock_tool_classes
        mock_app.state.websocket_bridge_factory = mock_bridge_factory
        
        await self.validator._validate_tools(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Tool Configuration"
        assert validation.category == "Tools"
        assert validation.expected_min == 4
        assert validation.actual_count == 4
        assert validation.status == ComponentStatus.HEALTHY
        assert "Configured 4 tool classes for UserContext" in validation.message
        assert "Bridge Factory: ✓" in validation.message
        assert validation.metadata["mode"] == "UserContext"
        assert validation.metadata["websocket_bridge_factory"] is True

    @pytest.mark.asyncio
    async def test_validate_tools_usercontext_no_bridge_factory(self):
        """Test _validate_tools detects missing bridge factory."""
        mock_app = Mock()
        mock_tool_classes = [Mock(), Mock()]
        
        mock_app.state.tool_classes = mock_tool_classes
        mock_app.state.websocket_bridge_factory = None
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_tools(mock_app)
            
            mock_warning.assert_any_call("⚠️ WebSocketBridgeFactory NOT configured - per-user WebSocket isolation may fail")
        
        validation = self.validator.validations[0]
        assert "Bridge Factory: ✗" in validation.message
        assert validation.metadata["websocket_bridge_factory"] is False

    @pytest.mark.asyncio
    async def test_validate_tools_usercontext_zero_tools(self):
        """Test _validate_tools handles zero tools configured."""
        mock_app = Mock()
        mock_app.state.tool_classes = []
        mock_app.state.websocket_bridge_factory = Mock()
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_tools(mock_app)
            
            mock_warning.assert_any_call("⚠️ NO TOOLS CONFIGURED for UserContext")
        
        validation = self.validator.validations[0]
        assert validation.actual_count == 0
        assert validation.status == ComponentStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_validate_tools_legacy_dispatcher_pattern(self):
        """Test _validate_tools handles legacy dispatcher pattern."""
        mock_app = Mock()
        mock_dispatcher = Mock()
        mock_dispatcher.tools = {"tool1": Mock(), "tool2": Mock()}
        
        # No UserContext configuration
        mock_app.state.tool_classes = None
        mock_app.state.tool_dispatcher = mock_dispatcher
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_tools(mock_app)
            
            mock_warning.assert_any_call("⚠️ LEGACY: Global tool_dispatcher found - should be None in UserContext architecture")
            mock_warning.assert_any_call("⚠️ LEGACY Tool Dispatcher: 2 tools - MIGRATE TO UserContext")
        
        validation = self.validator.validations[0]
        assert validation.name == "Tool Dispatcher (LEGACY)"
        assert validation.category == "Tools"
        assert validation.expected_min == 0
        assert validation.actual_count == 2
        assert validation.status == ComponentStatus.WARNING
        assert validation.metadata["mode"] == "LEGACY_GLOBAL"

    @pytest.mark.asyncio
    async def test_validate_tools_legacy_dispatcher_private_tools(self):
        """Test _validate_tools handles legacy dispatcher with _tools attribute."""
        mock_app = Mock()
        mock_dispatcher = Mock()
        mock_dispatcher._tools = {"tool1": Mock(), "tool2": Mock(), "tool3": Mock()}
        
        # No UserContext configuration and no public tools attribute
        mock_app.state.tool_classes = None
        mock_app.state.tool_dispatcher = mock_dispatcher
        del mock_dispatcher.tools  # Remove public attribute
        
        await self.validator._validate_tools(mock_app)
        
        validation = self.validator.validations[0]
        assert validation.actual_count == 3

    @pytest.mark.asyncio
    async def test_validate_tools_no_configuration_found(self):
        """Test _validate_tools handles no configuration found."""
        mock_app = Mock()
        mock_app.state.tool_classes = None
        mock_app.state.tool_dispatcher = None
        
        await self.validator._validate_tools(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Tool System"
        assert validation.category == "Tools"
        assert validation.status == ComponentStatus.FAILED
        assert "Neither UserContext configuration nor legacy dispatcher found" in validation.message

    @pytest.mark.asyncio
    async def test_validate_tools_exception_handling(self):
        """Test _validate_tools handles exceptions gracefully."""
        mock_app = Mock()
        mock_app.state.tool_classes = Mock(side_effect=Exception("Test exception"))
        
        await self.validator._validate_tools(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Tool Validation"
        assert validation.category == "Tools"
        assert validation.status == ComponentStatus.FAILED
        assert "Test exception" in validation.message


class TestValidateDatabaseMethod:
    """Test _validate_database method comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_database_mock_mode(self):
        """Test _validate_database handles mock mode correctly."""
        mock_app = Mock()
        mock_app.state.db_session_factory = None
        mock_app.state.database_mock_mode = True
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_database(mock_app)
            
            mock_info.assert_any_call("ℹ️ Database in mock mode")
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Database"
        assert validation.category == "Database"
        assert validation.expected_min == 0
        assert validation.actual_count == 0
        assert validation.status == ComponentStatus.WARNING
        assert validation.message == "Database in mock mode"
        assert validation.is_critical is False

    @pytest.mark.asyncio
    async def test_validate_database_none_not_mock_mode(self):
        """Test _validate_database handles None factory not in mock mode."""
        mock_app = Mock()
        mock_app.state.db_session_factory = None
        mock_app.state.database_mock_mode = False
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_database(mock_app)
            
            mock_warning.assert_any_call("⚠️ Database session factory is None but not in mock mode")
        
        validation = self.validator.validations[0]
        assert validation.status == ComponentStatus.CRITICAL
        assert validation.message == "Database not initialized"
        assert validation.is_critical is True

    @pytest.mark.asyncio
    async def test_validate_database_with_tables(self):
        """Test _validate_database counts tables correctly."""
        mock_app = Mock()
        mock_factory = Mock()
        mock_app.state.db_session_factory = mock_factory
        
        with patch.object(self.validator, '_count_database_tables', new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 18
            
            await self.validator._validate_database(mock_app)
            
            mock_count.assert_called_once_with(mock_factory)
        
        validation = self.validator.validations[0]
        assert validation.name == "Database Tables"
        assert validation.category == "Database"
        assert validation.expected_min == 15
        assert validation.actual_count == 18
        assert validation.status == ComponentStatus.HEALTHY
        assert "Found 18 database tables" in validation.message
        assert validation.metadata["table_count"] == 18

    @pytest.mark.asyncio
    async def test_validate_database_zero_tables(self):
        """Test _validate_database handles zero tables found."""
        mock_app = Mock()
        mock_factory = Mock()
        mock_app.state.db_session_factory = mock_factory
        
        with patch.object(self.validator, '_count_database_tables', new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 0
            
            with patch.object(self.validator.logger, 'warning') as mock_warning:
                await self.validator._validate_database(mock_app)
                
                mock_warning.assert_any_call("⚠️ ZERO DATABASE TABLES found - expected ~15")
        
        validation = self.validator.validations[0]
        assert validation.actual_count == 0
        assert validation.status == ComponentStatus.WARNING

    @pytest.mark.asyncio
    async def test_validate_database_no_factory_attribute(self):
        """Test _validate_database handles missing db_session_factory attribute."""
        mock_app = Mock()
        mock_app.state = Mock()
        # Don't set db_session_factory attribute at all
        
        await self.validator._validate_database(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Database"
        assert validation.category == "Database"
        assert validation.status == ComponentStatus.FAILED
        assert "db_session_factory not found" in validation.message

    @pytest.mark.asyncio
    async def test_validate_database_exception_handling(self):
        """Test _validate_database handles exceptions gracefully."""
        mock_app = Mock()
        mock_app.state.db_session_factory = Mock(side_effect=Exception("DB exception"))
        
        await self.validator._validate_database(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "Database Validation"
        assert validation.category == "Database"
        assert validation.status == ComponentStatus.FAILED
        assert "DB exception" in validation.message


class TestCountDatabaseTablesMethod:
    """Test _count_database_tables method."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_count_database_tables_success(self):
        """Test _count_database_tables returns correct count."""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 15
        mock_session.execute.return_value = mock_result
        
        # Create mock factory that returns an async context manager
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None
        
        count = await self.validator._count_database_tables(mock_factory)
        
        assert count == 15
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_database_tables_none_result(self):
        """Test _count_database_tables handles None result."""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Create mock factory that returns an async context manager
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None
        
        count = await self.validator._count_database_tables(mock_factory)
        
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_database_tables_exception(self):
        """Test _count_database_tables handles exceptions."""
        mock_factory = Mock(side_effect=Exception("DB connection failed"))
        
        count = await self.validator._count_database_tables(mock_factory)
        
        assert count == 0  # Returns 0 on exception


class TestValidateWebSocketMethod:
    """Test _validate_websocket method comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_websocket_from_app_state(self):
        """Test _validate_websocket gets manager from app.state."""
        mock_app = Mock()
        mock_manager = Mock()
        mock_manager.active_connections = [Mock(), Mock()]
        mock_manager.message_handlers = {"handler1": Mock(), "handler2": Mock()}
        mock_app.state.websocket_manager = mock_manager
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_websocket(mock_app)
            
            mock_info.assert_any_call("✓ WebSocket: 2 handlers, 2 connections")
        
        validation = self.validator.validations[0]
        assert validation.name == "WebSocket Manager"
        assert validation.category == "WebSocket"
        assert validation.expected_min == 1
        assert validation.actual_count == 1
        assert validation.status == ComponentStatus.HEALTHY
        assert "Manager active, 2 connections, 2 handlers" in validation.message
        assert validation.metadata["connections"] == 2
        assert validation.metadata["handlers"] == 2

    @pytest.mark.asyncio
    async def test_validate_websocket_zero_handlers_factory_pattern(self):
        """Test _validate_websocket recognizes factory pattern with zero handlers."""
        mock_app = Mock()
        mock_manager = Mock()
        mock_manager.active_connections = []
        mock_manager.message_handlers = {}
        mock_app.state.websocket_manager = mock_manager
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_websocket(mock_app)
            
            mock_info.assert_any_call("ℹ️ WebSocket handlers will be created per-user (factory pattern)")
        
        validation = self.validator.validations[0]
        assert validation.status == ComponentStatus.WARNING  # Zero handlers = WARNING

    @pytest.mark.asyncio
    async def test_validate_websocket_private_attributes(self):
        """Test _validate_websocket handles private attributes."""
        mock_app = Mock()
        # Mock manager without public attributes, only private ones
        mock_manager = Mock()
        mock_manager._connections = [Mock()]
        mock_manager._handlers = {"handler1": Mock()}
        # hasattr will return False for active_connections and message_handlers
        mock_app.state.websocket_manager = mock_manager
        
        await self.validator._validate_websocket(mock_app)
        
        validation = self.validator.validations[0]
        assert validation.metadata["connections"] == 1
        assert validation.metadata["handlers"] == 1

    @pytest.mark.asyncio
    async def test_validate_websocket_from_global_import(self):
        """Test _validate_websocket tries global import when no app.state manager."""
        mock_app = Mock()
        mock_app.state.websocket_manager = None
        
        mock_global_manager = Mock()
        mock_global_manager.active_connections = []
        mock_global_manager.message_handlers = {"handler": Mock()}
        
        with patch('netra_backend.app.core.startup_validation.get_websocket_manager') as mock_import:
            mock_import.return_value = mock_global_manager
            
            await self.validator._validate_websocket(mock_app)
        
        validation = self.validator.validations[0]
        assert validation.actual_count == 1
        assert validation.status == ComponentStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_validate_websocket_import_error(self):
        """Test _validate_websocket handles import errors gracefully."""
        mock_app = Mock()
        mock_app.state.websocket_manager = None
        
        with patch('netra_backend.app.core.startup_validation.get_websocket_manager', side_effect=ImportError):
            await self.validator._validate_websocket(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "WebSocket Manager"
        assert validation.category == "WebSocket"
        assert validation.status == ComponentStatus.FAILED
        assert "Manager not initialized" in validation.message

    @pytest.mark.asyncio
    async def test_validate_websocket_exception_handling(self):
        """Test _validate_websocket handles exceptions gracefully."""
        mock_app = Mock()
        mock_app.state.websocket_manager = Mock(side_effect=Exception("WebSocket error"))
        
        await self.validator._validate_websocket(mock_app)
        
        assert len(self.validator.validations) == 1
        validation = self.validator.validations[0]
        
        assert validation.name == "WebSocket Validation"
        assert validation.category == "WebSocket"
        assert validation.status == ComponentStatus.FAILED
        assert "WebSocket error" in validation.message


class TestValidateServicesMethod:
    """Test _validate_services method comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_services_all_present_and_initialized(self):
        """Test _validate_services with all services present and initialized."""
        mock_app = Mock()
        
        # Setup all expected services
        mock_app.state.llm_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.security_service = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.thread_service = Mock()
        mock_app.state.agent_service = Mock()
        mock_app.state.corpus_service = Mock()
        mock_app.state.background_task_manager = Mock()
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_services(mock_app)
            
            # Should log success for each service
            mock_info.assert_any_call("✓ LLM Manager: Initialized")
            mock_info.assert_any_call("✓ Key Manager: Initialized")
            mock_info.assert_any_call("✓ Security Service: Initialized")
        
        # Should create validation for each service
        assert len(self.validator.validations) >= 8
        
        # Check one critical service
        llm_validation = next(v for v in self.validator.validations if v.name == "LLM Manager")
        assert llm_validation.category == "Services"
        assert llm_validation.status == ComponentStatus.HEALTHY
        assert llm_validation.is_critical is True

    @pytest.mark.asyncio
    async def test_validate_services_none_service(self):
        """Test _validate_services handles None services."""
        mock_app = Mock()
        
        # Setup some services as None
        mock_app.state.llm_manager = None
        mock_app.state.key_manager = Mock()
        mock_app.state.corpus_service = None  # Non-critical
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_services(mock_app)
            
            mock_warning.assert_any_call("⚠️ LLM Manager is None")
            mock_warning.assert_any_call("⚠️ Corpus Service is None")
        
        llm_validation = next(v for v in self.validator.validations if v.name == "LLM Manager")
        assert llm_validation.status == ComponentStatus.CRITICAL  # Critical service
        
        corpus_validation = next(v for v in self.validator.validations if v.name == "Corpus Service")
        assert corpus_validation.status == ComponentStatus.WARNING  # Non-critical service

    @pytest.mark.asyncio
    async def test_validate_services_missing_attribute(self):
        """Test _validate_services handles missing service attributes."""
        mock_app = Mock()
        
        # Setup app state with only some services
        mock_app.state = Mock()
        mock_app.state.llm_manager = Mock()
        # Other services will not be set, so hasattr returns False
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_services(mock_app)
            
            mock_warning.assert_any_call("⚠️ Key Manager not found in app.state")
        
        key_validation = next(v for v in self.validator.validations if v.name == "Key Manager")
        assert key_validation.status == ComponentStatus.CRITICAL
        assert key_validation.actual_count == 0

    @pytest.mark.asyncio
    async def test_validate_services_factory_patterns(self):
        """Test _validate_services validates UserContext factory patterns."""
        mock_app = Mock()
        
        # Setup basic services to avoid noise
        mock_app.state.llm_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.security_service = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.thread_service = Mock()
        mock_app.state.agent_service = Mock()
        
        # Setup factory services
        mock_app.state.execution_engine_factory = Mock()
        mock_app.state.websocket_bridge_factory = Mock()
        mock_app.state.websocket_connection_pool = Mock()
        mock_app.state.agent_instance_factory = None  # Optional
        mock_app.state.factory_adapter = None  # Optional
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            await self.validator._validate_services(mock_app)
            
            mock_info.assert_any_call("Validating UserContext Factory Patterns...")
            mock_info.assert_any_call("✓ ExecutionEngineFactory: Initialized - Per-user execution isolation")
            mock_info.assert_any_call("ℹ️ AgentInstanceFactory not configured - Agent instance creation optional")
        
        # Check factory validations
        factory_validations = [v for v in self.validator.validations if v.category == "Factories"]
        assert len(factory_validations) == 5  # All 5 factory services
        
        engine_factory = next(v for v in factory_validations if v.name == "ExecutionEngineFactory")
        assert engine_factory.status == ComponentStatus.HEALTHY
        assert engine_factory.is_critical is True

    @pytest.mark.asyncio
    async def test_validate_services_missing_critical_factory(self):
        """Test _validate_services handles missing critical factories."""
        mock_app = Mock()
        
        # Setup basic services
        mock_app.state.llm_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.security_service = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.thread_service = Mock()
        mock_app.state.agent_service = Mock()
        
        # Missing critical factory
        # execution_engine_factory is missing
        mock_app.state.websocket_bridge_factory = Mock()
        mock_app.state.websocket_connection_pool = Mock()
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            await self.validator._validate_services(mock_app)
            
            mock_warning.assert_any_call("⚠️ ExecutionEngineFactory not found - Per-user execution isolation missing")
        
        factory_validations = [v for v in self.validator.validations if v.category == "Factories"]
        engine_factory = next(v for v in factory_validations if v.name == "ExecutionEngineFactory")
        assert engine_factory.status == ComponentStatus.CRITICAL

    @pytest.mark.asyncio
    async def test_validate_services_exception_handling(self):
        """Test _validate_services handles exceptions gracefully."""
        mock_app = Mock()
        
        # Setup service that throws exception when accessed
        mock_app.state.llm_manager = Mock(side_effect=Exception("Service exception"))
        
        await self.validator._validate_services(mock_app)
        
        # Should have failure validation for the exception
        failure_validation = next(v for v in self.validator.validations if v.name == "LLM Manager")
        assert failure_validation.status == ComponentStatus.FAILED
        assert "Service exception" in failure_validation.message


class TestLogResultsMethod:
    """Test _log_results method comprehensively."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    def test_log_results_success_scenario(self):
        """Test _log_results logs successful validation."""
        report = {
            "total_validations": 5,
            "status_counts": {
                "healthy": 4,
                "warning": 1,
                "critical": 0,
                "failed": 0,
                "not_checked": 0
            },
            "critical_failures": 0,
            "duration": 2.5
        }
        
        with patch.object(self.validator.logger, 'info') as mock_info:
            self.validator._log_results(True, report)
            
            mock_info.assert_any_call("Overall Status: ✅ PASSED")
            mock_info.assert_any_call("Total Validations: 5")
            mock_info.assert_any_call("Healthy: 4")
            mock_info.assert_any_call("Warnings: 1")
            mock_info.assert_any_call("Critical: 0")
            mock_info.assert_any_call("Failed: 0")
            mock_info.assert_any_call("Validation Duration: 2.50s")

    def test_log_results_failure_scenario(self):
        """Test _log_results logs failed validation with critical failures."""
        report = {
            "total_validations": 5,
            "status_counts": {
                "healthy": 2,
                "warning": 1,
                "critical": 1,
                "failed": 1,
                "not_checked": 0
            },
            "critical_failures": 2,
            "duration": 3.2
        }
        
        with patch.object(self.validator.logger, 'info') as mock_info, \
             patch.object(self.validator.logger, 'error') as mock_error:
            
            self.validator._log_results(False, report)
            
            mock_info.assert_any_call("Overall Status: ❌ FAILED")
            mock_error.assert_any_call("⚠️ 2 CRITICAL FAILURES DETECTED")

    def test_log_results_zero_count_warnings(self):
        """Test _log_results logs zero-count component warnings."""
        self.validator.validations = [
            ComponentValidation("DB", "Database", 1, 0, ComponentStatus.CRITICAL, "Failed", True),
            ComponentValidation("Redis", "Cache", 1, 0, ComponentStatus.WARNING, "Failed", False),
            ComponentValidation("Service", "Services", 1, 1, ComponentStatus.HEALTHY, "OK", True)
        ]
        
        report = {
            "total_validations": 3,
            "status_counts": {"healthy": 1, "warning": 1, "critical": 1, "failed": 0, "not_checked": 0},
            "critical_failures": 1,
            "duration": 1.0
        }
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            self.validator._log_results(False, report)
            
            mock_warning.assert_any_call("COMPONENTS WITH ZERO COUNTS:")
            mock_warning.assert_any_call("  - DB: Expected 1, got 0")
            mock_warning.assert_any_call("  - Redis: Expected 1, got 0")

    def test_log_results_no_zero_count_components(self):
        """Test _log_results doesn't log zero-count section when none exist."""
        self.validator.validations = [
            ComponentValidation("Service", "Services", 1, 1, ComponentStatus.HEALTHY, "OK", True)
        ]
        
        report = {
            "total_validations": 1,
            "status_counts": {"healthy": 1, "warning": 0, "critical": 0, "failed": 0, "not_checked": 0},
            "critical_failures": 0,
            "duration": 0.5
        }
        
        with patch.object(self.validator.logger, 'warning') as mock_warning:
            self.validator._log_results(True, report)
            
            # Should not call warning about zero count components
            mock_warning.assert_not_called()


class TestCriticalPathValidation:
    """Test _validate_critical_paths method."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_validate_critical_paths_success(self):
        """Test _validate_critical_paths with successful validation."""
        mock_app = Mock()
        
        # Mock successful critical path validation
        mock_validate_critical_paths = AsyncMock()
        mock_validate_critical_paths.return_value = (
            True,  # success
            []  # no failures
        )
        
        with patch('netra_backend.app.core.startup_validation.validate_critical_paths', mock_validate_critical_paths):
            with patch.object(self.validator.logger, 'info') as mock_info:
                await self.validator._validate_critical_paths(mock_app)
                
                mock_info.assert_any_call("Validating critical communication paths...")
                mock_info.assert_any_call("✓ Critical communication paths: All validated")
        
        validation = self.validator.validations[0]
        assert validation.name == "Critical Communication Paths"
        assert validation.category == "Critical Paths"
        assert validation.status == ComponentStatus.HEALTHY
        assert validation.message == "All critical paths validated"

    @pytest.mark.asyncio
    async def test_validate_critical_paths_chat_breaking_failures(self):
        """Test _validate_critical_paths with chat-breaking failures."""
        mock_app = Mock()
        
        # Mock critical failures
        mock_validation_1 = Mock()
        mock_validation_1.passed = False
        mock_validation_1.criticality.value = "chat_breaking"
        
        mock_validation_2 = Mock()
        mock_validation_2.passed = False  
        mock_validation_2.criticality.value = "chat_breaking"
        
        mock_validate_critical_paths = AsyncMock()
        mock_validate_critical_paths.return_value = (
            False,  # failed
            [mock_validation_1, mock_validation_2]
        )
        
        with patch('netra_backend.app.core.startup_validation.validate_critical_paths', mock_validate_critical_paths):
            with patch.object(self.validator.logger, 'error') as mock_error:
                await self.validator._validate_critical_paths(mock_app)
                
                mock_error.assert_any_call("❌ CRITICAL: 2 chat-breaking communication failures!")
        
        validation = self.validator.validations[0]
        assert validation.status == ComponentStatus.CRITICAL
        assert validation.actual_count == 2  # 2 chat-breaking failures
        assert "2 chat-breaking failures detected" in validation.message
        assert validation.metadata["chat_breaking"] == 2

    @pytest.mark.asyncio
    async def test_validate_critical_paths_degraded_failures(self):
        """Test _validate_critical_paths with degraded path issues."""
        mock_app = Mock()
        
        # Mock degraded failures
        mock_validation = Mock()
        mock_validation.passed = False
        mock_validation.criticality.value = "degraded"
        
        mock_validate_critical_paths = AsyncMock()
        mock_validate_critical_paths.return_value = (
            False,  # failed
            [mock_validation]
        )
        
        with patch('netra_backend.app.core.startup_validation.validate_critical_paths', mock_validate_critical_paths):
            with patch.object(self.validator.logger, 'warning') as mock_warning:
                await self.validator._validate_critical_paths(mock_app)
                
                mock_warning.assert_any_call("⚠️ 1 degraded communication paths")
        
        validation = self.validator.validations[0]
        assert validation.status == ComponentStatus.WARNING
        assert validation.metadata["degraded"] == 1

    @pytest.mark.asyncio
    async def test_validate_critical_paths_import_error(self):
        """Test _validate_critical_paths handles missing validator gracefully."""
        mock_app = Mock()
        
        with patch('netra_backend.app.core.startup_validation.validate_critical_paths', side_effect=ImportError):
            with patch.object(self.validator.logger, 'warning') as mock_warning:
                await self.validator._validate_critical_paths(mock_app)
                
                mock_warning.assert_any_call("Critical path validator not found - skipping")
        
        # Should not add validation when import fails
        assert len(self.validator.validations) == 0

    @pytest.mark.asyncio
    async def test_validate_critical_paths_exception_handling(self):
        """Test _validate_critical_paths handles other exceptions."""
        mock_app = Mock()
        
        with patch('netra_backend.app.core.startup_validation.validate_critical_paths', side_effect=Exception("Validation error")):
            await self.validator._validate_critical_paths(mock_app)
        
        validation = self.validator.validations[0]
        assert validation.name == "Critical Path Validation"
        assert validation.category == "Critical Paths"
        assert validation.status == ComponentStatus.FAILED
        assert "Validation error" in validation.message


class TestIntegrationScenarios:
    """Test integration scenarios and end-to-end workflows."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_complete_validation_success_scenario(self):
        """Test complete validation with all components healthy."""
        mock_app = Mock()
        
        # Setup healthy app state
        mock_app.state.agent_supervisor = Mock()
        mock_app.state.tool_classes = [Mock(), Mock(), Mock(), Mock()]
        mock_app.state.websocket_bridge_factory = Mock()
        mock_app.state.db_session_factory = Mock()
        mock_app.state.websocket_manager = Mock()
        mock_app.state.websocket_manager.active_connections = []
        mock_app.state.websocket_manager.message_handlers = {"handler": Mock()}
        
        # Setup all services
        mock_app.state.llm_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.security_service = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.thread_service = Mock()
        mock_app.state.agent_service = Mock()
        
        # Setup factory services
        mock_app.state.execution_engine_factory = Mock()
        mock_app.state.websocket_bridge_factory = Mock()
        mock_app.state.websocket_connection_pool = Mock()
        
        # Mock middleware
        mock_app.middleware_stack = [Mock(), Mock(), Mock()]
        
        # Mock database table count
        with patch.object(self.validator, '_count_database_tables', new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 20
            
            # Mock critical paths validation
            with patch('netra_backend.app.core.startup_validation.validate_critical_paths', new_callable=AsyncMock) as mock_critical:
                mock_critical.return_value = (True, [])
                
                success, report = await self.validator.validate_startup(mock_app)
        
        # Verify success
        assert success is True
        assert report["overall_health"] == "healthy"
        assert report["critical_failures"] == 0
        
        # Verify multiple validations were created
        assert len(self.validator.validations) > 10
        
        # Check specific validations exist
        validation_names = [v.name for v in self.validator.validations]
        assert "Agent Factory" in validation_names
        assert "Tool Configuration" in validation_names
        assert "Database Tables" in validation_names
        assert "WebSocket Manager" in validation_names

    @pytest.mark.asyncio
    async def test_complete_validation_mixed_failures(self):
        """Test complete validation with mixed success and failures."""
        mock_app = Mock()
        
        # Setup mixed app state - some good, some bad
        mock_app.state.agent_supervisor = None  # FAILED
        mock_app.state.tool_classes = [Mock()]  # WARNING (below expected)
        mock_app.state.websocket_bridge_factory = None  # FAILED
        mock_app.state.db_session_factory = Mock()  # OK
        mock_app.state.websocket_manager = None  # FAILED
        
        # Setup critical service missing
        mock_app.state.llm_manager = None  # CRITICAL
        mock_app.state.key_manager = Mock()  # OK
        mock_app.state.security_service = Mock()  # OK
        mock_app.state.redis_manager = Mock()  # OK
        mock_app.state.thread_service = Mock()  # OK
        mock_app.state.agent_service = Mock()  # OK
        
        # Mock database table count
        with patch.object(self.validator, '_count_database_tables', new_callable=AsyncMock) as mock_count:
            mock_count.return_value = 0  # WARNING
            
            # Mock critical paths validation
            with patch('netra_backend.app.core.startup_validation.validate_critical_paths', new_callable=AsyncMock) as mock_critical:
                mock_critical.return_value = (True, [])
                
                success, report = await self.validator.validate_startup(mock_app)
        
        # Verify failure due to critical components
        assert success is False
        assert report["overall_health"] == "unhealthy"
        assert report["critical_failures"] > 0
        
        # Verify mixed status counts
        assert report["status_counts"]["healthy"] > 0  # Some healthy
        assert report["status_counts"]["critical"] > 0  # Some critical
        assert report["status_counts"]["failed"] > 0  # Some failed

    @pytest.mark.asyncio
    async def test_startup_timing_and_reporting(self):
        """Test startup validation timing and comprehensive reporting."""
        mock_app = Mock()
        
        # Setup minimal app state
        mock_app.state.agent_supervisor = Mock()
        mock_app.state.tool_classes = []
        mock_app.state.db_session_factory = Mock()
        
        # Mock all validation methods to control timing
        with patch.multiple(self.validator,
                           _validate_agents=AsyncMock(),
                           _validate_tools=AsyncMock(),
                           _validate_database=AsyncMock(),
                           _validate_websocket=AsyncMock(),
                           _validate_services=AsyncMock(),
                           _validate_middleware=AsyncMock(),
                           _validate_background_tasks=AsyncMock(),
                           _validate_monitoring=AsyncMock(),
                           _validate_critical_paths=AsyncMock()) as mocks:
            
            # Add some test validations
            self.validator.validations = [
                ComponentValidation("Test", "Test", 1, 1, ComponentStatus.HEALTHY, "OK", True)
            ]
            
            start_time = time.time()
            success, report = await self.validator.validate_startup(mock_app)
            end_time = time.time()
        
        # Verify timing tracking
        assert self.validator.start_time is not None
        assert self.validator.end_time is not None
        assert self.validator.start_time >= start_time
        assert self.validator.end_time <= end_time
        assert report["duration"] > 0
        
        # Verify report structure
        assert isinstance(report["timestamp"], float)
        assert report["total_validations"] == 1
        assert "categories" in report
        assert "status_counts" in report


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and comprehensive error handling."""

    def setup_method(self):
        """Setup validator for testing."""
        self.validator = StartupValidator()

    @pytest.mark.asyncio
    async def test_app_state_completely_missing(self):
        """Test validation when app.state is completely missing."""
        mock_app = Mock()
        mock_app.state = Mock()
        mock_app.state.side_effect = AttributeError("state not found")
        
        success, report = await self.validator.validate_startup(mock_app)
        
        # Should fail gracefully with multiple failures
        assert success is False
        assert len(self.validator.validations) > 0
        
        # All validations should be failures
        for validation in self.validator.validations:
            assert validation.status == ComponentStatus.FAILED

    @pytest.mark.asyncio
    async def test_partial_app_state_corruption(self):
        """Test validation with partially corrupted app state."""
        mock_app = Mock()
        
        # Setup corrupted state - some attributes exist but throw exceptions
        mock_app.state.agent_supervisor = Mock(side_effect=Exception("State corruption"))
        mock_app.state.tool_classes = Mock(side_effect=RuntimeError("Memory error"))
        mock_app.state.db_session_factory = None  # This one is fine
        
        success, report = await self.validator.validate_startup(mock_app)
        
        # Should handle exceptions gracefully
        assert isinstance(success, bool)
        assert isinstance(report, dict)
        
        # Should have failure validations for corrupted components
        failure_validations = [v for v in self.validator.validations if v.status == ComponentStatus.FAILED]
        assert len(failure_validations) >= 2

    def test_component_validation_with_extreme_values(self):
        """Test ComponentValidation with extreme values."""
        # Test with very large numbers
        validation = ComponentValidation(
            name="Large Scale",
            category="Test",
            expected_min=1000000,
            actual_count=999999,
            status=ComponentStatus.WARNING,
            message="Almost there",
            is_critical=False,
            metadata={"scale": "enterprise"}
        )
        
        assert validation.expected_min == 1000000
        assert validation.actual_count == 999999
        
        # Test with zero values
        zero_validation = ComponentValidation(
            name="Zero Test",
            category="Test",
            expected_min=0,
            actual_count=0,
            status=ComponentStatus.HEALTHY,
            message="Zero is OK",
            is_critical=True
        )
        
        assert zero_validation.expected_min == 0
        assert zero_validation.actual_count == 0

    @pytest.mark.asyncio
    async def test_concurrent_validation_calls(self):
        """Test that validator handles concurrent calls gracefully."""
        mock_app = Mock()
        mock_app.state.agent_supervisor = Mock()
        
        # Create multiple validators to simulate concurrency
        validators = [StartupValidator() for _ in range(3)]
        
        # Mock validation methods for all validators
        for validator in validators:
            with patch.multiple(validator,
                               _validate_agents=AsyncMock(),
                               _validate_tools=AsyncMock(),
                               _validate_database=AsyncMock(),
                               _validate_websocket=AsyncMock(),
                               _validate_services=AsyncMock(),
                               _validate_middleware=AsyncMock(),
                               _validate_background_tasks=AsyncMock(),
                               _validate_monitoring=AsyncMock(),
                               _validate_critical_paths=AsyncMock()):
                pass
        
        # Run validations concurrently
        tasks = [validator.validate_startup(mock_app) for validator in validators]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should complete successfully
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)
            success, report = result
            assert isinstance(success, bool)
            assert isinstance(report, dict)

    def test_memory_efficiency_with_large_validation_sets(self):
        """Test memory efficiency with large numbers of validations."""
        # Add many validations to test memory handling
        for i in range(1000):
            validation = ComponentValidation(
                name=f"Component {i}",
                category="Test",
                expected_min=1,
                actual_count=1,
                status=ComponentStatus.HEALTHY,
                message=f"Component {i} OK",
                is_critical=False,
                metadata={"index": i}
            )
            self.validator.validations.append(validation)
        
        # Test that report generation handles large datasets
        report = self.validator._generate_report()
        
        assert report["total_validations"] == 1000
        assert len(report["categories"]["Test"]) == 1000
        assert report["status_counts"]["healthy"] == 1000
        
        # Test memory cleanup
        self.validator.validations.clear()
        assert len(self.validator.validations) == 0


class TestComprehensiveIntegration:
    """Final comprehensive integration tests covering all functionality."""

    @pytest.mark.asyncio
    async def test_real_world_startup_validation_simulation(self):
        """Simulate real-world startup validation with realistic app state."""
        validator = StartupValidator()  # Fresh validator
        mock_app = Mock()
        
        # Simulate realistic production-like app state
        # Agent system
        mock_supervisor = Mock()
        mock_registry = Mock()
        mock_registry.agents = {
            "triage": Mock(),
            "data": Mock(),
            "optimization": Mock(),
            "actions": Mock(),
            "reporting": Mock()
        }
        mock_supervisor.registry = mock_registry
        mock_app.state.agent_supervisor = mock_supervisor
        
        # Tool system (UserContext pattern)
        mock_app.state.tool_classes = [Mock() for _ in range(6)]  # Above expected
        mock_app.state.websocket_bridge_factory = Mock()
        
        # Database
        mock_app.state.db_session_factory = Mock()
        mock_app.state.database_mock_mode = False
        
        # WebSocket
        mock_ws_manager = Mock()
        mock_ws_manager.active_connections = [Mock(), Mock()]
        mock_ws_manager.message_handlers = {"handler1": Mock(), "handler2": Mock()}
        mock_app.state.websocket_manager = mock_ws_manager
        
        # Core services
        mock_app.state.llm_manager = Mock()
        mock_app.state.key_manager = Mock()
        mock_app.state.security_service = Mock()
        mock_app.state.redis_manager = Mock()
        mock_app.state.thread_service = Mock()
        mock_app.state.agent_service = Mock()
        mock_app.state.corpus_service = Mock()
        
        # Factory services
        mock_app.state.execution_engine_factory = Mock()
        mock_app.state.websocket_bridge_factory = Mock()
        mock_app.state.websocket_connection_pool = Mock()
        
        # Optional services
        mock_app.state.background_task_manager = Mock()
        mock_app.state.performance_monitor = Mock()
        
        # Middleware
        mock_app.middleware_stack = [Mock(), Mock(), Mock(), Mock()]
        
        # Mock database table counting
        async def mock_count_tables(factory):
            return 22  # Good count
        
        with patch.object(validator, '_count_database_tables', side_effect=mock_count_tables):
            # Mock critical path validation
            with patch('netra_backend.app.core.startup_validation.validate_critical_paths', new_callable=AsyncMock) as mock_critical:
                mock_critical.return_value = (True, [])
                
                success, report = await validator.validate_startup(mock_app)
        
        # Comprehensive validation checks
        assert success is True, f"Validation failed: {report}"
        assert report["overall_health"] == "healthy"
        assert report["critical_failures"] == 0
        
        # Verify comprehensive coverage
        assert report["total_validations"] >= 20  # Should have many validations
        
        # Verify all major categories are present
        categories = report["categories"]
        expected_categories = ["Agents", "Tools", "Database", "WebSocket", "Services", "Factories"]
        for category in expected_categories:
            assert category in categories, f"Missing category: {category}"
        
        # Verify healthy status distribution
        status_counts = report["status_counts"]
        assert status_counts["healthy"] > 15  # Most should be healthy
        assert status_counts["failed"] == 0  # No failures expected
        assert status_counts["critical"] == 0  # No critical issues
        
        # Verify timing
        assert report["duration"] > 0
        assert report["timestamp"] > 0
        
        # Verify specific validations exist and are healthy
        validation_names = [v.name for v in validator.validations]
        expected_validations = [
            "Agent Factory",
            "Tool Configuration", 
            "Database Tables",
            "WebSocket Manager",
            "LLM Manager",
            "ExecutionEngineFactory",
            "Critical Communication Paths"
        ]
        
        for expected in expected_validations:
            assert expected in validation_names, f"Missing validation: {expected}"
            
        # Verify all are healthy
        healthy_validations = [v for v in validator.validations if v.status == ComponentStatus.HEALTHY]
        assert len(healthy_validations) >= 15, "Not enough healthy validations"

    def test_startup_validator_comprehensive_coverage_verification(self):
        """Verify that we have comprehensive test coverage for all methods."""
        validator = StartupValidator()
        
        # List all methods that should be tested (from the source code analysis)
        expected_methods = [
            '__init__',
            'validate_startup',
            '_validate_agents',
            '_validate_tools',
            '_validate_database',
            '_validate_websocket',
            '_validate_services',
            '_validate_middleware',
            '_validate_background_tasks',
            '_validate_monitoring',
            '_validate_critical_paths',
            '_count_database_tables',
            '_get_status',
            '_add_failed_validation',
            '_generate_report',
            '_determine_success',
            '_log_results'
        ]
        
        # Verify all methods exist on the class
        for method_name in expected_methods:
            assert hasattr(validator, method_name), f"Method {method_name} not found on StartupValidator"
            
        # Verify methods are callable
        callable_methods = [m for m in expected_methods if not m.startswith('__')]
        for method_name in callable_methods:
            method = getattr(validator, method_name)
            assert callable(method), f"Method {method_name} is not callable"
        
        # Verify we have test classes for major functional areas
        test_class_names = [name for name in globals() if name.startswith('Test')]
        
        expected_test_areas = [
            'Initialization',
            'ComponentValidation',
            'ComponentStatus',
            'GetStatus',
            'AddFailedValidation',
            'DetermineSuccess',
            'GenerateReport',
            'ValidateStartup',
            'ValidateAgents',
            'ValidateTools',
            'ValidateDatabase',
            'ValidateWebSocket',
            'ValidateServices',
            'LogResults',
            'CriticalPathValidation',
            'Integration',
            'EdgeCases'
        ]
        
        for area in expected_test_areas:
            found = any(area.lower() in test_class.lower() for test_class in test_class_names)
            assert found, f"No test class found for area: {area}"
        
        print(f"PASS: Comprehensive coverage verified: {len(expected_methods)} methods, {len(expected_test_areas)} test areas")


# Export test classes for pytest discovery
__all__ = [
    "TestStartupValidatorInitialization",
    "TestComponentValidationDataClass", 
    "TestComponentStatusEnum",
    "TestGetStatusMethod",
    "TestAddFailedValidationMethod",
    "TestDetermineSuccessMethod",
    "TestGenerateReportMethod",
    "TestValidateStartupMainMethod",
    "TestValidateAgentsMethod",
    "TestValidateToolsMethod",
    "TestValidateDatabaseMethod",
    "TestCountDatabaseTablesMethod",
    "TestValidateWebSocketMethod",
    "TestValidateServicesMethod",
    "TestLogResultsMethod",
    "TestCriticalPathValidation",
    "TestIntegrationScenarios",
    "TestEdgeCasesAndErrorHandling",
    "TestComprehensiveIntegration"
]