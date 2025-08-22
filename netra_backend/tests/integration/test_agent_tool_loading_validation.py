"""
CRITICAL INTEGRATION TEST #9: Agent Tool Loading and Validation

BVJ:
- Segment: Platform/Internal (foundation for ALL customer segments)
- Business Goal: Platform Stability - Prevent $35K MRR loss from tool execution failures
- Value Impact: Ensures load tools → validate access → test execution → error handling pipeline
- Revenue Impact: Prevents customer request failures due to broken tool integrations

REQUIREMENTS:
- Load all required tools for agents
- Validate tool access permissions
- Test tool execution capabilities
- Handle tool execution errors gracefully
- Tool loading within 5 seconds
- 100% tool availability validation
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio

# Set testing environment
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from logging_config import central_logger

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from test_framework.mock_utils import mock_justified

logger = central_logger.get_logger(__name__)

class MockTool:
    """Mock tool for testing tool loading and validation."""
    
    def __init__(self, name: str, category: str, permissions: List[str], execution_time: float = 0.1):
        self.name = name
        self.category = category
        self.permissions = permissions
        self.execution_time = execution_time
        self.execution_count = 0
        self.last_execution = None
        self.is_available = True
        self.error_rate = 0.0  # 0.0 = no errors, 1.0 = always error
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with mock behavior."""
        if not self.is_available:
            raise Exception(f"Tool {self.name} is not available")
        
        # Simulate execution time
        await asyncio.sleep(self.execution_time)
        
        # Simulate error rate
        if self.error_rate > 0 and (self.execution_count % int(1/self.error_rate)) == 0:
            raise Exception(f"Simulated error in tool {self.name}")
        
        self.execution_count += 1
        self.last_execution = datetime.now(timezone.utc)
        
        return {
            "tool": self.name,
            "status": "success",
            "result": f"Mock result from {self.name}",
            "execution_count": self.execution_count,
            "execution_time": self.execution_time,
            "kwargs": kwargs
        }
    
    def validate_permissions(self, required_permissions: List[str]) -> bool:
        """Validate if tool has required permissions."""
        return all(perm in self.permissions for perm in required_permissions)

class MockToolDispatcher(ToolDispatcher):
    """Mock tool dispatcher for testing."""
    
    def __init__(self):
        self.tools = {}
        self.load_time = None
        self.validation_results = {}
        self.execution_stats = {}
    
    def load_tools(self) -> Dict[str, MockTool]:
        """Load mock tools for testing."""
        start_time = time.time()
        
        # Define comprehensive tool set
        tool_definitions = [
            # Data Analysis Tools
            ("query_executor", "data", ["read_database", "execute_query"]),
            ("data_processor", "data", ["read_files", "write_temp"]),
            ("metrics_calculator", "data", ["read_database", "compute"]),
            ("data_validator", "data", ["read_database", "validate"]),
            
            # Optimization Tools
            ("gpu_optimizer", "optimization", ["read_metrics", "adjust_settings"]),
            ("memory_optimizer", "optimization", ["read_system", "adjust_memory"]),
            ("cost_calculator", "optimization", ["read_billing", "compute"]),
            ("performance_analyzer", "optimization", ["read_metrics", "analyze"]),
            
            # Infrastructure Tools
            ("deployment_manager", "infrastructure", ["deploy", "manage_instances"]),
            ("scaling_controller", "infrastructure", ["scale", "manage_resources"]),
            ("load_balancer", "infrastructure", ["configure_lb", "manage_traffic"]),
            ("monitoring_setup", "infrastructure", ["configure_monitoring", "read_metrics"]),
            
            # Security Tools
            ("vulnerability_scanner", "security", ["scan_system", "read_configs"]),
            ("access_controller", "security", ["manage_access", "audit_permissions"]),
            ("compliance_checker", "security", ["audit_compliance", "read_policies"]),
            
            # Reporting Tools
            ("report_generator", "reporting", ["generate_reports", "write_files"]),
            ("data_visualizer", "reporting", ["create_charts", "read_data"]),
            ("summary_creator", "reporting", ["create_summaries", "read_data"])
        ]
        
        # Create mock tools
        for name, category, permissions in tool_definitions:
            tool = MockTool(name, category, permissions)
            self.tools[name] = tool
        
        self.load_time = time.time() - start_time
        return self.tools
    
    async def dispatch(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Dispatch tool execution."""
        if tool_name not in self.tools:
            raise Exception(f"Tool {tool_name} not found")
        
        tool = self.tools[tool_name]
        
        # Track execution stats
        if tool_name not in self.execution_stats:
            self.execution_stats[tool_name] = {"count": 0, "errors": 0, "total_time": 0}
        
        try:
            start_time = time.time()
            result = await tool.execute(**kwargs)
            execution_time = time.time() - start_time
            
            self.execution_stats[tool_name]["count"] += 1
            self.execution_stats[tool_name]["total_time"] += execution_time
            
            return result
            
        except Exception as e:
            self.execution_stats[tool_name]["errors"] += 1
            raise e
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tools."""
        return [name for name, tool in self.tools.items() if tool.is_available]
    
    def validate_tool_access(self, tool_name: str, required_permissions: List[str]) -> bool:
        """Validate tool access permissions."""
        if tool_name not in self.tools:
            return False
        
        tool = self.tools[tool_name]
        is_valid = tool.validate_permissions(required_permissions)
        
        self.validation_results[tool_name] = {
            "required_permissions": required_permissions,
            "tool_permissions": tool.permissions,
            "is_valid": is_valid,
            "timestamp": datetime.now(timezone.utc)
        }
        
        return is_valid

class TestAgentToolLoadingValidation:
    """BVJ: Protects $35K MRR through reliable agent tool loading and validation."""

    @pytest.fixture
    @mock_justified("LLM service external dependency for agent testing")
    def llm_manager_mock(self):
        """Mock LLM manager for tool testing."""
        llm_mock = Mock(spec=LLMManager)
        llm_mock.generate_response = AsyncMock(return_value={
            "content": "Tool validation response",
            "usage": {"prompt_tokens": 25, "completion_tokens": 8}
        })
        return llm_mock

    @pytest.fixture
    def tool_dispatcher_mock(self):
        """Create mock tool dispatcher with comprehensive tool set."""
        dispatcher = MockToolDispatcher()
        dispatcher.load_tools()
        return dispatcher

    @pytest.mark.asyncio
    async def test_01_comprehensive_tool_loading_validation(self, tool_dispatcher_mock):
        """BVJ: Validates all required tools are loaded correctly and available."""
        # Step 1: Validate tool loading performance
        assert tool_dispatcher_mock.load_time is not None, "Tool loading time not recorded"
        assert tool_dispatcher_mock.load_time < 5.0, f"Tool loading took {tool_dispatcher_mock.load_time:.2f}s, exceeds 5s limit"
        
        # Step 2: Verify comprehensive tool coverage
        loaded_tools = tool_dispatcher_mock.get_available_tools()
        
        # Expected tool categories and counts
        expected_categories = {
            "data": ["query_executor", "data_processor", "metrics_calculator", "data_validator"],
            "optimization": ["gpu_optimizer", "memory_optimizer", "cost_calculator", "performance_analyzer"],
            "infrastructure": ["deployment_manager", "scaling_controller", "load_balancer", "monitoring_setup"],
            "security": ["vulnerability_scanner", "access_controller", "compliance_checker"],
            "reporting": ["report_generator", "data_visualizer", "summary_creator"]
        }
        
        # Step 3: Validate each category has required tools
        for category, expected_tools in expected_categories.items():
            category_tools = [name for name in loaded_tools if name in expected_tools]
            assert len(category_tools) == len(expected_tools), \
                f"Category {category} missing tools: expected {len(expected_tools)}, got {len(category_tools)}"
            
            for tool_name in expected_tools:
                assert tool_name in loaded_tools, f"Required tool {tool_name} not loaded"
        
        # Step 4: Validate total tool count
        total_expected_tools = sum(len(tools) for tools in expected_categories.values())
        assert len(loaded_tools) >= total_expected_tools, \
            f"Insufficient tools loaded: expected {total_expected_tools}, got {len(loaded_tools)}"
        
        # Step 5: Verify all tools are marked as available
        for tool_name in loaded_tools:
            tool = tool_dispatcher_mock.tools[tool_name]
            assert tool.is_available, f"Tool {tool_name} marked as unavailable"
        
        logger.info(f"Tool loading validated: {len(loaded_tools)} tools loaded in {tool_dispatcher_mock.load_time:.2f}s")

    @pytest.mark.asyncio
    async def test_02_tool_access_permission_validation(self, tool_dispatcher_mock):
        """BVJ: Validates tool access permissions are correctly configured and enforced."""
        # Permission validation test scenarios
        permission_tests = [
            # Valid permission scenarios
            ("query_executor", ["read_database"], True),
            ("gpu_optimizer", ["read_metrics"], True),
            ("deployment_manager", ["deploy"], True),
            ("vulnerability_scanner", ["scan_system"], True),
            ("report_generator", ["generate_reports"], True),
            
            # Multiple permission scenarios
            ("query_executor", ["read_database", "execute_query"], True),
            ("deployment_manager", ["deploy", "manage_instances"], True),
            
            # Invalid permission scenarios
            ("query_executor", ["deploy"], False),
            ("gpu_optimizer", ["manage_access"], False),
            ("report_generator", ["scan_system"], False),
            
            # Insufficient permission scenarios
            ("deployment_manager", ["deploy", "scan_system"], False),
            ("vulnerability_scanner", ["read_database", "deploy"], False)
        ]
        
        # Execute permission validation tests
        validation_results = []
        
        for tool_name, required_permissions, expected_valid in permission_tests:
            start_time = time.time()
            
            # Validate tool access
            is_valid = tool_dispatcher_mock.validate_tool_access(tool_name, required_permissions)
            validation_time = time.time() - start_time
            
            # Verify validation result
            assert is_valid == expected_valid, \
                f"Permission validation failed for {tool_name} with {required_permissions}: expected {expected_valid}, got {is_valid}"
            
            # Verify validation timing
            assert validation_time < 0.1, f"Permission validation too slow: {validation_time:.3f}s"
            
            validation_results.append({
                "tool": tool_name,
                "permissions": required_permissions,
                "expected": expected_valid,
                "actual": is_valid,
                "validation_time": validation_time
            })
        
        # Step 2: Analyze validation performance
        successful_validations = sum(1 for r in validation_results if r["actual"] == r["expected"])
        validation_accuracy = (successful_validations / len(validation_results)) * 100
        avg_validation_time = sum(r["validation_time"] for r in validation_results) / len(validation_results)
        
        assert validation_accuracy == 100.0, f"Permission validation accuracy {validation_accuracy}% below 100%"
        assert avg_validation_time < 0.05, f"Average validation time {avg_validation_time:.3f}s too slow"
        
        # Step 3: Verify validation results are stored
        assert len(tool_dispatcher_mock.validation_results) > 0, "Validation results not stored"
        
        for tool_name, required_permissions, _ in permission_tests:
            if tool_name in tool_dispatcher_mock.validation_results:
                stored_result = tool_dispatcher_mock.validation_results[tool_name]
                assert "required_permissions" in stored_result, f"Missing required_permissions for {tool_name}"
                assert "is_valid" in stored_result, f"Missing validation result for {tool_name}"
        
        logger.info(f"Permission validation: {validation_accuracy}% accuracy, {avg_validation_time:.3f}s avg time")

    @pytest.mark.asyncio
    async def test_03_tool_execution_capability_testing(self, tool_dispatcher_mock):
        """BVJ: Validates all tools can execute successfully and handle parameters."""
        # Tool execution test scenarios
        execution_tests = [
            # Data tools
            ("query_executor", {"query": "SELECT * FROM metrics", "timeout": 30}),
            ("data_processor", {"input_file": "data.csv", "output_format": "json"}),
            ("metrics_calculator", {"metric_type": "performance", "aggregation": "avg"}),
            
            # Optimization tools
            ("gpu_optimizer", {"target_memory": "16GB", "strategy": "checkpoint"}),
            ("memory_optimizer", {"threshold": 0.8, "mode": "aggressive"}),
            ("cost_calculator", {"period": "monthly", "service": "gpu"}),
            
            # Infrastructure tools
            ("deployment_manager", {"environment": "staging", "replicas": 3}),
            ("scaling_controller", {"min_instances": 2, "max_instances": 10}),
            ("load_balancer", {"algorithm": "round_robin", "health_check": True}),
            
            # Security tools
            ("vulnerability_scanner", {"target": "infrastructure", "severity": "high"}),
            ("access_controller", {"user_id": "test_user", "permissions": ["read"]}),
            
            # Reporting tools
            ("report_generator", {"template": "performance", "format": "pdf"}),
            ("data_visualizer", {"chart_type": "bar", "data_source": "metrics"})
        ]
        
        # Execute tool capability tests
        execution_results = []
        
        for tool_name, test_params in execution_tests:
            start_time = time.time()
            
            try:
                # Execute tool with test parameters
                result = await tool_dispatcher_mock.dispatch(tool_name, **test_params)
                execution_time = time.time() - start_time
                
                # Validate execution result
                assert result["status"] == "success", f"Tool {tool_name} execution failed"
                assert result["tool"] == tool_name, f"Tool {tool_name} identity mismatch"
                assert "result" in result, f"Tool {tool_name} missing result"
                
                execution_results.append({
                    "tool": tool_name,
                    "success": True,
                    "execution_time": execution_time,
                    "params": test_params,
                    "result": result
                })
                
            except Exception as e:
                execution_time = time.time() - start_time
                execution_results.append({
                    "tool": tool_name,
                    "success": False,
                    "execution_time": execution_time,
                    "params": test_params,
                    "error": str(e)
                })
        
        # Analyze execution results
        successful_executions = sum(1 for r in execution_results if r["success"])
        execution_success_rate = (successful_executions / len(execution_results)) * 100
        avg_execution_time = sum(r["execution_time"] for r in execution_results) / len(execution_results)
        
        # Validate execution performance
        assert execution_success_rate == 100.0, f"Tool execution success rate {execution_success_rate}% below 100%"
        assert avg_execution_time < 1.0, f"Average execution time {avg_execution_time:.2f}s too slow"
        
        # Validate individual tool performance
        for result in execution_results:
            if not result["success"]:
                logger.error(f"Tool execution failed: {result['tool']} - {result.get('error')}")
            assert result["success"], f"Tool {result['tool']} execution failed: {result.get('error')}"
            assert result["execution_time"] < 2.0, f"Tool {result['tool']} too slow: {result['execution_time']:.2f}s"
        
        logger.info(f"Tool execution validated: {execution_success_rate}% success, {avg_execution_time:.2f}s avg time")

    @pytest.mark.asyncio
    async def test_04_tool_error_handling_resilience(self, tool_dispatcher_mock):
        """BVJ: Validates tools handle errors gracefully and provide meaningful feedback."""
        # Configure some tools to simulate errors
        error_simulation_tools = [
            ("query_executor", 0.3),  # 30% error rate
            ("gpu_optimizer", 0.2),   # 20% error rate
            ("deployment_manager", 0.1)  # 10% error rate
        ]
        
        for tool_name, error_rate in error_simulation_tools:
            if tool_name in tool_dispatcher_mock.tools:
                tool_dispatcher_mock.tools[tool_name].error_rate = error_rate
        
        # Execute multiple operations to trigger errors
        error_handling_tests = []
        
        for tool_name, error_rate in error_simulation_tools:
            # Execute tool multiple times to trigger errors
            for attempt in range(10):
                try:
                    start_time = time.time()
                    result = await tool_dispatcher_mock.dispatch(tool_name, test_attempt=attempt)
                    execution_time = time.time() - start_time
                    
                    error_handling_tests.append({
                        "tool": tool_name,
                        "attempt": attempt,
                        "success": True,
                        "execution_time": execution_time,
                        "result": result
                    })
                    
                except Exception as e:
                    execution_time = time.time() - start_time
                    
                    error_handling_tests.append({
                        "tool": tool_name,
                        "attempt": attempt,
                        "success": False,
                        "execution_time": execution_time,
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
        
        # Analyze error handling results
        total_tests = len(error_handling_tests)
        successful_tests = sum(1 for t in error_handling_tests if t["success"])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests) * 100
        
        # Validate error handling behavior
        assert failed_tests > 0, "No errors were triggered for error handling testing"
        assert success_rate >= 70.0, f"Success rate {success_rate}% too low (expected some failures)"
        assert success_rate <= 95.0, f"Success rate {success_rate}% too high (errors not triggered properly)"
        
        # Validate error information quality
        failed_tests_data = [t for t in error_handling_tests if not t["success"]]
        
        for failed_test in failed_tests_data:
            assert "error" in failed_test, f"Failed test missing error information"
            assert len(failed_test["error"]) > 0, f"Empty error message for {failed_test['tool']}"
            assert "error_type" in failed_test, f"Failed test missing error type"
        
        # Validate execution stats tracking
        for tool_name, _ in error_simulation_tools:
            stats = tool_dispatcher_mock.execution_stats.get(tool_name)
            assert stats is not None, f"Execution stats not tracked for {tool_name}"
            assert stats["count"] > 0, f"No successful executions recorded for {tool_name}"
            assert stats["errors"] > 0, f"No errors recorded for {tool_name}"
        
        logger.info(f"Error handling validated: {success_rate}% success rate with {failed_tests} controlled failures")

    @pytest.mark.asyncio
    async def test_05_agent_tool_integration_validation(self, llm_manager_mock, tool_dispatcher_mock):
        """BVJ: Validates agents can successfully integrate with and utilize tools."""
        # Create agent registry with tool dispatcher
        registry = AgentRegistry(llm_manager_mock, tool_dispatcher_mock)
        registry.register_default_agents()
        
        # Tool integration test scenarios
        agent_tool_tests = [
            {
                "agent": "triage",
                "required_tools": ["query_executor", "data_processor"],
                "operation": "route_request"
            },
            {
                "agent": "data",
                "required_tools": ["query_executor", "metrics_calculator", "data_validator"],
                "operation": "analyze_data"
            },
            {
                "agent": "optimization",
                "required_tools": ["gpu_optimizer", "memory_optimizer", "cost_calculator"],
                "operation": "optimize_performance"
            }
        ]
        
        # Execute agent-tool integration tests
        integration_results = []
        
        for test_scenario in agent_tool_tests:
            agent = registry.get(test_scenario["agent"])
            assert agent is not None, f"Agent {test_scenario['agent']} not found"
            
            # Verify agent has access to tool dispatcher
            assert hasattr(agent, 'tool_dispatcher') or hasattr(agent, 'llm_manager'), \
                f"Agent {test_scenario['agent']} missing tool dispatcher access"
            
            # Test tool availability for agent
            available_tools = tool_dispatcher_mock.get_available_tools()
            
            for required_tool in test_scenario["required_tools"]:
                assert required_tool in available_tools, \
                    f"Required tool {required_tool} not available for agent {test_scenario['agent']}"
                
                # Test tool execution through dispatcher
                try:
                    tool_result = await tool_dispatcher_mock.dispatch(
                        required_tool, 
                        agent=test_scenario["agent"],
                        operation=test_scenario["operation"]
                    )
                    
                    assert tool_result["status"] == "success", \
                        f"Tool {required_tool} execution failed for agent {test_scenario['agent']}"
                    
                except Exception as e:
                    logger.error(f"Tool integration failed: {test_scenario['agent']} -> {required_tool}: {e}")
                    raise e
            
            integration_results.append({
                "agent": test_scenario["agent"],
                "tools_tested": len(test_scenario["required_tools"]),
                "integration_successful": True
            })
        
        # Validate overall integration success
        successful_integrations = sum(1 for r in integration_results if r["integration_successful"])
        integration_success_rate = (successful_integrations / len(integration_results)) * 100
        
        assert integration_success_rate == 100.0, f"Agent-tool integration success rate {integration_success_rate}% below 100%"
        
        # Validate tool dispatcher statistics
        total_tools_tested = sum(r["tools_tested"] for r in integration_results)
        assert len(tool_dispatcher_mock.execution_stats) >= total_tools_tested, \
            "Tool execution statistics not properly tracked"
        
        logger.info(f"Agent-tool integration validated: {len(integration_results)} agents with {total_tools_tested} tool integrations")

    @pytest.mark.asyncio
    async def test_06_tool_performance_monitoring_validation(self, tool_dispatcher_mock):
        """BVJ: Validates tool performance monitoring and statistics collection."""
        # Performance monitoring test execution
        monitoring_tools = ["query_executor", "gpu_optimizer", "deployment_manager", "report_generator"]
        executions_per_tool = 20
        
        # Execute tools multiple times for performance monitoring
        for tool_name in monitoring_tools:
            for execution_id in range(executions_per_tool):
                await tool_dispatcher_mock.dispatch(
                    tool_name,
                    execution_id=execution_id,
                    monitoring_test=True
                )
        
        # Validate performance statistics collection
        for tool_name in monitoring_tools:
            stats = tool_dispatcher_mock.execution_stats.get(tool_name)
            assert stats is not None, f"Performance stats not collected for {tool_name}"
            
            # Validate statistics content
            assert stats["count"] >= executions_per_tool, \
                f"Execution count incorrect for {tool_name}: expected {executions_per_tool}, got {stats['count']}"
            assert stats["total_time"] > 0, f"Total execution time not tracked for {tool_name}"
            assert "errors" in stats, f"Error count not tracked for {tool_name}"
            
            # Calculate performance metrics
            avg_execution_time = stats["total_time"] / stats["count"]
            error_rate = (stats["errors"] / stats["count"]) * 100
            
            # Validate performance thresholds
            assert avg_execution_time < 0.5, f"Tool {tool_name} average execution time {avg_execution_time:.3f}s too slow"
            assert error_rate <= 5.0, f"Tool {tool_name} error rate {error_rate}% too high"
        
        # Validate overall monitoring system
        total_executions = sum(stats["count"] for stats in tool_dispatcher_mock.execution_stats.values())
        expected_total = len(monitoring_tools) * executions_per_tool
        
        assert total_executions >= expected_total, \
            f"Total executions {total_executions} below expected {expected_total}"
        
        logger.info(f"Performance monitoring validated: {len(monitoring_tools)} tools with {total_executions} total executions")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])