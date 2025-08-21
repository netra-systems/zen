"""Demo service module for enterprise demonstrations."""

# FIXME: DemoService not available in corpus.core
# from netra_backend.app.services.corpus.core import DemoService
from netra_backend.app.agents.demo_service.triage import DemoTriageService  
from netra_backend.app.agents.demo_service.optimization import DemoOptimizationService
from netra_backend.app.agents.demo_service.reporting import DemoReportingService

__all__ = [
    "DemoService",
    "DemoTriageService", 
    "DemoOptimizationService",
    "DemoReportingService"
]