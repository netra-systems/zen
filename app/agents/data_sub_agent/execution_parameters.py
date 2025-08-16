"""Parameter processing for DataSubAgent execution."""

from typing import Dict, Any, Tuple
from datetime import datetime, timedelta, UTC


class ParameterProcessor:
    """Handles parameter extraction and processing for execution."""
    
    def __init__(self, execution_engine):
        self.engine = execution_engine
    
    def extract_analysis_params(self, state: "DeepAgentState") -> Dict[str, Any]:
        """Extract analysis parameters from triage result."""
        triage_result = state.triage_result
        if not triage_result:
            return self._build_analysis_params_dict({}, {})
        key_params = getattr(triage_result, 'key_parameters', {})
        intent = self._extract_user_intent_dict(triage_result)
        return self._build_analysis_params_dict(key_params, intent)
    
    def _extract_user_intent_dict(self, triage_result) -> Dict[str, Any]:
        """Extract user intent and convert to dict format."""
        user_intent = getattr(triage_result, 'user_intent', None)
        if not user_intent:
            return {}
        return {
            "primary": getattr(user_intent, 'primary_intent', 'general'),
            "secondary": getattr(user_intent, 'secondary_intents', [])
        }
    
    def _build_analysis_params_dict(self, key_params: Any, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Build analysis parameters dictionary."""
        if hasattr(key_params, '__dict__'):
            return self._build_params_from_object(key_params, intent)
        else:
            return self._build_params_from_dict(key_params, intent)
    
    def _build_params_from_object(self, key_params: Any, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters from Pydantic object."""
        return {
            "user_id": getattr(key_params, "user_id", 1),
            "workload_id": getattr(key_params, "workload_id", None),
            "metric_names": getattr(key_params, "metrics", ["latency_ms", "throughput", "cost_cents"]),
            "time_range_str": getattr(key_params, "time_range", "last_24_hours"),
            "primary_intent": intent.get("primary", "general")
        }
    
    def _build_params_from_dict(self, key_params: Any, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters from dict or empty value."""
        defaults = self._get_default_params()
        if not isinstance(key_params, dict):
            key_params = {}
        return {
            "user_id": key_params.get("user_id", defaults["user_id"]),
            "workload_id": key_params.get("workload_id", defaults["workload_id"]),
            "metric_names": key_params.get("metrics", defaults["metric_names"]),
            "time_range_str": key_params.get("time_range", defaults["time_range_str"]),
            "primary_intent": intent.get("primary", "general")
        }
    
    def _get_default_params(self) -> Dict[str, Any]:
        """Get default parameter values."""
        return {
            "user_id": 1,
            "workload_id": None,
            "metric_names": ["latency_ms", "throughput", "cost_cents"],
            "time_range_str": "last_24_hours"
        }
    
    def parse_time_range(self, time_range_str: str) -> Tuple[datetime, datetime]:
        """Parse time range string into datetime tuple."""
        end_time = datetime.now(UTC)
        time_deltas = self._get_time_delta_mapping()
        start_time = end_time - time_deltas.get(time_range_str, timedelta(days=1))
        return (start_time, end_time)
    
    def _get_time_delta_mapping(self) -> Dict[str, timedelta]:
        """Get mapping of time range strings to timedelta objects."""
        return {
            "last_hour": timedelta(hours=1),
            "last_24_hours": timedelta(days=1),
            "last_week": timedelta(weeks=1),
            "last_month": timedelta(days=30)
        }
    
    def create_base_result(self, params: Dict[str, Any], time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create base result structure."""
        return {
            "analysis_type": params["primary_intent"],
            "parameters": self._create_parameters_section(params, time_range),
            "results": {}
        }
    
    def _create_parameters_section(self, params: Dict[str, Any], time_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Create parameters section of result."""
        return {
            "user_id": params["user_id"],
            "workload_id": params["workload_id"],
            "time_range": self._format_time_range(time_range),
            "metrics": params["metric_names"],
            "primary_intent": params["primary_intent"]
        }
    
    def _format_time_range(self, time_range: Tuple[datetime, datetime]) -> Dict[str, str]:
        """Format time range for result output."""
        start_time, end_time = time_range
        return {
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }