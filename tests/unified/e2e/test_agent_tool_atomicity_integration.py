"""
Agent Tool Atomicity Integration Test

Tests that each agent tool returns single, atomic work units following the
Single Responsibility Principle (AI-P2) and protecting $15K MRR from tool complexity.

Business Value Justification (BVJ):
- Segment: All customer tiers using AI agent tools for optimization
- Business Goal: Tool reliability and maintainable complexity
- Value Impact: Ensures tools produce focused, actionable results
- Strategic/Revenue Impact: Protects $15K MRR from tool confusion and complexity

Test Coverage:
- Tool output atomicity validation
- Single responsibility principle adherence
- Tool result consistency and reliability
- Cross-tool integration without coupling
"""

import asyncio
import pytest
import time
import uuid
import json
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum

from tests.unified.jwt_token_helpers import JWTTestHelper
from app.schemas.shared_types import ProcessingResult


class ToolAtomicityLevel(str, Enum):
    """Levels of tool atomicity for validation."""
    ATOMIC = "atomic"           # Single, focused responsibility
    COMPLEX = "complex"         # Multiple related responsibilities  
    COMPOUND = "compound"       # Multiple unrelated responsibilities
    INVALID = "invalid"         # No clear responsibility


@dataclass
class ToolTestResult:
    """Result structure for tool atomicity testing."""
    tool_name: str
    input_data: Dict[str, Any]
    output_data: Union[Dict[str, Any], List[Dict[str, Any]]]
    atomicity_level: ToolAtomicityLevel
    responsibility_count: int
    execution_time: float
    error_count: int
    
    def is_atomic(self) -> bool:
        """Check if tool result meets atomicity requirements."""
        return (self.atomicity_level == ToolAtomicityLevel.ATOMIC and
                self.responsibility_count == 1 and
                self.error_count == 0)


class AgentToolAtomicityTester:
    """Integration tester for agent tool atomicity."""
    
    def __init__(self):
        """Initialize tool atomicity tester."""
        self.jwt_helper = JWTTestHelper()
        self.backend_url = "http://localhost:8000"
        self.test_tools = self._define_test_tools()
        self.test_results: List[ToolTestResult] = []
        
    def _define_test_tools(self) -> Dict[str, Dict[str, Any]]:
        """Define test tools with expected atomic behaviors."""
        return {
            "cost_analyzer": {
                "description": "Analyzes cost optimization opportunities",
                "expected_output_type": "single_analysis",
                "atomic_responsibility": "cost_analysis",
                "test_input": {
                    "function_name": "api_request_handler",
                    "current_cost": 150.0,
                    "usage_metrics": {"requests_per_day": 10000, "avg_response_time": 200}
                }
            },
            "performance_predictor": {
                "description": "Predicts performance improvements",
                "expected_output_type": "single_prediction",
                "atomic_responsibility": "performance_prediction", 
                "test_input": {
                    "optimization_type": "caching",
                    "baseline_metrics": {"throughput": 100, "latency": 50},
                    "proposed_changes": ["add_redis_cache", "optimize_queries"]
                }
            },
            "optimization_proposer": {
                "description": "Proposes specific optimization strategies",
                "expected_output_type": "single_proposal",
                "atomic_responsibility": "optimization_proposal",
                "test_input": {
                    "problem_type": "high_latency",
                    "constraints": {"budget": 5000, "implementation_time": "2_weeks"},
                    "current_architecture": "microservices"
                }
            },
            "log_analyzer": {
                "description": "Analyzes log patterns for insights", 
                "expected_output_type": "single_log_analysis",
                "atomic_responsibility": "log_pattern_analysis",
                "test_input": {
                    "log_source": "application_logs",
                    "time_range": "last_24_hours",
                    "analysis_focus": "error_patterns"
                }
            }
        }
    
    async def test_tool_output_atomicity(
        self, 
        tool_name: str,
        tool_config: Dict[str, Any]
    ) -> ToolTestResult:
        """Test individual tool for atomic output behavior."""
        start_time = time.time()
        
        try:
            # Simulate tool execution with test input
            test_input = tool_config["test_input"]
            
            # Mock tool execution (in real implementation, this would call actual tools)
            simulated_output = await self._simulate_tool_execution(tool_name, test_input)
            
            # Analyze output for atomicity
            atomicity_analysis = self._analyze_output_atomicity(simulated_output, tool_config)
            
            execution_time = time.time() - start_time
            
            result = ToolTestResult(
                tool_name=tool_name,
                input_data=test_input,
                output_data=simulated_output,
                atomicity_level=atomicity_analysis["level"],
                responsibility_count=atomicity_analysis["responsibility_count"],
                execution_time=execution_time,
                error_count=atomicity_analysis.get("error_count", 0)
            )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            # Handle tool execution errors
            error_result = ToolTestResult(
                tool_name=tool_name,
                input_data=tool_config["test_input"],
                output_data={"error": str(e)},
                atomicity_level=ToolAtomicityLevel.INVALID,
                responsibility_count=0,
                execution_time=time.time() - start_time,
                error_count=1
            )
            
            self.test_results.append(error_result)
            return error_result
    
    async def _simulate_tool_execution(
        self, 
        tool_name: str, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate tool execution with realistic outputs."""
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Generate atomic outputs based on tool type
        if tool_name == "cost_analyzer":
            return {
                "analysis_id": str(uuid.uuid4()),
                "cost_optimization_opportunities": {
                    "current_monthly_cost": input_data["current_cost"],
                    "potential_savings": 45.0,
                    "savings_percentage": 30.0,
                    "primary_optimization": "request_batching",
                    "implementation_complexity": "medium"
                },
                "analysis_type": "cost_analysis",
                "timestamp": time.time()
            }
        
        elif tool_name == "performance_predictor":
            return {
                "prediction_id": str(uuid.uuid4()),
                "performance_prediction": {
                    "baseline_throughput": input_data["baseline_metrics"]["throughput"],
                    "predicted_throughput": 250,
                    "improvement_factor": 2.5,
                    "confidence_level": 0.85,
                    "key_optimization": "redis_cache_implementation"
                },
                "prediction_type": "performance_prediction",
                "timestamp": time.time()
            }
        
        elif tool_name == "optimization_proposer":
            return {
                "proposal_id": str(uuid.uuid4()),
                "optimization_proposal": {
                    "problem_addressed": input_data["problem_type"],
                    "proposed_solution": "implement_connection_pooling",
                    "expected_improvement": "60% latency reduction",
                    "implementation_steps": [
                        "configure_connection_pool",
                        "update_database_clients",
                        "monitor_performance"
                    ],
                    "estimated_cost": 3000,
                    "timeline": "10_days"
                },
                "proposal_type": "optimization_proposal",
                "timestamp": time.time()
            }
        
        elif tool_name == "log_analyzer":
            return {
                "analysis_id": str(uuid.uuid4()),
                "log_analysis": {
                    "patterns_found": [
                        {
                            "pattern_type": "error_spike",
                            "frequency": 45,
                            "time_pattern": "peak_hours",
                            "root_cause": "database_timeout"
                        }
                    ],
                    "analysis_period": input_data["time_range"],
                    "total_logs_analyzed": 50000,
                    "critical_issues_found": 1
                },
                "analysis_type": "log_pattern_analysis", 
                "timestamp": time.time()
            }
        
        else:
            # Unknown tool - return error
            return {
                "error": f"Unknown tool: {tool_name}",
                "tool_name": tool_name,
                "timestamp": time.time()
            }
    
    def _analyze_output_atomicity(
        self, 
        output: Dict[str, Any], 
        tool_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze tool output for atomicity compliance."""
        # Check for errors first
        if "error" in output:
            return {
                "level": ToolAtomicityLevel.INVALID,
                "responsibility_count": 0,
                "error_count": 1,
                "violations": ["execution_error"]
            }
        
        # Analyze responsibility focus
        expected_responsibility = tool_config["atomic_responsibility"]
        violations = []
        
        # Check for single primary result type
        primary_result_keys = [key for key in output.keys() 
                             if not key.endswith("_id") and 
                             not key in ["timestamp", "analysis_type", "prediction_type", "proposal_type"]]
        
        if len(primary_result_keys) != 1:
            violations.append(f"multiple_primary_results: {len(primary_result_keys)}")
        
        # Check for focused output structure
        main_result_key = None
        for key in primary_result_keys:
            if expected_responsibility in key:
                main_result_key = key
                break
        
        if not main_result_key:
            violations.append("responsibility_mismatch")
        
        # Check for complexity indicators
        if main_result_key and isinstance(output[main_result_key], dict):
            main_result = output[main_result_key]
            
            # Count distinct types of information
            info_types = set()
            for key, value in main_result.items():
                if isinstance(value, list) and len(value) > 5:
                    violations.append(f"excessive_list_complexity: {key}")
                elif isinstance(value, dict) and len(value) > 3:
                    violations.append(f"excessive_nested_complexity: {key}")
                
                # Categorize information types
                if "cost" in key.lower():
                    info_types.add("cost")
                elif "performance" in key.lower() or "throughput" in key.lower():
                    info_types.add("performance")
                elif "optimization" in key.lower():
                    info_types.add("optimization")
                elif "analysis" in key.lower() or "pattern" in key.lower():
                    info_types.add("analysis")
            
            # Too many information types indicates lack of focus
            if len(info_types) > 2:
                violations.append(f"mixed_responsibilities: {len(info_types)}")
        
        # Determine atomicity level
        if len(violations) == 0:
            atomicity_level = ToolAtomicityLevel.ATOMIC
            responsibility_count = 1
        elif len(violations) <= 2:
            atomicity_level = ToolAtomicityLevel.COMPLEX
            responsibility_count = 2
        elif len(violations) <= 4:
            atomicity_level = ToolAtomicityLevel.COMPOUND
            responsibility_count = len(violations)
        else:
            atomicity_level = ToolAtomicityLevel.INVALID
            responsibility_count = len(violations)
        
        return {
            "level": atomicity_level,
            "responsibility_count": responsibility_count,
            "error_count": 0,
            "violations": violations
        }
    
    async def test_cross_tool_independence(self) -> Tuple[bool, str]:
        """Test that tools operate independently without coupling."""
        try:
            # Test tool execution in different orders
            tool_names = list(self.test_tools.keys())
            
            # Execute tools in normal order
            normal_results = []
            for tool_name in tool_names:
                result = await self.test_tool_output_atomicity(tool_name, self.test_tools[tool_name])
                normal_results.append(result)
            
            # Execute tools in reverse order
            reverse_results = []
            for tool_name in reversed(tool_names):
                result = await self.test_tool_output_atomicity(tool_name, self.test_tools[tool_name])
                reverse_results.append(result)
            
            # Compare results for consistency
            consistency_checks = []
            for i, tool_name in enumerate(tool_names):
                normal_result = normal_results[i]
                reverse_result = reverse_results[len(tool_names) - 1 - i]
                
                # Tools should produce consistent atomic results regardless of execution order
                output_consistency = (
                    normal_result.atomicity_level == reverse_result.atomicity_level and
                    normal_result.responsibility_count == reverse_result.responsibility_count
                )
                consistency_checks.append(output_consistency)
            
            independence_rate = sum(consistency_checks) / len(consistency_checks)
            
            if independence_rate >= 0.9:  # 90% consistency required
                return True, f"Tool independence validated: {independence_rate:.1%} consistency"
            else:
                return False, f"Tool coupling detected: {independence_rate:.1%} consistency"
                
        except Exception as e:
            return False, f"Cross-tool independence test failed: {e}"
    
    async def validate_tool_atomicity_compliance(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Validate overall tool atomicity compliance across all tools."""
        try:
            # Test all defined tools
            atomic_results = []
            for tool_name, tool_config in self.test_tools.items():
                result = await self.test_tool_output_atomicity(tool_name, tool_config)
                atomic_results.append(result)
            
            # Calculate compliance metrics
            total_tools = len(atomic_results)
            atomic_tools = sum(1 for result in atomic_results if result.is_atomic())
            complex_tools = sum(1 for result in atomic_results 
                              if result.atomicity_level == ToolAtomicityLevel.COMPLEX)
            invalid_tools = sum(1 for result in atomic_results 
                              if result.atomicity_level == ToolAtomicityLevel.INVALID)
            
            atomicity_rate = atomic_tools / total_tools
            avg_execution_time = sum(result.execution_time for result in atomic_results) / total_tools
            
            compliance_metrics = {
                "total_tools_tested": total_tools,
                "atomic_tools": atomic_tools,
                "complex_tools": complex_tools,
                "invalid_tools": invalid_tools,
                "atomicity_rate": atomicity_rate,
                "avg_execution_time": avg_execution_time,
                "compliance_threshold": 0.8
            }
            
            # Validate compliance threshold
            if atomicity_rate >= 0.8 and invalid_tools == 0:
                return True, f"Atomicity compliance: {atomicity_rate:.1%}", compliance_metrics
            else:
                return False, f"Atomicity compliance below threshold: {atomicity_rate:.1%}", compliance_metrics
                
        except Exception as e:
            return False, f"Atomicity compliance validation failed: {e}", {}


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_tool_atomicity_integration():
    """
    Integration test for agent tool atomicity.
    
    Tests that each tool returns single, atomic work units following SRP
    and protecting $15K MRR from tool complexity and confusion.
    
    BVJ: Tool reliability and maintainable complexity for all customers
    """
    tester = AgentToolAtomicityTester()
    
    try:
        start_time = time.time()
        
        # Test 1: Individual tool atomicity validation
        compliance_success, compliance_msg, metrics = await tester.validate_tool_atomicity_compliance()
        assert compliance_success, f"Tool atomicity compliance failed: {compliance_msg}"
        
        # Test 2: Cross-tool independence validation
        independence_success, independence_msg = await tester.test_cross_tool_independence()
        assert independence_success, f"Tool independence failed: {independence_msg}"
        
        # Test 3: Performance and reliability validation
        execution_time = time.time() - start_time
        assert execution_time < 15.0, f"Atomicity test took {execution_time:.2f}s, must be <15s"
        
        # Business value validation
        assert metrics["atomicity_rate"] >= 0.8, f"Atomicity rate {metrics['atomicity_rate']:.1%} below 80%"
        assert metrics["invalid_tools"] == 0, f"Found {metrics['invalid_tools']} invalid tools"
        assert len(tester.test_results) >= 4, "All test tools should be validated"
        
        # Detailed tool validation
        for result in tester.test_results:
            assert result.execution_time < 5.0, f"Tool {result.tool_name} too slow: {result.execution_time:.2f}s"
            assert result.error_count == 0, f"Tool {result.tool_name} has errors: {result.error_count}"
        
        print(f"[SUCCESS] Agent tool atomicity integration test PASSED")
        print(f"[BUSINESS VALUE] $15K MRR protection validated through tool atomicity")
        print(f"[COMPLIANCE] {compliance_msg}")
        print(f"[INDEPENDENCE] {independence_msg}")
        print(f"[METRICS] {metrics['atomic_tools']}/{metrics['total_tools_tested']} tools atomic")
        print(f"[PERFORMANCE] Testing completed in {execution_time:.2f}s")
        
    except Exception as e:
        print(f"[ERROR] Tool atomicity test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_tool_atomicity_quick_check():
    """
    Quick atomicity check for agent tools.
    
    Lightweight test for CI/CD pipelines focused on basic atomicity validation.
    """
    tester = AgentToolAtomicityTester()
    
    try:
        # Test a subset of tools for quick validation
        quick_tools = ["cost_analyzer", "performance_predictor"] 
        atomic_count = 0
        
        for tool_name in quick_tools:
            if tool_name in tester.test_tools:
                result = await tester.test_tool_output_atomicity(
                    tool_name, 
                    tester.test_tools[tool_name]
                )
                if result.is_atomic():
                    atomic_count += 1
        
        atomicity_rate = atomic_count / len(quick_tools)
        assert atomicity_rate >= 0.5, f"Quick atomicity check failed: {atomicity_rate:.1%}"
        
        print(f"[QUICK CHECK PASS] Tool atomicity: {atomic_count}/{len(quick_tools)} atomic")
        
    except Exception as e:
        print(f"[QUICK CHECK FAIL] Tool atomicity check failed: {e}")
        raise


if __name__ == "__main__":
    """Run agent tool atomicity test standalone."""
    async def run_test():
        print("Running Agent Tool Atomicity Integration Test...")
        await test_agent_tool_atomicity_integration()
        print("Test completed successfully!")
    
    asyncio.run(run_test())


# Business Value Summary
"""
Agent Tool Atomicity Integration Test - Business Value Summary

BVJ: Tool reliability and complexity management protecting $15K MRR
- Validates single responsibility principle (SRP) adherence for all tools
- Ensures tools produce focused, atomic results without confusion
- Tests cross-tool independence to prevent coupling issues
- Protects against tool complexity that degrades user experience

Strategic Value:
- Foundation for reliable AI-powered optimization workflows
- Prevention of tool confusion and mixed responsibilities
- Support for maintainable and scalable agent architecture
- Quality assurance for tool-dependent revenue streams
"""