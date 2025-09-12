"""
Mock Failure Simulator

Helper utility to simulate various failure conditions that might trigger
mock/fallback responses in the Netra system. Used by mock response elimination
tests to prove that fallback responses can reach users.

Business Value: Validates system behavior under failure conditions to ensure
users receive authentic error handling instead of mock responses.
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can be simulated."""
    LLM_API_FAILURE = "llm_api_failure"
    DATABASE_FAILURE = "database_failure" 
    TIMEOUT_FAILURE = "timeout_failure"
    RATE_LIMIT_FAILURE = "rate_limit_failure"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    NETWORK_FAILURE = "network_failure"
    AUTHENTICATION_FAILURE = "authentication_failure"
    DATA_ACCESS_FAILURE = "data_access_failure"


@dataclass
class FailureScenario:
    """Represents a specific failure scenario to simulate."""
    failure_type: FailureType
    trigger_pattern: str
    expected_fallback: str
    business_impact: str
    recovery_time_ms: int = 5000
    severity: str = "medium"


class MockFailureSimulator:
    """
    Simulates various failure conditions to test mock response elimination.
    
    This class helps create failure scenarios that might trigger fallback
    responses, allowing tests to validate that authentic error handling
    is used instead of mock responses.
    """
    
    def __init__(self):
        self.failure_scenarios = self._initialize_failure_scenarios()
        self.active_failures = {}
    
    def _initialize_failure_scenarios(self) -> List[FailureScenario]:
        """Initialize predefined failure scenarios."""
        return [
            FailureScenario(
                failure_type=FailureType.LLM_API_FAILURE,
                trigger_pattern=" ALERT:  SIMULATE_LLM_FAILURE  ALERT: ",
                expected_fallback="I apologize, but I encountered an error processing your request.",
                business_impact="Users receive generic error instead of authentic AI response",
                severity="high"
            ),
            FailureScenario(
                failure_type=FailureType.DATA_ACCESS_FAILURE,
                trigger_pattern="SYSTEM_FAILURE_TEST",
                expected_fallback="_generate_fallback_data() returns mock analytics",
                business_impact="Users receive fabricated data as if it were real analytics",
                severity="critical"
            ),
            FailureScenario(
                failure_type=FailureType.TIMEOUT_FAILURE,
                trigger_pattern="TIMEOUT_SCENARIO_" + "X" * 1000,
                expected_fallback="Processing completed with fallback response",
                business_impact="Users misled about processing completion", 
                severity="medium"
            ),
            FailureScenario(
                failure_type=FailureType.MEMORY_EXHAUSTION,
                trigger_pattern="MEMORY_OVERLOAD_" + "DATA" * 2000,
                expected_fallback="System resource limitation response",
                business_impact="Generic resource error instead of specific guidance",
                severity="high"
            ),
            FailureScenario(
                failure_type=FailureType.RATE_LIMIT_FAILURE,
                trigger_pattern="RATE_LIMIT_TRIGGER",
                expected_fallback="Service temporarily unavailable",
                business_impact="No guidance on when service will be available",
                severity="medium"
            )
        ]
    
    def get_failure_scenario(self, failure_type: FailureType) -> Optional[FailureScenario]:
        """Get a specific failure scenario by type."""
        for scenario in self.failure_scenarios:
            if scenario.failure_type == failure_type:
                return scenario
        return None
    
    def create_llm_failure_query(
        self, 
        base_message: str = "Analyze cost optimization",
        complexity_multiplier: int = 1000
    ) -> Dict[str, Any]:
        """
        Create a query designed to trigger LLM API failures.
        
        Args:
            base_message: Base message to expand
            complexity_multiplier: How much to expand the message
            
        Returns:
            Query dictionary designed to overwhelm LLM processing
        """
        scenario = self.get_failure_scenario(FailureType.LLM_API_FAILURE)
        
        # Create overwhelmingly complex query
        complex_message = (
            f"{scenario.trigger_pattern} {base_message} " +
            "Complex nested analysis with overwhelming parameters: " +
            "x" * complexity_multiplier
        )
        
        return {
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": complex_message,
            "context": {
                "failure_simulation": True,
                "failure_type": "llm_api_failure",
                "expected_fallback": scenario.expected_fallback
            },
            "request_id": f"llm_failure_test_{int(time.time())}"
        }
    
    def create_data_access_failure_query(
        self,
        analytics_request: str = "Generate comprehensive analytics report"
    ) -> Dict[str, Any]:
        """
        Create a query designed to trigger data access failures.
        
        Args:
            analytics_request: Type of analytics to request
            
        Returns:
            Query dictionary designed to trigger data access failure
        """
        scenario = self.get_failure_scenario(FailureType.DATA_ACCESS_FAILURE)
        
        failure_message = f"{scenario.trigger_pattern}: {analytics_request}"
        
        return {
            "type": "agent_request",
            "agent": "unified_data_agent", 
            "message": failure_message,
            "context": {
                "failure_simulation": True,
                "failure_type": "data_access_failure",
                "expected_fallback": scenario.expected_fallback,
                "analytics_required": True
            },
            "request_id": f"data_failure_test_{int(time.time())}"
        }
    
    def create_execution_timeout_query(
        self,
        base_request: str = "Complex processing request"
    ) -> Dict[str, Any]:
        """
        Create a query designed to trigger execution timeouts.
        
        Args:
            base_request: Base request to make complex
            
        Returns:
            Query dictionary designed to cause timeout
        """
        scenario = self.get_failure_scenario(FailureType.TIMEOUT_FAILURE)
        
        timeout_message = f"{base_request} {scenario.trigger_pattern}"
        
        return {
            "type": "agent_request",
            "agent": "enhanced_execution_agent",
            "message": timeout_message,
            "context": {
                "failure_simulation": True,
                "failure_type": "timeout_failure", 
                "expected_fallback": scenario.expected_fallback,
                "complexity": "extreme"
            },
            "request_id": f"timeout_test_{int(time.time())}"
        }
    
    def create_enterprise_critical_failure_query(
        self,
        business_scenario: str,
        arr_value: int = 500000
    ) -> Dict[str, Any]:
        """
        Create a failure query for enterprise customers where mock responses
        would have severe business impact.
        
        Args:
            business_scenario: Description of business scenario
            arr_value: Annual recurring revenue value for the customer
            
        Returns:
            Query designed to trigger failures in high-value scenarios
        """
        failure_triggers = [
            " ALERT:  FORCE_FAILURE_SCENARIO  ALERT: ",
            "CRITICAL_SYSTEM_OVERLOAD",
            "ENTERPRISE_STRESS_TEST"
        ]
        
        trigger = random.choice(failure_triggers)
        
        critical_message = f"{trigger} {business_scenario}"
        
        return {
            "type": "agent_request",
            "agent": "cost_optimizer",
            "message": critical_message,
            "context": {
                "failure_simulation": True,
                "enterprise_critical": True,
                "arr_value": arr_value,
                "business_impact": "critical",
                "mock_response_unacceptable": True
            },
            "request_id": f"enterprise_critical_failure_{int(time.time())}"
        }
    
    def analyze_response_for_mock_indicators(
        self,
        response_content: str,
        expected_authentic_indicators: List[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a response to detect mock/fallback indicators.
        
        Args:
            response_content: The response content to analyze
            expected_authentic_indicators: List of indicators that suggest authenticity
            
        Returns:
            Analysis results with mock detection and authenticity assessment
        """
        if expected_authentic_indicators is None:
            expected_authentic_indicators = [
                "authentic analysis",
                "real data", 
                "verified information",
                "service unavailable - contact support"
            ]
        
        # Common mock response patterns
        mock_indicators = [
            "i apologize, but i encountered an error",
            "processing completed with fallback response",
            "fallback",
            "generic error",
            "system error",
            "mock response",
            "sample data",
            "placeholder",
            "generated data",
            "fallback data",
            "default response"
        ]
        
        found_mock_indicators = []
        found_authentic_indicators = []
        
        content_lower = response_content.lower()
        
        # Check for mock indicators
        for indicator in mock_indicators:
            if indicator in content_lower:
                found_mock_indicators.append(indicator)
        
        # Check for authentic indicators  
        for indicator in expected_authentic_indicators:
            if indicator in content_lower:
                found_authentic_indicators.append(indicator)
        
        # Analyze patterns that suggest mock data
        suspicious_patterns = []
        
        # Check for suspiciously round numbers
        import re
        numbers = re.findall(r'\d+\.?\d*', response_content)
        round_numbers = []
        for num_str in numbers:
            try:
                num = float(num_str)
                if num >= 100 and num % 100 == 0:
                    round_numbers.append(num)
            except ValueError:
                continue
        
        if len(round_numbers) > 2:
            suspicious_patterns.append(f"Multiple suspiciously round numbers: {round_numbers}")
        
        # Check for generic language patterns
        generic_phrases = [
            "approximately",
            "around",
            "roughly", 
            "about",
            "estimated",
            "sample",
            "example"
        ]
        
        found_generic = [phrase for phrase in generic_phrases if phrase in content_lower]
        if len(found_generic) > 3:
            suspicious_patterns.append(f"Excessive generic language: {found_generic}")
        
        return {
            "is_likely_mock": len(found_mock_indicators) > 0,
            "mock_indicators_found": found_mock_indicators,
            "authentic_indicators_found": found_authentic_indicators,
            "suspicious_patterns": suspicious_patterns,
            "authenticity_score": max(0, len(found_authentic_indicators) - len(found_mock_indicators)),
            "business_risk_level": self._assess_business_risk(found_mock_indicators, suspicious_patterns)
        }
    
    def _assess_business_risk(
        self,
        mock_indicators: List[str],
        suspicious_patterns: List[str]
    ) -> str:
        """Assess the business risk level of detected mock responses."""
        
        risk_score = 0
        
        # High-risk mock indicators
        high_risk_indicators = [
            "fallback response",
            "generic error", 
            "system error",
            "mock response"
        ]
        
        for indicator in mock_indicators:
            if indicator in high_risk_indicators:
                risk_score += 3
            else:
                risk_score += 1
        
        risk_score += len(suspicious_patterns)
        
        if risk_score >= 5:
            return "critical"
        elif risk_score >= 3:
            return "high"
        elif risk_score >= 1:
            return "medium"
        else:
            return "low"
    
    def create_progressive_failure_sequence(
        self,
        base_scenario: str,
        failure_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Create a sequence of queries with progressively triggering failures.
        
        Args:
            base_scenario: Base scenario description
            failure_count: Number of progressive failures to create
            
        Returns:
            List of queries designed to trigger failures progressively
        """
        sequence = []
        
        failure_types = [
            FailureType.RATE_LIMIT_FAILURE,
            FailureType.TIMEOUT_FAILURE,
            FailureType.LLM_API_FAILURE
        ]
        
        for i in range(failure_count):
            failure_type = failure_types[i % len(failure_types)]
            scenario = self.get_failure_scenario(failure_type)
            
            query = {
                "type": "agent_request",
                "agent": "cost_optimizer", 
                "message": f"{base_scenario} - Progressive failure {i+1}: {scenario.trigger_pattern}",
                "context": {
                    "failure_simulation": True,
                    "failure_sequence": True,
                    "sequence_number": i + 1,
                    "failure_type": failure_type.value,
                    "expected_fallback": scenario.expected_fallback
                },
                "request_id": f"progressive_failure_{i+1}_{int(time.time())}"
            }
            
            sequence.append(query)
        
        return sequence
    
    def validate_authentic_error_handling(
        self,
        response_content: str,
        user_subscription: str = "free",
        arr_value: int = 0
    ) -> Dict[str, Any]:
        """
        Validate that error handling is authentic and appropriate for user tier.
        
        Args:
            response_content: Response to validate
            user_subscription: User subscription tier
            arr_value: Annual recurring revenue value
            
        Returns:
            Validation results with recommendations
        """
        analysis = self.analyze_response_for_mock_indicators(response_content)
        
        # Define appropriate error handling by tier
        tier_requirements = {
            "free": {
                "min_authenticity_score": 0,
                "acceptable_generic": True,
                "escalation_required": False
            },
            "mid": {
                "min_authenticity_score": 1,
                "acceptable_generic": False,
                "escalation_required": False  
            },
            "enterprise": {
                "min_authenticity_score": 2,
                "acceptable_generic": False,
                "escalation_required": True
            }
        }
        
        requirements = tier_requirements.get(user_subscription, tier_requirements["free"])
        
        validation_results = {
            "meets_tier_requirements": True,
            "violations": [],
            "recommendations": [],
            "business_risk": analysis["business_risk_level"]
        }
        
        # Check authenticity score requirement
        if analysis["authenticity_score"] < requirements["min_authenticity_score"]:
            validation_results["meets_tier_requirements"] = False
            validation_results["violations"].append(
                f"Authenticity score {analysis['authenticity_score']} below "
                f"required {requirements['min_authenticity_score']} for {user_subscription} tier"
            )
        
        # Check for inappropriate generic responses
        if not requirements["acceptable_generic"] and analysis["mock_indicators_found"]:
            validation_results["meets_tier_requirements"] = False
            validation_results["violations"].append(
                f"Generic/mock responses not acceptable for {user_subscription} tier: "
                f"{analysis['mock_indicators_found']}"
            )
        
        # Check escalation requirements for enterprise
        if requirements["escalation_required"]:
            escalation_indicators = [
                "contact support",
                "escalation",
                "premium support",
                "immediate assistance"
            ]
            
            has_escalation = any(
                indicator in response_content.lower()
                for indicator in escalation_indicators
            )
            
            if not has_escalation:
                validation_results["meets_tier_requirements"] = False
                validation_results["violations"].append(
                    f"Enterprise tier requires escalation path but none provided"
                )
        
        # Generate recommendations
        if validation_results["violations"]:
            if user_subscription == "enterprise":
                validation_results["recommendations"].append(
                    "Implement premium error handling with immediate escalation"
                )
            else:
                validation_results["recommendations"].append(
                    "Replace generic responses with authentic error communication"
                )
        
        return validation_results


# Utility functions for common failure scenarios
def create_board_presentation_failure() -> Dict[str, Any]:
    """Create failure scenario for board presentation (high business impact)."""
    simulator = MockFailureSimulator()
    return simulator.create_enterprise_critical_failure_query(
        "URGENT: Board meeting in 2 hours. Need comprehensive analysis.",
        arr_value=1000000
    )


def create_cfo_financial_analysis_failure() -> Dict[str, Any]:
    """Create failure scenario for CFO financial analysis (critical data integrity)."""
    simulator = MockFailureSimulator()
    return simulator.create_data_access_failure_query(
        "CFO CRITICAL: Analyze Q4 spend optimization for annual budgeting"
    )


def create_contract_renewal_failure() -> Dict[str, Any]:
    """Create failure scenario during contract renewal (competitive risk)."""
    simulator = MockFailureSimulator()
    return simulator.create_enterprise_critical_failure_query(
        "Contract renewal evaluation: Demonstrate platform value",
        arr_value=600000
    )