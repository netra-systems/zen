"""Core Tests - Split from test_agent_tool_atomicity_integration.py

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
import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from shared.isolated_environment import IsolatedEnvironment

import pytest

from netra_backend.app.schemas.shared_types import ProcessingResult
from tests.e2e.jwt_token_helpers import JWTTestHelper


class ToolAtomicityLevel(Enum):
    """Enum for tool atomicity levels."""
    ATOMIC = "atomic"
    COMPLEX = "complex"
    COMPOUND = "compound"
    INVALID = "invalid"


@dataclass
@pytest.mark.e2e
class ToolResultTests:
    """Result of tool atomicity testing."""
    tool_name: str
    atomicity_level: ToolAtomicityLevel
    responsibility_count: int
    error_count: int
    violations: List[str]
    execution_time_ms: float

    def is_atomic(self) -> bool:
        """Check if tool result meets atomicity requirements."""
        return (self.atomicity_level == ToolAtomicityLevel.ATOMIC and
                self.responsibility_count == 1 and
                self.error_count == 0)


@pytest.mark.e2e
class ToolAtomicityerTests:
    """Tester for agent tool atomicity."""

    def __init__(self):
        """Initialize tool atomicity tester."""
        self.jwt_helper = JWTTestHelper()
        self.backend_url = "http://localhost:8000"
        self.test_tools = self._define_test_tools()
        self.test_results: List[ToolResultTests] = []

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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_tool_atomicity_basic_validation():
    """Test basic tool atomicity validation."""
    tester = ToolAtomicityerTests()
    
    # Test a simple atomic output
    mock_output = {
        "cost_analysis": {
            "current_cost": 150.0,
            "optimized_cost": 120.0,
            "savings": 30.0
        }
    }
    
    tool_config = tester.test_tools["cost_analyzer"]
    result = tester._analyze_output_atomicity(mock_output, tool_config)
    
    assert result["level"] == ToolAtomicityLevel.ATOMIC
    assert result["responsibility_count"] == 1
    assert result["error_count"] == 0


@pytest.mark.asyncio
@pytest.mark.integration 
async def test_tool_complexity_detection():
    """Test detection of non-atomic tool outputs."""
    tester = ToolAtomicityerTests()
    
    # Test a complex output with multiple responsibilities
    mock_output = {
        "cost_analysis": {"cost": 150.0},
        "performance_data": {"throughput": 100},
        "optimization_plan": {"steps": ["a", "b", "c"]}
    }
    
    tool_config = tester.test_tools["cost_analyzer"]
    result = tester._analyze_output_atomicity(mock_output, tool_config)
    
    assert result["level"] != ToolAtomicityLevel.ATOMIC
    assert result["responsibility_count"] > 1
    assert len(result["violations"]) > 0
