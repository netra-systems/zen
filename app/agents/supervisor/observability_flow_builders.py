"""Flow data builder module for supervisor observability.

Handles building data structures for flow logging.
Each function must be ≤8 lines as per architecture requirements.
"""

import time
from typing import Dict, List, Any


class FlowDataBuilder:
    """Builds data structures for flow logging."""

    def build_flow_event_data(self, flows: Dict[str, Dict[str, Any]], event: str, 
                             flow_id: str, correlation_id: str) -> Dict[str, Any]:
        """Build flow event data structure."""
        flow_data = flows.get(flow_id, {})
        base_data = self._get_base_flow_data(event, flow_id, correlation_id)
        state_summary = self._build_flow_state_summary(flow_data)
        return {**base_data, "state_summary": state_summary}

    def _get_base_flow_data(self, event: str, flow_id: str, correlation_id: str) -> Dict[str, Any]:
        """Get base flow data structure."""
        return {
            "type": "supervisor_flow",
            "event": event,
            "flow_id": flow_id,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }

    def _build_flow_state_summary(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build flow state summary."""
        return {
            "total_steps": flow_data.get("total_steps", 0),
            "completed_steps": flow_data.get("completed_steps", 0),
            "current_phase": flow_data.get("current_phase", "unknown"),
            "active_agents": []
        }

    def build_step_event_data(self, flows: Dict[str, Dict[str, Any]], event: str, 
                             flow_id: str, step_name: str, step_type: str) -> Dict[str, Any]:
        """Build step event data structure."""
        flow_data = flows.get(flow_id, {})
        base_data = self._get_base_flow_data(event, flow_id, flow_data.get("correlation_id", ""))
        step_data = {"step_name": step_name, "step_type": step_type}
        state_summary = self._build_flow_state_summary(flow_data)
        return {**base_data, **step_data, "state_summary": state_summary}

    def build_decision_data(self, flows: Dict[str, Dict[str, Any]], flow_id: str, 
                           decision_point: str, chosen_path: str) -> Dict[str, Any]:
        """Build decision event data."""
        flow_data = flows.get(flow_id, {})
        correlation_id = flow_data.get("correlation_id", "")
        return self._create_decision_dict(flow_id, decision_point, chosen_path, correlation_id)

    def _create_decision_dict(self, flow_id: str, decision_point: str, 
                             chosen_path: str, correlation_id: str) -> Dict[str, Any]:
        """Create decision data dictionary."""
        return {
            "type": "supervisor_decision",
            "flow_id": flow_id,
            "decision_point": decision_point,
            "chosen_path": chosen_path,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }

    def build_parallel_data(self, flows: Dict[str, Dict[str, Any]], 
                           flow_id: str, agent_names: List[str]) -> Dict[str, Any]:
        """Build parallel execution data."""
        flow_data = flows.get(flow_id, {})
        correlation_id = flow_data.get("correlation_id", "")
        return self._create_parallel_dict(flow_id, agent_names, correlation_id)

    def _create_parallel_dict(self, flow_id: str, agent_names: List[str], 
                             correlation_id: str) -> Dict[str, Any]:
        """Create parallel execution dictionary."""
        return {
            "type": "supervisor_parallel",
            "flow_id": flow_id,
            "agent_names": agent_names,
            "agent_count": len(agent_names),
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }

    def build_sequential_data(self, flows: Dict[str, Dict[str, Any]], 
                             flow_id: str, agent_sequence: List[str]) -> Dict[str, Any]:
        """Build sequential execution data."""
        flow_data = flows.get(flow_id, {})
        correlation_id = flow_data.get("correlation_id", "")
        return self._create_sequential_dict(flow_id, agent_sequence, correlation_id)

    def _create_sequential_dict(self, flow_id: str, agent_sequence: List[str], 
                               correlation_id: str) -> Dict[str, Any]:
        """Create sequential execution dictionary."""
        return {
            "type": "supervisor_sequential",
            "flow_id": flow_id,
            "agent_sequence": agent_sequence,
            "sequence_length": len(agent_sequence),
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }

    def build_retry_data(self, flows: Dict[str, Dict[str, Any]], flow_id: str, 
                        step_name: str, attempt_num: int) -> Dict[str, Any]:
        """Build retry attempt data."""
        flow_data = flows.get(flow_id, {})
        correlation_id = flow_data.get("correlation_id", "")
        return self._create_retry_dict(flow_id, step_name, attempt_num, correlation_id)

    def _create_retry_dict(self, flow_id: str, step_name: str, 
                          attempt_num: int, correlation_id: str) -> Dict[str, Any]:
        """Create retry attempt dictionary."""
        return {
            "type": "supervisor_retry",
            "flow_id": flow_id,
            "step_name": step_name,
            "attempt_number": attempt_num,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }

    def build_fallback_data(self, flows: Dict[str, Dict[str, Any]], flow_id: str, 
                           failed_step: str, fallback_step: str) -> Dict[str, Any]:
        """Build fallback trigger data."""
        flow_data = flows.get(flow_id, {})
        correlation_id = flow_data.get("correlation_id", "")
        return self._create_fallback_dict(flow_id, failed_step, fallback_step, correlation_id)

    def _create_fallback_dict(self, flow_id: str, failed_step: str, 
                             fallback_step: str, correlation_id: str) -> Dict[str, Any]:
        """Create fallback trigger dictionary."""
        return {
            "type": "supervisor_fallback",
            "flow_id": flow_id,
            "failed_step": failed_step,
            "fallback_step": fallback_step,
            "correlation_id": correlation_id,
            "timestamp": time.time()
        }