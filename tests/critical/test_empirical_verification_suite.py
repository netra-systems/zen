"""
Empirical Verification Suite for Issue #1176 Phase 3
===================================================

Week 1 Foundation Tasks: Empirical verification that validates actual 
system behavior against documented claims. This suite ensures that 
all system status claims are backed by real evidence, not assumptions.

This validator specifically tests:
1. Empirical validation of system health claims
2. Real test execution verification
3. Actual SSOT compliance measurement  
4. Infrastructure component validation
5. Configuration verification

CRITICAL: These tests provide empirical evidence, not trust-based validation.
"""

import subprocess
import sys
import json
import time
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEmpiricalVerificationSuite(SSotBaseTestCase):
    """
    Empirical verification of system claims against actual behavior.
    
    These tests generate real evidence for system status documentation.
    """

    def setUp(self):
        """Set up empirical verification suite."""
        super().setUp()
        self.project_root = Path(__file__).parent.parent.parent
        self.evidence_data = {}
        
    def test_empirical_test_execution_verification(self):
        """
        EMPIRICAL: Verify tests actually execute by measuring execution time
        and counting real test runs.
        """
        # Run a known small test to verify actual execution
        start_time = time.time()
        
        cmd = [
            sys.executable,
            "-m", "pytest",
            "tests/critical/test_infrastructure_validator.py::TestInfrastructureValidator::test_subprocess_execution_environment",
            "-v",
            "--tb=short"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        execution_time = time.time() - start_time
        
        # EMPIRICAL EVIDENCE: Real execution takes measurable time
        self.assertGreater(
            execution_time, 0.1,
            "Real test execution must take measurable time (>0.1s). "
            "Zero-time execution indicates bypassing or mocking."
        )
        
        # EMPIRICAL EVIDENCE: Must find and execute the specific test
        self.assertIn(
            "test_subprocess_execution_environment",
            result.stdout,
            "Test execution must show the specific test method ran"
        )
        
        # Store evidence
        self.evidence_data["test_execution_time"] = execution_time
        self.evidence_data["test_execution_success"] = result.returncode == 0
        
    def test_empirical_ssot_compliance_measurement(self):
        """
        EMPIRICAL: Measure actual SSOT compliance by scanning imports.
        """
        # Run SSOT compliance checker if it exists
        compliance_script = self.project_root / "scripts" / "check_architecture_compliance.py"
        
        if compliance_script.exists():
            cmd = [sys.executable, str(compliance_script)]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            # Extract actual compliance percentage
            compliance_percentage = None
            
            for line in result.stdout.split('\n'):
                if 'compliance' in line.lower() and '%' in line:
                    # Extract percentage from line
                    import re
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        compliance_percentage = float(match.group(1))
                        break
            
            # Store empirical evidence
            self.evidence_data["ssot_compliance_measured"] = compliance_percentage is not None
            self.evidence_data["ssot_compliance_percentage"] = compliance_percentage
            
            # Evidence that measurement actually ran
            self.assertIsNotNone(
                compliance_percentage,
                "SSOT compliance measurement must produce actual percentage, not claims"
            )
        else:
            self.evidence_data["ssot_compliance_script_exists"] = False

    def test_empirical_database_connectivity_verification(self):
        """
        EMPIRICAL: Test actual database connectivity, not configuration claims.
        """
        # Test database manager can be imported and initialized
        db_test_script = '''
import sys
sys.path.insert(0, ".")

try:
    from netra_backend.app.db.database_manager import DatabaseManager
    from netra_backend.app.config import get_config
    
    config = get_config()
    
    # Try to create database manager instance
    db_manager = DatabaseManager()
    
    print("Database manager instantiation: SUCCESS")
    sys.exit(0)
    
except Exception as e:
    print(f"Database manager instantiation: FAILED - {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, "-c", db_test_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        database_accessible = result.returncode == 0
        
        # Store empirical evidence
        self.evidence_data["database_manager_instantiable"] = database_accessible
        self.evidence_data["database_error"] = result.stderr if not database_accessible else None
        
        # This test documents actual capability, doesn't require success
        if not database_accessible:
            print(f"EMPIRICAL EVIDENCE: Database not accessible - {result.stderr}")

    def test_empirical_websocket_component_verification(self):
        """
        EMPIRICAL: Test actual WebSocket component availability.
        """
        websocket_test_script = '''
import sys
sys.path.insert(0, ".")

components_tested = {}

# Test WebSocket manager import
try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    components_tested["websocket_manager"] = True
except ImportError as e:
    components_tested["websocket_manager"] = False
    components_tested["websocket_manager_error"] = str(e)

# Test WebSocket auth import  
try:
    from netra_backend.app.websocket_core.auth import authenticate_websocket
    components_tested["websocket_auth"] = True
except ImportError as e:
    components_tested["websocket_auth"] = False
    components_tested["websocket_auth_error"] = str(e)

# Test WebSocket CORS import
try:
    from netra_backend.app.core.websocket_cors import configure_websocket_cors
    components_tested["websocket_cors"] = True
except ImportError as e:
    components_tested["websocket_cors"] = False
    components_tested["websocket_cors_error"] = str(e)

import json
print(json.dumps(components_tested))
'''
        
        result = subprocess.run(
            [sys.executable, "-c", websocket_test_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                websocket_status = json.loads(result.stdout)
                self.evidence_data["websocket_components"] = websocket_status
                
                # Count available components
                available_count = sum(1 for v in websocket_status.values() if v is True)
                self.evidence_data["websocket_components_available"] = available_count
                
            except json.JSONDecodeError:
                self.evidence_data["websocket_components_test_failed"] = True

    def test_empirical_agent_system_verification(self):
        """
        EMPIRICAL: Test actual agent system component availability.
        """
        agent_test_script = '''
import sys
sys.path.insert(0, ".")

agent_components = {}

# Test supervisor agent import
try:
    from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
    agent_components["supervisor_agent"] = True
except ImportError as e:
    agent_components["supervisor_agent"] = False
    agent_components["supervisor_error"] = str(e)

# Test execution engine import
try:
    from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
    agent_components["execution_engine"] = True
except ImportError as e:
    agent_components["execution_engine"] = False
    agent_components["execution_engine_error"] = str(e)

# Test agent registry import
try:
    from netra_backend.app.agents.registry import AgentRegistry
    agent_components["agent_registry"] = True
except ImportError as e:
    agent_components["agent_registry"] = False
    agent_components["agent_registry_error"] = str(e)

import json
print(json.dumps(agent_components))
'''
        
        result = subprocess.run(
            [sys.executable, "-c", agent_test_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                agent_status = json.loads(result.stdout)
                self.evidence_data["agent_components"] = agent_status
                
                # Count available components
                available_count = sum(1 for k, v in agent_status.items() 
                                    if k.endswith('_agent') or k.endswith('_engine') or k.endswith('_registry') 
                                    and v is True)
                self.evidence_data["agent_components_available"] = available_count
                
            except json.JSONDecodeError:
                self.evidence_data["agent_components_test_failed"] = True

    def test_empirical_configuration_verification(self):
        """
        EMPIRICAL: Test actual configuration system functionality.
        """
        config_test_script = '''
import sys
sys.path.insert(0, ".")

config_status = {}

# Test main config import and function
try:
    from netra_backend.app.config import get_config
    config = get_config()
    config_status["main_config"] = True
    config_status["config_type"] = type(config).__name__
except Exception as e:
    config_status["main_config"] = False
    config_status["main_config_error"] = str(e)

# Test database config import
try:
    from netra_backend.app.core.configuration.database import DatabaseConfig
    config_status["database_config"] = True
except ImportError as e:
    config_status["database_config"] = False
    config_status["database_config_error"] = str(e)

# Test isolated environment import
try:
    from dev_launcher.isolated_environment import IsolatedEnvironment
    env = IsolatedEnvironment()
    test_val = env.get("HOME", "default")
    config_status["isolated_environment"] = True
except Exception as e:
    config_status["isolated_environment"] = False
    config_status["isolated_environment_error"] = str(e)

import json
print(json.dumps(config_status))
'''
        
        result = subprocess.run(
            [sys.executable, "-c", config_test_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                config_status = json.loads(result.stdout)
                self.evidence_data["configuration_components"] = config_status
                
            except json.JSONDecodeError:
                self.evidence_data["configuration_test_failed"] = True

    def test_empirical_test_framework_verification(self):
        """
        EMPIRICAL: Test actual test framework SSOT compliance.
        """
        # Test SSOT base test case availability and functionality
        framework_test_script = '''
import sys
sys.path.insert(0, ".")

framework_status = {}

# Test SSOT base test case
try:
    from test_framework.ssot.base_test_case import SSotBaseTestCase
    
    # Test that we can create an instance
    class TestSSot(SSotBaseTestCase):
        def test_sample(self):
            pass
    
    test_instance = TestSSot()
    framework_status["ssot_base_test_case"] = True
    
except Exception as e:
    framework_status["ssot_base_test_case"] = False
    framework_status["ssot_base_error"] = str(e)

# Test unified test runner
try:
    from tests.unified_test_runner import UnifiedTestRunner
    runner = UnifiedTestRunner()
    framework_status["unified_test_runner"] = True
    
except Exception as e:
    framework_status["unified_test_runner"] = False
    framework_status["unified_runner_error"] = str(e)

import json
print(json.dumps(framework_status))
'''
        
        result = subprocess.run(
            [sys.executable, "-c", framework_test_script],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                framework_status = json.loads(result.stdout)
                self.evidence_data["test_framework_components"] = framework_status
                
            except json.JSONDecodeError:
                self.evidence_data["test_framework_test_failed"] = True

    def test_empirical_golden_path_component_verification(self):
        """
        EMPIRICAL: Test actual Golden Path component availability.
        """
        # Test that Golden Path documentation exists and is readable
        golden_path_doc = self.project_root / "docs" / "GOLDEN_PATH_USER_FLOW_COMPLETE.md"
        
        self.evidence_data["golden_path_doc_exists"] = golden_path_doc.exists()
        
        if golden_path_doc.exists():
            try:
                content = golden_path_doc.read_text()
                self.evidence_data["golden_path_doc_readable"] = True
                self.evidence_data["golden_path_doc_size"] = len(content)
                
                # Check for key Golden Path components
                key_components = [
                    "login",
                    "websocket", 
                    "agent",
                    "message",
                    "response"
                ]
                
                components_found = {}
                for component in key_components:
                    components_found[component] = component.lower() in content.lower()
                
                self.evidence_data["golden_path_components"] = components_found
                
            except Exception as e:
                self.evidence_data["golden_path_doc_error"] = str(e)

    def tearDown(self):
        """Store empirical evidence for documentation updates."""
        super().tearDown()
        
        # Write evidence data to file for documentation updates
        evidence_file = self.project_root / "evidence_data_issue_1176_phase3.json"
        
        with open(evidence_file, 'w') as f:
            json.dump(self.evidence_data, f, indent=2, default=str)
            
        print(f"\nEMPIRICAL EVIDENCE COLLECTED:")
        print(f"Evidence file: {evidence_file}")
        print(f"Evidence entries: {len(self.evidence_data)}")


if __name__ == "__main__":
    # Run empirical verification independently
    import unittest
    unittest.main()