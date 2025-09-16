#!/usr/bin/env python3
"""
Architecture Compliance Checker Package
Enforces CLAUDE.md architectural rules with modular design.
"""

from scripts.compliance.cli import CLIHandler, OutputHandler
from scripts.compliance.core import ComplianceConfig, ComplianceResults, Violation
from scripts.compliance.orchestrator import ArchitectureEnforcer
from scripts.compliance.reporter import ComplianceReporter
from scripts.compliance.improved_ssot_checker import ImprovedSSOTChecker

__all__ = [
    'Violation',
    'ComplianceResults',
    'ComplianceConfig',
    'ArchitectureEnforcer',
    'CLIHandler',
    'OutputHandler',
    'ComplianceReporter',
    'ImprovedSSOTChecker'
]