"""
Main compliance rule factory.
Coordinates OWASP and standard compliance rule creation through focused modules.
"""

from app.logging_config import central_logger
from netra_backend.app.compliance_checks import ComplianceCheckManager
from netra_backend.app.owasp_rules import OwaspRuleFactory
from netra_backend.app.standard_rules import StandardRuleFactory

logger = central_logger.get_logger(__name__)


class ComplianceRuleFactory:
    """Main factory for creating all compliance rules."""
    
    def __init__(self, check_manager: ComplianceCheckManager):
        self.check_manager = check_manager
        self.owasp_factory = OwaspRuleFactory(check_manager)
        self.standard_factory = StandardRuleFactory(check_manager)
    
    def initialize_all_checks(self) -> None:
        """Initialize all compliance checks."""
        self.owasp_factory.add_all_owasp_checks()
        self.standard_factory.add_all_standard_checks()