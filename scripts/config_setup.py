#!/usr/bin/env python3
"""
Configuration Setup Orchestrator for Netra AI Platform installer.
Orchestrates database setup, environment files, and testing.
CRITICAL: All functions MUST be  <= 8 lines, file  <= 300 lines.
"""

import sys
from pathlib import Path
from typing import List

# Add scripts directory to path for imports
script_dir = Path(__file__).parent

from config_setup_core import create_environment_file, setup_databases
from config_setup_scripts import create_startup_scripts, test_installation
from installer_types import InstallerConfig, InstallerResult


def combine_config_results(results: List[InstallerResult]) -> InstallerResult:
    """Combine multiple configuration results"""
    all_messages = []
    all_errors = []
    all_warnings = []
    overall_success = True
    
    for result in results:
        all_messages.extend(result.messages)
        all_errors.extend(result.errors)
        all_warnings.extend(result.warnings)
        if not result.success:
            overall_success = False
    
    return InstallerResult(overall_success, all_messages, all_errors, all_warnings)


def run_complete_configuration_setup(config: InstallerConfig) -> InstallerResult:
    """Run complete configuration and setup process"""
    setup_results = [
        setup_databases(config),
        create_environment_file(config),
        create_startup_scripts(config),
        test_installation(config)
    ]
    
    return combine_config_results(setup_results)