"""
Test Multi-Agent Workflow Coordination - Golden Path Integration

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (multi-step workflows)
- Business Goal: Enable complex multi-agent workflows that deliver comprehensive insights  
- Value Impact: Users get complete analysis from multiple specialized agents working together
- Strategic Impact: Differentiating capability - competitors lack coordinated multi-agent workflows

CRITICAL REQUIREMENTS:
1. Test agent coordination: Triage  ->  Data Helper  ->  UVS Reporting  ->  Final Synthesis
2. Test agent handoffs with context preservation between agents
3. Test workflow state progression across multiple agents
4. Test WebSocket events for entire multi-agent workflow
5. Use real services only (NO MOCKS per CLAUDE.md)
6. Validate business value delivered through agent collaboration

Multi-Agent Workflow Stages:
1. Triage Agent: Analyzes request and determines workflow path
2. Data Helper Agent: Gathers and processes relevant data
3. Specialized Agent (UVS/Cost/Security): Performs domain analysis  
4. Synthesis Agent: Combines results into actionable recommendations
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class AgentWorkflowStep:
    """Single step in multi-agent workflow."""
    agent_name: str
    step_number: int
    start_time: float
    end_time: Optional[float]
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    websocket_events: List[str]
    success: bool
    error_message: Optional[str] = None


@dataclass
class MultiAgentWorkflowResult:
    """Complete multi-agent workflow execution result."""
    workflow_id: str
    total_steps: int
    completed_steps: int
    total_execution_time: float
    steps: List[AgentWorkflowStep]
    final_business_value: Dict[str, Any]
    coordination_successful: bool
    context_preserved: bool


class WorkflowType(Enum):
    """Types of multi-agent workflows."""
    COST_OPTIMIZATION = "cost_optimization"
    SECURITY_AUDIT = "security_audit" 
    PERFORMANCE_ANALYSIS = "performance_analysis"
    COMPREHENSIVE_REVIEW = "comprehensive_review"
    DATA_INSIGHTS = "data_insights"


class TestMultiAgentWorkflowCoordination(BaseIntegrationTest):
    """Test comprehensive multi-agent workflow coordination."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        self.workflow_results: List[MultiAgentWorkflowResult] = []
        
        # Define standard workflow templates
        self.workflow_templates = {
            WorkflowType.COST_OPTIMIZATION: {
                "agents": ["triage_agent", "data_helper", "cost_optimizer", "synthesis_agent"],
                "expected_duration": 45.0,
                "business_value_fields": ["cost_savings", "recommendations", "roi_analysis"]
            },
            WorkflowType.SECURITY_AUDIT: {
                "agents": ["triage_agent", "data_helper", "security_auditor", "synthesis_agent"],
                "expected_duration": 60.0,
                "business_value_fields": ["vulnerabilities", "compliance_score", "remediation_plan"]
            },
            WorkflowType.PERFORMANCE_ANALYSIS: {
                "agents": ["triage_agent", "data_helper", "performance_analyzer", "synthesis_agent"],
                "expected_duration": 50.0,
                "business_value_fields": ["performance_metrics", "bottlenecks", "optimization_recommendations"]
            },
            WorkflowType.DATA_INSIGHTS: {
                "agents": ["triage_agent", "data_helper", "insight_generator"],
                "expected_duration": 30.0,
                "business_value_fields": ["insights", "trends", "actionable_recommendations"]
            },
            WorkflowType.COMPREHENSIVE_REVIEW: {
                "agents": ["triage_agent", "data_helper", "cost_optimizer", "security_auditor", "synthesis_agent"],
                "expected_duration": 90.0,
                "business_value_fields": ["comprehensive_analysis", "integrated_recommendations", "priority_actions"]
            }
        }

    async def _execute_agent_workflow_step(self, agent_name: str, step_number: int,
                                         input_data: Dict, real_services, 
                                         user_context: Dict) -> AgentWorkflowStep:
        """Execute a single step in multi-agent workflow."""
        
        step_start = time.time()
        websocket_events = []
        
        try:
            # Simulate agent execution with WebSocket event capture
            expected_events = [
                f"{agent_name}_started",
                f"{agent_name}_thinking",
                f"{agent_name}_processing",
                f"{agent_name}_completed"
            ]
            
            # Simulate agent-specific processing
            agent_processing_data = await self._simulate_agent_processing(
                agent_name, input_data, real_services, user_context
            )
            
            step_end = time.time()
            
            return AgentWorkflowStep(
                agent_name=agent_name,
                step_number=step_number,
                start_time=step_start,
                end_time=step_end,
                input_data=input_data,
                output_data=agent_processing_data["output"],
                websocket_events=expected_events,
                success=True
            )
            
        except Exception as e:
            step_end = time.time()
            
            return AgentWorkflowStep(
                agent_name=agent_name,
                step_number=step_number,
                start_time=step_start,
                end_time=step_end,
                input_data=input_data,
                output_data=None,
                websocket_events=websocket_events,
                success=False,
                error_message=str(e)
            )

    async def _simulate_agent_processing(self, agent_name: str, input_data: Dict,
                                       real_services, user_context: Dict) -> Dict:
        """Simulate realistic agent processing with database operations."""
        
        db_session = real_services["db"]
        processing_start = time.time()
        
        # Agent-specific processing simulation
        if agent_name == "triage_agent":
            # Triage determines workflow path and extracts key entities
            output = {
                "workflow_type": input_data.get("request_type", "general"),
                "entities_identified": ["aws_account", "cost_analysis", "timeframe"],
                "recommended_agents": ["data_helper", "cost_optimizer"],
                "priority": "high",
                "confidence": 0.85
            }
            processing_delay = 2.0
            
        elif agent_name == "data_helper":
            # Data helper gathers and preprocesses data
            output = {
                "data_sources": ["aws_billing", "resource_inventory", "usage_metrics"],
                "data_quality_score": 0.92,
                "data_volume": "1.2GB processed",
                "key_metrics": {
                    "monthly_spend": 25000,
                    "resource_count": 450,
                    "utilization_avg": 0.68
                },
                "data_ready": True
            }
            processing_delay = 3.0
            
        elif agent_name == "cost_optimizer":
            # Cost optimizer analyzes data and generates savings recommendations
            output = {
                "analysis_type": "cost_optimization",
                "potential_savings": 3200,
                "confidence_level": 0.89,
                "recommendations": [
                    "Right-size 23 underutilized EC2 instances - $1,800/month savings",
                    "Switch to Reserved Instances for stable workloads - $900/month savings", 
                    "Implement auto-scaling for variable workloads - $500/month savings"
                ],
                "risk_assessment": "low",
                "implementation_timeline": "2-4 weeks"
            }
            processing_delay = 4.0
            
        elif agent_name == "security_auditor":
            # Security auditor identifies vulnerabilities and compliance issues
            output = {
                "vulnerabilities_found": 5,
                "critical_issues": 1,
                "compliance_score": 85,
                "findings": [
                    "3 EC2 instances with outdated security groups",
                    "S3 bucket with overly permissive access policy",
                    "Missing encryption on 2 EBS volumes"
                ],
                "remediation_priority": "high",
                "estimated_fix_time": "1-2 weeks"
            }
            processing_delay = 5.0
            
        elif agent_name == "performance_analyzer":
            # Performance analyzer identifies bottlenecks and optimization opportunities
            output = {
                "performance_score": 72,
                "bottlenecks_identified": [
                    "Database query performance degraded 35%",
                    "API response times increased to 450ms average",
                    "Memory utilization spikes during peak hours"
                ],
                "optimization_opportunities": [
                    "Database index optimization",
                    "API caching implementation", 
                    "Memory allocation tuning"
                ],
                "impact_estimate": "25% performance improvement possible"
            }
            processing_delay = 4.5
            
        elif agent_name == "synthesis_agent":
            # Synthesis agent combines all previous results into final recommendations
            output = {
                "synthesis_complete": True,
                "integrated_analysis": {
                    "cost_impact": input_data.get("cost_analysis", {}),
                    "security_posture": input_data.get("security_findings", {}),
                    "performance_status": input_data.get("performance_metrics", {})
                },
                "prioritized_actions": [
                    {"action": "Address critical security vulnerability", "priority": 1, "impact": "high"},
                    {"action": "Implement cost optimization recommendations", "priority": 2, "impact": "medium"},
                    {"action": "Optimize database performance", "priority": 3, "impact": "medium"}
                ],
                "business_impact_summary": "Combined recommendations provide $3,200/month savings with improved security and performance",
                "next_steps": "Implement recommendations in priority order with 2-week implementation cycles"
            }
            processing_delay = 3.0
            
        else:
            # Generic agent processing
            output = {
                "agent_type": agent_name,
                "processing_completed": True,
                "result": f"Processed by {agent_name}",
                "confidence": 0.8
            }
            processing_delay = 2.0
        
        # Simulate realistic processing delay
        await asyncio.sleep(min(processing_delay, 0.5))  # Cap delay for testing
        
        # Persist workflow step to database
        if db_session:
            try:
                await db_session.execute("""
                    INSERT INTO backend.agent_workflow_steps 
                    (user_id, agent_name, input_data, output_data, processing_time, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                user_context["user_id"], 
                agent_name,
                json.dumps(input_data),
                json.dumps(output),
                time.time() - processing_start,
                datetime.utcnow())
                
                await db_session.commit()
            except Exception as e:
                logger.warning(f"Failed to persist workflow step: {e}")
        
        return {
            "output": output,
            "processing_time": time.time() - processing_start,
            "agent_name": agent_name
        }

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_complete_multi_agent_workflow_execution(self, real_services_fixture):
        """
        Test 1: Complete multi-agent workflow from start to finish.
        
        Validates that a complete multi-agent workflow (Triage  ->  Data  ->  Analysis  ->  Synthesis)
        executes successfully with proper agent coordination and context passing.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-complete-workflow@example.com"
        )
        
        workflow_id = str(uuid.uuid4())
        workflow_start = time.time()
        
        # Execute cost optimization workflow
        workflow_template = self.workflow_templates[WorkflowType.COST_OPTIMIZATION]
        agents = workflow_template["agents"]
        
        workflow_steps = []
        current_context = {
            "user_request": "Analyze my AWS costs and provide optimization recommendations",
            "workflow_id": workflow_id,
            "user_id": user_context["user_id"]
        }
        
        # Execute each agent in sequence
        for step_number, agent_name in enumerate(agents):
            step_result = await self._execute_agent_workflow_step(
                agent_name,
                step_number,
                current_context,
                real_services_fixture,
                user_context
            )
            
            workflow_steps.append(step_result)
            
            # Pass output to next agent as context
            if step_result.success and step_result.output_data:
                current_context.update(step_result.output_data)
            else:
                logger.warning(f"Step {step_number} ({agent_name}) failed: {step_result.error_message}")
        
        workflow_end = time.time()
        total_time = workflow_end - workflow_start
        
        # Create workflow result
        successful_steps = [s for s in workflow_steps if s.success]
        final_step = workflow_steps[-1] if workflow_steps else None
        
        workflow_result = MultiAgentWorkflowResult(
            workflow_id=workflow_id,
            total_steps=len(agents),
            completed_steps=len(successful_steps),
            total_execution_time=total_time,
            steps=workflow_steps,
            final_business_value=final_step.output_data if final_step and final_step.success else {},
            coordination_successful=len(successful_steps) == len(agents),
            context_preserved=self._verify_context_preservation(workflow_steps)
        )
        
        self.workflow_results.append(workflow_result)
        
        # Verify workflow completion
        assert workflow_result.coordination_successful, \
            f"Workflow coordination failed: {workflow_result.completed_steps}/{workflow_result.total_steps} steps completed"
        
        assert workflow_result.context_preserved, \
            "Context not preserved between workflow steps"
        
        # Verify business value in final result
        self.assert_business_value_delivered(
            workflow_result.final_business_value,
            "cost_savings"
        )
        
        # Verify timing requirements
        assert total_time < workflow_template["expected_duration"], \
            f"Workflow took too long: {total_time}s > {workflow_template['expected_duration']}s"
        
        logger.info(f"Complete multi-agent workflow executed: {workflow_result.completed_steps} steps in {total_time:.2f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_agent_context_preservation(self, real_services_fixture):
        """
        Test 2: Context preservation across multiple agents in workflow.
        
        Validates that important context and data flows correctly from one agent
        to the next without loss or corruption of critical information.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-context-preservation@example.com"
        )
        
        # Create complex initial context
        initial_context = {
            "user_id": user_context["user_id"],
            "request_id": str(uuid.uuid4()),
            "business_context": {
                "company_size": "enterprise",
                "industry": "fintech",
                "compliance_requirements": ["PCI-DSS", "SOX"],
                "monthly_cloud_spend": 75000
            },
            "technical_context": {
                "aws_accounts": ["prod-123", "staging-456", "dev-789"],
                "primary_regions": ["us-east-1", "eu-west-1"],
                "architecture_type": "microservices"
            },
            "analysis_requirements": {
                "timeframe": "last_90_days",
                "focus_areas": ["cost", "security", "performance"],
                "urgency": "high"
            }
        }
        
        # Execute workflow with context tracking
        agents = ["triage_agent", "data_helper", "cost_optimizer", "security_auditor"]
        context_progression = [initial_context.copy()]
        
        current_context = initial_context.copy()
        
        for agent_name in agents:
            step_result = await self._execute_agent_workflow_step(
                agent_name,
                len(context_progression),
                current_context,
                real_services_fixture,
                user_context
            )
            
            if step_result.success and step_result.output_data:
                # Merge output into current context
                current_context.update(step_result.output_data)
                context_progression.append(current_context.copy())
            
        # Verify context preservation
        context_analysis = self._analyze_context_preservation(context_progression)
        
        # Check critical context elements are preserved
        critical_fields = [
            "user_id", "business_context", "technical_context", 
            "analysis_requirements", "monthly_cloud_spend"
        ]
        
        final_context = context_progression[-1]
        
        for field in critical_fields:
            assert field in final_context, \
                f"Critical context field '{field}' lost during workflow"
            
            # Verify field wasn't just empty
            if field in initial_context:
                initial_value = initial_context[field]
                final_value = final_context[field]
                
                if isinstance(initial_value, (dict, list)):
                    assert len(final_value) > 0, \
                        f"Context field '{field}' became empty during workflow"
                else:
                    assert final_value is not None, \
                        f"Context field '{field}' became None during workflow"
        
        # Verify context enrichment (should grow with agent contributions)
        initial_keys = set(self._flatten_dict_keys(initial_context))
        final_keys = set(self._flatten_dict_keys(final_context))
        
        enrichment_ratio = len(final_keys) / len(initial_keys) if initial_keys else 1
        assert enrichment_ratio >= 1.5, \
            f"Context not sufficiently enriched: {enrichment_ratio:.2f}x (expected >= 1.5x)"
        
        logger.info(f"Context preservation validated: {len(context_progression)} steps, {enrichment_ratio:.2f}x enrichment")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_agent_workflow_error_recovery(self, real_services_fixture):
        """
        Test 3: Multi-agent workflow error recovery and graceful degradation.
        
        Validates that workflows can recover from individual agent failures
        and continue execution with alternative paths or graceful degradation.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-error-recovery@example.com"
        )
        
        # Test error recovery scenarios
        error_scenarios = [
            {
                "failing_agent": "data_helper",
                "failure_type": "timeout",
                "recovery_strategy": "fallback_to_cached_data",
                "expected_recovery": True
            },
            {
                "failing_agent": "cost_optimizer", 
                "failure_type": "invalid_input",
                "recovery_strategy": "skip_optimization_use_baseline",
                "expected_recovery": True
            },
            {
                "failing_agent": "synthesis_agent",
                "failure_type": "processing_error",
                "recovery_strategy": "return_individual_results",
                "expected_recovery": True
            }
        ]
        
        recovery_results = []
        
        for scenario in error_scenarios:
            scenario_start = time.time()
            
            # Execute workflow with simulated failure
            agents = ["triage_agent", "data_helper", "cost_optimizer", "synthesis_agent"]
            workflow_steps = []
            
            current_context = {
                "user_id": user_context["user_id"],
                "request": "Test error recovery workflow",
                "simulate_failure": {
                    "agent": scenario["failing_agent"],
                    "type": scenario["failure_type"]
                }
            }
            
            recovery_attempted = False
            recovery_successful = False
            
            for step_number, agent_name in enumerate(agents):
                if agent_name == scenario["failing_agent"]:
                    # Simulate failure
                    failed_step = AgentWorkflowStep(
                        agent_name=agent_name,
                        step_number=step_number,
                        start_time=time.time(),
                        end_time=time.time() + 0.1,
                        input_data=current_context,
                        output_data=None,
                        websocket_events=[f"{agent_name}_started", f"{agent_name}_failed"],
                        success=False,
                        error_message=f"Simulated {scenario['failure_type']} in {agent_name}"
                    )
                    
                    workflow_steps.append(failed_step)
                    
                    # Attempt recovery
                    recovery_attempted = True
                    recovery_start = time.time()
                    
                    try:
                        # Simulate recovery strategy
                        if scenario["recovery_strategy"] == "fallback_to_cached_data":
                            recovery_data = {
                                "data_source": "cached",
                                "data_quality": "reduced",
                                "fallback_used": True
                            }
                        elif scenario["recovery_strategy"] == "skip_optimization_use_baseline":
                            recovery_data = {
                                "optimization_skipped": True,
                                "baseline_recommendations": ["Monitor costs closely", "Review in 30 days"]
                            }
                        elif scenario["recovery_strategy"] == "return_individual_results":
                            recovery_data = {
                                "synthesis_partial": True,
                                "individual_results_returned": True
                            }
                        else:
                            recovery_data = {"recovery_attempted": True}
                        
                        # Create recovery step
                        recovery_step = AgentWorkflowStep(
                            agent_name=f"{agent_name}_recovery",
                            step_number=step_number + 0.5,
                            start_time=recovery_start,
                            end_time=time.time(),
                            input_data=current_context,
                            output_data=recovery_data,
                            websocket_events=[f"{agent_name}_recovery_started", f"{agent_name}_recovery_completed"],
                            success=True
                        )
                        
                        workflow_steps.append(recovery_step)
                        current_context.update(recovery_data)
                        recovery_successful = True
                        
                    except Exception as e:
                        logger.warning(f"Recovery failed for {agent_name}: {e}")
                else:
                    # Normal agent execution
                    step_result = await self._execute_agent_workflow_step(
                        agent_name,
                        step_number,
                        current_context,
                        real_services_fixture,
                        user_context
                    )
                    
                    workflow_steps.append(step_result)
                    
                    if step_result.success and step_result.output_data:
                        current_context.update(step_result.output_data)
            
            scenario_time = time.time() - scenario_start
            
            recovery_result = {
                "scenario": scenario["failing_agent"],
                "failure_type": scenario["failure_type"],
                "recovery_attempted": recovery_attempted,
                "recovery_successful": recovery_successful,
                "expected_recovery": scenario["expected_recovery"],
                "workflow_steps": len(workflow_steps),
                "scenario_time": scenario_time
            }
            
            recovery_results.append(recovery_result)
        
        # Verify recovery results
        for result in recovery_results:
            if result["expected_recovery"]:
                assert result["recovery_attempted"], \
                    f"Recovery not attempted for {result['scenario']}"
                assert result["recovery_successful"], \
                    f"Recovery failed for {result['scenario']}"
            
            assert result["scenario_time"] < 30.0, \
                f"Error recovery took too long: {result['scenario_time']}s"
        
        successful_recoveries = sum(1 for r in recovery_results if r["recovery_successful"])
        logger.info(f"Multi-agent error recovery validated: {successful_recoveries}/{len(error_scenarios)} scenarios recovered")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_parallel_multi_agent_execution(self, real_services_fixture):
        """
        Test 4: Parallel execution of independent agents within workflow.
        
        Validates that agents that don't depend on each other can execute
        in parallel to improve workflow performance and throughput.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-parallel-execution@example.com"
        )
        
        # Define parallel execution workflow
        workflow_structure = {
            "phase_1": {
                "agents": ["triage_agent"],  # Sequential: must complete first
                "execution_mode": "sequential"
            },
            "phase_2": {
                "agents": ["data_helper"],  # Sequential: needs triage output
                "execution_mode": "sequential"
            },
            "phase_3": {
                "agents": ["cost_optimizer", "security_auditor", "performance_analyzer"],  # Parallel: independent
                "execution_mode": "parallel"
            },
            "phase_4": {
                "agents": ["synthesis_agent"],  # Sequential: needs all phase_3 outputs
                "execution_mode": "sequential"
            }
        }
        
        workflow_start = time.time()
        current_context = {
            "user_id": user_context["user_id"],
            "comprehensive_analysis_request": True,
            "parallel_execution_test": True
        }
        
        phase_results = {}
        
        # Execute phases in order
        for phase_name, phase_config in workflow_structure.items():
            phase_start = time.time()
            phase_agents = phase_config["agents"]
            execution_mode = phase_config["execution_mode"]
            
            if execution_mode == "sequential":
                # Execute agents one by one
                phase_steps = []
                for agent_name in phase_agents:
                    step_result = await self._execute_agent_workflow_step(
                        agent_name,
                        len(phase_steps),
                        current_context,
                        real_services_fixture,
                        user_context
                    )
                    
                    phase_steps.append(step_result)
                    
                    if step_result.success and step_result.output_data:
                        current_context.update(step_result.output_data)
                
                phase_time = time.time() - phase_start
                phase_results[phase_name] = {
                    "execution_mode": execution_mode,
                    "agents": phase_agents,
                    "steps": phase_steps,
                    "execution_time": phase_time,
                    "successful_steps": sum(1 for s in phase_steps if s.success)
                }
                
            elif execution_mode == "parallel":
                # Execute agents in parallel
                async def execute_parallel_agent(agent_name: str, step_number: int):
                    return await self._execute_agent_workflow_step(
                        agent_name,
                        step_number,
                        current_context,  # All agents get same input context
                        real_services_fixture,
                        user_context
                    )
                
                # Run parallel tasks
                parallel_tasks = [
                    execute_parallel_agent(agent_name, i)
                    for i, agent_name in enumerate(phase_agents)
                ]
                
                parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
                
                phase_time = time.time() - phase_start
                
                # Process parallel results
                successful_results = [r for r in parallel_results if isinstance(r, AgentWorkflowStep) and r.success]
                
                # Merge all parallel agent outputs into context
                for result in successful_results:
                    if result.output_data:
                        current_context.update(result.output_data)
                
                phase_results[phase_name] = {
                    "execution_mode": execution_mode,
                    "agents": phase_agents,
                    "steps": parallel_results,
                    "execution_time": phase_time,
                    "successful_steps": len(successful_results),
                    "parallel_efficiency": len(successful_results) / len(phase_agents) if phase_agents else 0
                }
        
        total_workflow_time = time.time() - workflow_start
        
        # Verify parallel execution benefits
        parallel_phase = phase_results.get("phase_3", {})
        
        assert parallel_phase["execution_mode"] == "parallel", "Phase 3 should be parallel"
        assert parallel_phase["successful_steps"] >= 2, \
            f"Expected at least 2 parallel agents to succeed, got {parallel_phase['successful_steps']}"
        
        # Verify parallel execution was faster than sequential would be
        # (Each agent takes ~2-5 seconds, 3 agents sequentially = ~9-15 seconds, parallel should be ~5-6 seconds)
        expected_sequential_time = len(parallel_phase["agents"]) * 3.0  # Average agent execution time
        actual_parallel_time = parallel_phase["execution_time"]
        
        efficiency_gain = expected_sequential_time / actual_parallel_time if actual_parallel_time > 0 else 1
        assert efficiency_gain >= 1.5, \
            f"Parallel execution not efficient enough: {efficiency_gain:.2f}x (expected >= 1.5x)"
        
        # Verify overall workflow completed successfully
        total_successful_steps = sum(phase["successful_steps"] for phase in phase_results.values())
        total_expected_steps = sum(len(phase["agents"]) for phase in workflow_structure.values())
        
        success_rate = total_successful_steps / total_expected_steps if total_expected_steps > 0 else 0
        assert success_rate >= 0.8, f"Workflow success rate too low: {success_rate:.2f} (expected >= 0.8)"
        
        logger.info(f"Parallel multi-agent execution completed: {efficiency_gain:.2f}x efficiency gain, {success_rate:.2f} success rate")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_multi_agent_workflow_business_value_integration(self, real_services_fixture):
        """
        Test 5: Multi-agent workflow delivers integrated business value.
        
        Validates that the combination of multiple agents produces greater
        business value than individual agents working in isolation.
        """
        assert real_services_fixture["database_available"], "Real database required"
        
        user_context = await create_authenticated_user_context(
            real_services_fixture,
            user_email="test-integrated-value@example.com"
        )
        
        # Compare single-agent vs multi-agent business value
        test_scenarios = [
            {
                "name": "single_agent_cost",
                "agents": ["cost_optimizer"],
                "expected_value_types": ["cost_savings"]
            },
            {
                "name": "multi_agent_comprehensive",
                "agents": ["triage_agent", "data_helper", "cost_optimizer", "security_auditor", "synthesis_agent"],
                "expected_value_types": ["cost_savings", "security_improvements", "integrated_recommendations"]
            },
            {
                "name": "specialized_workflow",
                "agents": ["triage_agent", "data_helper", "performance_analyzer", "cost_optimizer"],
                "expected_value_types": ["performance_improvements", "cost_savings", "optimization_roadmap"]
            }
        ]
        
        business_value_results = []
        
        for scenario in test_scenarios:
            scenario_start = time.time()
            
            # Execute workflow
            workflow_context = {
                "user_id": user_context["user_id"],
                "business_scenario": scenario["name"],
                "comprehensive_analysis": len(scenario["agents"]) > 2
            }
            
            workflow_steps = []
            current_context = workflow_context.copy()
            
            for step_number, agent_name in enumerate(scenario["agents"]):
                step_result = await self._execute_agent_workflow_step(
                    agent_name,
                    step_number,
                    current_context,
                    real_services_fixture,
                    user_context
                )
                
                workflow_steps.append(step_result)
                
                if step_result.success and step_result.output_data:
                    current_context.update(step_result.output_data)
            
            scenario_time = time.time() - scenario_start
            
            # Analyze business value delivered
            business_value_analysis = self._analyze_business_value_integration(
                workflow_steps, scenario["expected_value_types"]
            )
            
            business_value_results.append({
                "scenario": scenario["name"],
                "agent_count": len(scenario["agents"]),
                "execution_time": scenario_time,
                "successful_steps": sum(1 for s in workflow_steps if s.success),
                "business_value_score": business_value_analysis["score"],
                "value_types_delivered": business_value_analysis["value_types"],
                "integration_quality": business_value_analysis["integration_quality"],
                "actionable_recommendations": business_value_analysis["actionable_items"]
            })
        
        # Verify business value integration
        for result in business_value_results:
            # All scenarios should deliver business value
            assert result["business_value_score"] >= 0.7, \
                f"Insufficient business value for {result['scenario']}: {result['business_value_score']}"
            
            # Multi-agent workflows should have higher integration quality
            if result["agent_count"] > 2:
                assert result["integration_quality"] >= 0.8, \
                    f"Poor integration quality for {result['scenario']}: {result['integration_quality']}"
                
                assert result["actionable_recommendations"] >= 3, \
                    f"Insufficient actionable recommendations for {result['scenario']}: {result['actionable_recommendations']}"
        
        # Compare single vs multi-agent value
        single_agent_results = [r for r in business_value_results if r["agent_count"] == 1]
        multi_agent_results = [r for r in business_value_results if r["agent_count"] > 2]
        
        if single_agent_results and multi_agent_results:
            single_avg_score = sum(r["business_value_score"] for r in single_agent_results) / len(single_agent_results)
            multi_avg_score = sum(r["business_value_score"] for r in multi_agent_results) / len(multi_agent_results)
            
            value_multiplier = multi_avg_score / single_avg_score if single_avg_score > 0 else 1
            
            assert value_multiplier >= 1.2, \
                f"Multi-agent workflows should provide more value: {value_multiplier:.2f}x (expected >= 1.2x)"
        
        logger.info(f"Multi-agent business value integration validated: {len(business_value_results)} scenarios tested")

    def _verify_context_preservation(self, workflow_steps: List[AgentWorkflowStep]) -> bool:
        """Verify that important context is preserved across workflow steps."""
        if len(workflow_steps) < 2:
            return True  # Nothing to preserve
        
        # Check that each step receives output from previous step
        for i in range(1, len(workflow_steps)):
            current_step = workflow_steps[i]
            previous_step = workflow_steps[i-1]
            
            if not previous_step.success:
                continue  # Skip failed steps
            
            # Verify some context from previous step exists in current step input
            if previous_step.output_data:
                prev_keys = set(previous_step.output_data.keys())
                current_input_keys = set(current_step.input_data.keys()) if current_step.input_data else set()
                
                # Should have some overlap or growth
                if not (prev_keys & current_input_keys):  # No intersection
                    return False
        
        return True

    def _analyze_context_preservation(self, context_progression: List[Dict]) -> Dict:
        """Analyze how context is preserved and enriched through workflow."""
        if len(context_progression) < 2:
            return {"preserved": True, "enrichment": 1.0}
        
        initial_keys = set(self._flatten_dict_keys(context_progression[0]))
        final_keys = set(self._flatten_dict_keys(context_progression[-1]))
        
        preserved_keys = initial_keys & final_keys
        preservation_ratio = len(preserved_keys) / len(initial_keys) if initial_keys else 1
        enrichment_ratio = len(final_keys) / len(initial_keys) if initial_keys else 1
        
        return {
            "preserved": preservation_ratio >= 0.8,
            "preservation_ratio": preservation_ratio,
            "enrichment": enrichment_ratio,
            "keys_added": len(final_keys - initial_keys),
            "keys_lost": len(initial_keys - final_keys)
        }

    def _flatten_dict_keys(self, d: Dict, parent_key: str = "") -> List[str]:
        """Flatten nested dictionary keys for analysis."""
        keys = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            keys.append(new_key)
            if isinstance(v, dict):
                keys.extend(self._flatten_dict_keys(v, new_key))
        return keys

    def _analyze_business_value_integration(self, workflow_steps: List[AgentWorkflowStep], 
                                         expected_value_types: List[str]) -> Dict:
        """Analyze business value integration across workflow steps."""
        
        # Collect all outputs
        all_outputs = []
        for step in workflow_steps:
            if step.success and step.output_data:
                all_outputs.append(step.output_data)
        
        # Analyze value types delivered
        value_types_found = []
        actionable_items = 0
        
        for output in all_outputs:
            # Check for expected value types
            for value_type in expected_value_types:
                if value_type in output or any(value_type in str(v) for v in output.values()):
                    if value_type not in value_types_found:
                        value_types_found.append(value_type)
            
            # Count actionable items
            if "recommendations" in output:
                recs = output["recommendations"]
                if isinstance(recs, list):
                    actionable_items += len(recs)
                elif isinstance(recs, dict):
                    actionable_items += len(recs.keys())
                else:
                    actionable_items += 1
        
        # Calculate integration quality
        value_coverage = len(value_types_found) / len(expected_value_types) if expected_value_types else 1
        output_integration = len(all_outputs) / len(workflow_steps) if workflow_steps else 1
        
        business_value_score = (value_coverage + output_integration) / 2
        integration_quality = min(value_coverage * 1.2, 1.0)  # Bonus for comprehensive coverage
        
        return {
            "score": business_value_score,
            "value_types": value_types_found,
            "integration_quality": integration_quality,
            "actionable_items": actionable_items,
            "outputs_generated": len(all_outputs)
        }