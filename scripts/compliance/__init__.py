#!/usr/bin/env python3
"""
Architecture Compliance Checker Package
Enforces CLAUDE.md architectural rules with modular design.
"""

from .core import Violation, ComplianceResults, ComplianceConfig
from .orchestrator import ArchitectureEnforcer
from .cli import CLIHandler, OutputHandler
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