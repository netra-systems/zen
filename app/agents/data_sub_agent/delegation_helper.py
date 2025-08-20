"""Delegation Helper for DataSubAgent

Separates delegation logic to maintain 450-line limit.
Handles method resolution and delegation patterns.

Business Value: Clean delegation patterns for modular architecture.
"""

from typing import List


class DataSubAgentDelegationHelper:
    """Helper for managing delegation patterns in DataSubAgent."""
    
    def get_delegation_methods(self) -> List[str]:
        """Get list of methods that can be delegated."""
        process_methods = self.get_process_delegation_methods()
        analysis_methods = self.get_analysis_delegation_methods()
        return process_methods + analysis_methods
    
    def get_process_delegation_methods(self) -> List[str]:
        """Get process-related delegation methods."""
        core_methods = ["_process_internal", "process_with_retry", "process_with_cache"]
        batch_methods = ["process_batch_safe", "process_concurrent", "process_stream"]
        supervisor_methods = ["process_and_persist", "handle_supervisor_request", "enrich_data"]
        return core_methods + batch_methods + supervisor_methods
    
    def get_analysis_delegation_methods(self) -> List[str]:
        """Get analysis-related delegation methods."""
        pipeline_methods = ["_transform_with_pipeline", "_apply_operation"]
        state_methods = ["save_state", "load_state", "recover"]
        analysis_methods = ["_analyze_performance_metrics", "_detect_anomalies", 
                           "_analyze_usage_patterns", "_analyze_correlations"]
        return pipeline_methods + state_methods + analysis_methods
    
    def resolve_delegation_method(self, name: str, delegation):
        """Resolve delegation method from delegation module."""
        if name == "enrich_data":
            return delegation.enrich_data_external
        return getattr(delegation, name)