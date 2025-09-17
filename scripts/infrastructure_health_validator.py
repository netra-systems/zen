#!/usr/bin/env python
"""
Infrastructure Health Validator for Issue #1176 Phase 3
======================================================

Week 1 Foundation Tasks: System health validation script that provides
empirical evidence for infrastructure status claims.

This validator performs comprehensive health checks and generates
evidence-based reports for system status documentation.

Usage:
    python scripts/infrastructure_health_validator.py [--output-format json|markdown]
    
Returns:
    - Exit code 0: All critical infrastructure healthy
    - Exit code 1: Critical infrastructure issues found
    - Exit code 2: Infrastructure validation failed to run
"""

import sys
import json
import time
import subprocess
import importlib
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, List, Any, Optional


class InfrastructureHealthValidator:
    """
    Comprehensive infrastructure health validation with empirical evidence collection.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.health_data = {
            "validation_timestamp": datetime.now(UTC).isoformat(),
            "validation_version": "1176_phase3_week1",
            "overall_health": "UNKNOWN",
            "critical_issues": [],
            "component_status": {},
            "empirical_evidence": {},
            "recommendations": []
        }
        
    def validate_test_infrastructure(self) -> Dict[str, Any]:
        """Validate test infrastructure components."""
        print("🔍 Validating Test Infrastructure...")
        
        test_infra_status = {
            "unified_test_runner": False,
            "ssot_framework": False, 
            "test_collection": False,
            "test_execution": False
        }
        
        # Test unified test runner
        try:
            test_runner_path = self.project_root / "tests" / "unified_test_runner.py"
            
            if test_runner_path.exists():
                # Test help command
                result = subprocess.run(
                    [sys.executable, str(test_runner_path), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.project_root
                )
                
                test_infra_status["unified_test_runner"] = result.returncode == 0
                
                if result.returncode != 0:
                    self.health_data["critical_issues"].append(
                        f"Unified test runner help command failed: {result.stderr}"
                    )
                    
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"Unified test runner validation failed: {e}"
            )
            
        # Test SSOT framework availability
        try:
            import test_framework.ssot.base_test_case
            test_infra_status["ssot_framework"] = True
        except ImportError as e:
            self.health_data["critical_issues"].append(
                f"SSOT framework not available: {e}"
            )
            
        # Test basic test collection
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "--quiet", "tests/critical/"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            test_infra_status["test_collection"] = result.returncode == 0
            
            if result.returncode != 0:
                self.health_data["critical_issues"].append(
                    f"Test collection failed: {result.stderr}"
                )
                
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"Test collection validation failed: {e}"
            )
            
        # Test actual test execution with timing
        try:
            start_time = time.time()
            
            result = subprocess.run(
                [sys.executable, "-m", "pytest", 
                 "tests/critical/test_infrastructure_validator.py::TestInfrastructureValidator::test_subprocess_execution_environment",
                 "-v"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_root
            )
            
            execution_time = time.time() - start_time
            
            test_infra_status["test_execution"] = (
                result.returncode == 0 and execution_time > 0.1
            )
            
            self.health_data["empirical_evidence"]["test_execution_time"] = execution_time
            
            if execution_time <= 0.1:
                self.health_data["critical_issues"].append(
                    "Test execution too fast - indicates bypassing or mocking"
                )
                
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"Test execution validation failed: {e}"
            )
            
        return test_infra_status
        
    def validate_application_components(self) -> Dict[str, Any]:
        """Validate core application components."""
        print("🔍 Validating Application Components...")
        
        app_status = {
            "config_system": False,
            "database_manager": False,
            "websocket_core": False,
            "agent_system": False,
            "cors_config": False
        }
        
        # Test config system
        try:
            from netra_backend.app.config import get_config
            config = get_config()
            app_status["config_system"] = config is not None
            
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"Config system failed: {e}"
            )
            
        # Test database manager
        try:
            from netra_backend.app.db.database_manager import DatabaseManager
            db_manager = DatabaseManager()
            app_status["database_manager"] = True
            
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"Database manager failed: {e}"
            )
            
        # Test WebSocket components
        websocket_components = 0
        websocket_total = 3
        
        try:
            from netra_backend.app.websocket_core.manager import WebSocketManager
            websocket_components += 1
        except ImportError:
            pass
            
        try:
            from netra_backend.app.websocket_core.auth import authenticate_websocket
            websocket_components += 1
        except ImportError:
            pass
            
        try:
            from netra_backend.app.core.websocket_cors import configure_websocket_cors
            websocket_components += 1
        except ImportError:
            pass
            
        app_status["websocket_core"] = websocket_components >= 2
        self.health_data["empirical_evidence"]["websocket_components_available"] = websocket_components
        
        if websocket_components < 2:
            self.health_data["critical_issues"].append(
                f"WebSocket components incomplete: {websocket_components}/{websocket_total} available"
            )
            
        # Test agent system
        agent_components = 0
        agent_total = 3
        
        try:
            from netra_backend.app.agents.supervisor_agent_modern import SupervisorAgent
            agent_components += 1
        except ImportError:
            pass
            
        try:
            from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
            agent_components += 1
        except ImportError:
            pass
            
        try:
            from netra_backend.app.agents.registry import AgentRegistry
            agent_components += 1
        except ImportError:
            pass
            
        app_status["agent_system"] = agent_components >= 2
        self.health_data["empirical_evidence"]["agent_components_available"] = agent_components
        
        if agent_components < 2:
            self.health_data["critical_issues"].append(
                f"Agent system components incomplete: {agent_components}/{agent_total} available"
            )
            
        # Test CORS config
        try:
            from shared.cors_config import get_cors_config
            cors_config = get_cors_config()
            app_status["cors_config"] = cors_config is not None
            
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"CORS config failed: {e}"
            )
            
        return app_status
        
    def validate_environment_setup(self) -> Dict[str, Any]:
        """Validate environment and path setup."""
        print("🔍 Validating Environment Setup...")
        
        env_status = {
            "python_path": False,
            "isolated_environment": False,
            "project_structure": False,
            "file_permissions": False
        }
        
        # Test Python path setup
        try:
            import netra_backend
            import test_framework
            import shared
            env_status["python_path"] = True
            
        except ImportError as e:
            self.health_data["critical_issues"].append(
                f"Python path setup failed: {e}"
            )
            
        # Test isolated environment
        try:
            from dev_launcher.isolated_environment import IsolatedEnvironment
            env = IsolatedEnvironment()
            test_val = env.get("HOME", "default")
            env_status["isolated_environment"] = True
            
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"Isolated environment failed: {e}"
            )
            
        # Test project structure
        required_dirs = ["tests", "test_framework", "netra_backend", "shared", "scripts"]
        missing_dirs = []
        
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                missing_dirs.append(dir_name)
                
        env_status["project_structure"] = len(missing_dirs) == 0
        
        if missing_dirs:
            self.health_data["critical_issues"].append(
                f"Missing project directories: {missing_dirs}"
            )
            
        # Test critical file permissions
        critical_files = [
            "tests/unified_test_runner.py",
            "test_framework/ssot/base_test_case.py"
        ]
        
        permission_issues = []
        
        for file_path in critical_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                permission_issues.append(f"{file_path}: Does not exist")
            elif not full_path.is_file():
                permission_issues.append(f"{file_path}: Not a file")
                
        env_status["file_permissions"] = len(permission_issues) == 0
        
        if permission_issues:
            self.health_data["critical_issues"].append(
                f"File permission issues: {permission_issues}"
            )
            
        return env_status
        
    def measure_ssot_compliance(self) -> Optional[float]:
        """Measure actual SSOT compliance if script is available."""
        print("🔍 Measuring SSOT Compliance...")
        
        compliance_script = self.project_root / "scripts" / "check_architecture_compliance.py"
        
        if not compliance_script.exists():
            self.health_data["empirical_evidence"]["ssot_compliance_script_available"] = False
            return None
            
        try:
            result = subprocess.run(
                [sys.executable, str(compliance_script)],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )
            
            # Extract compliance percentage
            import re
            for line in result.stdout.split('\n'):
                if 'compliance' in line.lower() and '%' in line:
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        compliance = float(match.group(1))
                        self.health_data["empirical_evidence"]["ssot_compliance_percentage"] = compliance
                        return compliance
                        
            self.health_data["empirical_evidence"]["ssot_compliance_measurement_failed"] = True
            return None
            
        except Exception as e:
            self.health_data["critical_issues"].append(
                f"SSOT compliance measurement failed: {e}"
            )
            return None
            
    def run_validation(self) -> bool:
        """Run complete infrastructure health validation."""
        print("🚀 Starting Infrastructure Health Validation...")
        print(f"Project Root: {self.project_root}")
        print(f"Timestamp: {self.health_data['validation_timestamp']}")
        print()
        
        # Run all validation checks
        self.health_data["component_status"]["test_infrastructure"] = self.validate_test_infrastructure()
        self.health_data["component_status"]["application_components"] = self.validate_application_components()
        self.health_data["component_status"]["environment_setup"] = self.validate_environment_setup()
        
        # Measure SSOT compliance
        ssot_compliance = self.measure_ssot_compliance()
        
        # Calculate overall health
        all_components = []
        for category in self.health_data["component_status"].values():
            all_components.extend(category.values())
            
        healthy_components = sum(1 for status in all_components if status)
        total_components = len(all_components)
        
        health_percentage = (healthy_components / total_components) * 100 if total_components > 0 else 0
        
        self.health_data["empirical_evidence"]["health_percentage"] = health_percentage
        self.health_data["empirical_evidence"]["healthy_components"] = healthy_components
        self.health_data["empirical_evidence"]["total_components"] = total_components
        
        # Determine overall health status
        critical_issues_count = len(self.health_data["critical_issues"])
        
        if critical_issues_count == 0 and health_percentage >= 90:
            self.health_data["overall_health"] = "HEALTHY"
        elif critical_issues_count <= 2 and health_percentage >= 75:
            self.health_data["overall_health"] = "STABLE_WITH_ISSUES"
        elif health_percentage >= 50:
            self.health_data["overall_health"] = "DEGRADED"
        else:
            self.health_data["overall_health"] = "CRITICAL"
            
        # Generate recommendations
        self._generate_recommendations()
        
        print()
        print("=" * 60)
        print(f"🏥 Infrastructure Health: {self.health_data['overall_health']}")
        print(f"📊 Health Percentage: {health_percentage:.1f}%")
        print(f"🔧 Components Healthy: {healthy_components}/{total_components}")
        print(f"⚠️  Critical Issues: {critical_issues_count}")
        
        if ssot_compliance is not None:
            print(f"📋 SSOT Compliance: {ssot_compliance:.1f}%")
            
        print("=" * 60)
        
        return self.health_data["overall_health"] in ["HEALTHY", "STABLE_WITH_ISSUES"]
        
    def _generate_recommendations(self):
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Test infrastructure recommendations
        test_infra = self.health_data["component_status"]["test_infrastructure"]
        
        if not test_infra.get("unified_test_runner"):
            recommendations.append("Fix unified test runner - critical for all testing")
            
        if not test_infra.get("ssot_framework"):
            recommendations.append("Restore SSOT test framework - required for consistent testing")
            
        if not test_infra.get("test_execution"):
            recommendations.append("Fix test execution - tests must actually run, not just collect")
            
        # Application component recommendations
        app_components = self.health_data["component_status"]["application_components"]
        
        if not app_components.get("config_system"):
            recommendations.append("Fix configuration system - critical for all services")
            
        if not app_components.get("websocket_core"):
            recommendations.append("Fix WebSocket components - required for Golden Path")
            
        if not app_components.get("agent_system"):
            recommendations.append("Fix agent system - core business functionality")
            
        # Environment recommendations
        env_status = self.health_data["component_status"]["environment_setup"]
        
        if not env_status.get("python_path"):
            recommendations.append("Fix Python path configuration - blocks all imports")
            
        if not env_status.get("project_structure"):
            recommendations.append("Restore missing project directories")
            
        # General recommendations
        critical_count = len(self.health_data["critical_issues"])
        
        if critical_count > 5:
            recommendations.append("Focus on critical infrastructure fixes before feature work")
            
        if self.health_data["empirical_evidence"].get("health_percentage", 0) < 75:
            recommendations.append("Infrastructure requires comprehensive remediation")
            
        self.health_data["recommendations"] = recommendations
        
    def output_json(self) -> str:
        """Output validation results as JSON."""
        return json.dumps(self.health_data, indent=2, default=str)
        
    def output_markdown(self) -> str:
        """Output validation results as Markdown."""
        md_lines = [
            f"# Infrastructure Health Validation Report",
            f"",
            f"**Validation Time:** {self.health_data['validation_timestamp']}",
            f"**Validation Version:** {self.health_data['validation_version']}",
            f"",
            f"## 🏥 Overall Health: {self.health_data['overall_health']}",
            f"",
            f"**Health Metrics:**",
            f"- Health Percentage: {self.health_data['empirical_evidence'].get('health_percentage', 0):.1f}%",
            f"- Healthy Components: {self.health_data['empirical_evidence'].get('healthy_components', 0)}/{self.health_data['empirical_evidence'].get('total_components', 0)}",
            f"- Critical Issues: {len(self.health_data['critical_issues'])}",
            f""
        ]
        
        if "ssot_compliance_percentage" in self.health_data["empirical_evidence"]:
            md_lines.append(f"- SSOT Compliance: {self.health_data['empirical_evidence']['ssot_compliance_percentage']:.1f}%")
            md_lines.append("")
            
        # Component status
        md_lines.extend([
            "## 🔧 Component Status",
            ""
        ])
        
        for category, components in self.health_data["component_status"].items():
            md_lines.append(f"### {category.replace('_', ' ').title()}")
            md_lines.append("")
            
            for component, status in components.items():
                status_icon = "✅" if status else "❌"
                md_lines.append(f"- {status_icon} {component.replace('_', ' ').title()}")
                
            md_lines.append("")
            
        # Critical issues
        if self.health_data["critical_issues"]:
            md_lines.extend([
                "## ⚠️ Critical Issues",
                ""
            ])
            
            for i, issue in enumerate(self.health_data["critical_issues"], 1):
                md_lines.append(f"{i}. {issue}")
                
            md_lines.append("")
            
        # Recommendations
        if self.health_data["recommendations"]:
            md_lines.extend([
                "## 💡 Recommendations",
                ""
            ])
            
            for i, rec in enumerate(self.health_data["recommendations"], 1):
                md_lines.append(f"{i}. {rec}")
                
            md_lines.append("")
            
        # Empirical evidence
        md_lines.extend([
            "## 📊 Empirical Evidence",
            ""
        ])
        
        for key, value in self.health_data["empirical_evidence"].items():
            formatted_key = key.replace('_', ' ').title()
            md_lines.append(f"- **{formatted_key}:** {value}")
            
        return "\n".join(md_lines)


def main():
    """Main entry point for infrastructure health validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Infrastructure Health Validator for Issue #1176 Phase 3"
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "markdown"],
        default="markdown",
        help="Output format for validation results"
    )
    parser.add_argument(
        "--output-file",
        help="Output file path (optional, defaults to stdout)"
    )
    
    args = parser.parse_args()
    
    try:
        validator = InfrastructureHealthValidator()
        success = validator.run_validation()
        
        # Generate output
        if args.output_format == "json":
            output = validator.output_json()
        else:
            output = validator.output_markdown()
            
        # Write output
        if args.output_file:
            with open(args.output_file, 'w') as f:
                f.write(output)
            print(f"\n📄 Validation report written to: {args.output_file}")
        else:
            print("\n" + output)
            
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ Infrastructure health validation failed: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()