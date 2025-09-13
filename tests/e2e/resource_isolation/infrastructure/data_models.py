"""

Data Models for Resource Isolation Testing



Contains dataclasses and configuration for resource isolation tests.

"""



import os

from dataclasses import dataclass

from typing import Any, Dict, Optional



import warnings

with warnings.catch_warnings():

    warnings.simplefilter("ignore", DeprecationWarning)

    import websockets

    try:

        from websockets import ServerConnection as WebSocketServerProtocol

    except ImportError:

        # Fallback for older versions

        from websockets import ServerConnection as WebSocketServerProtocol



# Performance Requirements

RESOURCE_LIMITS = {

    "per_agent_cpu_max": 25.0,      # 25% CPU per agent

    "per_agent_memory_mb": 512,     # 512MB memory per agent

    "isolation_violations": 0,       # Zero violations

    "cross_tenant_impact_max": 10.0  # < 10% performance impact

}



@dataclass

class ResourceMetrics:

    """Resource utilization metrics for an agent."""

    tenant_id: str

    timestamp: float

    cpu_percent: float

    memory_mb: float

    memory_percent: float

    threads: int

    handles: int = 0

    io_reads: int = 0

    io_writes: int = 0



@dataclass

class TenantAgent:

    """Represents a tenant's agent instance."""

    tenant_id: str

    user_id: str

    websocket_uri: str

    jwt_token: str

    connection: Optional[WebSocketServerProtocol] = None

    process_info: Optional[Dict] = None

    

@dataclass

class ResourceViolation:

    """Represents a resource usage violation."""

    tenant_id: str

    violation_type: str  # 'cpu', 'memory', 'isolation'

    severity: str       # 'warning', 'critical'

    measured_value: float

    threshold_value: float

    timestamp: float



@dataclass 

class PerformanceImpactReport:

    """Report on cross-tenant performance impact."""

    baseline_metrics: Dict[str, ResourceMetrics]

    stressed_metrics: Dict[str, ResourceMetrics]

    impact_percentages: Dict[str, float]

