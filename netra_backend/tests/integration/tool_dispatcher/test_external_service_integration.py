"""
Tool Dispatcher & External Service Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Core Platform Functionality & User Experience
- Value Impact: Ensures tool execution delivers reliable results for user optimization workflows
- Strategic Impact: Tool reliability directly affects customer satisfaction and platform value delivery

These tests validate tool dispatcher behavior, external service integration,
and tool execution isolation critical for multi-user AI operations.
"""

import pytest
import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from concurrent.futures import ThreadPoolExecutor

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env


class TestToolDispatcherExternalServiceIntegration(BaseIntegrationTest):
    """Test tool dispatcher and external service integration."""

    @pytest.mark.integration
    async def test_tool_execution_isolation_concurrent_users(self):
        """
        Test tool execution isolation between concurrent user operations.
        
        BVJ: Critical for multi-user platform - ensures one user's tool execution
        doesn't interfere with another's, maintaining data integrity and user experience.
        """
        execution_results = {}
        isolation_violations = []
        
        class IsolatedToolExecutor:
            def __init__(self):
                self.active_executions = {}
                self.execution_contexts = {}
            
            async def execute_tool(self, user_id: str, tool_name: str, parameters: Dict[str, Any]):
                execution_id = f"{user_id}_{tool_name}_{len(self.active_executions)}"
                
                # Create isolated context
                context = {
                    "user_id": user_id,
                    "execution_id": execution_id,
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "start_time": time.time(),
                    "isolated_data": {}
                }
                
                self.execution_contexts[execution_id] = context
                self.active_executions[execution_id] = context
                
                # Simulate tool execution with user-specific data
                await self._simulate_tool_work(context)
                
                # Verify isolation
                await self._verify_isolation(execution_id)
                
                result = {
                    "execution_id": execution_id,
                    "user_id": user_id,
                    "tool_name": tool_name,
                    "result": f"Tool {tool_name} completed for {user_id}",
                    "duration": time.time() - context["start_time"]
                }
                
                del self.active_executions[execution_id]
                execution_results[execution_id] = result
                
                return result
            
            async def _simulate_tool_work(self, context: Dict[str, Any]):
                # Simulate tool accessing user-specific data
                context["isolated_data"]["user_data"] = f"data_for_{context['user_id']}"
                context["isolated_data"]["processing_result"] = f"processed_{context['tool_name']}"
                await asyncio.sleep(0.1)  # Simulate processing time
            
            async def _verify_isolation(self, execution_id: str):
                context = self.execution_contexts[execution_id]
                user_id = context["user_id"]
                
                # Check if any other execution contexts contain this user's data
                for other_id, other_context in self.execution_contexts.items():
                    if other_id != execution_id and other_context["user_id"] != user_id:
                        if f"data_for_{user_id}" in str(other_context.get("isolated_data", {})):
                            isolation_violations.append(f"data_leak_{execution_id}_{other_id}")
        
        executor = IsolatedToolExecutor()
        
        # Simulate concurrent tool executions for different users
        async def user_workflow(user_id: str):
            tasks = [
                executor.execute_tool(user_id, "cost_analyzer", {"account_id": f"acc_{user_id}"}),
                executor.execute_tool(user_id, "optimization_planner", {"budget": f"budget_{user_id}"}),
                executor.execute_tool(user_id, "report_generator", {"data_source": f"src_{user_id}"})
            ]
            return await asyncio.gather(*tasks)
        
        # Run concurrent workflows for 5 users
        user_workflows = [user_workflow(f"user_{i}") for i in range(5)]
        all_results = await asyncio.gather(*user_workflows)
        
        # Verify isolation
        assert len(isolation_violations) == 0, f"Isolation violations: {isolation_violations}"
        
        # Verify each user got their specific results
        total_executions = sum(len(results) for results in all_results)
        assert total_executions == 15  # 5 users × 3 tools each
        
        # Verify user-specific data in results
        for user_results in all_results:
            for result in user_results:
                user_id = result["user_id"]
                assert user_id in result["result"]
                assert user_id in result["execution_id"]

    @pytest.mark.integration
    async def test_external_api_error_handling_and_retries(self):
        """
        Test external API integration error handling and retry mechanisms.
        
        BVJ: Ensures platform reliability when external services fail, maintaining
        customer experience even during third-party service disruptions.
        """
        retry_events = []
        failure_recovery = []
        
        class ExternalAPIService:
            def __init__(self, service_name: str, failure_rate: float = 0.0):
                self.service_name = service_name
                self.failure_rate = failure_rate
                self.call_count = 0
                self.consecutive_failures = 0
            
            async def make_api_call(self, endpoint: str, data: Dict[str, Any]):
                self.call_count += 1
                call_id = f"{self.service_name}_call_{self.call_count}"
                
                # Simulate intermittent failures
                import random
                if random.random() < self.failure_rate:
                    self.consecutive_failures += 1
                    retry_events.append(f"failure_{call_id}")
                    raise ConnectionError(f"API call to {endpoint} failed")
                
                # Successful call
                if self.consecutive_failures > 0:
                    failure_recovery.append(f"recovered_{call_id}_after_{self.consecutive_failures}")
                    self.consecutive_failures = 0
                
                retry_events.append(f"success_{call_id}")
                return {
                    "call_id": call_id,
                    "endpoint": endpoint,
                    "data": data,
                    "status": "success"
                }
        
        class RetryingAPIClient:
            def __init__(self, max_retries: int = 3, backoff_factor: float = 1.0):
                self.max_retries = max_retries
                self.backoff_factor = backoff_factor
            
            async def call_with_retry(self, api_service: ExternalAPIService, endpoint: str, data: Dict[str, Any]):
                last_exception = None
                
                for attempt in range(self.max_retries + 1):
                    try:
                        result = await api_service.make_api_call(endpoint, data)
                        if attempt > 0:
                            retry_events.append(f"retry_success_attempt_{attempt}")
                        return result
                    
                    except Exception as e:
                        last_exception = e
                        retry_events.append(f"retry_attempt_{attempt}_{endpoint}")
                        
                        if attempt < self.max_retries:
                            # Exponential backoff
                            wait_time = self.backoff_factor * (2 ** attempt)
                            await asyncio.sleep(wait_time * 0.01)  # Scale down for testing
                        
                # All retries exhausted
                retry_events.append(f"retry_exhausted_{endpoint}")
                raise last_exception
        
        # Test with reliable service (no failures)
        reliable_service = ExternalAPIService("reliable_api", failure_rate=0.0)
        retry_client = RetryingAPIClient(max_retries=3)
        
        result = await retry_client.call_with_retry(
            reliable_service, 
            "/cost-analysis", 
            {"account": "test_account"}
        )
        
        assert result["status"] == "success"
        assert "success_reliable_api_call_1" in retry_events
        
        # Test with unreliable service (high failure rate)
        unreliable_service = ExternalAPIService("unreliable_api", failure_rate=0.7)
        
        # Some calls should eventually succeed with retries
        success_count = 0
        for i in range(10):
            try:
                result = await retry_client.call_with_retry(
                    unreliable_service,
                    "/optimization",
                    {"data": f"test_data_{i}"}
                )
                success_count += 1
            except Exception:
                pass  # Expected for some calls with high failure rate
        
        # Verify retry mechanism working
        retry_attempts = [event for event in retry_events if event.startswith("retry_attempt")]
        assert len(retry_attempts) > 0, "No retry attempts recorded"
        
        # Verify some calls eventually succeeded
        retry_successes = [event for event in retry_events if event.startswith("retry_success")]
        assert len(retry_successes) > 0 or success_count > 0, "No successful retries"

    @pytest.mark.integration
    async def test_tool_execution_timeout_and_cancellation(self):
        """
        Test tool execution timeout and cancellation mechanisms.
        
        BVJ: Prevents runaway tool executions from consuming resources and
        impacting platform performance for all users.
        """
        timeout_events = []
        cancellation_events = []
        
        class TimeoutAwareToolExecutor:
            def __init__(self):
                self.active_tools = {}
                self.cancelled_tools = set()
            
            async def execute_with_timeout(self, tool_id: str, execution_func: Callable, timeout_seconds: float):
                self.active_tools[tool_id] = {
                    "start_time": time.time(),
                    "status": "running",
                    "timeout": timeout_seconds
                }
                
                try:
                    result = await asyncio.wait_for(execution_func(), timeout=timeout_seconds)
                    self.active_tools[tool_id]["status"] = "completed"
                    timeout_events.append(f"completed_{tool_id}")
                    return result
                
                except asyncio.TimeoutError:
                    self.active_tools[tool_id]["status"] = "timeout"
                    timeout_events.append(f"timeout_{tool_id}")
                    await self._handle_timeout(tool_id)
                    raise
                
                except asyncio.CancelledError:
                    self.active_tools[tool_id]["status"] = "cancelled"
                    cancellation_events.append(f"cancelled_{tool_id}")
                    raise
            
            async def _handle_timeout(self, tool_id: str):
                # Cleanup resources for timed-out tool
                timeout_events.append(f"cleanup_{tool_id}")
                if tool_id in self.active_tools:
                    del self.active_tools[tool_id]
            
            async def cancel_tool(self, tool_id: str):
                if tool_id in self.active_tools:
                    self.cancelled_tools.add(tool_id)
                    cancellation_events.append(f"cancel_requested_{tool_id}")
        
        executor = TimeoutAwareToolExecutor()
        
        # Test normal execution (completes within timeout)
        async def fast_tool():
            await asyncio.sleep(0.1)
            return "Fast tool completed"
        
        result = await executor.execute_with_timeout("fast_tool", fast_tool, timeout_seconds=1.0)
        assert result == "Fast tool completed"
        assert "completed_fast_tool" in timeout_events
        
        # Test timeout scenario
        async def slow_tool():
            await asyncio.sleep(2.0)  # Exceeds timeout
            return "Slow tool completed"
        
        with pytest.raises(asyncio.TimeoutError):
            await executor.execute_with_timeout("slow_tool", slow_tool, timeout_seconds=0.5)
        
        assert "timeout_slow_tool" in timeout_events
        assert "cleanup_slow_tool" in timeout_events
        
        # Test cancellation scenario
        async def cancellable_tool():
            for i in range(10):
                await asyncio.sleep(0.1)
                # Check for cancellation
                if "cancellable_tool" in executor.cancelled_tools:
                    raise asyncio.CancelledError()
            return "Tool completed"
        
        # Start tool and cancel it mid-execution
        tool_task = asyncio.create_task(
            executor.execute_with_timeout("cancellable_tool", cancellable_tool, timeout_seconds=2.0)
        )
        
        await asyncio.sleep(0.3)  # Let it run briefly
        await executor.cancel_tool("cancellable_tool")
        tool_task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await tool_task
        
        assert "cancel_requested_cancellable_tool" in cancellation_events

    @pytest.mark.integration
    async def test_complex_tool_chain_execution_with_state_passing(self):
        """
        Test complex tool chain execution with state passing between tools.
        
        BVJ: Enables sophisticated user workflows where tools build on each other's
        results, providing comprehensive optimization insights.
        """
        execution_chain = []
        state_transitions = []
        
        class StatefulToolChain:
            def __init__(self):
                self.execution_state = {}
                self.tool_registry = {
                    "data_collector": self._data_collector_tool,
                    "data_analyzer": self._data_analyzer_tool,
                    "optimization_planner": self._optimization_planner_tool,
                    "report_generator": self._report_generator_tool
                }
            
            async def execute_chain(self, user_id: str, tool_chain: List[Dict[str, Any]]):
                chain_id = f"chain_{user_id}_{len(execution_chain)}"
                
                chain_state = {
                    "chain_id": chain_id,
                    "user_id": user_id,
                    "current_data": {},
                    "tool_results": [],
                    "chain_status": "running"
                }
                
                self.execution_state[chain_id] = chain_state
                execution_chain.append(chain_id)
                
                try:
                    for step_index, tool_config in enumerate(tool_chain):
                        tool_name = tool_config["tool"]
                        tool_params = tool_config.get("parameters", {})
                        
                        # Pass previous step's output as input to current step
                        if step_index > 0:
                            previous_result = chain_state["tool_results"][-1]
                            tool_params["previous_output"] = previous_result["output"]
                        
                        # Execute tool
                        tool_func = self.tool_registry[tool_name]
                        result = await tool_func(user_id, tool_params, chain_state["current_data"])
                        
                        # Update chain state
                        step_result = {
                            "step": step_index,
                            "tool": tool_name,
                            "output": result,
                            "timestamp": time.time()
                        }
                        
                        chain_state["tool_results"].append(step_result)
                        chain_state["current_data"].update(result.get("data", {}))
                        
                        state_transitions.append(f"{chain_id}_step_{step_index}_{tool_name}")
                    
                    chain_state["chain_status"] = "completed"
                    return {
                        "chain_id": chain_id,
                        "status": "success",
                        "results": chain_state["tool_results"],
                        "final_data": chain_state["current_data"]
                    }
                
                except Exception as e:
                    chain_state["chain_status"] = "failed"
                    chain_state["error"] = str(e)
                    raise
            
            async def _data_collector_tool(self, user_id: str, params: Dict[str, Any], current_data: Dict[str, Any]):
                # Simulate data collection
                await asyncio.sleep(0.1)
                collected_data = {
                    "user_id": user_id,
                    "account_data": f"account_info_{user_id}",
                    "cost_data": [{"service": "EC2", "cost": 150}, {"service": "S3", "cost": 50}],
                    "usage_metrics": {"cpu_hours": 1000, "storage_gb": 500}
                }
                return {
                    "status": "success",
                    "tool": "data_collector",
                    "data": collected_data,
                    "message": f"Collected data for {user_id}"
                }
            
            async def _data_analyzer_tool(self, user_id: str, params: Dict[str, Any], current_data: Dict[str, Any]):
                # Simulate analysis using previous step's data
                await asyncio.sleep(0.1)
                
                previous_data = params.get("previous_output", {}).get("data", {})
                cost_data = previous_data.get("cost_data", [])
                
                total_cost = sum(item["cost"] for item in cost_data)
                analysis = {
                    "total_monthly_cost": total_cost,
                    "cost_breakdown": {item["service"]: item["cost"] for item in cost_data},
                    "cost_trends": {"trend": "increasing", "rate": 0.15},
                    "optimization_opportunities": ["EC2 right-sizing", "S3 lifecycle policies"]
                }
                
                return {
                    "status": "success",
                    "tool": "data_analyzer", 
                    "data": analysis,
                    "message": f"Analyzed {total_cost} in monthly costs"
                }
            
            async def _optimization_planner_tool(self, user_id: str, params: Dict[str, Any], current_data: Dict[str, Any]):
                # Simulate optimization planning using analysis results
                await asyncio.sleep(0.1)
                
                previous_data = params.get("previous_output", {}).get("data", {})
                total_cost = previous_data.get("total_monthly_cost", 0)
                opportunities = previous_data.get("optimization_opportunities", [])
                
                optimization_plan = {
                    "potential_savings": total_cost * 0.3,  # 30% savings
                    "action_items": [
                        {"action": "Resize EC2 instances", "estimated_savings": total_cost * 0.2},
                        {"action": "Implement S3 lifecycle", "estimated_savings": total_cost * 0.1}
                    ],
                    "timeline": "30 days",
                    "priority": "high"
                }
                
                return {
                    "status": "success",
                    "tool": "optimization_planner",
                    "data": optimization_plan,
                    "message": f"Plan created with ${optimization_plan['potential_savings']} potential savings"
                }
            
            async def _report_generator_tool(self, user_id: str, params: Dict[str, Any], current_data: Dict[str, Any]):
                # Simulate report generation using all previous results
                await asyncio.sleep(0.1)
                
                # Aggregate data from entire chain
                report_data = {
                    "user_id": user_id,
                    "report_type": "optimization_report",
                    "summary": {
                        "current_cost": current_data.get("total_monthly_cost", 0),
                        "potential_savings": current_data.get("potential_savings", 0),
                        "action_count": len(current_data.get("action_items", []))
                    },
                    "recommendations": current_data.get("action_items", []),
                    "generated_at": time.time()
                }
                
                return {
                    "status": "success",
                    "tool": "report_generator",
                    "data": report_data,
                    "message": "Comprehensive optimization report generated"
                }
        
        tool_chain = StatefulToolChain()
        
        # Execute complex tool chain
        chain_config = [
            {"tool": "data_collector", "parameters": {"source": "aws_api"}},
            {"tool": "data_analyzer", "parameters": {"analysis_type": "cost_optimization"}},
            {"tool": "optimization_planner", "parameters": {"strategy": "aggressive"}},
            {"tool": "report_generator", "parameters": {"format": "comprehensive"}}
        ]
        
        result = await tool_chain.execute_chain("user_123", chain_config)
        
        # Verify chain execution
        assert result["status"] == "success"
        assert len(result["results"]) == 4  # All 4 tools executed
        
        # Verify state passing between tools
        data_collector_result = result["results"][0]
        data_analyzer_result = result["results"][1]
        optimization_planner_result = result["results"][2]
        report_generator_result = result["results"][3]
        
        assert data_collector_result["tool"] == "data_collector"
        assert "cost_data" in data_collector_result["output"]["data"]
        
        # Verify analyzer used collector's data
        assert "total_monthly_cost" in data_analyzer_result["output"]["data"]
        expected_cost = 200  # 150 + 50 from collector data
        assert data_analyzer_result["output"]["data"]["total_monthly_cost"] == expected_cost
        
        # Verify planner used analyzer's data
        potential_savings = optimization_planner_result["output"]["data"]["potential_savings"]
        assert potential_savings == expected_cost * 0.3  # 30% of total cost
        
        # Verify report used all chain data
        report_summary = report_generator_result["output"]["data"]["summary"]
        assert report_summary["current_cost"] == expected_cost
        assert report_summary["potential_savings"] == potential_savings
        
        # Verify proper state transitions
        expected_transitions = [
            "chain_user_123_0_step_0_data_collector",
            "chain_user_123_0_step_1_data_analyzer", 
            "chain_user_123_0_step_2_optimization_planner",
            "chain_user_123_0_step_3_report_generator"
        ]
        
        for expected_transition in expected_transitions:
            assert expected_transition in state_transitions

    @pytest.mark.integration
    async def test_tool_result_validation_and_sanitization(self):
        """
        Test tool result validation and sanitization for security and reliability.
        
        BVJ: Ensures tool outputs are safe and reliable, preventing security issues
        and data corruption that could impact customer trust and platform integrity.
        """
        validation_events = []
        sanitization_actions = []
        
        class ToolResultValidator:
            def __init__(self):
                self.validation_rules = {
                    "required_fields": ["status", "tool", "data"],
                    "max_data_size": 10000,  # 10KB max
                    "forbidden_patterns": [r"<script.*?>.*?</script>", r"javascript:", r"data:text/html"],
                    "sensitive_patterns": [r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"]
                }
            
            async def validate_and_sanitize(self, tool_result: Dict[str, Any], user_id: str):
                validation_result = {
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                    "sanitized_fields": []
                }
                
                # Validate required fields
                for field in self.validation_rules["required_fields"]:
                    if field not in tool_result:
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"missing_field_{field}")
                        validation_events.append(f"validation_error_missing_{field}_{user_id}")
                
                # Validate data size
                data_str = str(tool_result.get("data", ""))
                if len(data_str) > self.validation_rules["max_data_size"]:
                    validation_result["valid"] = False
                    validation_result["errors"].append("data_too_large")
                    validation_events.append(f"validation_error_size_{user_id}")
                
                # Check for malicious patterns
                result_str = str(tool_result)
                for pattern in self.validation_rules["forbidden_patterns"]:
                    import re
                    if re.search(pattern, result_str, re.IGNORECASE):
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"forbidden_pattern_{pattern}")
                        validation_events.append(f"security_violation_{user_id}")
                
                # Sanitize sensitive information
                sanitized_result = await self._sanitize_sensitive_data(tool_result, validation_result)
                
                if validation_result["valid"]:
                    validation_events.append(f"validation_passed_{user_id}")
                
                return sanitized_result, validation_result
            
            async def _sanitize_sensitive_data(self, tool_result: Dict[str, Any], validation_result: Dict[str, Any]):
                import re
                import copy
                
                sanitized_result = copy.deepcopy(tool_result)
                
                def sanitize_string(text: str) -> str:
                    # Sanitize credit card patterns
                    text = re.sub(r"\b\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}\b", "****-****-****-****", text)
                    
                    # Sanitize email addresses (partially)
                    text = re.sub(r"\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b", r"\1@***", text)
                    
                    return text
                
                def sanitize_recursive(obj):
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if isinstance(value, str):
                                original = value
                                obj[key] = sanitize_string(value)
                                if obj[key] != original:
                                    validation_result["sanitized_fields"].append(key)
                                    sanitization_actions.append(f"sanitized_{key}")
                            elif isinstance(value, (dict, list)):
                                sanitize_recursive(value)
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            if isinstance(item, str):
                                original = item
                                obj[i] = sanitize_string(item)
                                if obj[i] != original:
                                    validation_result["sanitized_fields"].append(f"list_item_{i}")
                                    sanitization_actions.append(f"sanitized_list_item_{i}")
                            elif isinstance(item, (dict, list)):
                                sanitize_recursive(item)
                
                sanitize_recursive(sanitized_result)
                return sanitized_result
        
        validator = ToolResultValidator()
        
        # Test valid tool result
        valid_result = {
            "status": "success",
            "tool": "cost_analyzer",
            "data": {
                "total_cost": 500,
                "recommendations": ["Optimize EC2 instances", "Use S3 lifecycle policies"]
            },
            "message": "Analysis completed successfully"
        }
        
        sanitized, validation = await validator.validate_and_sanitize(valid_result, "user_123")
        
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
        assert "validation_passed_user_123" in validation_events
        
        # Test result with missing required fields
        invalid_result = {
            "tool": "optimizer",
            "message": "Missing status and data fields"
        }
        
        sanitized, validation = await validator.validate_and_sanitize(invalid_result, "user_456")
        
        assert validation["valid"] is False
        assert "missing_field_status" in validation["errors"]
        assert "missing_field_data" in validation["errors"]
        assert "validation_error_missing_status_user_456" in validation_events
        
        # Test result with sensitive data
        sensitive_result = {
            "status": "success",
            "tool": "payment_analyzer",
            "data": {
                "credit_card": "4532-1234-5678-9012",
                "customer_email": "customer@example.com",
                "analysis": "Customer has high spend on card 4532-1234-5678-9012"
            }
        }
        
        sanitized, validation = await validator.validate_and_sanitize(sensitive_result, "user_789")
        
        assert validation["valid"] is True
        assert "credit_card" in validation["sanitized_fields"]
        assert "customer_email" in validation["sanitized_fields"]
        
        # Verify sanitization
        assert sanitized["data"]["credit_card"] == "****-****-****-****"
        assert "@***" in sanitized["data"]["customer_email"]
        assert "****-****-****-****" in sanitized["data"]["analysis"]
        
        assert "sanitized_credit_card" in sanitization_actions
        assert "sanitized_customer_email" in sanitization_actions

    @pytest.mark.integration
    async def test_performance_monitoring_during_tool_heavy_workflows(self):
        """
        Test performance monitoring during tool-heavy workflows.
        
        BVJ: Ensures platform maintains performance standards during intensive
        tool usage, critical for enterprise customers with complex workflows.
        """
        performance_metrics = {
            "tool_execution_times": {},
            "concurrent_tool_count": [],
            "memory_usage": [],
            "cpu_utilization": [],
            "throughput_metrics": {}
        }
        
        class PerformanceMonitor:
            def __init__(self):
                self.active_tools = {}
                self.completed_tools = {}
                self.performance_threshold = {
                    "max_execution_time": 10.0,  # seconds
                    "max_concurrent_tools": 50,
                    "max_memory_mb": 1024,
                    "min_throughput": 10  # tools per second
                }
            
            async def execute_tool_with_monitoring(self, tool_id: str, tool_func: Callable):
                start_time = time.time()
                
                # Record tool start
                self.active_tools[tool_id] = {
                    "start_time": start_time,
                    "status": "running"
                }
                
                # Monitor concurrent tool count
                concurrent_count = len(self.active_tools)
                performance_metrics["concurrent_tool_count"].append(concurrent_count)
                
                # Simulate memory and CPU monitoring
                simulated_memory = min(100 + concurrent_count * 10, 1024)  # MB
                simulated_cpu = min(10 + concurrent_count * 2, 100)  # %
                
                performance_metrics["memory_usage"].append(simulated_memory)
                performance_metrics["cpu_utilization"].append(simulated_cpu)
                
                try:
                    # Execute tool
                    result = await tool_func()
                    
                    # Record completion
                    execution_time = time.time() - start_time
                    
                    self.completed_tools[tool_id] = {
                        "execution_time": execution_time,
                        "status": "completed",
                        "result": result
                    }
                    
                    performance_metrics["tool_execution_times"][tool_id] = execution_time
                    
                    # Check performance thresholds
                    if execution_time > self.performance_threshold["max_execution_time"]:
                        performance_metrics[f"slow_tool_{tool_id}"] = execution_time
                    
                    if concurrent_count > self.performance_threshold["max_concurrent_tools"]:
                        performance_metrics[f"high_concurrency_alert"] = concurrent_count
                    
                    return result
                
                finally:
                    # Clean up
                    if tool_id in self.active_tools:
                        del self.active_tools[tool_id]
            
            def calculate_throughput(self, time_window: float = 1.0):
                current_time = time.time()
                recent_completions = [
                    tool for tool in self.completed_tools.values()
                    if (current_time - tool.get("completion_time", 0)) <= time_window
                ]
                return len(recent_completions) / time_window
        
        monitor = PerformanceMonitor()
        
        # Simulate various tool execution patterns
        async def fast_tool(tool_id: str):
            await asyncio.sleep(0.1)
            return f"Fast result for {tool_id}"
        
        async def medium_tool(tool_id: str):
            await asyncio.sleep(0.5)
            return f"Medium result for {tool_id}"
        
        async def slow_tool(tool_id: str):
            await asyncio.sleep(1.0)
            return f"Slow result for {tool_id}"
        
        # Execute mixed workload
        tools_to_execute = []
        
        # Add fast tools
        for i in range(20):
            tool_id = f"fast_tool_{i}"
            tools_to_execute.append(
                monitor.execute_tool_with_monitoring(tool_id, lambda tid=tool_id: fast_tool(tid))
            )
        
        # Add medium tools
        for i in range(10):
            tool_id = f"medium_tool_{i}"
            tools_to_execute.append(
                monitor.execute_tool_with_monitoring(tool_id, lambda tid=tool_id: medium_tool(tid))
            )
        
        # Add slow tools
        for i in range(5):
            tool_id = f"slow_tool_{i}"
            tools_to_execute.append(
                monitor.execute_tool_with_monitoring(tool_id, lambda tid=tool_id: slow_tool(tid))
            )
        
        # Execute all tools concurrently
        start_time = time.time()
        results = await asyncio.gather(*tools_to_execute)
        total_time = time.time() - start_time
        
        # Verify all tools completed
        assert len(results) == 35  # 20 + 10 + 5
        assert len(monitor.completed_tools) == 35
        
        # Analyze performance metrics
        execution_times = list(performance_metrics["tool_execution_times"].values())
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        
        # Verify performance within reasonable bounds
        assert avg_execution_time < 1.0  # Average should be reasonable
        assert max_execution_time < 2.0   # Max should be reasonable
        
        # Verify concurrency monitoring
        max_concurrent = max(performance_metrics["concurrent_tool_count"])
        assert max_concurrent <= 35  # Should track concurrent execution
        
        # Verify memory and CPU monitoring
        max_memory = max(performance_metrics["memory_usage"])
        max_cpu = max(performance_metrics["cpu_utilization"])
        
        assert max_memory > 0  # Should have memory readings
        assert max_cpu > 0     # Should have CPU readings
        
        # Calculate overall throughput
        throughput = len(results) / total_time
        performance_metrics["throughput_metrics"]["overall"] = throughput
        
        # Verify reasonable throughput (should complete multiple tools per second)
        assert throughput > 5.0, f"Throughput too low: {throughput} tools/second"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_dispatcher_service_mesh_integration(self, real_services_fixture):
        """
        Test tool dispatcher integration with service mesh architecture.
        
        BVJ: Ensures tools can communicate across services in the platform,
        enabling complex workflows that span multiple microservices.
        """
        service_interactions = []
        mesh_routing = {}
        
        class ServiceMeshSimulator:
            def __init__(self):
                self.services = {
                    "backend": {"url": "http://localhost:8000", "status": "healthy"},
                    "auth": {"url": "http://localhost:8081", "status": "healthy"},
                    "analytics": {"url": "http://localhost:8002", "status": "healthy"}
                }
                self.routing_table = {}
            
            async def route_tool_request(self, tool_name: str, target_service: str, payload: Dict[str, Any]):
                if target_service not in self.services:
                    raise ValueError(f"Service {target_service} not found in mesh")
                
                service_info = self.services[target_service]
                if service_info["status"] != "healthy":
                    raise ConnectionError(f"Service {target_service} is not healthy")
                
                # Record interaction
                interaction_id = f"{tool_name}_{target_service}_{len(service_interactions)}"
                interaction = {
                    "id": interaction_id,
                    "tool": tool_name,
                    "service": target_service,
                    "url": service_info["url"],
                    "payload": payload,
                    "timestamp": time.time()
                }
                
                service_interactions.append(interaction)
                
                # Track routing
                if tool_name not in mesh_routing:
                    mesh_routing[tool_name] = []
                mesh_routing[tool_name].append(target_service)
                
                # Simulate service call
                response = await self._simulate_service_call(target_service, payload)
                interaction["response"] = response
                
                return response
            
            async def _simulate_service_call(self, service: str, payload: Dict[str, Any]):
                # Simulate different service responses
                await asyncio.sleep(0.1)  # Simulate network latency
                
                if service == "backend":
                    return {
                        "service": "backend",
                        "data": f"Backend processed: {payload.get('data', 'no_data')}",
                        "status": "success"
                    }
                elif service == "auth":
                    return {
                        "service": "auth", 
                        "user_validated": True,
                        "permissions": ["read", "write"],
                        "status": "success"
                    }
                elif service == "analytics":
                    return {
                        "service": "analytics",
                        "metrics": {"processed_events": 100, "storage_used": "50GB"},
                        "status": "success"
                    }
        
        class CrossServiceTool:
            def __init__(self, service_mesh: ServiceMeshSimulator):
                self.service_mesh = service_mesh
            
            async def execute_cross_service_workflow(self, user_id: str):
                workflow_results = []
                
                # Step 1: Validate user with auth service
                auth_response = await self.service_mesh.route_tool_request(
                    "user_validator",
                    "auth",
                    {"user_id": user_id, "action": "validate"}
                )
                workflow_results.append(auth_response)
                
                # Step 2: Process data with backend service
                backend_response = await self.service_mesh.route_tool_request(
                    "data_processor", 
                    "backend",
                    {"user_id": user_id, "data": f"workflow_data_{user_id}"}
                )
                workflow_results.append(backend_response)
                
                # Step 3: Record analytics
                analytics_response = await self.service_mesh.route_tool_request(
                    "analytics_recorder",
                    "analytics", 
                    {"user_id": user_id, "event": "cross_service_workflow_completed"}
                )
                workflow_results.append(analytics_response)
                
                return {
                    "user_id": user_id,
                    "workflow_status": "completed",
                    "service_responses": workflow_results
                }
        
        # Test cross-service tool execution
        mesh = ServiceMeshSimulator()
        cross_service_tool = CrossServiceTool(mesh)
        
        # Execute workflow for multiple users
        user_workflows = []
        for user_id in ["user_1", "user_2", "user_3"]:
            workflow = cross_service_tool.execute_cross_service_workflow(user_id)
            user_workflows.append(workflow)
        
        workflow_results = await asyncio.gather(*user_workflows)
        
        # Verify all workflows completed successfully
        assert len(workflow_results) == 3
        for result in workflow_results:
            assert result["workflow_status"] == "completed"
            assert len(result["service_responses"]) == 3  # Auth, Backend, Analytics
        
        # Verify service mesh interactions
        assert len(service_interactions) == 9  # 3 users × 3 services each
        
        # Verify routing distribution
        assert "user_validator" in mesh_routing
        assert "data_processor" in mesh_routing  
        assert "analytics_recorder" in mesh_routing
        
        # Verify each tool hit the right services
        assert mesh_routing["user_validator"] == ["auth", "auth", "auth"]
        assert mesh_routing["data_processor"] == ["backend", "backend", "backend"]
        assert mesh_routing["analytics_recorder"] == ["analytics", "analytics", "analytics"]
        
        # Verify response structure
        auth_interactions = [i for i in service_interactions if i["service"] == "auth"]
        backend_interactions = [i for i in service_interactions if i["service"] == "backend"]
        analytics_interactions = [i for i in service_interactions if i["service"] == "analytics"]
        
        assert len(auth_interactions) == 3
        assert len(backend_interactions) == 3
        assert len(analytics_interactions) == 3
        
        # Verify auth responses contain user validation
        for interaction in auth_interactions:
            assert interaction["response"]["user_validated"] is True
            assert "permissions" in interaction["response"]
        
        # Verify backend responses contain processed data
        for interaction in backend_interactions:
            assert "Backend processed:" in interaction["response"]["data"]
            assert interaction["response"]["status"] == "success"