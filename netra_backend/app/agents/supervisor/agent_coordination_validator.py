"""Agent Coordination Validator for Enterprise Data Integrity.

This module validates data integrity and coordination consistency across
multi-agent workflows to prevent revenue calculation errors and business
data corruption during agent handoffs.

Business Value: Protects $100K+ Enterprise deals from coordination failures.
"""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from loguru import logger


@dataclass
class DataIntegrityResult:
    """Result of data integrity validation."""
    is_valid: bool
    integrity_hash: str
    validation_timestamp: float
    corruption_details: Optional[Dict[str, Any]] = None
    business_impact: Optional[str] = None


@dataclass
class CoordinationValidationResult:
    """Result of agent coordination validation."""
    coordination_valid: bool
    execution_order_correct: bool
    data_handoffs_valid: bool
    tool_results_propagated: bool
    isolation_maintained: bool
    validation_details: Dict[str, Any]


class AgentCoordinationValidator:
    """Validates agent coordination and data integrity for Enterprise workflows."""

    # Critical business data fields that must survive handoffs
    CRITICAL_REVENUE_FIELDS = {
        "revenue_calculation", "cost_analysis", "savings_potential", 
        "roi_percentage", "payback_period_months", "total_potential_savings"
    }
    
    CRITICAL_DATA_FIELDS = {
        "customer_id", "current_monthly_cost", "projected_savings",
        "optimization_recommendations", "implementation_timeline"
    }

    def __init__(self):
        self.validation_history: List[Dict[str, Any]] = []
        self.integrity_violations: List[Dict[str, Any]] = []

    def calculate_data_integrity_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash for data integrity validation.
        
        Args:
            data: Business data dictionary to hash
            
        Returns:
            SHA-256 hash of critical business data
        """
        # Extract only critical business fields for integrity calculation
        critical_data = {}
        
        for field in self.CRITICAL_REVENUE_FIELDS | self.CRITICAL_DATA_FIELDS:
            if field in data:
                critical_data[field] = data[field]
        
        # Create deterministic hash from critical data
        data_string = json.dumps(critical_data, sort_keys=True, default=str)
        return hashlib.sha256(data_string.encode()).hexdigest()

    def validate_agent_handoff_integrity(
        self, 
        pre_handoff_data: Dict[str, Any],
        post_handoff_data: Dict[str, Any],
        agent_name: str,
        workflow_id: str
    ) -> DataIntegrityResult:
        """Validate data integrity across agent handoff.
        
        Args:
            pre_handoff_data: Business data before agent execution
            post_handoff_data: Business data after agent execution  
            agent_name: Name of the agent that executed
            workflow_id: Unique workflow identifier
            
        Returns:
            DataIntegrityResult with validation details
        """
        pre_hash = self.calculate_data_integrity_hash(pre_handoff_data)
        post_hash = self.calculate_data_integrity_hash(post_handoff_data)
        
        validation_result = DataIntegrityResult(
            is_valid=(pre_hash == post_hash),
            integrity_hash=post_hash,
            validation_timestamp=time.time()
        )
        
        if not validation_result.is_valid:
            # Analyze what changed to determine business impact
            corruption_details = self._analyze_data_corruption(
                pre_handoff_data, post_handoff_data, agent_name
            )
            
            validation_result.corruption_details = corruption_details
            validation_result.business_impact = self._assess_business_impact(corruption_details)
            
            # Log integrity violation
            violation = {
                "workflow_id": workflow_id,
                "agent_name": agent_name,
                "pre_hash": pre_hash,
                "post_hash": post_hash,
                "corruption_details": corruption_details,
                "business_impact": validation_result.business_impact,
                "timestamp": validation_result.validation_timestamp
            }
            self.integrity_violations.append(violation)
            
            logger.error(f"CRITICAL: Data integrity violation in {agent_name} handoff. "
                        f"Workflow: {workflow_id}, Impact: {validation_result.business_impact}")
        
        return validation_result

    def validate_tool_result_propagation(
        self,
        agent_results: Dict[str, Any],
        expected_propagation_chain: List[str]
    ) -> bool:
        """Validate that tool results are properly propagated between agents.
        
        Args:
            agent_results: Dictionary of agent name to results
            expected_propagation_chain: Expected order of agent execution
            
        Returns:
            True if tool results are properly propagated
        """
        for i in range(1, len(expected_propagation_chain)):
            current_agent = expected_propagation_chain[i]
            previous_agent = expected_propagation_chain[i-1]
            
            if current_agent not in agent_results:
                logger.warning(f"Tool propagation check: {current_agent} not in results")
                continue
                
            current_result = agent_results[current_agent]
            
            # Check if current agent has access to previous agent's data
            if isinstance(current_result, dict):
                has_previous_data = any(
                    previous_agent in str(value).lower() or 
                    "previous" in str(key).lower() or
                    "inherited" in str(key).lower()
                    for key, value in current_result.items()
                )
                
                if not has_previous_data:
                    logger.warning(f"Tool propagation failure: {current_agent} missing data from {previous_agent}")
                    return False
        
        return True

    def validate_execution_order_compliance(
        self,
        executed_agents: List[str],
        dependency_rules: Dict[str, List[str]]
    ) -> Tuple[bool, List[str]]:
        """Validate that agents were executed in correct dependency order.
        
        Args:
            executed_agents: List of agents in execution order
            dependency_rules: Dictionary of agent dependencies
            
        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []
        executed_set = set()
        
        for agent in executed_agents:
            # Check if all dependencies were executed before this agent
            dependencies = dependency_rules.get(agent, [])
            
            for dependency in dependencies:
                if dependency not in executed_set:
                    violation = f"{agent} executed before dependency {dependency}"
                    violations.append(violation)
                    logger.error(f"Execution order violation: {violation}")
            
            executed_set.add(agent)
        
        return len(violations) == 0, violations

    def validate_concurrent_isolation(
        self,
        workflow_states: Dict[str, Any],
        user_contexts: Dict[str, Any]
    ) -> bool:
        """Validate that concurrent user workflows are properly isolated.
        
        Args:
            workflow_states: Dictionary of workflow ID to state
            user_contexts: Dictionary of user ID to context
            
        Returns:
            True if isolation is maintained
        """
        # Check for cross-contamination between user contexts
        user_data_sets = {}
        
        for user_id, context in user_contexts.items():
            if hasattr(context, 'agent_results'):
                user_data_sets[user_id] = set(str(context.agent_results).split())
        
        # Check for data overlap between different users (should not happen)
        user_ids = list(user_data_sets.keys())
        for i in range(len(user_ids)):
            for j in range(i + 1, len(user_ids)):
                user1, user2 = user_ids[i], user_ids[j]
                overlap = user_data_sets[user1] & user_data_sets[user2]
                
                # Filter out common words that are expected to overlap
                common_words = {"success", "true", "false", "agent", "result", "data"}
                significant_overlap = overlap - common_words
                
                if len(significant_overlap) > 5:  # Threshold for significant overlap
                    logger.error(f"Concurrent isolation violation: Users {user1} and {user2} "
                                f"share {len(significant_overlap)} data elements")
                    return False
        
        return True

    def validate_complete_coordination(
        self,
        workflow_id: str,
        executed_agents: List[str],
        agent_results: Dict[str, Any],
        dependency_rules: Dict[str, List[str]],
        pre_execution_state: Dict[str, Any],
        post_execution_state: Dict[str, Any]
    ) -> CoordinationValidationResult:
        """Perform complete coordination validation for Enterprise workflow.
        
        Args:
            workflow_id: Unique workflow identifier
            executed_agents: List of agents in execution order
            agent_results: Dictionary of agent results
            dependency_rules: Agent dependency requirements
            pre_execution_state: Workflow state before execution
            post_execution_state: Workflow state after execution
            
        Returns:
            Complete coordination validation result
        """
        # Validate execution order
        order_valid, order_violations = self.validate_execution_order_compliance(
            executed_agents, dependency_rules
        )
        
        # Validate tool result propagation
        propagation_valid = self.validate_tool_result_propagation(
            agent_results, executed_agents
        )
        
        # Validate data handoff integrity
        handoff_integrity = self.validate_agent_handoff_integrity(
            pre_execution_state, post_execution_state, 
            "workflow_complete", workflow_id
        )
        
        # Create comprehensive validation result
        result = CoordinationValidationResult(
            coordination_valid=(order_valid and propagation_valid and handoff_integrity.is_valid),
            execution_order_correct=order_valid,
            data_handoffs_valid=handoff_integrity.is_valid,
            tool_results_propagated=propagation_valid,
            isolation_maintained=True,  # Will be set by caller if needed
            validation_details={
                "workflow_id": workflow_id,
                "executed_agents": executed_agents,
                "order_violations": order_violations,
                "integrity_hash": handoff_integrity.integrity_hash,
                "corruption_details": handoff_integrity.corruption_details,
                "business_impact": handoff_integrity.business_impact,
                "validation_timestamp": time.time()
            }
        )
        
        # Log validation results
        if result.coordination_valid:
            logger.info(f"✅ Complete coordination validation passed for workflow {workflow_id}")
        else:
            logger.error(f"❌ Coordination validation failed for workflow {workflow_id}: "
                        f"Order: {order_valid}, Handoffs: {handoff_integrity.is_valid}, "
                        f"Propagation: {propagation_valid}")
        
        # Store validation history
        self.validation_history.append(result.validation_details)
        
        return result

    def _analyze_data_corruption(
        self, 
        pre_data: Dict[str, Any], 
        post_data: Dict[str, Any],
        agent_name: str
    ) -> Dict[str, Any]:
        """Analyze what data was corrupted during agent execution."""
        corruption_details = {
            "agent_name": agent_name,
            "corrupted_fields": [],
            "missing_fields": [],
            "added_fields": [],
            "value_changes": []
        }
        
        # Check for corrupted critical fields
        for field in self.CRITICAL_REVENUE_FIELDS | self.CRITICAL_DATA_FIELDS:
            pre_value = pre_data.get(field)
            post_value = post_data.get(field)
            
            if pre_value != post_value:
                corruption_details["corrupted_fields"].append(field)
                corruption_details["value_changes"].append({
                    "field": field,
                    "pre_value": pre_value,
                    "post_value": post_value
                })
        
        # Check for missing fields
        pre_fields = set(pre_data.keys()) & (self.CRITICAL_REVENUE_FIELDS | self.CRITICAL_DATA_FIELDS)
        post_fields = set(post_data.keys()) & (self.CRITICAL_REVENUE_FIELDS | self.CRITICAL_DATA_FIELDS)
        
        corruption_details["missing_fields"] = list(pre_fields - post_fields)
        corruption_details["added_fields"] = list(post_fields - pre_fields)
        
        return corruption_details

    def _assess_business_impact(self, corruption_details: Dict[str, Any]) -> str:
        """Assess business impact of data corruption."""
        corrupted_fields = set(corruption_details.get("corrupted_fields", []))
        
        if corrupted_fields & self.CRITICAL_REVENUE_FIELDS:
            return "CRITICAL - Revenue calculation corruption can cause $100K+ deal loss"
        elif corrupted_fields & self.CRITICAL_DATA_FIELDS:
            return "HIGH - Business data corruption can cause customer trust issues"
        elif corruption_details.get("missing_fields"):
            return "MEDIUM - Missing data may cause incomplete analysis"
        else:
            return "LOW - Non-critical data changes detected"

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validation activities."""
        return {
            "total_validations": len(self.validation_history),
            "integrity_violations": len(self.integrity_violations),
            "validation_success_rate": (
                (len(self.validation_history) - len(self.integrity_violations)) / 
                max(1, len(self.validation_history))
            ),
            "recent_violations": self.integrity_violations[-5:] if self.integrity_violations else [],
            "critical_business_impact_violations": [
                v for v in self.integrity_violations 
                if v.get("business_impact", "").startswith("CRITICAL")
            ]
        }