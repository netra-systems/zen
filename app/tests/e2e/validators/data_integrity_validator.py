"""
Data Integrity Validation Framework for E2E Agent Testing
Validates type safety, data flow, referential integrity, and state consistency.
Maximum 300 lines, functions ≤8 lines.
"""

from typing import Dict, List, Any, Optional, Union, Set
from pydantic import BaseModel, Field
from datetime import datetime, UTC
from app.agents.state import DeepAgentState
from app.agents.triage_sub_agent.models import TriageResult
from app.schemas.shared_types import DataAnalysisResponse, AnomalyDetectionResponse
from app.tests.e2e.state_validation_utils import StateIntegrityChecker


class TypeSafetyResult(BaseModel):
    """Result of type safety verification."""
    is_type_safe: bool = Field(default=False)
    type_violations: List[str] = Field(default_factory=list)
    stage_name: str
    validated_types: List[str] = Field(default_factory=list)


class DataFlowResult(BaseModel):
    """Result of data flow tracking."""
    data_preserved: bool = Field(default=False)
    data_corruption_detected: bool = Field(default=False)
    data_loss_detected: bool = Field(default=False)
    flow_violations: List[str] = Field(default_factory=list)
    data_transformations: List[str] = Field(default_factory=list)


class ReferentialIntegrityResult(BaseModel):
    """Result of referential integrity checks."""
    integrity_maintained: bool = Field(default=False)
    broken_references: List[str] = Field(default_factory=list)
    orphaned_data: List[str] = Field(default_factory=list)
    reference_chain_valid: bool = Field(default=False)


class AuditTrailResult(BaseModel):
    """Result of audit trail validation."""
    trail_complete: bool = Field(default=False)
    missing_trail_entries: List[str] = Field(default_factory=list)
    trail_entries: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp_consistency: bool = Field(default=False)


class StateConsistencyResult(BaseModel):
    """Result of state consistency verification."""
    state_consistent: bool = Field(default=False)
    consistency_violations: List[str] = Field(default_factory=list)
    step_count_valid: bool = Field(default=False)
    result_progression_valid: bool = Field(default=False)


class DataIntegrityValidationResult(BaseModel):
    """Comprehensive data integrity validation result."""
    type_safety: TypeSafetyResult
    data_flow: DataFlowResult
    referential_integrity: ReferentialIntegrityResult
    audit_trail: AuditTrailResult
    state_consistency: StateConsistencyResult
    overall_integrity: bool = Field(default=False)


class TypeSafetyValidator:
    """Validates type safety at each stage."""
    
    def __init__(self):
        self.integrity_checker = StateIntegrityChecker()
    
    def verify_triage_types(self, state: DeepAgentState) -> TypeSafetyResult:
        """Verify type safety for triage stage."""
        result = TypeSafetyResult(stage_name="triage")
        violations = []
        validated_types = []
        
        try:
            self.integrity_checker.type_validator.validate_state_base_types(state)
            validated_types.append("DeepAgentState")
            self.integrity_checker.type_validator.validate_triage_result_types(state.triage_result)
            validated_types.append("TriageResult")
            result.is_type_safe = True
        except (AssertionError, TypeError) as e:
            violations.append(f"Triage type violation: {str(e)}")
        
        result.type_violations = violations
        result.validated_types = validated_types
        return result
    
    def verify_data_types(self, state: DeepAgentState) -> TypeSafetyResult:
        """Verify type safety for data stage."""
        result = TypeSafetyResult(stage_name="data")
        violations = []
        validated_types = []
        
        try:
            self.integrity_checker.type_validator.validate_complete_state_types(state)
            validated_types.extend(["DeepAgentState", "TriageResult", "DataResult"])
            result.is_type_safe = True
        except (AssertionError, TypeError) as e:
            violations.append(f"Data type violation: {str(e)}")
        
        result.type_violations = violations
        result.validated_types = validated_types
        return result
    
    def validate_type_transitions(self, before_state: DeepAgentState, 
                                after_state: DeepAgentState) -> List[str]:
        """Validate type safety during state transitions."""
        violations = []
        
        # Check base types preserved
        if type(before_state.user_request) != type(after_state.user_request):
            violations.append("User request type changed during transition")
        
        # Check result type consistency
        if before_state.triage_result and after_state.triage_result:
            if type(before_state.triage_result) != type(after_state.triage_result):
                violations.append("Triage result type changed during transition")
        
        return violations


class DataFlowTracker:
    """Tracks data flow to detect loss or corruption."""
    
    def track_triage_flow(self, initial_state: DeepAgentState, 
                         final_state: DeepAgentState) -> DataFlowResult:
        """Track data flow through triage stage."""
        result = DataFlowResult()
        
        # Check data preservation
        result.data_preserved = self._check_triage_preservation(initial_state, final_state)
        result.data_corruption_detected = self._detect_triage_corruption(initial_state, final_state)
        result.data_loss_detected = self._detect_triage_loss(initial_state, final_state)
        result.data_transformations = self._track_triage_transformations(initial_state, final_state)
        
        if result.data_corruption_detected:
            result.flow_violations.append("Data corruption detected in triage flow")
        if result.data_loss_detected:
            result.flow_violations.append("Data loss detected in triage flow")
        
        return result
    
    def track_data_flow(self, initial_state: DeepAgentState,
                       final_state: DeepAgentState) -> DataFlowResult:
        """Track data flow through data analysis stage."""
        result = DataFlowResult()
        
        result.data_preserved = self._check_data_preservation(initial_state, final_state)
        result.data_corruption_detected = self._detect_data_corruption(initial_state, final_state)
        result.data_loss_detected = self._detect_data_loss(initial_state, final_state)
        result.data_transformations = self._track_data_transformations(initial_state, final_state)
        
        if result.data_corruption_detected:
            result.flow_violations.append("Data corruption detected in data flow")
        if result.data_loss_detected:
            result.flow_violations.append("Data loss detected in data flow")
        
        return result
    
    def _check_triage_preservation(self, initial: DeepAgentState, final: DeepAgentState) -> bool:
        """Check if essential data is preserved during triage."""
        return (initial.user_request == final.user_request and
                initial.chat_thread_id == final.chat_thread_id and
                initial.user_id == final.user_id)
    
    def _check_data_preservation(self, initial: DeepAgentState, final: DeepAgentState) -> bool:
        """Check if essential data is preserved during data analysis."""
        preserved = self._check_triage_preservation(initial, final)
        if initial.triage_result and final.triage_result:
            preserved = preserved and (initial.triage_result == final.triage_result)
        return preserved
    
    def _detect_triage_corruption(self, initial: DeepAgentState, final: DeepAgentState) -> bool:
        """Detect data corruption during triage."""
        if initial.user_request != final.user_request:
            return len(final.user_request) < len(initial.user_request) * 0.5
        return False
    
    def _detect_data_corruption(self, initial: DeepAgentState, final: DeepAgentState) -> bool:
        """Detect data corruption during data analysis."""
        corruption = self._detect_triage_corruption(initial, final)
        
        # Check if triage result was corrupted
        if initial.triage_result and final.triage_result:
            if hasattr(initial.triage_result, 'category') and hasattr(final.triage_result, 'category'):
                corruption = corruption or (initial.triage_result.category != final.triage_result.category)
        
        return corruption
    
    def _detect_triage_loss(self, initial: DeepAgentState, final: DeepAgentState) -> bool:
        """Detect data loss during triage."""
        return not final.user_request or len(final.user_request.strip()) == 0
    
    def _detect_data_loss(self, initial: DeepAgentState, final: DeepAgentState) -> bool:
        """Detect data loss during data analysis."""
        loss = self._detect_triage_loss(initial, final)
        return loss or (initial.triage_result is not None and final.triage_result is None)
    
    def _track_triage_transformations(self, initial: DeepAgentState, final: DeepAgentState) -> List[str]:
        """Track transformations during triage."""
        transformations = []
        if final.triage_result and not initial.triage_result:
            transformations.append("Created triage result")
        if final.step_count > initial.step_count:
            transformations.append("Incremented step count")
        return transformations
    
    def _track_data_transformations(self, initial: DeepAgentState, final: DeepAgentState) -> List[str]:
        """Track transformations during data analysis."""
        transformations = self._track_triage_transformations(initial, final)
        if final.data_result and not initial.data_result:
            transformations.append("Created data analysis result")
        return transformations


class ReferentialIntegrityChecker:
    """Checks referential integrity between related data."""
    
    def check_triage_references(self, state: DeepAgentState) -> ReferentialIntegrityResult:
        """Check referential integrity for triage stage."""
        result = ReferentialIntegrityResult()
        
        broken_refs = []
        if state.triage_result:
            # Check if user_request is still referenced properly
            if not state.user_request:
                broken_refs.append("Triage result exists but user_request is missing")
        
        result.broken_references = broken_refs
        result.reference_chain_valid = len(broken_refs) == 0
        result.integrity_maintained = result.reference_chain_valid
        return result
    
    def check_data_references(self, state: DeepAgentState) -> ReferentialIntegrityResult:
        """Check referential integrity for data stage."""
        result = ReferentialIntegrityResult()
        
        broken_refs = []
        orphaned = []
        
        # Check data result has proper triage reference
        if state.data_result and not state.triage_result:
            orphaned.append("Data result exists without triage result")
        
        # Check step count consistency
        expected_steps = sum([1 for r in [state.triage_result, state.data_result] if r is not None])
        if state.step_count < expected_steps:
            broken_refs.append("Step count inconsistent with completed stages")
        
        result.broken_references = broken_refs
        result.orphaned_data = orphaned
        result.reference_chain_valid = len(broken_refs) == 0 and len(orphaned) == 0
        result.integrity_maintained = result.reference_chain_valid
        return result


class AuditTrailValidator:
    """Validates complete audit trail."""
    
    def validate_trail(self, state: DeepAgentState) -> AuditTrailResult:
        """Validate complete audit trail."""
        result = AuditTrailResult()
        
        trail_entries = self._extract_trail_entries(state)
        missing_entries = self._check_missing_entries(state)
        timestamp_consistent = self._validate_timestamps(trail_entries)
        
        result.trail_entries = trail_entries
        result.missing_trail_entries = missing_entries
        result.timestamp_consistency = timestamp_consistent
        result.trail_complete = len(missing_entries) == 0
        
        return result
    
    def _extract_trail_entries(self, state: DeepAgentState) -> List[Dict[str, Any]]:
        """Extract audit trail entries from state."""
        entries = []
        
        if state.triage_result:
            entries.append({
                "stage": "triage",
                "timestamp": datetime.now(UTC).isoformat(),
                "data_present": True
            })
        
        if state.data_result:
            entries.append({
                "stage": "data",
                "timestamp": datetime.now(UTC).isoformat(),
                "data_present": True
            })
        
        return entries
    
    def _check_missing_entries(self, state: DeepAgentState) -> List[str]:
        """Check for missing audit trail entries."""
        missing = []
        
        if state.step_count > 0 and not state.triage_result:
            missing.append("Triage audit entry missing")
        
        if state.step_count > 1 and not state.data_result:
            missing.append("Data analysis audit entry missing")
        
        return missing
    
    def _validate_timestamps(self, entries: List[Dict[str, Any]]) -> bool:
        """Validate timestamp consistency in trail."""
        if len(entries) < 2:
            return True
        
        # Check chronological order
        for i in range(1, len(entries)):
            if entries[i]["timestamp"] < entries[i-1]["timestamp"]:
                return False
        
        return True


class StateConsistencyValidator:
    """Validates overall state consistency."""
    
    def __init__(self):
        self.integrity_checker = StateIntegrityChecker()
    
    def validate_consistency(self, state: DeepAgentState) -> StateConsistencyResult:
        """Validate complete state consistency."""
        result = StateConsistencyResult()
        violations = []
        
        try:
            self.integrity_checker.check_pipeline_state_consistency(state)
            result.step_count_valid = True
            result.result_progression_valid = True
            result.state_consistent = True
        except AssertionError as e:
            violations.append(str(e))
            result.state_consistent = False
        
        result.consistency_violations = violations
        return result


class DataIntegrityValidator:
    """Comprehensive data integrity validation framework."""
    
    def __init__(self):
        self.type_safety_validator = TypeSafetyValidator()
        self.data_flow_tracker = DataFlowTracker()
        self.referential_checker = ReferentialIntegrityChecker()
        self.audit_validator = AuditTrailValidator()
        self.consistency_validator = StateConsistencyValidator()
    
    def validate_triage_integrity(self, initial_state: DeepAgentState,
                                 final_state: DeepAgentState) -> DataIntegrityValidationResult:
        """Validate complete data integrity for triage stage."""
        type_safety = self.type_safety_validator.verify_triage_types(final_state)
        data_flow = self.data_flow_tracker.track_triage_flow(initial_state, final_state)
        referential = self.referential_checker.check_triage_references(final_state)
        audit_trail = self.audit_validator.validate_trail(final_state)
        consistency = self.consistency_validator.validate_consistency(final_state)
        
        overall_integrity = all([
            type_safety.is_type_safe,
            data_flow.data_preserved and not data_flow.data_corruption_detected,
            referential.integrity_maintained,
            audit_trail.trail_complete,
            consistency.state_consistent
        ])
        
        return DataIntegrityValidationResult(
            type_safety=type_safety,
            data_flow=data_flow,
            referential_integrity=referential,
            audit_trail=audit_trail,
            state_consistency=consistency,
            overall_integrity=overall_integrity
        )
    
    def validate_data_integrity(self, initial_state: DeepAgentState,
                               final_state: DeepAgentState) -> DataIntegrityValidationResult:
        """Validate complete data integrity for data analysis stage."""
        type_safety = self.type_safety_validator.verify_data_types(final_state)
        data_flow = self.data_flow_tracker.track_data_flow(initial_state, final_state)
        referential = self.referential_checker.check_data_references(final_state)
        audit_trail = self.audit_validator.validate_trail(final_state)
        consistency = self.consistency_validator.validate_consistency(final_state)
        
        overall_integrity = all([
            type_safety.is_type_safe,
            data_flow.data_preserved and not data_flow.data_corruption_detected,
            referential.integrity_maintained,
            audit_trail.trail_complete,
            consistency.state_consistent
        ])
        
        return DataIntegrityValidationResult(
            type_safety=type_safety,
            data_flow=data_flow,
            referential_integrity=referential,
            audit_trail=audit_trail,
            state_consistency=consistency,
            overall_integrity=overall_integrity
        )