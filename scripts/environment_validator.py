#!/usr/bin/env python3
"""
Elite Environment Validation Script
Validates complete development environment configuration with REAL connections.
"""

import os
import sys
import json
import asyncio
import socket
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.environment_validator_core import EnvironmentValidatorCore
from scripts.environment_validator_database import DatabaseValidator
from scripts.environment_validator_ports import PortValidator
from scripts.environment_validator_dependencies import DependencyValidator


class EnvironmentValidator:
    """Main environment validation orchestrator."""
    
    def __init__(self):
        """Initialize validator with core components."""
        self.core = EnvironmentValidatorCore()
        self.db_validator = DatabaseValidator()
        self.port_validator = PortValidator()
        self.dep_validator = DependencyValidator()
        self.results = {}
        
    async def validate_complete_environment(self) -> Dict[str, Any]:
        """Execute comprehensive environment validation."""
        print("ELITE ENVIRONMENT VALIDATION - ULTRA DEEP THINKING")
        print("=" * 80)
        
        await self._validate_all_components()
        self._generate_final_report()
        return self.results
    
    async def _validate_all_components(self) -> None:
        """Validate all environment components in parallel."""
        validation_tasks = [
            self._validate_env_variables(),
            self._validate_databases(),
            self._validate_ports(),
            self._validate_dependencies()
        ]
        
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        self._process_validation_results(results)
    
    async def _validate_env_variables(self) -> Dict[str, Any]:
        """Validate environment variables configuration."""
        print("* Validating Environment Variables...")
        return await self.core.validate_environment_variables()
    
    async def _validate_databases(self) -> Dict[str, Any]:
        """Validate database connectivity."""
        print("* Testing Database Connections...")
        return await self.db_validator.validate_all_databases()
    
    async def _validate_ports(self) -> Dict[str, Any]:
        """Validate port availability."""
        print("* Checking Port Availability...")
        return await self.port_validator.validate_required_ports()
    
    async def _validate_dependencies(self) -> Dict[str, Any]:
        """Validate system dependencies."""
        print("* Validating Dependencies...")
        return await self.dep_validator.validate_all_dependencies()
    
    def _process_validation_results(self, results: List[Any]) -> None:
        """Process validation results from all components."""
        component_names = ["env_vars", "databases", "ports", "dependencies"]
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.results[component_names[i]] = {"status": "error", "error": str(result)}
            else:
                self.results[component_names[i]] = result
    
    def _generate_final_report(self) -> None:
        """Generate comprehensive validation report."""
        report_generator = ValidationReportGenerator(self.results)
        report_generator.display_comprehensive_report()
        report_generator.save_results_to_file()


class ValidationReportGenerator:
    """Generates and displays validation reports."""
    
    def __init__(self, results: Dict[str, Any]):
        """Initialize report generator with results."""
        self.results = results
        self.timestamp = datetime.now().isoformat()
    
    def display_comprehensive_report(self) -> None:
        """Display comprehensive validation report."""
        self._display_header()
        self._display_component_summaries()
        self._display_overall_status()
        self._display_recommendations()
    
    def _display_header(self) -> None:
        """Display report header."""
        print("\n" + "=" * 80)
        print("ELITE ENVIRONMENT VALIDATION REPORT")
        print("=" * 80)
        print(f"Timestamp: {self.timestamp}")
    
    def _display_component_summaries(self) -> None:
        """Display summaries for each component."""
        for component, data in self.results.items():
            self._display_component_status(component, data)
    
    def _display_component_status(self, component: str, data: Dict[str, Any]) -> None:
        """Display status for a single component."""
        status = data.get("status", "unknown")
        icon = "[OK]" if status == "success" else "[ERROR]" if status == "error" else "[WARN]"
        
        print(f"\n{icon} {component.upper().replace('_', ' ')}: {status.upper()}")
        if "summary" in data:
            print(f"   {data['summary']}")
    
    def _display_overall_status(self) -> None:
        """Display overall environment status."""
        total_success = sum(1 for r in self.results.values() if r.get("status") == "success")
        total_components = len(self.results)
        
        if total_success == total_components:
            print(f"\n[SUCCESS] ENVIRONMENT FULLY VALIDATED ({total_success}/{total_components})")
        else:
            print(f"\n[WARNING] ENVIRONMENT NEEDS ATTENTION ({total_success}/{total_components})")
    
    def _display_recommendations(self) -> None:
        """Display actionable recommendations."""
        print("\nRECOMMENDATIONS:")
        for component, data in self.results.items():
            if data.get("status") != "success" and "recommendations" in data:
                for rec in data["recommendations"]:
                    print(f"   - {rec}")
    
    def save_results_to_file(self) -> None:
        """Save validation results to JSON file."""
        output_file = project_root / "environment_validation_report.json"
        
        report_data = {
            "timestamp": self.timestamp,
            "validation_results": self.results,
            "overall_status": self._calculate_overall_status()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\nFull report saved to: {output_file}")
    
    def _calculate_overall_status(self) -> str:
        """Calculate overall validation status."""
        statuses = [r.get("status", "unknown") for r in self.results.values()]
        
        if all(s == "success" for s in statuses):
            return "success"
        elif any(s == "error" for s in statuses):
            return "error"
        else:
            return "warning"


async def main():
    """Main execution function."""
    try:
        validator = EnvironmentValidator()
        await validator.validate_complete_environment()
        
    except KeyboardInterrupt:
        print("\n[WARNING] Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())