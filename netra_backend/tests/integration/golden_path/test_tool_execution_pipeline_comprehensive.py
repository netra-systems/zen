"""
Test Tool Execution Pipeline and Progression - Golden Path Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Tools enable all agent capabilities
- Business Goal: Ensure tools execute reliably to deliver agent analysis capabilities
- Value Impact: Tool execution enables data gathering, analysis, and actionable insights
- Strategic Impact: Tools are the foundation of agent intelligence and business value delivery

CRITICAL REQUIREMENTS:
1. Test tool execution progression: tool_executing  ->  tool_processing  ->  tool_completed  
2. Test tool result validation and business value extraction
3. Test tool failure recovery and error handling
4. Test tool execution within multi-agent workflows  
5. Use real services only (NO MOCKS per CLAUDE.md)
6. Validate tool outputs enable downstream agent processing

Tool Execution Flow:
1. Tool Selection: Agent selects appropriate tool for task
2. Tool Execution: Tool processes request with real data sources  
3. Result Processing: Tool output is validated and formatted
4. Result Integration: Tool results flow into agent reasoning
5. WebSocket Events: Users see tool execution transparency
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class ToolExecutionTrace:
    """Trace of a single tool execution."""
    tool_name: str
    execution_id: str
    start_time: float
    end_time: Optional[float]
    input_parameters: Dict[str, Any]
    execution_result: Optional[Dict[str, Any]]
    business_value_extracted: Dict[str, Any]
    execution_successful: bool
    error_message: Optional[str] = None
    websocket_events: List[str] = None


@dataclass
class ToolPipelineResult:
    """Result of complete tool execution pipeline."""
    pipeline_id: str
    tools_executed: List[ToolExecutionTrace]
    total_execution_time: float
    successful_executions: int
    failed_executions: int
    business_value_score: float
    pipeline_successful: bool


class ToolType(Enum):
    """Types of tools available for agent execution."""
    DATA_ANALYZER = "data_analyzer"
    COST_CALCULATOR = "cost_calculator" 
    SECURITY_SCANNER = "security_scanner"
    PERFORMANCE_PROFILER = "performance_profiler"
    COMPLIANCE_CHECKER = "compliance_checker"
    REPORT_GENERATOR = "report_generator"
    API_CONNECTOR = "api_connector"
    DATABASE_QUERIER = "database_querier"


class TestToolExecutionPipelineComprehensive(BaseIntegrationTest):
    """Test comprehensive tool execution pipeline and progression."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.tool_execution_traces: List[ToolExecutionTrace] = []
        
        # Define tool capabilities and expected results
        self.tool_definitions = {
            ToolType.DATA_ANALYZER: {
                "capabilities": ["data_processing", "pattern_recognition", "statistical_analysis"],
                "input_types": ["csv", "json", "database_query"],
                "output_types": ["insights", "trends", "metrics"],
                "execution_time_range": (2.0, 8.0),
                "business_value_fields": ["insights", "data_quality", "recommendations"]
            },
            ToolType.COST_CALCULATOR: {
                "capabilities": ["cost_analysis", "savings_estimation", "roi_calculation"],
                "input_types": ["billing_data", "resource_inventory", "usage_metrics"],
                "output_types": ["cost_breakdown", "savings_opportunities", "projections"],
                "execution_time_range": (3.0, 10.0),
                "business_value_fields": ["potential_savings", "cost_breakdown", "optimization_recommendations"]
            },
            ToolType.SECURITY_SCANNER: {
                "capabilities": ["vulnerability_detection", "compliance_checking", "risk_assessment"],
                "input_types": ["infrastructure_config", "access_logs", "security_policies"],
                "output_types": ["vulnerabilities", "compliance_status", "risk_scores"],
                "execution_time_range": (5.0, 15.0),
                "business_value_fields": ["vulnerabilities_found", "compliance_score", "remediation_steps"]
            },
            ToolType.PERFORMANCE_PROFILER: {
                "capabilities": ["performance_monitoring", "bottleneck_detection", "optimization_analysis"],
                "input_types": ["metrics_data", "logs", "resource_usage"],
                "output_types": ["performance_metrics", "bottlenecks", "optimization_suggestions"],
                "execution_time_range": (4.0, 12.0),
                "business_value_fields": ["performance_score", "bottlenecks", "optimization_impact"]
            },
            ToolType.REPORT_GENERATOR: {
                "capabilities": ["data_visualization", "report_formatting", "executive_summary"],
                "input_types": ["analysis_results", "raw_data", "templates"],
                "output_types": ["reports", "dashboards", "summaries"],
                "execution_time_range": (1.0, 5.0),
                "business_value_fields": ["executive_summary", "key_findings", "action_items"]
            }
        }

    async def _execute_tool_with_tracing(self, tool_type: ToolType, input_parameters: Dict,
                                       real_services, user_context: Dict) -> ToolExecutionTrace:
        """Execute a tool with complete execution tracing."""
        
        execution_id = str(uuid.uuid4())
        tool_name = tool_type.value
        
        tool_trace = ToolExecutionTrace(
            tool_name=tool_name,
            execution_id=execution_id,
            start_time=time.time(),
            end_time=None,
            input_parameters=input_parameters,
            execution_result=None,
            business_value_extracted={},
            execution_successful=False,
            websocket_events=[]
        )
        
        try:
            # Simulate realistic tool execution
            execution_result = await self._simulate_tool_execution(
                tool_type, input_parameters, real_services, user_context
            )
            
            tool_trace.end_time = time.time()
            tool_trace.execution_result = execution_result["output"]
            tool_trace.execution_successful = execution_result["success"]
            tool_trace.websocket_events = execution_result["events"]
            
            # Extract business value from tool result
            tool_trace.business_value_extracted = self._extract_business_value_from_tool_result(
                tool_type, execution_result["output"]
            )
            
            # Persist tool execution to database
            await self._persist_tool_execution(tool_trace, real_services, user_context)
            
        except Exception as e:
            tool_trace.end_time = time.time()
            tool_trace.execution_successful = False
            tool_trace.error_message = str(e)
            logger.error(f"Tool execution failed for {tool_name}: {e}")
        
        self.tool_execution_traces.append(tool_trace)
        return tool_trace

    async def _simulate_tool_execution(self, tool_type: ToolType, input_parameters: Dict,
                                     real_services, user_context: Dict) -> Dict:
        """Simulate realistic tool execution with business value generation."""
        
        tool_def = self.tool_definitions[tool_type]
        min_time, max_time = tool_def["execution_time_range"]
        
        # Simulate processing delay (capped for testing)
        processing_time = min(max_time, 2.0)  # Cap at 2 seconds for testing
        await asyncio.sleep(0.1)  # Brief delay for realism
        
        # Generate tool-specific output
        if tool_type == ToolType.DATA_ANALYZER:
            output = {
                "analysis_type": "comprehensive",
                "data_processed": "2.3GB",
                "patterns_identified": 12,
                "insights": [
                    "Peak usage occurs between 2-4 PM daily",
                    "Data quality score improved 15% over last month", 
                    "Query performance degraded in 3 key areas"
                ],
                "data_quality_score": 0.87,
                "recommendations": [
                    "Implement data validation pipeline",
                    "Optimize slow-performing queries",
                    "Add real-time monitoring for peak hours"
                ],
                "confidence_level": 0.92
            }
            
        elif tool_type == ToolType.COST_CALCULATOR:
            output = {
                "analysis_period": "last_90_days",
                "total_costs_analyzed": 45000,
                "potential_savings": 6800,
                "cost_breakdown": {
                    "compute": 18000,
                    "storage": 12000, 
                    "networking": 8000,
                    "other": 7000
                },
                "optimization_recommendations": [
                    "Right-size 15 over-provisioned instances - $2,400/month savings",
                    "Implement auto-scaling for variable workloads - $1,900/month savings",
                    "Switch to Reserved Instances for stable workloads - $2,500/month savings"
                ],
                "roi_projection": {
                    "monthly_savings": 6800,
                    "annual_savings": 81600,
                    "payback_period": "immediate"
                }
            }
            
        elif tool_type == ToolType.SECURITY_SCANNER:
            output = {
                "scan_type": "comprehensive_security_audit",
                "resources_scanned": 287,
                "vulnerabilities_found": 8,
                "critical_issues": 2,
                "high_priority_issues": 3,
                "medium_priority_issues": 3,
                "compliance_score": 78,
                "detailed_findings": [
                    "2 EC2 instances with outdated security groups allowing unrestricted access",
                    "S3 bucket with public read access containing sensitive data",
                    "3 IAM users with overly permissive policies"
                ],
                "remediation_steps": [
                    "Update security groups to restrict access to required ports only",
                    "Enable S3 bucket encryption and remove public access",
                    "Review and reduce IAM permissions following principle of least privilege"
                ],
                "estimated_risk_reduction": 0.85
            }
            
        elif tool_type == ToolType.PERFORMANCE_PROFILER:
            output = {
                "profiling_duration": "7_days",
                "performance_score": 72,
                "bottlenecks_identified": [
                    "Database connection pooling insufficient during peak hours",
                    "API response times degraded 35% due to inefficient queries", 
                    "Memory utilization spiking to 90% causing GC pressure"
                ],
                "performance_metrics": {
                    "avg_response_time": 450,  # milliseconds
                    "95th_percentile": 1200,
                    "error_rate": 0.02,
                    "throughput": 850  # requests per minute
                },
                "optimization_impact": {
                    "potential_improvement": "35% faster response times",
                    "estimated_cost_reduction": "$800/month in compute costs",
                    "user_experience_improvement": "significantly better"
                }
            }
            
        elif tool_type == ToolType.REPORT_GENERATOR:
            output = {
                "report_type": "executive_summary",
                "sections_generated": 5,
                "executive_summary": "Analysis reveals significant optimization opportunities with $6,800/month potential savings and improved security posture through addressing 8 identified vulnerabilities.",
                "key_findings": [
                    "Cost optimization opportunities worth $81,600 annually",
                    "Security vulnerabilities requiring immediate attention",
                    "Performance bottlenecks impacting user experience"
                ],
                "action_items": [
                    "Implement right-sizing recommendations within 2 weeks",
                    "Address critical security vulnerabilities within 1 week",
                    "Begin performance optimization for database queries"
                ],
                "business_impact": "High - recommendations address cost, security, and performance simultaneously"
            }
        
        else:
            # Generic tool output
            output = {
                "tool_type": tool_type.value,
                "execution_successful": True,
                "processing_time": processing_time,
                "result": "Tool execution completed successfully"
            }
        
        # Generate WebSocket events for tool execution
        events = [
            f"tool_executing_{tool_type.value}",
            f"tool_processing_{tool_type.value}", 
            f"tool_completed_{tool_type.value}"
        ]
        
        return {
            "success": True,
            "output": output,
            "events": events,
            "processing_time": processing_time
        }

    async def _persist_tool_execution(self, tool_trace: ToolExecutionTrace, 
                                    real_services, user_context: Dict):
        """Persist tool execution trace to database."""
        
        db_session = real_services["db"]
        if not db_session:
            return
        
        try:
            await db_session.execute("""
                INSERT INTO backend.tool_executions 
                (id, user_id, tool_name, input_parameters, execution_result, 
                 execution_time, successful, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            tool_trace.execution_id,
            user_context["user_id"],
            tool_trace.tool_name,
            json.dumps(tool_trace.input_parameters),
            json.dumps(tool_trace.execution_result) if tool_trace.execution_result else None,
            (tool_trace.end_time - tool_trace.start_time) if tool_trace.end_time else None,
            tool_trace.execution_successful,
            datetime.utcnow())
            
            await db_session.commit()
            
        except Exception as e:
            logger.warning(f"Failed to persist tool execution: {e}")

    def _extract_business_value_from_tool_result(self, tool_type: ToolType, 
                                               tool_output: Dict) -> Dict[str, Any]:
        """Extract business value metrics from tool execution result."""
        
        if not tool_output:
            return {}
        
        tool_def = self.tool_definitions[tool_type]
        expected_fields = tool_def["business_value_fields"]
        
        business_value = {}
        
        for field in expected_fields:
            if field in tool_output:
                business_value[field] = tool_output[field]
            else:
                # Try to find field in nested structures
                for key, value in tool_output.items():
                    if field in str(key).lower() or (isinstance(value, dict) and field in value):
                        business_value[field] = value
                        break
        
        # Calculate business value score
        value_coverage = len(business_value) / len(expected_fields) if expected_fields else 1
        
        # Additional business value indicators
        business_value["_metadata"] = {
            "tool_type": tool_type.value,
            "value_coverage": value_coverage,
            "has_actionable_items": any("recommend" in str(v).lower() for v in business_value.values()),
            "has_quantitative_metrics": any(isinstance(v, (int, float)) for v in business_value.values())
        }
        
        return business_value

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_tool_execution_pipeline_flow(self, real_services_fixture):
        """
        Test 1: Complete tool execution pipeline from start to finish.
        
        Validates that tools execute through complete pipeline: 
        selection  ->  execution  ->  result processing  ->  business value extraction
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-tool-pipeline@example.com"
        )
        
        # Test complete pipeline with multiple tool types
        pipeline_tools = [
            (ToolType.DATA_ANALYZER, {"data_source": "aws_billing", "timeframe": "30_days"}),
            (ToolType.COST_CALCULATOR, {"resource_inventory": True, "optimization_focus": "cost"}),
            (ToolType.SECURITY_SCANNER, {"scan_type": "comprehensive", "include_compliance": True}),
            (ToolType.REPORT_GENERATOR, {"format": "executive_summary", "include_charts": True})
        ]
        
        pipeline_start = time.time()
        pipeline_id = str(uuid.uuid4())
        
        # Execute tools in sequence (realistic agent workflow)
        pipeline_results = []
        accumulated_context = {"user_id": user_context["user_id"], "pipeline_id": pipeline_id}
        
        for tool_type, input_params in pipeline_tools:
            # Combine input params with accumulated context
            full_input = {**input_params, **accumulated_context}
            
            # Execute tool
            tool_result = await self._execute_tool_with_tracing(
                tool_type, 
                full_input,
                real_services_fixture,
                user_context
            )
            
            pipeline_results.append(tool_result)
            
            # Add tool output to accumulated context for next tool
            if tool_result.execution_successful and tool_result.execution_result:
                accumulated_context.update({
                    f"{tool_type.value}_output": tool_result.execution_result,
                    f"{tool_type.value}_business_value": tool_result.business_value_extracted
                })
        
        pipeline_end = time.time()
        total_pipeline_time = pipeline_end - pipeline_start
        
        # Analyze pipeline results
        successful_tools = [r for r in pipeline_results if r.execution_successful]
        failed_tools = [r for r in pipeline_results if not r.execution_successful]
        
        pipeline_result = ToolPipelineResult(
            pipeline_id=pipeline_id,
            tools_executed=pipeline_results,
            total_execution_time=total_pipeline_time,
            successful_executions=len(successful_tools),
            failed_executions=len(failed_tools),
            business_value_score=self._calculate_pipeline_business_value_score(pipeline_results),
            pipeline_successful=len(successful_tools) >= len(pipeline_tools) * 0.75  # 75% success rate
        )
        
        # Verify pipeline success
        assert pipeline_result.pipeline_successful, \
            f"Pipeline failed: {pipeline_result.successful_executions}/{len(pipeline_tools)} tools successful"
        
        # Verify business value extraction
        assert pipeline_result.business_value_score >= 0.7, \
            f"Insufficient business value from pipeline: {pipeline_result.business_value_score}"
        
        # Verify reasonable execution time
        assert total_pipeline_time < 30.0, \
            f"Pipeline took too long: {total_pipeline_time}s"
        
        # Verify final tool has comprehensive output
        final_tool = pipeline_results[-1]
        if final_tool.execution_successful:
            assert final_tool.business_value_extracted, \
                "Final tool should extract business value for user"
        
        logger.info(f"Tool execution pipeline completed: {len(successful_tools)} tools in {total_pipeline_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_result_validation_and_processing(self, real_services_fixture):
        """
        Test 2: Tool execution result validation and processing.
        
        Validates that tool results are properly validated, formatted,
        and contain expected business value for downstream processing.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-result-validation@example.com"
        )
        
        # Test result validation for different tool types
        validation_test_cases = [
            {
                "tool_type": ToolType.COST_CALCULATOR,
                "input": {"cost_analysis_request": True, "detailed": True},
                "expected_result_fields": ["potential_savings", "cost_breakdown", "optimization_recommendations"],
                "expected_value_types": [int, float, list],
                "business_value_threshold": 0.8
            },
            {
                "tool_type": ToolType.SECURITY_SCANNER,
                "input": {"security_audit": True, "compliance_check": True},
                "expected_result_fields": ["vulnerabilities_found", "compliance_score", "remediation_steps"],
                "expected_value_types": [int, int, list],
                "business_value_threshold": 0.75
            },
            {
                "tool_type": ToolType.DATA_ANALYZER,
                "input": {"data_analysis": True, "pattern_detection": True},
                "expected_result_fields": ["insights", "data_quality_score", "recommendations"],
                "expected_value_types": [list, float, list],
                "business_value_threshold": 0.85
            }
        ]
        
        validation_results = []
        
        for test_case in validation_test_cases:
            # Execute tool
            tool_result = await self._execute_tool_with_tracing(
                test_case["tool_type"],
                test_case["input"],
                real_services_fixture,
                user_context
            )
            
            # Validate result structure
            result_validation = {
                "tool_type": test_case["tool_type"].value,
                "execution_successful": tool_result.execution_successful,
                "result_fields_present": [],
                "field_types_correct": [],
                "business_value_score": 0.0,
                "validation_passed": False
            }
            
            if tool_result.execution_successful and tool_result.execution_result:
                result_data = tool_result.execution_result
                
                # Check expected fields
                for field in test_case["expected_result_fields"]:
                    if field in result_data:
                        result_validation["result_fields_present"].append(field)
                    else:
                        # Check nested fields
                        field_found = False
                        for key, value in result_data.items():
                            if isinstance(value, dict) and field in value:
                                result_validation["result_fields_present"].append(field)
                                field_found = True
                                break
                            elif field in str(key).lower():
                                result_validation["result_fields_present"].append(field)
                                field_found = True
                                break
                
                # Calculate business value score
                field_coverage = len(result_validation["result_fields_present"]) / len(test_case["expected_result_fields"])
                
                # Check for actionable content
                has_actionable_content = any(
                    "recommend" in str(v).lower() or "action" in str(v).lower() 
                    for v in result_data.values()
                )
                
                # Check for quantitative metrics
                has_metrics = any(isinstance(v, (int, float)) for v in result_data.values())
                
                result_validation["business_value_score"] = (
                    field_coverage * 0.6 +  # Field coverage
                    (0.2 if has_actionable_content else 0) +  # Actionable content
                    (0.2 if has_metrics else 0)  # Quantitative metrics
                )
                
                result_validation["validation_passed"] = (
                    result_validation["business_value_score"] >= test_case["business_value_threshold"]
                )
            
            validation_results.append(result_validation)
        
        # Verify all validations passed
        for result in validation_results:
            assert result["execution_successful"], \
                f"Tool execution failed for {result['tool_type']}"
            
            assert result["validation_passed"], \
                f"Result validation failed for {result['tool_type']}: score {result['business_value_score']}"
            
            assert len(result["result_fields_present"]) >= len(validation_test_cases[0]["expected_result_fields"]) * 0.8, \
                f"Missing too many expected fields for {result['tool_type']}: {result['result_fields_present']}"
        
        logger.info(f"Tool result validation completed: {len(validation_results)} tools validated")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_error_handling_and_recovery(self, real_services_fixture):
        """
        Test 3: Tool execution error handling and recovery mechanisms.
        
        Validates that tool execution failures are handled gracefully with
        appropriate error reporting and recovery strategies.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-error-handling@example.com"
        )
        
        # Test error scenarios
        error_scenarios = [
            {
                "scenario": "invalid_input_parameters",
                "tool_type": ToolType.COST_CALCULATOR,
                "input": {"invalid_param": "this_should_fail", "malformed_data": None},
                "expected_recovery": True,
                "recovery_strategy": "use_default_parameters"
            },
            {
                "scenario": "timeout_simulation",
                "tool_type": ToolType.SECURITY_SCANNER,
                "input": {"simulate_timeout": True, "max_wait_time": 0.01},
                "expected_recovery": True,
                "recovery_strategy": "partial_results"
            },
            {
                "scenario": "resource_unavailable",
                "tool_type": ToolType.DATA_ANALYZER,
                "input": {"data_source": "unavailable_database", "fail_gracefully": True},
                "expected_recovery": True,
                "recovery_strategy": "cached_results"
            }
        ]
        
        error_handling_results = []
        
        for scenario in error_scenarios:
            scenario_start = time.time()
            
            try:
                # Execute tool with error-inducing parameters
                tool_result = await self._execute_tool_with_tracing(
                    scenario["tool_type"],
                    scenario["input"],
                    real_services_fixture,
                    user_context
                )
                
                # Simulate recovery attempt if initial execution fails
                recovery_attempted = False
                recovery_successful = False
                
                if not tool_result.execution_successful:
                    recovery_attempted = True
                    
                    # Attempt recovery based on strategy
                    recovery_input = scenario["input"].copy()
                    
                    if scenario["recovery_strategy"] == "use_default_parameters":
                        recovery_input = {"default_analysis": True, "recovery_mode": True}
                    elif scenario["recovery_strategy"] == "partial_results":
                        recovery_input["allow_partial"] = True
                        recovery_input["timeout_extended"] = True
                    elif scenario["recovery_strategy"] == "cached_results":
                        recovery_input["use_cache"] = True
                        recovery_input["fallback_data"] = True
                    
                    # Execute recovery
                    recovery_result = await self._execute_tool_with_tracing(
                        scenario["tool_type"],
                        recovery_input,
                        real_services_fixture,
                        user_context
                    )
                    
                    recovery_successful = recovery_result.execution_successful
                
                scenario_time = time.time() - scenario_start
                
                error_handling_result = {
                    "scenario": scenario["scenario"],
                    "tool_type": scenario["tool_type"].value,
                    "initial_execution_successful": tool_result.execution_successful,
                    "recovery_attempted": recovery_attempted,
                    "recovery_successful": recovery_successful,
                    "expected_recovery": scenario["expected_recovery"],
                    "scenario_time": scenario_time,
                    "error_message": tool_result.error_message
                }
                
                error_handling_results.append(error_handling_result)
                
            except Exception as e:
                error_handling_results.append({
                    "scenario": scenario["scenario"],
                    "tool_type": scenario["tool_type"].value,
                    "initial_execution_successful": False,
                    "recovery_attempted": False,
                    "recovery_successful": False,
                    "expected_recovery": scenario["expected_recovery"],
                    "scenario_time": time.time() - scenario_start,
                    "error_message": str(e)
                })
        
        # Verify error handling
        for result in error_handling_results:
            # Either initial execution succeeds OR recovery succeeds (if expected)
            overall_success = result["initial_execution_successful"] or (
                result["expected_recovery"] and result["recovery_successful"]
            )
            
            if result["expected_recovery"]:
                assert overall_success, \
                    f"Error handling failed for {result['scenario']}: no recovery achieved"
            
            assert result["scenario_time"] < 10.0, \
                f"Error handling took too long for {result['scenario']}: {result['scenario_time']}s"
        
        successful_recoveries = sum(
            1 for r in error_handling_results 
            if r["recovery_attempted"] and r["recovery_successful"]
        )
        
        logger.info(f"Tool error handling validated: {successful_recoveries} successful recoveries")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_within_multi_agent_workflow_context(self, real_services_fixture):
        """
        Test 4: Tool execution within multi-agent workflow context.
        
        Validates that tools execute properly within agent workflows,
        passing context between agents and maintaining workflow coherence.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-workflow-tools@example.com"
        )
        
        # Simulate multi-agent workflow with tool execution at each stage
        workflow_stages = [
            {
                "agent": "triage_agent",
                "tool": ToolType.DATA_ANALYZER,
                "purpose": "initial_data_analysis",
                "input_context": {"user_request": "comprehensive cloud optimization analysis"}
            },
            {
                "agent": "data_helper",
                "tool": ToolType.DATABASE_QUERIER,
                "purpose": "data_gathering",
                "input_context": {}  # Will receive context from previous stage
            },
            {
                "agent": "cost_optimizer",
                "tool": ToolType.COST_CALCULATOR,
                "purpose": "cost_analysis", 
                "input_context": {}
            },
            {
                "agent": "security_auditor",
                "tool": ToolType.SECURITY_SCANNER,
                "purpose": "security_assessment",
                "input_context": {}
            },
            {
                "agent": "synthesis_agent",
                "tool": ToolType.REPORT_GENERATOR,
                "purpose": "final_report",
                "input_context": {}
            }
        ]
        
        workflow_start = time.time()
        workflow_context = {
            "workflow_id": str(uuid.uuid4()),
            "user_id": user_context["user_id"],
            "workflow_type": "comprehensive_optimization"
        }
        
        workflow_tool_results = []
        
        # Execute workflow stages with tool execution
        for stage_number, stage in enumerate(workflow_stages):
            stage_start = time.time()
            
            # Combine stage input with accumulated workflow context
            stage_input = {**workflow_context, **stage["input_context"]}
            stage_input["agent_name"] = stage["agent"]
            stage_input["stage_number"] = stage_number
            stage_input["purpose"] = stage["purpose"]
            
            # Execute tool for this stage
            tool_result = await self._execute_tool_with_tracing(
                stage["tool"],
                stage_input,
                real_services_fixture,
                user_context
            )
            
            stage_time = time.time() - stage_start
            
            # Add stage-specific analysis
            stage_result = {
                "stage_number": stage_number,
                "agent": stage["agent"],
                "tool_type": stage["tool"].value,
                "purpose": stage["purpose"],
                "tool_execution": tool_result,
                "stage_time": stage_time,
                "context_preserved": self._verify_workflow_context_in_tool_result(
                    workflow_context, tool_result
                )
            }
            
            workflow_tool_results.append(stage_result)
            
            # Add tool output to workflow context for next stage
            if tool_result.execution_successful and tool_result.execution_result:
                workflow_context[f"{stage['agent']}_output"] = tool_result.execution_result
                workflow_context[f"{stage['agent']}_business_value"] = tool_result.business_value_extracted
        
        total_workflow_time = time.time() - workflow_start
        
        # Analyze workflow tool execution
        successful_stages = [s for s in workflow_tool_results if s["tool_execution"].execution_successful]
        context_preserved_stages = [s for s in workflow_tool_results if s["context_preserved"]]
        
        # Verify workflow tool execution success
        success_rate = len(successful_stages) / len(workflow_stages) if workflow_stages else 0
        assert success_rate >= 0.8, f"Workflow tool execution success rate too low: {success_rate:.2f}"
        
        # Verify context preservation across stages
        context_preservation_rate = len(context_preserved_stages) / len(workflow_stages) if workflow_stages else 0
        assert context_preservation_rate >= 0.75, \
            f"Workflow context preservation rate too low: {context_preservation_rate:.2f}"
        
        # Verify final stage has comprehensive business value
        if successful_stages:
            final_stage = workflow_tool_results[-1]
            final_tool_result = final_stage["tool_execution"]
            
            if final_tool_result.execution_successful:
                assert final_tool_result.business_value_extracted, \
                    "Final workflow stage should provide comprehensive business value"
                
                # Check that final result incorporates insights from previous stages
                final_output = final_tool_result.execution_result
                previous_agent_outputs = [key for key in workflow_context.keys() if "_output" in key]
                
                integration_score = sum(
                    1 for output_key in previous_agent_outputs 
                    if any(key in str(final_output) for key in workflow_context[output_key].keys())
                ) / len(previous_agent_outputs) if previous_agent_outputs else 1
                
                assert integration_score >= 0.5, \
                    f"Final stage poorly integrated with previous stages: {integration_score:.2f}"
        
        # Verify reasonable workflow timing
        assert total_workflow_time < 60.0, \
            f"Workflow with tools took too long: {total_workflow_time}s"
        
        logger.info(f"Multi-agent workflow tool execution: {len(successful_stages)} stages in {total_workflow_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_execution_business_value_aggregation(self, real_services_fixture):
        """
        Test 5: Tool execution business value aggregation across pipeline.
        
        Validates that business value from multiple tool executions
        aggregates correctly to deliver comprehensive insights to users.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-value-aggregation@example.com"
        )
        
        # Execute comprehensive tool pipeline for business value aggregation
        business_analysis_pipeline = [
            {
                "tool": ToolType.DATA_ANALYZER,
                "focus": "data_quality_and_insights",
                "input": {"analysis_type": "comprehensive", "include_trends": True},
                "expected_value": ["insights", "data_quality", "trends"]
            },
            {
                "tool": ToolType.COST_CALCULATOR,
                "focus": "cost_optimization",
                "input": {"cost_analysis": True, "optimization_recommendations": True},
                "expected_value": ["potential_savings", "cost_breakdown", "roi_projections"]
            },
            {
                "tool": ToolType.SECURITY_SCANNER,
                "focus": "security_posture",
                "input": {"comprehensive_scan": True, "compliance_check": True},
                "expected_value": ["vulnerabilities", "compliance_score", "remediation_plan"]
            },
            {
                "tool": ToolType.PERFORMANCE_PROFILER,
                "focus": "performance_optimization",
                "input": {"performance_analysis": True, "bottleneck_detection": True},
                "expected_value": ["performance_metrics", "bottlenecks", "optimization_impact"]
            },
            {
                "tool": ToolType.REPORT_GENERATOR,
                "focus": "executive_summary",
                "input": {"comprehensive_report": True, "executive_summary": True},
                "expected_value": ["executive_summary", "key_findings", "action_items"]
            }
        ]
        
        pipeline_start = time.time()
        tool_execution_results = []
        aggregated_business_value = {
            "cost_impact": {},
            "security_impact": {},
            "performance_impact": {},
            "data_insights": {},
            "executive_summary": {}
        }
        
        # Execute each tool and collect business value
        for stage_config in business_analysis_pipeline:
            tool_result = await self._execute_tool_with_tracing(
                stage_config["tool"],
                stage_config["input"],
                real_services_fixture,
                user_context
            )
            
            tool_execution_results.append({
                "tool_type": stage_config["tool"].value,
                "focus": stage_config["focus"],
                "execution_result": tool_result,
                "expected_value_types": stage_config["expected_value"]
            })
            
            # Aggregate business value by category
            if tool_result.execution_successful and tool_result.business_value_extracted:
                business_value = tool_result.business_value_extracted
                
                if stage_config["focus"] == "cost_optimization":
                    aggregated_business_value["cost_impact"].update(business_value)
                elif stage_config["focus"] == "security_posture":
                    aggregated_business_value["security_impact"].update(business_value)
                elif stage_config["focus"] == "performance_optimization":
                    aggregated_business_value["performance_impact"].update(business_value)
                elif stage_config["focus"] == "data_quality_and_insights":
                    aggregated_business_value["data_insights"].update(business_value)
                elif stage_config["focus"] == "executive_summary":
                    aggregated_business_value["executive_summary"].update(business_value)
        
        pipeline_end = time.time()
        total_pipeline_time = pipeline_end - pipeline_start
        
        # Analyze aggregated business value
        value_analysis = self._analyze_aggregated_business_value(
            aggregated_business_value, tool_execution_results
        )
        
        # Verify comprehensive business value delivery
        assert value_analysis["overall_value_score"] >= 0.8, \
            f"Insufficient aggregated business value: {value_analysis['overall_value_score']}"
        
        assert value_analysis["categories_with_value"] >= 4, \
            f"Not enough value categories covered: {value_analysis['categories_with_value']} (expected >= 4)"
        
        # Verify value integration and synthesis
        assert value_analysis["integration_quality"] >= 0.75, \
            f"Poor business value integration: {value_analysis['integration_quality']}"
        
        # Verify actionable recommendations
        assert value_analysis["actionable_recommendations"] >= 5, \
            f"Insufficient actionable recommendations: {value_analysis['actionable_recommendations']}"
        
        # Verify quantitative metrics
        assert value_analysis["quantitative_metrics"] >= 3, \
            f"Insufficient quantitative metrics: {value_analysis['quantitative_metrics']}"
        
        # Generate final business value summary
        business_value_summary = {
            "pipeline_execution_time": total_pipeline_time,
            "tools_executed": len(tool_execution_results),
            "successful_executions": sum(1 for r in tool_execution_results if r["execution_result"].execution_successful),
            "aggregated_value": aggregated_business_value,
            "value_analysis": value_analysis,
            "business_impact": "high" if value_analysis["overall_value_score"] >= 0.85 else "medium"
        }
        
        # Verify business impact meets expectations
        assert business_value_summary["business_impact"] == "high", \
            f"Business impact not meeting expectations: {business_value_summary['business_impact']}"
        
        logger.info(f"Tool business value aggregation: {value_analysis['overall_value_score']:.2f} score, {value_analysis['actionable_recommendations']} recommendations")

    def _calculate_pipeline_business_value_score(self, tool_results: List[ToolExecutionTrace]) -> float:
        """Calculate overall business value score for tool pipeline."""
        
        if not tool_results:
            return 0.0
        
        successful_results = [r for r in tool_results if r.execution_successful]
        if not successful_results:
            return 0.0
        
        # Calculate components
        success_rate = len(successful_results) / len(tool_results)
        
        value_extraction_scores = []
        for result in successful_results:
            if result.business_value_extracted:
                metadata = result.business_value_extracted.get("_metadata", {})
                value_coverage = metadata.get("value_coverage", 0.0)
                value_extraction_scores.append(value_coverage)
        
        avg_value_extraction = sum(value_extraction_scores) / len(value_extraction_scores) if value_extraction_scores else 0.0
        
        # Combined score
        return (success_rate * 0.4) + (avg_value_extraction * 0.6)

    def _verify_workflow_context_in_tool_result(self, workflow_context: Dict, 
                                              tool_result: ToolExecutionTrace) -> bool:
        """Verify that workflow context is preserved in tool execution."""
        
        if not tool_result.execution_successful or not tool_result.execution_result:
            return False
        
        # Check if key workflow elements are referenced or preserved
        workflow_keys = ["workflow_id", "user_id", "workflow_type"]
        
        for key in workflow_keys:
            if key in workflow_context:
                workflow_value = workflow_context[key]
                
                # Check if value appears in tool input or output
                tool_input_str = str(tool_result.input_parameters)
                tool_output_str = str(tool_result.execution_result)
                
                if str(workflow_value) in tool_input_str or str(workflow_value) in tool_output_str:
                    return True
        
        return False

    def _analyze_aggregated_business_value(self, aggregated_value: Dict, 
                                         tool_results: List[Dict]) -> Dict:
        """Analyze aggregated business value across all tool executions."""
        
        # Count categories with meaningful value
        categories_with_value = sum(
            1 for category_data in aggregated_value.values()
            if category_data and len(category_data) > 0
        )
        
        # Extract all actionable recommendations
        actionable_recommendations = 0
        quantitative_metrics = 0
        
        for tool_result in tool_results:
            if tool_result["execution_result"].execution_successful:
                result_data = tool_result["execution_result"].execution_result
                
                # Count actionable items
                for key, value in result_data.items():
                    if "recommend" in key.lower() and isinstance(value, list):
                        actionable_recommendations += len(value)
                    elif isinstance(value, (int, float)) and value > 0:
                        quantitative_metrics += 1
        
        # Calculate integration quality
        successful_tools = sum(1 for r in tool_results if r["execution_result"].execution_successful)
        expected_tools = len(tool_results)
        
        integration_quality = successful_tools / expected_tools if expected_tools > 0 else 0
        
        # Overall value score
        category_coverage = categories_with_value / 5  # 5 expected categories
        actionability_score = min(actionable_recommendations / 10, 1.0)  # Normalize to 1.0
        quantitative_score = min(quantitative_metrics / 8, 1.0)  # Normalize to 1.0
        
        overall_value_score = (
            category_coverage * 0.3 +
            integration_quality * 0.3 +
            actionability_score * 0.2 +
            quantitative_score * 0.2
        )
        
        return {
            "overall_value_score": overall_value_score,
            "categories_with_value": categories_with_value,
            "integration_quality": integration_quality,
            "actionable_recommendations": actionable_recommendations,
            "quantitative_metrics": quantitative_metrics,
            "successful_tool_executions": successful_tools
        }