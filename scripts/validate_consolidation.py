#!/usr/bin/env python
"""Comprehensive validation script for SSOT consolidation.

This script validates the consolidation changes without requiring Docker.
It checks imports, module structure, and basic functionality.
"""
import os
import sys
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(message: str):
    """Print a section header."""
    print(f"\n{BLUE}{BOLD}{'=' * 70}{RESET}")
    print(f"{BLUE}{BOLD}{message}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 70}{RESET}")

def print_success(message: str):
    """Print success message."""
    try:
        print(f"{GREEN}[U+2713] {message}{RESET}")
    except UnicodeEncodeError:
        print(f"{GREEN}[OK] {message}{RESET}")

def print_warning(message: str):
    """Print warning message."""
    try:
        print(f"{YELLOW} WARNING:  {message}{RESET}")
    except UnicodeEncodeError:
        print(f"{YELLOW}[WARN] {message}{RESET}")

def print_error(message: str):
    """Print error message."""
    try:
        print(f"{RED}[U+2717] {message}{RESET}")
    except UnicodeEncodeError:
        print(f"{RED}[FAIL] {message}{RESET}")

def print_info(message: str):
    """Print info message."""
    print(f"  {message}")


class ConsolidationValidator:
    """Validates SSOT consolidation changes."""
    
    def __init__(self):
        self.results = {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'critical_failures': [],
            'team_status': {}
        }
        
    def run_all_validations(self) -> Dict[str, Any]:
        """Run all validation checks."""
        print_header("SSOT CONSOLIDATION VALIDATION")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Python Version: {sys.version}")
        
        # Team validations
        self.validate_team_3_triage()
        self.validate_team_8_websocket()
        self.validate_core_imports()
        self.validate_test_infrastructure()
        self.check_import_consistency()
        
        # Generate summary
        self.print_summary()
        
        return self.results
    
    def validate_team_3_triage(self):
        """Validate Team 3: Triage SubAgent consolidation."""
        print_header("TEAM 3: Triage SubAgent Consolidation")
        
        # Check if old module is removed
        old_module = "netra_backend.app.agents.triage_sub_agent"
        try:
            importlib.import_module(old_module)
            self.record_failure(f"Old module {old_module} still exists", critical=True)
        except ImportError:
            self.record_success("Old triage_sub_agent module properly removed")
        
        # Check new unified module
        try:
            from netra_backend.app.agents.triage.unified_triage_agent import (
                UnifiedTriageAgent,
                UnifiedTriageAgentFactory,
                TriageConfig
            )
            self.record_success("UnifiedTriageAgent imports successfully")
            
            # Check factory pattern
            if hasattr(UnifiedTriageAgentFactory, 'create_for_context'):
                self.record_success("Factory pattern implemented with create_for_context")
            else:
                self.record_failure("Factory pattern missing create_for_context method")
                
        except ImportError as e:
            self.record_failure(f"Cannot import UnifiedTriageAgent: {e}", critical=True)
        
        # Check models separation
        try:
            from netra_backend.app.agents.triage.models import (
                TriageResult,
                Priority,
                Complexity,
                ExtractedEntities,
                UserIntent,
                ToolRecommendation
            )
            self.record_success("Triage models properly separated")
            
            # Verify TriageResult structure
            result = TriageResult()
            if hasattr(result, 'category') and hasattr(result, 'priority'):
                self.record_success("TriageResult has required attributes")
            else:
                self.record_failure("TriageResult missing required attributes")
                
        except ImportError as e:
            self.record_failure(f"Cannot import triage models: {e}", critical=True)
        
        # Check execution priority
        try:
            from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
            if hasattr(UnifiedTriageAgent, 'EXECUTION_ORDER'):
                if UnifiedTriageAgent.EXECUTION_ORDER == 0:
                    self.record_success("Triage agent has correct execution priority (0 - FIRST)")
                else:
                    self.record_failure(f"Wrong execution priority: {UnifiedTriageAgent.EXECUTION_ORDER}")
            else:
                self.record_warning("EXECUTION_ORDER not defined on UnifiedTriageAgent")
        except:
            pass
        
        self.results['team_status']['team_3_triage'] = {
            'consolidation_complete': self.results['failed'] == 0,
            'factory_pattern': True,
            'models_separated': True,
            'execution_order': 'FIRST (0)'
        }
    
    def validate_team_8_websocket(self):
        """Validate Team 8: WebSocket consolidation."""
        print_header("TEAM 8: WebSocket Consolidation")
        
        # Check unified WebSocket manager
        try:
            from netra_backend.app.websocket_core import (
                UnifiedWebSocketManager,
                UnifiedWebSocketEmitter,
                WebSocketEmitterPool,
                CRITICAL_EVENTS
            )
            self.record_success("WebSocket core imports successfully")
            
            # Check critical events
            expected_events = {
                'agent_started',
                'agent_thinking', 
                'tool_executing',
                'tool_completed',
                'agent_completed'
            }
            
            if CRITICAL_EVENTS == expected_events:
                self.record_success("All 5 critical WebSocket events defined")
            else:
                missing = expected_events - CRITICAL_EVENTS if isinstance(CRITICAL_EVENTS, set) else expected_events
                self.record_failure(f"Missing critical events: {missing}")
                
        except ImportError as e:
            self.record_failure(f"Cannot import WebSocket components: {e}", critical=True)
        
        # Check backward compatibility
        try:
            from netra_backend.app.websocket_core import (
                WebSocketManager,
                WebSocketEventEmitter,
                RateLimiter
            )
            self.record_success("WebSocket backward compatibility maintained")
        except ImportError as e:
            self.record_warning(f"Backward compatibility issue: {e}")
        
        self.results['team_status']['team_8_websocket'] = {
            'unified_manager': True,
            'critical_events': 5,
            'backward_compatible': True
        }
    
    def validate_core_imports(self):
        """Validate core system imports."""
        print_header("Core System Imports")
        
        critical_modules = [
            "netra_backend.app.agents.supervisor.agent_registry",
            "netra_backend.app.agents.supervisor.execution_engine",
            "netra_backend.app.agents.tool_dispatcher",
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.websocket_core.unified_emitter",
            "netra_backend.app.core.configuration.base",
            "netra_backend.app.llm.llm_manager",
        ]
        
        for module_name in critical_modules:
            try:
                importlib.import_module(module_name)
                self.record_success(f"Import {module_name.split('.')[-1]}")
            except ImportError as e:
                self.record_failure(f"Cannot import {module_name}: {e}", critical=True)
    
    def validate_test_infrastructure(self):
        """Check test infrastructure status."""
        print_header("Test Infrastructure")
        
        # Check for Docker/Podman
        docker_available = False
        try:
            import subprocess
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                docker_available = True
                self.record_success("Docker is available")
        except:
            pass
        
        if not docker_available:
            try:
                import subprocess
                result = subprocess.run(['podman', '--version'], capture_output=True, timeout=5)
                if result.returncode == 0:
                    self.record_success("Podman is available")
                    docker_available = True
            except:
                pass
        
        if not docker_available:
            self.record_warning("No container runtime available (Docker/Podman)")
        
        # Check test framework
        test_modules = [
            "test_framework.base",
            "test_framework.test_context",
            "pytest",
        ]
        
        for module in test_modules:
            try:
                importlib.import_module(module)
                self.record_success(f"Test module {module} available")
            except ImportError:
                self.record_warning(f"Test module {module} not available")
    
    def check_import_consistency(self):
        """Check for any remaining old imports."""
        print_header("Import Consistency Check")
        
        # Check for old triage imports
        old_import_pattern = "from netra_backend.app.agents.triage_sub_agent"
        
        python_files = list(Path(project_root).rglob("*.py"))
        files_with_old_imports = []
        
        for py_file in python_files[:100]:  # Check first 100 files for speed
            try:
                content = py_file.read_text(encoding='utf-8')
                if old_import_pattern in content:
                    files_with_old_imports.append(str(py_file))
            except:
                pass
        
        if files_with_old_imports:
            self.record_failure(f"Found {len(files_with_old_imports)} files with old imports")
            for file in files_with_old_imports[:5]:  # Show first 5
                print_info(f"  - {file}")
        else:
            self.record_success("No old triage_sub_agent imports found (sample check)")
    
    def record_success(self, message: str):
        """Record a successful check."""
        self.results['total_checks'] += 1
        self.results['passed'] += 1
        print_success(message)
    
    def record_failure(self, message: str, critical: bool = False):
        """Record a failed check."""
        self.results['total_checks'] += 1
        self.results['failed'] += 1
        if critical:
            self.results['critical_failures'].append(message)
        print_error(message)
    
    def record_warning(self, message: str):
        """Record a warning."""
        self.results['warnings'] += 1
        print_warning(message)
    
    def print_summary(self):
        """Print validation summary."""
        print_header("VALIDATION SUMMARY")
        
        total = self.results['total_checks']
        passed = self.results['passed']
        failed = self.results['failed']
        warnings = self.results['warnings']
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"\nTotal Checks: {total}")
        print(f"Passed: {GREEN}{passed}{RESET} ({pass_rate:.1f}%)")
        print(f"Failed: {RED}{failed}{RESET}")
        print(f"Warnings: {YELLOW}{warnings}{RESET}")
        
        if self.results['critical_failures']:
            print(f"\n{RED}{BOLD}CRITICAL FAILURES:{RESET}")
            for failure in self.results['critical_failures']:
                print(f"  {RED}[U+2022] {failure}{RESET}")
        
        # Team status
        print(f"\n{BOLD}Team Status:{RESET}")
        for team, status in self.results['team_status'].items():
            team_name = team.replace('_', ' ').title()
            if isinstance(status, dict) and status.get('consolidation_complete'):
                try:
                    print(f"  {GREEN}[U+2713]{RESET} {team_name}: Consolidation appears complete")
                except UnicodeEncodeError:
                    print(f"  {GREEN}[OK]{RESET} {team_name}: Consolidation appears complete")
            else:
                try:
                    print(f"  {YELLOW} WARNING: {RESET} {team_name}: In progress or needs verification")
                except UnicodeEncodeError:
                    print(f"  {YELLOW}[WARN]{RESET} {team_name}: In progress or needs verification")
        
        # Overall verdict
        print(f"\n{BOLD}Overall Status:{RESET}")
        if failed == 0 and len(self.results['critical_failures']) == 0:
            try:
                print(f"{GREEN}{BOLD}[U+2713] VALIDATION PASSED - System appears stable{RESET}")
            except UnicodeEncodeError:
                print(f"{GREEN}{BOLD}[OK] VALIDATION PASSED - System appears stable{RESET}")
        elif len(self.results['critical_failures']) > 0:
            try:
                print(f"{RED}{BOLD}[U+2717] VALIDATION FAILED - Critical issues found{RESET}")
            except UnicodeEncodeError:
                print(f"{RED}{BOLD}[FAIL] VALIDATION FAILED - Critical issues found{RESET}")
        else:
            try:
                print(f"{YELLOW}{BOLD} WARNING:  VALIDATION PARTIAL - Some issues need attention{RESET}")
            except UnicodeEncodeError:
                print(f"{YELLOW}{BOLD}[WARN] VALIDATION PARTIAL - Some issues need attention{RESET}")
        
        # Recommendations
        print(f"\n{BOLD}Recommendations:{RESET}")
        if not self.results.get('docker_available'):
            print("  1. Install Docker or Podman for full testing capabilities")
        if failed > 0:
            print("  2. Fix import errors before proceeding with consolidation")
        if warnings > 0:
            print("  3. Address warnings to ensure smooth operation")
        print("  4. Run full test suite once container runtime is available")


def main():
    """Main execution."""
    validator = ConsolidationValidator()
    results = validator.run_all_validations()
    
    # Exit with appropriate code
    if results['failed'] > 0 or len(results['critical_failures']) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()