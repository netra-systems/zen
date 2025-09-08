"""
Interface Evolution Governance Framework

This module implements comprehensive interface evolution governance to prevent
systematic interface contract failures and parameter mismatches.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Zero-tolerance interface evolution failures
- Value Impact: Prevents CASCADE FAILURES from interface changes
- Strategic Impact: ROOT CAUSE #4 & #5 prevention - Interface Change Management & Governance

Key Features:
- Interface change impact analysis
- Automated breaking change detection
- Contract evolution validation
- Change approval workflows
- Rollback safety mechanisms
- Pre-commit governance hooks

Root Cause Prevention (Five Whys):
- WHY #5: Interface Evolution Governance - Systematic governance framework
- WHY #4: Interface Change Management - Automated change impact detection  
- WHY #3: Factory Pattern Consistency - Validates consistency across changes
- WHY #2: Parameter Name Standardization - Enforces naming during evolution
- WHY #1: Better Error Messages - Clear change impact reports

Design Philosophy:
- GOVERNANCE FIRST: All interface changes must be approved
- IMPACT ANALYSIS: Full impact assessment before any change
- ROLLBACK SAFETY: Every change must have a rollback plan
- AUTOMATION: Minimize human error in interface evolution
- DOCUMENTATION: Every change must be documented and tracked
"""

import json
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pathlib import Path
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict
import inspect

from shared.lifecycle.interface_contract_validation import (
    InterfaceContract,
    ParameterContract,
    InterfaceContractRegistry,
    get_global_registry
)

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of interface changes."""
    PARAMETER_ADD = "parameter_add"
    PARAMETER_REMOVE = "parameter_remove"
    PARAMETER_RENAME = "parameter_rename"
    PARAMETER_TYPE_CHANGE = "parameter_type_change"
    PARAMETER_DEFAULT_CHANGE = "parameter_default_change"
    METHOD_ADD = "method_add"
    METHOD_REMOVE = "method_remove"
    METHOD_SIGNATURE_CHANGE = "method_signature_change"
    CLASS_HIERARCHY_CHANGE = "class_hierarchy_change"


class ChangeImpact(Enum):
    """Impact levels of interface changes."""
    BREAKING = "breaking"          # Requires immediate attention, breaks existing code
    POTENTIALLY_BREAKING = "potentially_breaking"  # May break code, needs analysis
    COMPATIBLE = "compatible"      # Backward compatible
    ENHANCEMENT = "enhancement"    # Adds functionality without breaking existing


class ChangeStatus(Enum):
    """Status of interface changes."""
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class InterfaceChange:
    """Represents a single interface change."""
    change_id: str
    interface_name: str
    change_type: ChangeType
    impact_level: ChangeImpact
    description: str
    old_value: Any = None
    new_value: Any = None
    affected_components: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    status: ChangeStatus = ChangeStatus.PROPOSED
    
    def __post_init__(self):
        if isinstance(self.affected_components, set):
            object.__setattr__(self, 'affected_components', frozenset(self.affected_components))


@dataclass
class ChangeRequest:
    """A request for interface changes with approval workflow."""
    request_id: str
    title: str
    description: str
    changes: List[InterfaceChange]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = "system"
    status: ChangeStatus = ChangeStatus.PROPOSED
    approval_required: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rollback_plan: Optional[str] = None
    
    def get_breaking_changes(self) -> List[InterfaceChange]:
        """Get all breaking changes in this request."""
        return [
            change for change in self.changes 
            if change.impact_level == ChangeImpact.BREAKING
        ]
    
    def get_total_impact_score(self) -> int:
        """Calculate total impact score for prioritization."""
        impact_weights = {
            ChangeImpact.BREAKING: 10,
            ChangeImpact.POTENTIALLY_BREAKING: 5,
            ChangeImpact.COMPATIBLE: 1,
            ChangeImpact.ENHANCEMENT: 0
        }
        
        return sum(impact_weights.get(change.impact_level, 0) for change in self.changes)


class InterfaceEvolutionAnalyzer:
    """Analyzes interface evolution and detects breaking changes."""
    
    def __init__(self, registry: InterfaceContractRegistry):
        self.registry = registry
        self.baseline_contracts: Dict[str, InterfaceContract] = {}
        
    def save_baseline(self, contracts: Dict[str, InterfaceContract]) -> None:
        """Save current contracts as baseline for future comparison."""
        self.baseline_contracts = contracts.copy()
        logger.info(f"Saved baseline for {len(contracts)} contracts")
        
    def analyze_changes(
        self, 
        current_contracts: Dict[str, InterfaceContract]
    ) -> List[InterfaceChange]:
        """Analyze changes between baseline and current contracts."""
        changes = []
        
        # Check for new contracts
        new_contracts = set(current_contracts.keys()) - set(self.baseline_contracts.keys())
        for contract_name in new_contracts:
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=contract_name,
                change_type=ChangeType.METHOD_ADD,
                impact_level=ChangeImpact.ENHANCEMENT,
                description=f"New interface contract: {contract_name}",
                new_value=contract_name
            )
            changes.append(change)
        
        # Check for removed contracts
        removed_contracts = set(self.baseline_contracts.keys()) - set(current_contracts.keys())
        for contract_name in removed_contracts:
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=contract_name,
                change_type=ChangeType.METHOD_REMOVE,
                impact_level=ChangeImpact.BREAKING,
                description=f"Removed interface contract: {contract_name}",
                old_value=contract_name
            )
            changes.append(change)
        
        # Check for modified contracts
        common_contracts = set(current_contracts.keys()) & set(self.baseline_contracts.keys())
        for contract_name in common_contracts:
            baseline_contract = self.baseline_contracts[contract_name]
            current_contract = current_contracts[contract_name]
            
            contract_changes = self._analyze_contract_changes(
                baseline_contract, current_contract
            )
            changes.extend(contract_changes)
        
        return changes
    
    def _analyze_contract_changes(
        self, 
        baseline: InterfaceContract, 
        current: InterfaceContract
    ) -> List[InterfaceChange]:
        """Analyze changes within a single contract."""
        changes = []
        
        # Analyze parameter changes
        baseline_params = {p.name: p for p in baseline.parameters}
        current_params = {p.name: p for p in current.parameters}
        
        # New parameters
        new_params = set(current_params.keys()) - set(baseline_params.keys())
        for param_name in new_params:
            param = current_params[param_name]
            impact = ChangeImpact.COMPATIBLE if not param.is_required else ChangeImpact.POTENTIALLY_BREAKING
            
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=baseline.name,
                change_type=ChangeType.PARAMETER_ADD,
                impact_level=impact,
                description=f"Added parameter: {param_name}",
                new_value=param_name
            )
            changes.append(change)
        
        # Removed parameters  
        removed_params = set(baseline_params.keys()) - set(current_params.keys())
        for param_name in removed_params:
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=baseline.name,
                change_type=ChangeType.PARAMETER_REMOVE,
                impact_level=ChangeImpact.BREAKING,
                description=f"Removed parameter: {param_name}",
                old_value=param_name
            )
            changes.append(change)
        
        # Modified parameters
        common_params = set(baseline_params.keys()) & set(current_params.keys())
        for param_name in common_params:
            baseline_param = baseline_params[param_name]
            current_param = current_params[param_name]
            
            param_changes = self._analyze_parameter_changes(
                baseline.name, baseline_param, current_param
            )
            changes.extend(param_changes)
        
        return changes
    
    def _analyze_parameter_changes(
        self, 
        interface_name: str,
        baseline: ParameterContract, 
        current: ParameterContract
    ) -> List[InterfaceChange]:
        """Analyze changes within a single parameter."""
        changes = []
        
        # Type hint changes
        if baseline.type_hint != current.type_hint:
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=interface_name,
                change_type=ChangeType.PARAMETER_TYPE_CHANGE,
                impact_level=ChangeImpact.POTENTIALLY_BREAKING,
                description=f"Parameter {baseline.name} type changed: {baseline.type_hint} -> {current.type_hint}",
                old_value=baseline.type_hint,
                new_value=current.type_hint
            )
            changes.append(change)
        
        # Required flag changes
        if baseline.is_required != current.is_required:
            impact = ChangeImpact.BREAKING if current.is_required else ChangeImpact.COMPATIBLE
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=interface_name,
                change_type=ChangeType.PARAMETER_DEFAULT_CHANGE,
                impact_level=impact,
                description=f"Parameter {baseline.name} required changed: {baseline.is_required} -> {current.is_required}",
                old_value=baseline.is_required,
                new_value=current.is_required
            )
            changes.append(change)
        
        # Default value changes
        if baseline.default_value != current.default_value:
            change = InterfaceChange(
                change_id=self._generate_change_id(),
                interface_name=interface_name,
                change_type=ChangeType.PARAMETER_DEFAULT_CHANGE,
                impact_level=ChangeImpact.COMPATIBLE,
                description=f"Parameter {baseline.name} default changed",
                old_value=str(baseline.default_value),
                new_value=str(current.default_value)
            )
            changes.append(change)
        
        return changes
    
    def _generate_change_id(self) -> str:
        """Generate unique change ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return hashlib.md5(timestamp.encode()).hexdigest()[:8]


class InterfaceEvolutionGovernor:
    """Governs interface evolution with approval workflows and safety checks."""
    
    def __init__(self, registry: InterfaceContractRegistry):
        self.registry = registry
        self.analyzer = InterfaceEvolutionAnalyzer(registry)
        self.change_requests: Dict[str, ChangeRequest] = {}
        self.change_history: List[InterfaceChange] = []
        
    def propose_change_request(
        self,
        title: str,
        description: str,
        changes: List[InterfaceChange],
        created_by: str = "system"
    ) -> ChangeRequest:
        """Propose a new change request."""
        request_id = self._generate_request_id()
        
        # Determine if approval is required
        has_breaking_changes = any(
            change.impact_level == ChangeImpact.BREAKING for change in changes
        )
        
        request = ChangeRequest(
            request_id=request_id,
            title=title,
            description=description,
            changes=changes,
            created_by=created_by,
            approval_required=has_breaking_changes
        )
        
        self.change_requests[request_id] = request
        
        logger.info(f"Proposed change request: {request_id} - {title}")
        if has_breaking_changes:
            logger.warning(f"Change request {request_id} contains breaking changes - approval required")
        
        return request
    
    def approve_change_request(
        self, 
        request_id: str, 
        approved_by: str,
        rollback_plan: Optional[str] = None
    ) -> bool:
        """Approve a change request."""
        if request_id not in self.change_requests:
            logger.error(f"Change request not found: {request_id}")
            return False
        
        request = self.change_requests[request_id]
        
        if request.status != ChangeStatus.PROPOSED:
            logger.error(f"Change request {request_id} is not in PROPOSED status")
            return False
        
        # Validate rollback plan for breaking changes
        breaking_changes = request.get_breaking_changes()
        if breaking_changes and not rollback_plan:
            logger.error(f"Rollback plan required for breaking changes in {request_id}")
            return False
        
        request.status = ChangeStatus.APPROVED
        request.approved_by = approved_by
        request.approved_at = datetime.now(timezone.utc)
        request.rollback_plan = rollback_plan
        
        logger.info(f"Approved change request: {request_id} by {approved_by}")
        return True
    
    def reject_change_request(self, request_id: str, reason: str) -> bool:
        """Reject a change request."""
        if request_id not in self.change_requests:
            logger.error(f"Change request not found: {request_id}")
            return False
        
        request = self.change_requests[request_id]
        request.status = ChangeStatus.REJECTED
        
        logger.info(f"Rejected change request: {request_id} - {reason}")
        return True
    
    def implement_change_request(self, request_id: str) -> bool:
        """Mark a change request as implemented."""
        if request_id not in self.change_requests:
            logger.error(f"Change request not found: {request_id}")
            return False
        
        request = self.change_requests[request_id]
        
        if request.status != ChangeStatus.APPROVED:
            logger.error(f"Change request {request_id} is not approved")
            return False
        
        request.status = ChangeStatus.IMPLEMENTED
        
        # Add changes to history
        for change in request.changes:
            implemented_change = InterfaceChange(
                change_id=change.change_id,
                interface_name=change.interface_name,
                change_type=change.change_type,
                impact_level=change.impact_level,
                description=change.description,
                old_value=change.old_value,
                new_value=change.new_value,
                affected_components=change.affected_components,
                created_at=change.created_at,
                created_by=change.created_by,
                status=ChangeStatus.IMPLEMENTED
            )
            self.change_history.append(implemented_change)
        
        logger.info(f"Implemented change request: {request_id}")
        return True
    
    def validate_change_safety(self, changes: List[InterfaceChange]) -> Dict[str, Any]:
        """Validate the safety of proposed changes."""
        validation_result = {
            "is_safe": True,
            "breaking_changes": [],
            "warnings": [],
            "recommendations": []
        }
        
        breaking_changes = [
            change for change in changes 
            if change.impact_level == ChangeImpact.BREAKING
        ]
        
        if breaking_changes:
            validation_result["is_safe"] = False
            validation_result["breaking_changes"] = [
                {
                    "interface": change.interface_name,
                    "change_type": change.change_type.value,
                    "description": change.description
                }
                for change in breaking_changes
            ]
            
            validation_result["recommendations"].append(
                "Breaking changes detected. Consider deprecation strategy before removal."
            )
        
        # Check for parameter renames that might cause the websocket_connection_id issue
        for change in changes:
            if (change.change_type == ChangeType.PARAMETER_RENAME and 
                "websocket" in str(change.old_value).lower()):
                validation_result["warnings"].append(
                    f"WebSocket parameter rename detected: {change.old_value} -> {change.new_value}. "
                    "Ensure all factory methods use consistent naming."
                )
        
        return validation_result
    
    def generate_change_impact_report(self, request_id: str) -> Dict[str, Any]:
        """Generate comprehensive change impact report."""
        if request_id not in self.change_requests:
            return {"error": f"Change request not found: {request_id}"}
        
        request = self.change_requests[request_id]
        
        # Analyze affected components
        all_affected = set()
        for change in request.changes:
            all_affected.update(change.affected_components)
        
        # Calculate impact metrics
        impact_metrics = {
            "total_changes": len(request.changes),
            "breaking_changes": len(request.get_breaking_changes()),
            "affected_interfaces": len(set(change.interface_name for change in request.changes)),
            "affected_components": len(all_affected),
            "impact_score": request.get_total_impact_score()
        }
        
        # Group changes by type
        changes_by_type = defaultdict(list)
        for change in request.changes:
            changes_by_type[change.change_type.value].append({
                "interface": change.interface_name,
                "description": change.description,
                "impact": change.impact_level.value
            })
        
        return {
            "request_id": request_id,
            "title": request.title,
            "status": request.status.value,
            "created_by": request.created_by,
            "created_at": request.created_at.isoformat(),
            "impact_metrics": impact_metrics,
            "changes_by_type": dict(changes_by_type),
            "safety_validation": self.validate_change_safety(request.changes),
            "affected_components": list(all_affected)
        }
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return f"req_{hashlib.md5(timestamp.encode()).hexdigest()[:8]}"


class PreCommitInterfaceGovernanceHook:
    """Pre-commit hook to enforce interface governance."""
    
    def __init__(self, governor: InterfaceEvolutionGovernor):
        self.governor = governor
        
    def validate_changes(self, changed_files: List[Path]) -> Dict[str, Any]:
        """Validate interface changes in pre-commit context."""
        validation_result = {
            "status": "PASS",
            "violations": [],
            "warnings": [],
            "blocking_issues": []
        }
        
        # Check for interface-related changes
        interface_files = [
            f for f in changed_files 
            if self._is_interface_file(f)
        ]
        
        if not interface_files:
            return validation_result
        
        # Analyze changes (simplified for pre-commit)
        for file_path in interface_files:
            file_violations = self._check_file_for_violations(file_path)
            validation_result["violations"].extend(file_violations)
        
        # Check for critical patterns
        critical_patterns = [
            "websocket_connection_id",
            "UserExecutionContext",
            "factory",
            "supervisor"
        ]
        
        for file_path in changed_files:
            if file_path.suffix == '.py':
                content_violations = self._check_content_patterns(file_path, critical_patterns)
                validation_result["warnings"].extend(content_violations)
        
        # Determine overall status
        if validation_result["violations"]:
            validation_result["status"] = "FAIL"
            validation_result["blocking_issues"] = [
                "Interface contract violations detected",
                "Run: python scripts/validate_factory_contracts.py --fix"
            ]
        elif validation_result["warnings"]:
            validation_result["status"] = "WARN"
        
        return validation_result
    
    def _is_interface_file(self, file_path: Path) -> bool:
        """Check if file contains interface definitions."""
        interface_indicators = [
            "factory",
            "contract",
            "interface",
            "user_execution_context",
            "supervisor_factory"
        ]
        
        file_str = str(file_path).lower()
        return any(indicator in file_str for indicator in interface_indicators)
    
    def _check_file_for_violations(self, file_path: Path) -> List[Dict[str, Any]]:
        """Check file for interface violations."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for websocket_connection_id usage
            if "websocket_connection_id=" in content:
                violations.append({
                    "file": str(file_path),
                    "type": "parameter_mismatch",
                    "message": "websocket_connection_id parameter found - should be websocket_client_id",
                    "severity": "CRITICAL"
                })
        
        except Exception as e:
            violations.append({
                "file": str(file_path),
                "type": "analysis_error",
                "message": f"Could not analyze file: {e}",
                "severity": "WARNING"
            })
        
        return violations
    
    def _check_content_patterns(self, file_path: Path, patterns: List[str]) -> List[Dict[str, Any]]:
        """Check file content for warning patterns."""
        warnings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    if pattern in line:
                        warnings.append({
                            "file": str(file_path),
                            "line": line_num,
                            "pattern": pattern,
                            "message": f"Interface-related change detected: {pattern}",
                            "severity": "INFO"
                        })
        
        except Exception:
            pass
        
        return warnings


def create_governance_system() -> InterfaceEvolutionGovernor:
    """Create and configure the interface evolution governance system."""
    registry = get_global_registry()
    governor = InterfaceEvolutionGovernor(registry)
    
    logger.info("Interface evolution governance system created")
    return governor


def validate_pre_commit_changes(changed_files: List[str]) -> bool:
    """Validate pre-commit changes for interface governance."""
    governor = create_governance_system()
    hook = PreCommitInterfaceGovernanceHook(governor)
    
    file_paths = [Path(f) for f in changed_files]
    result = hook.validate_changes(file_paths)
    
    # Print results
    if result["status"] == "FAIL":
        logger.error("❌ Pre-commit validation FAILED")
        for violation in result["violations"]:
            logger.error(f"  {violation['file']}: {violation['message']}")
        
        for issue in result["blocking_issues"]:
            logger.error(f"  BLOCKING: {issue}")
        
        return False
    
    elif result["status"] == "WARN":
        logger.warning("⚠️ Pre-commit validation passed with warnings")
        for warning in result["warnings"]:
            logger.warning(f"  {warning['file']}:{warning.get('line', '?')}: {warning['message']}")
    
    else:
        logger.info("✅ Pre-commit validation PASSED")
    
    return True


# Export public interface
__all__ = [
    "ChangeType",
    "ChangeImpact", 
    "ChangeStatus",
    "InterfaceChange",
    "ChangeRequest",
    "InterfaceEvolutionAnalyzer",
    "InterfaceEvolutionGovernor",
    "PreCommitInterfaceGovernanceHook",
    "create_governance_system",
    "validate_pre_commit_changes"
]