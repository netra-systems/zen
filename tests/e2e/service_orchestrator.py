"""

Service Orchestrator - E2E Service Management (SSOT Compliant)



This file now redirects to the UnifiedServiceOrchestrator to maintain 

Single Source of Truth (SSOT) compliance.



Business Value: Eliminates duplicate Docker management implementations

and provides consistent E2E test infrastructure.

"""



# SSOT compliance: Import from unified orchestrator

from tests.e2e.unified_service_orchestrator import (

    UnifiedServiceOrchestrator as E2EServiceOrchestrator,

    create_test_orchestrator,

    cleanup_test_orchestrator

)



# Backward compatibility exports

__all__ = [

    'E2EServiceOrchestrator',

    'create_test_orchestrator', 

    'cleanup_test_orchestrator'

]

