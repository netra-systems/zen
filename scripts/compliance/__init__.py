#!/usr/bin/env python3
"""
Architecture Compliance Checker Package
Enforces CLAUDE.md architectural rules with modular design.
"""

from .cli import CLIHandler, OutputHandler
from .core import ComplianceConfig, ComplianceResults, Violation
from .orchestrator import ArchitectureEnforcer
from .reporter import ComplianceReporter

__all__ = [
    'Violation',
    'ComplianceResults', 
    'ComplianceConfig',
    'ArchitectureEnforcer',
    'CLIHandler',
    'OutputHandler',
    'ComplianceReporter'
]