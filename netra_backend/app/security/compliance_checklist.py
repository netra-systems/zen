"""
Security Compliance Checklist for Netra AI Platform.
Implements comprehensive security compliance checks against industry standards.
"""

from netra_backend.app.compliance_checks import ComplianceCheckManager, ComplianceStandard, ComplianceCheck
from netra_backend.app.compliance_validators import ComplianceValidator
from netra_backend.app.compliance_rules import ComplianceRuleFactory


class SecurityComplianceChecklist:
    """Comprehensive security compliance checklist."""
    
    def __init__(self):
        self.check_manager = ComplianceCheckManager()
        self.validator = ComplianceValidator(self.check_manager)
        self.rule_factory = ComplianceRuleFactory(self.check_manager)
        self._initialize_checks()
    
    def _initialize_checks(self) -> None:
        """Initialize all compliance checks."""
        self.rule_factory.initialize_all_checks()
    
    @property
    def checks(self):
        """Backward compatibility property."""
        return self.check_manager.checks
    
    def get_compliance_summary(self):
        """Get overall compliance summary."""
        return self.validator.get_compliance_summary()
    
    def get_checks_by_standard(self, standard: ComplianceStandard):
        """Get all checks for a specific standard."""
        return self.check_manager.get_checks_by_standard(standard)
    
    def get_high_priority_issues(self):
        """Get high priority compliance issues."""
        return self.validator.get_high_priority_issues()
    
    def get_remediation_plan(self):
        """Get prioritized remediation plan."""
        return self.validator.get_remediation_plan()
    
    def export_compliance_report(self):
        """Export compliance report as formatted text."""
        return self.validator.export_compliance_report()


# Global instance
security_compliance_checklist = SecurityComplianceChecklist()