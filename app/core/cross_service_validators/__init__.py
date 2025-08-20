"""
Cross-Service Validators Framework

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: Growth & Enterprise
2. Business Goal: Reduce service integration failures by 90%
3. Value Impact: $15K+ monthly revenue protection from avoiding outages
4. Revenue Impact: Prevent 5-10% customer churn from reliability issues

Validates contracts, data consistency, performance, and security
across service boundaries to ensure reliable service interactions.
"""

from .contract_validators import (
    APIContractValidator,
    WebSocketContractValidator,
    SchemaCompatibilityValidator,
    EndpointValidator
)

from .data_consistency_validators import (
    UserDataConsistencyValidator,
    SessionStateValidator,
    MessageDeliveryValidator,
    CrossServiceDataValidator
)

from .performance_validators import (
    LatencyValidator,
    ThroughputValidator,
    ResourceUsageValidator,
    CommunicationOverheadValidator
)

from .security_validators import (
    TokenValidationValidator,
    PermissionEnforcementValidator,
    AuditTrailValidator,
    ServiceAuthValidator
)

from .validator_framework import (
    CrossServiceValidatorFramework,
    ValidationReport,
    ValidationResult,
    ValidationStatus,
    ValidationSeverity,
    ValidatorRegistry
)

__all__ = [
    "APIContractValidator",
    "WebSocketContractValidator", 
    "SchemaCompatibilityValidator",
    "EndpointValidator",
    "UserDataConsistencyValidator",
    "SessionStateValidator",
    "MessageDeliveryValidator",
    "CrossServiceDataValidator",
    "LatencyValidator",
    "ThroughputValidator",
    "ResourceUsageValidator",
    "CommunicationOverheadValidator",
    "TokenValidationValidator",
    "PermissionEnforcementValidator",
    "AuditTrailValidator",
    "ServiceAuthValidator",
    "CrossServiceValidatorFramework",
    "ValidationReport",
    "ValidationResult",
    "ValidationStatus",
    "ValidationSeverity",
    "ValidatorRegistry"
]