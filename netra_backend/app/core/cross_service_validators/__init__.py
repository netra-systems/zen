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

from netra_backend.app.core.cross_service_validators.contract_validators import (
    APIContractValidator,
    EndpointValidator,
    SchemaCompatibilityValidator,
    WebSocketContractValidator,
)
from netra_backend.app.core.cross_service_validators.data_consistency_validators import (
    CrossServiceDataValidator,
    MessageDeliveryValidator,
    SessionStateValidator,
    UserDataConsistencyValidator,
)
from netra_backend.app.core.cross_service_validators.performance_validators import (
    CommunicationOverheadValidator,
    LatencyValidator,
    ResourceUsageValidator,
    ThroughputValidator,
)
from netra_backend.app.core.cross_service_validators.security_validators import (
    AuditTrailValidator,
    PermissionEnforcementValidator,
    ServiceAuthValidator,
    TokenValidationValidator,
)
from netra_backend.app.core.cross_service_validators.validator_framework import (
    CrossServiceValidatorFramework,
    ValidationReport,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
    ValidatorRegistry,
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