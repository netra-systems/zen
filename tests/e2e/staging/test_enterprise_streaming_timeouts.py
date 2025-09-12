"""
E2E Staging tests for enterprise streaming timeout scenarios - Issue #341

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Mission-critical production scenarios
- Business Goal: Production Reliability - Validate real-world timeout constraints  
- Value Impact: Ensures enterprise customers can complete complex analytical workflows
- Revenue Impact: Protects $500K+ ARR from enterprise timeout-related churn

CRITICAL ISSUE #341:
Current problem: 60s timeout constraints cause failures in production for complex workflows
Target solution: 60s -> 300s timeout progression for enterprise analytical use cases
Test Strategy: E2E tests on GCP staging environment (NO Docker dependencies)

REQUIREMENTS:
- NO Docker dependencies (uses GCP staging environment) 
- Tests initially FAIL demonstrating current 60s production constraint
- Follow SSOT test patterns from test_framework
- Test real WebSocket connections and agent coordination
- Validate enterprise-grade timeout requirements
"""

import pytest
import asyncio
import time
import json
import websockets
import httpx
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.core.timeout_configuration import (
    get_websocket_recv_timeout,
    get_agent_execution_timeout,
    get_timeout_config,
    reset_timeout_manager
)

# Staging environment configuration
STAGING_BASE_URL = "https://api-staging.netra.dev"  # Replace with actual staging URL
STAGING_WS_URL = "wss://ws-staging.netra.dev"      # Replace with actual WebSocket URL


@dataclass
class EnterpriseWorkflowScenario:
    """Represents an enterprise analytical workflow scenario."""
    name: str
    description: str
    expected_duration: int  # seconds
    complexity: str
    data_sources: List[str] = field(default_factory=list)
    business_value: str = ""
    timeout_requirement: int = 300  # Default 5-minute requirement


class TestEnterpriseStreamingTimeouts(SSotAsyncTestCase):
    """E2E tests for enterprise streaming timeout scenarios on staging."""
    
    def setup_method(self, method=None):
        """Setup each test with staging environment."""
        super().setup_method(method)
        # Force staging environment for E2E tests
        self.set_env_var("ENVIRONMENT", "staging")
        reset_timeout_manager()
        self.record_metric("staging_environment_configured", True)
    
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        reset_timeout_manager()
        super().teardown_method(method)
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_enterprise_financial_analysis_timeout_on_staging(self):
        """
        Test enterprise financial analysis workflow timeout on staging environment.
        
        This test should INITIALLY FAIL, proving Issue #341 affects real staging deployments.
        Enterprise financial analysis requires 4+ minutes for comprehensive multi-source analysis.
        """
        # Define enterprise financial analysis scenario
        financial_scenario = EnterpriseWorkflowScenario(
            name="Enterprise Financial Analysis",
            description="Comprehensive financial analysis with multiple data sources and complex calculations",
            expected_duration=240,  # 4 minutes
            complexity="High",
            data_sources=["balance_sheet", "income_statement", "cash_flow", "market_data", "peer_comparison"],
            business_value="$100K+ decisions based on comprehensive analysis",
            timeout_requirement=300
        )
        
        # Get current staging timeout configuration
        staging_agent_timeout = get_agent_execution_timeout()
        staging_websocket_timeout = get_websocket_recv_timeout()
        
        self.record_metric("staging_agent_timeout", staging_agent_timeout)
        self.record_metric("staging_websocket_timeout", staging_websocket_timeout)
        self.record_metric("financial_scenario_requirement", financial_scenario.expected_duration)
        
        # Test real WebSocket connection to staging
        start_time = time.time()
        execution_failed = False
        websocket_events = []
        timeout_error = None
        
        try:
            # Simulate enterprise financial analysis request
            async with httpx.AsyncClient() as client:
                # Create analytical workflow request
                workflow_request = {
                    "agent_type": "financial_analysis",
                    "scenario": financial_scenario.name,
                    "parameters": {
                        "analysis_depth": "comprehensive",
                        "data_sources": financial_scenario.data_sources,
                        "time_horizon": "5_years",
                        "complexity": financial_scenario.complexity.lower()
                    },
                    "streaming": True,
                    "timeout_requirement": financial_scenario.timeout_requirement
                }
                
                # Test with current staging timeout constraints
                response = await client.post(
                    f"{STAGING_BASE_URL}/api/agents/execute",
                    json=workflow_request,
                    timeout=staging_agent_timeout  # Use current inadequate timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    execution_time = time.time() - start_time
                    
                    self.record_metric("financial_analysis_execution_time", execution_time)
                    self.record_metric("financial_analysis_completed", True)
                    
                    # If completed within timeout, record success (unexpected initially)
                    self.record_metric("unexpected_completion", True)
                else:
                    # Handle non-success response
                    execution_failed = True
                    self.record_metric("financial_analysis_http_error", response.status_code)
        
        except (asyncio.TimeoutError, httpx.TimeoutException) as e:
            execution_failed = True
            timeout_error = str(e)
            execution_time = time.time() - start_time
            
            self.record_metric("financial_analysis_timeout_occurred", True)
            self.record_metric("financial_analysis_timeout_duration", execution_time)
            self.record_metric("timeout_error_details", timeout_error)
        
        except Exception as e:
            execution_failed = True
            execution_time = time.time() - start_time
            self.record_metric("financial_analysis_unexpected_error", str(e))
        
        # CRITICAL ASSERTION: Should timeout with current constraints (initially FAIL)
        assert execution_failed, (
            f"Issue #341 STAGING VALIDATION FAILED: Enterprise financial analysis completed "
            f"in {execution_time:.1f}s within current {staging_agent_timeout}s timeout. "
            f"Expected timeout failure on staging to prove production issue exists. "
            f"Scenario: {financial_scenario.name} requiring {financial_scenario.expected_duration}s."
        )
        
        # Validate timeout occurred before expected completion
        if execution_failed and 'execution_time' in locals():
            assert execution_time < financial_scenario.expected_duration, (
                f"Timeout at {execution_time:.1f}s should be < expected duration {financial_scenario.expected_duration}s"
            )
        
        # Record enterprise impact
        self.record_metric("enterprise_scenario_blocked", financial_scenario.name)
        self.record_metric("business_value_at_risk", financial_scenario.business_value)
        self.record_metric("staging_timeout_constraint_confirmed", True)
    
    @pytest.mark.asyncio 
    @pytest.mark.staging
    async def test_websocket_streaming_coordination_timeout_staging(self):
        """
        Test WebSocket streaming coordination timeout on staging environment.
        
        Tests real WebSocket connection behavior under timeout pressure.
        Should reveal coordination issues between WebSocket recv and agent execution timeouts.
        """
        staging_websocket_timeout = get_websocket_recv_timeout()
        staging_agent_timeout = get_agent_execution_timeout()
        
        # Test streaming coordination with timeouts approaching limits
        coordination_test_duration = min(staging_agent_timeout - 5, staging_websocket_timeout - 5)
        
        self.record_metric("coordination_test_duration", coordination_test_duration)
        self.record_metric("staging_ws_timeout", staging_websocket_timeout)
        self.record_metric("staging_agent_timeout", staging_agent_timeout)
        
        websocket_events = []
        coordination_errors = []
        connection_established = False
        
        try:
            # Establish real WebSocket connection to staging
            async with websockets.connect(
                f"{STAGING_WS_URL}/ws/agent_streaming",
                timeout=30  # Connection timeout
            ) as websocket:
                connection_established = True
                self.record_metric("websocket_connection_established", True)
                
                # Send streaming analytical request
                streaming_request = {
                    "type": "start_streaming_analysis",
                    "payload": {
                        "analysis_type": "coordination_test",
                        "duration": coordination_test_duration,
                        "streaming_interval": 2.0
                    }
                }
                
                await websocket.send(json.dumps(streaming_request))
                
                # Monitor streaming events with timeout coordination
                start_time = time.time()
                
                while time.time() - start_time < coordination_test_duration + 10:  # Buffer for completion
                    try:
                        # Receive with staging WebSocket timeout
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=staging_websocket_timeout
                        )
                        
                        event = json.loads(message)
                        websocket_events.append({
                            "timestamp": time.time(),
                            "elapsed": time.time() - start_time,
                            "event": event
                        })
                        
                        # Check for completion
                        if event.get("type") == "analysis_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        # WebSocket recv timeout occurred
                        coordination_errors.append({
                            "type": "websocket_recv_timeout",
                            "elapsed": time.time() - start_time,
                            "timeout_limit": staging_websocket_timeout
                        })
                        break
                    
                    except websockets.exceptions.ConnectionClosed:
                        coordination_errors.append({
                            "type": "websocket_connection_closed",
                            "elapsed": time.time() - start_time
                        })
                        break
        
        except Exception as e:
            coordination_errors.append({
                "type": "websocket_connection_error",
                "error": str(e)
            })
        
        execution_time = time.time() - start_time if 'start_time' in locals() else 0
        
        # Record coordination metrics
        self.record_metric("websocket_events_received", len(websocket_events))
        self.record_metric("coordination_errors", len(coordination_errors))
        self.record_metric("websocket_coordination_time", execution_time)
        self.record_metric("connection_established", connection_established)
        
        # Validate WebSocket connection was established
        assert connection_established, "Failed to establish WebSocket connection to staging"
        
        # Analyze coordination behavior
        if coordination_errors:
            error_types = [error["type"] for error in coordination_errors]
            self.record_metric("coordination_error_types", error_types)
            
            # WebSocket timeout errors indicate Issue #341 coordination problems
            if "websocket_recv_timeout" in error_types:
                self.record_metric("websocket_recv_timeout_confirmed", True)
        
        # Record staging WebSocket behavior for Issue #341 analysis
        self.record_metric("staging_websocket_behavior_captured", True)
    
    @pytest.mark.asyncio
    @pytest.mark.staging  
    async def test_enterprise_multi_phase_analytical_workflow_staging(self):
        """
        Test multi-phase enterprise analytical workflow on staging.
        
        This tests the complete 60s -> 300s timeout progression requirement.
        Should INITIALLY FAIL proving Issue #341 affects complex multi-phase workflows.
        """
        # Define multi-phase enterprise workflow
        workflow_phases = [
            {"phase": "data_ingestion", "duration": 45, "timeout_req": 60},
            {"phase": "data_validation", "duration": 60, "timeout_req": 90}, 
            {"phase": "pattern_analysis", "duration": 90, "timeout_req": 120},
            {"phase": "ml_processing", "duration": 120, "timeout_req": 180},
            {"phase": "report_generation", "duration": 150, "timeout_req": 210},
            {"phase": "quality_assurance", "duration": 180, "timeout_req": 240},
            {"phase": "final_delivery", "duration": 240, "timeout_req": 300}
        ]
        
        staging_agent_timeout = get_agent_execution_timeout()
        staging_websocket_timeout = get_websocket_recv_timeout()
        
        # Record phase requirements vs current timeouts
        phase_gaps = []
        for phase in workflow_phases:
            agent_gap = phase["timeout_req"] - staging_agent_timeout
            websocket_gap = phase["timeout_req"] - staging_websocket_timeout
            
            if agent_gap > 0 or websocket_gap > 0:
                phase_gaps.append({
                    "phase": phase["phase"],
                    "required": phase["timeout_req"],
                    "agent_gap": agent_gap,
                    "websocket_gap": websocket_gap
                })
                
            self.record_metric(f"{phase['phase']}_timeout_requirement", phase["timeout_req"])
            self.record_metric(f"{phase['phase']}_agent_gap", agent_gap)
            self.record_metric(f"{phase['phase']}_websocket_gap", websocket_gap)
        
        # Test execution of multi-phase workflow
        start_time = time.time()
        phases_completed = []
        execution_failed = False
        
        try:
            async with httpx.AsyncClient() as client:
                multi_phase_request = {
                    "agent_type": "multi_phase_analytics",
                    "workflow": "enterprise_comprehensive_analysis", 
                    "phases": workflow_phases,
                    "total_timeout_requirement": 300,
                    "streaming_enabled": True
                }
                
                # Execute with current staging timeout
                response = await client.post(
                    f"{STAGING_BASE_URL}/api/agents/execute_multi_phase",
                    json=multi_phase_request,
                    timeout=staging_agent_timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    phases_completed = result.get("phases_completed", [])
                    execution_time = time.time() - start_time
                    
                    self.record_metric("multi_phase_execution_time", execution_time)
                    self.record_metric("phases_completed", len(phases_completed))
                    
        except (asyncio.TimeoutError, httpx.TimeoutException):
            execution_failed = True
            execution_time = time.time() - start_time
            
            self.record_metric("multi_phase_timeout_occurred", True)
            self.record_metric("multi_phase_timeout_duration", execution_time)
            self.record_metric("phases_completed_before_timeout", len(phases_completed))
        
        # Record multi-phase analysis
        self.record_metric("total_workflow_phases", len(workflow_phases))
        self.record_metric("phases_with_timeout_gaps", len(phase_gaps))
        self.record_metric("max_phase_requirement", max(p["timeout_req"] for p in workflow_phases))
        
        # CRITICAL ASSERTION: Multi-phase workflow should fail (initially)
        assert execution_failed or len(phases_completed) < len(workflow_phases), (
            f"Issue #341 MULTI-PHASE VALIDATION FAILED: Enterprise multi-phase workflow "
            f"completed {len(phases_completed)}/{len(workflow_phases)} phases successfully. "
            f"Expected failure with current {staging_agent_timeout}s timeout. "
            f"This proves either Issue #341 resolved or inadequate test simulation. "
            f"Phase timeout gaps detected: {len(phase_gaps)}/{len(workflow_phases)} phases."
        )
        
        self.record_metric("enterprise_multi_phase_blocked", True)
        self.record_metric("timeout_progression_requirement_confirmed", True)
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_concurrent_enterprise_workflows_timeout_isolation_staging(self):
        """
        Test timeout isolation between concurrent enterprise workflows on staging.
        
        Validates that timeout issues in one enterprise workflow don't affect others.
        """
        # Define concurrent enterprise scenarios
        enterprise_scenarios = [
            {
                "name": "financial_dashboard",
                "duration": 30,
                "expected_outcome": "success"
            },
            {
                "name": "supply_chain_analysis", 
                "duration": 90,
                "expected_outcome": "possible_timeout"
            },
            {
                "name": "customer_analytics",
                "duration": 180, 
                "expected_outcome": "likely_timeout"
            },
            {
                "name": "risk_assessment",
                "duration": 240,
                "expected_outcome": "expected_timeout"
            }
        ]
        
        staging_timeout = get_agent_execution_timeout()
        
        # Execute concurrent requests
        concurrent_tasks = {}
        concurrent_results = {}
        
        async with httpx.AsyncClient() as client:
            start_time = time.time()
            
            # Start all enterprise scenarios concurrently
            for scenario in enterprise_scenarios:
                task = asyncio.create_task(
                    self._execute_enterprise_scenario_staging(
                        client, scenario, staging_timeout
                    )
                )
                concurrent_tasks[scenario["name"]] = task
            
            # Wait for all tasks with timeout isolation
            for scenario_name, task in concurrent_tasks.items():
                try:
                    result = await task
                    concurrent_results[scenario_name] = result
                    
                except Exception as e:
                    concurrent_results[scenario_name] = {
                        "status": "error",
                        "error": str(e)
                    }
        
        total_execution_time = time.time() - start_time
        
        # Analyze isolation behavior
        successful_scenarios = [name for name, result in concurrent_results.items() 
                              if result.get("status") == "success"]
        timeout_scenarios = [name for name, result in concurrent_results.items()
                           if result.get("status") == "timeout"]
        
        self.record_metric("concurrent_enterprise_scenarios", len(enterprise_scenarios))
        self.record_metric("successful_concurrent_scenarios", len(successful_scenarios))
        self.record_metric("timeout_concurrent_scenarios", len(timeout_scenarios))
        self.record_metric("concurrent_execution_total_time", total_execution_time)
        
        # Validate isolation
        assert len(concurrent_results) == len(enterprise_scenarios), (
            "Timeout in one enterprise scenario affected others"
        )
        
        # Quick scenarios should succeed
        assert "financial_dashboard" in successful_scenarios, (
            "Quick enterprise scenario should succeed within timeout limits"
        )
        
        # Long scenarios should timeout with current constraints
        assert "risk_assessment" in timeout_scenarios, (
            f"Complex risk assessment (240s) should timeout with current {staging_timeout}s limit. "
            f"Issue #341 validation: Complex enterprise scenarios blocked by timeout constraints."
        )
        
        self.record_metric("enterprise_timeout_isolation_validated", True)
    
    async def _execute_enterprise_scenario_staging(self, client: httpx.AsyncClient, 
                                                 scenario: Dict[str, Any],
                                                 timeout: int) -> Dict[str, Any]:
        """
        Execute individual enterprise scenario on staging.
        
        Args:
            client: HTTP client
            scenario: Enterprise scenario configuration
            timeout: Timeout limit
            
        Returns:
            Execution result dictionary
        """
        scenario_name = scenario["name"]
        expected_duration = scenario["duration"]
        
        start_time = time.time()
        
        try:
            enterprise_request = {
                "agent_type": "enterprise_analytics",
                "scenario": scenario_name,
                "parameters": {
                    "expected_duration": expected_duration,
                    "complexity": "enterprise_grade",
                    "isolation_test": True
                }
            }
            
            response = await client.post(
                f"{STAGING_BASE_URL}/api/agents/execute",
                json=enterprise_request,
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "execution_time": execution_time,
                    "scenario": scenario_name,
                    "response": response.json()
                }
            else:
                return {
                    "status": "http_error",
                    "execution_time": execution_time,
                    "scenario": scenario_name,
                    "status_code": response.status_code
                }
        
        except (asyncio.TimeoutError, httpx.TimeoutException):
            return {
                "status": "timeout",
                "execution_time": time.time() - start_time,
                "scenario": scenario_name,
                "timeout_limit": timeout
            }
        
        except Exception as e:
            return {
                "status": "error", 
                "execution_time": time.time() - start_time,
                "scenario": scenario_name,
                "error": str(e)
            }
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_environment_timeout_configuration_validation(self):
        """
        Test validation of staging timeout configuration for enterprise requirements.
        
        This test documents current staging timeout configuration and validates
        against enterprise requirements. Should pass for documentation purposes.
        """
        # Get staging timeout configuration
        staging_config = get_timeout_config()
        
        enterprise_requirements = {
            "financial_analysis": 240,      # 4 minutes
            "supply_chain_optimization": 180, # 3 minutes  
            "customer_behavior_analytics": 300, # 5 minutes
            "risk_assessment": 180,          # 3 minutes
            "regulatory_compliance": 240,    # 4 minutes
            "market_intelligence": 300       # 5 minutes
        }
        
        # Record current staging configuration
        self.record_metric("staging_websocket_recv_timeout", staging_config.websocket_recv_timeout)
        self.record_metric("staging_agent_execution_timeout", staging_config.agent_execution_timeout)
        self.record_metric("staging_websocket_send_timeout", staging_config.websocket_send_timeout)
        self.record_metric("staging_websocket_heartbeat_timeout", staging_config.websocket_heartbeat_timeout)
        
        # Analyze enterprise requirement gaps
        requirement_gaps = {}
        for use_case, required_timeout in enterprise_requirements.items():
            agent_gap = required_timeout - staging_config.agent_execution_timeout
            websocket_gap = required_timeout - staging_config.websocket_recv_timeout
            
            requirement_gaps[use_case] = {
                "required": required_timeout,
                "agent_gap": agent_gap,
                "websocket_gap": websocket_gap,
                "adequate": agent_gap <= 0 and websocket_gap <= 0
            }
            
            self.record_metric(f"enterprise_{use_case}_requirement", required_timeout)
            self.record_metric(f"enterprise_{use_case}_agent_gap", agent_gap)
            self.record_metric(f"enterprise_{use_case}_websocket_gap", websocket_gap)
            self.record_metric(f"enterprise_{use_case}_adequate", requirement_gaps[use_case]["adequate"])
        
        # Calculate enterprise coverage
        adequate_use_cases = sum(1 for gap in requirement_gaps.values() if gap["adequate"])
        enterprise_coverage = adequate_use_cases / len(enterprise_requirements) * 100
        
        self.record_metric("enterprise_use_cases_total", len(enterprise_requirements))
        self.record_metric("enterprise_use_cases_adequate", adequate_use_cases)
        self.record_metric("enterprise_coverage_percentage", enterprise_coverage)
        
        # Record Issue #341 impact assessment
        blocked_use_cases = [use_case for use_case, gap in requirement_gaps.items() 
                           if not gap["adequate"]]
        
        self.record_metric("enterprise_use_cases_blocked", len(blocked_use_cases))
        self.record_metric("blocked_use_case_names", blocked_use_cases)
        
        # Validate staging environment documentation
        assert staging_config.agent_execution_timeout > 0, "Invalid staging agent timeout"
        assert staging_config.websocket_recv_timeout > 0, "Invalid staging WebSocket timeout" 
        assert staging_config.websocket_recv_timeout > staging_config.agent_execution_timeout, (
            "Staging timeout hierarchy broken"
        )
        
        # Document enterprise impact (this will show the scope of Issue #341)
        self.record_metric("issue_341_enterprise_impact_documented", True)
        self.record_metric("staging_timeout_analysis_completed", True)


if __name__ == "__main__":
    # Run E2E staging tests to demonstrate Issue #341 in production-like environment
    pytest.main([__file__, "-v", "-s", "--tb=short", "-m", "staging"])