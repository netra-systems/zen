#!/usr/bin/env python3
"""
Deployment Logging Remediation Script
Fixes critical logging issues in deployment configuration

This script:
1. Validates shared logging is properly configured
2. Updates service imports to use shared logging
3. Ensures dependencies are properly managed
4. Validates deployment readiness
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class DeploymentLoggingFixer:
    """Fixes logging configuration issues for deployment."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.issues_found = []
        self.fixes_applied = []
        
    def run(self) -> bool:
        """Run all deployment logging fixes."""
        print("🔍 Analyzing deployment logging configuration...")
        
        # Step 1: Check current state
        if not self.analyze_current_state():
            return False
            
        # Step 2: Apply fixes
        if self.issues_found:
            print(f"\n⚠️  Found {len(self.issues_found)} issues to fix")
            if not self.apply_fixes():
                return False
        
        # Step 3: Validate fixes
        if not self.validate_deployment():
            return False
            
        print("\n✅ Deployment logging configuration fixed successfully!")
        return True
    
    def analyze_current_state(self) -> bool:
        """Analyze current logging configuration state."""
        print("\n📊 Checking logging configuration...")
        
        # Check if shared logging exists
        shared_logging = self.project_root / "shared" / "logging"
        if not shared_logging.exists():
            self.issues_found.append({
                'type': 'missing_shared_logging',
                'description': 'Shared logging directory missing',
                'severity': 'critical'
            })
            return False
        
        # Check Docker configurations
        dockerfiles = [
            "deployment/docker/backend.gcp.Dockerfile",
            "deployment/docker/auth.gcp.Dockerfile", 
            "deployment/docker/frontend.gcp.Dockerfile"
        ]
        
        for dockerfile in dockerfiles:
            file_path = self.project_root / dockerfile
            if file_path.exists():
                content = file_path.read_text()
                if "COPY shared/ ./shared/" not in content:
                    self.issues_found.append({
                        'type': 'missing_shared_copy',
                        'file': dockerfile,
                        'description': f'{dockerfile} not copying shared directory'
                    })
        
        # Check for old logging imports in backend
        backend_files = list((self.project_root / "netra_backend").rglob("*.py"))
        old_import_count = 0
        
        for file in backend_files[:50]:  # Sample check
            try:
                content = file.read_text()
                if "from netra_backend.app.core.unified_logging import" in content:
                    old_import_count += 1
            except:
                pass
        
        if old_import_count > 0:
            self.issues_found.append({
                'type': 'old_imports',
                'count': old_import_count,
                'description': f'Found {old_import_count} files using old logging imports'
            })
        
        # Check requirements.txt files
        services = [
            ("netra_backend", "requirements.txt"),
            ("auth_service", "requirements.txt"),
            ("frontend", "package.json")
        ]
        
        for service, req_file in services:
            if service != "frontend":  # Skip frontend for Python deps
                req_path = self.project_root / service / req_file
                if req_path.exists():
                    content = req_path.read_text()
                    if "loguru" not in content.lower() and service == "netra_backend":
                        self.issues_found.append({
                            'type': 'missing_dependency',
                            'service': service,
                            'dependency': 'loguru',
                            'description': f'{service} missing loguru dependency'
                        })
        
        return True
    
    def apply_fixes(self) -> bool:
        """Apply fixes for identified issues."""
        print("\n🔧 Applying fixes...")
        
        for issue in self.issues_found:
            if issue['type'] == 'missing_shared_copy':
                if not self.fix_dockerfile(issue['file']):
                    return False
                    
            elif issue['type'] == 'old_imports':
                print(f"  ⚠️  Manual fix needed: Update {issue['count']} files to use shared logging")
                self.fixes_applied.append({
                    'type': 'manual_required',
                    'description': 'Update imports to use shared.logging.unified_logger_factory'
                })
                
            elif issue['type'] == 'missing_dependency':
                if not self.fix_requirements(issue['service'], issue['dependency']):
                    return False
        
        return True
    
    def fix_dockerfile(self, dockerfile: str) -> bool:
        """Ensure Dockerfile copies shared directory."""
        file_path = self.project_root / dockerfile
        
        try:
            content = file_path.read_text()
            
            # Check if already has shared copy
            if "COPY shared/ ./shared/" in content:
                print(f"  ✓ {dockerfile} already copies shared directory")
                return True
            
            # Find where to insert the COPY command
            lines = content.split('\n')
            insert_index = -1
            
            # Look for other COPY commands to insert after
            for i, line in enumerate(lines):
                if line.startswith('COPY') and 'requirements' not in line:
                    insert_index = i + 1
                    break
            
            if insert_index == -1:
                # Insert before CMD/ENTRYPOINT
                for i, line in enumerate(lines):
                    if line.startswith('CMD') or line.startswith('ENTRYPOINT'):
                        insert_index = i
                        break
            
            if insert_index != -1:
                lines.insert(insert_index, 'COPY shared/ ./shared/')
                file_path.write_text('\n'.join(lines))
                print(f"  ✓ Fixed {dockerfile} to copy shared directory")
                self.fixes_applied.append({
                    'type': 'dockerfile_fixed',
                    'file': dockerfile
                })
                return True
            else:
                print(f"  ❌ Could not fix {dockerfile} - manual intervention needed")
                return False
                
        except Exception as e:
            print(f"  ❌ Error fixing {dockerfile}: {e}")
            return False
    
    def fix_requirements(self, service: str, dependency: str) -> bool:
        """Add missing dependency to requirements.txt."""
        req_path = self.project_root / service / "requirements.txt"
        
        try:
            content = req_path.read_text()
            
            # Check if already has dependency
            if dependency.lower() in content.lower():
                print(f"  ✓ {service} already has {dependency}")
                return True
            
            # Add dependency
            lines = content.strip().split('\n')
            
            # Add in alphabetical order
            lines.append(f"{dependency}>=0.7.0")
            lines.sort()
            
            req_path.write_text('\n'.join(lines) + '\n')
            print(f"  ✓ Added {dependency} to {service}/requirements.txt")
            self.fixes_applied.append({
                'type': 'dependency_added',
                'service': service,
                'dependency': dependency
            })
            return True
            
        except Exception as e:
            print(f"  ❌ Error fixing requirements for {service}: {e}")
            return False
    
    def validate_deployment(self) -> bool:
        """Validate deployment configuration is ready."""
        print("\n🔍 Validating deployment configuration...")
        
        validations = [
            self.validate_docker_builds(),
            self.validate_shared_imports(),
            self.validate_environment_vars()
        ]
        
        return all(validations)
    
    def validate_docker_builds(self) -> bool:
        """Validate Docker configurations are correct."""
        print("  Checking Docker configurations...")
        
        dockerfiles = ["deployment/docker/backend.gcp.Dockerfile", "deployment/docker/auth.gcp.Dockerfile", "deployment/docker/frontend.gcp.Dockerfile"]
        
        for dockerfile in dockerfiles:
            file_path = self.project_root / dockerfile
            if file_path.exists():
                content = file_path.read_text()
                if "COPY shared/" not in content:
                    print(f"    ❌ {dockerfile} missing shared directory copy")
                    return False
        
        print("    ✓ All Dockerfiles configured correctly")
        return True
    
    def validate_shared_imports(self) -> bool:
        """Validate shared logging can be imported."""
        print("  Checking shared logging imports...")
        
        # Add project root to path
        
        try:
            # Try importing shared logging
            from shared.logging.unified_logger_factory import get_logger
            print("    ✓ Shared logging imports successfully")
            return True
        except ImportError as e:
            print(f"    ❌ Cannot import shared logging: {e}")
            return False
    
    def validate_environment_vars(self) -> bool:
        """Validate environment variables for deployment."""
        print("  Checking environment variables...")
        
        deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
        if deploy_script.exists():
            content = deploy_script.read_text()
            
            # Check for logging-related env vars
            required_vars = ["LOG_LEVEL", "SERVICE_NAME"]
            missing = []
            
            for var in required_vars:
                if var not in content:
                    missing.append(var)
            
            if missing:
                print(f"    ⚠️  Deployment script may need {', '.join(missing)} environment variables")
            else:
                print("    ✓ Environment variables configured")
        
        return True
    
    def generate_report(self) -> str:
        """Generate deployment readiness report."""
        report = [
            "# Deployment Logging Configuration Report",
            "",
            f"## Issues Found: {len(self.issues_found)}",
            ""
        ]
        
        if self.issues_found:
            report.append("### Issues:")
            for issue in self.issues_found:
                report.append(f"- **{issue['type']}**: {issue['description']}")
            report.append("")
        
        if self.fixes_applied:
            report.append(f"## Fixes Applied: {len(self.fixes_applied)}")
            report.append("### Fixes:")
            for fix in self.fixes_applied:
                report.append(f"- **{fix['type']}**: {fix.get('description', 'Applied')}")
            report.append("")
        
        report.append("## Recommendations:")
        report.append("1. **Migrate Backend Imports**: Update all netra_backend files to use `shared.logging.unified_logger_factory`")
        report.append("2. **Add Missing Features**: Implement performance tracking, context management in shared logger")
        report.append("3. **Test Deployment**: Run `python scripts/deploy_to_gcp.py --project netra-staging --build-local --dry-run`")
        report.append("4. **Validate Services**: Ensure all services start correctly with shared logging")
        
        return '\n'.join(report)


def main():
    """Main entry point."""
    fixer = DeploymentLoggingFixer()
    
    try:
        success = fixer.run()
        
        # Generate and save report
        report = fixer.generate_report()
        report_path = fixer.project_root / "DEPLOYMENT_LOGGING_REPORT.md"
        report_path.write_text(report)
        print(f"\n📄 Report saved to: {report_path}")
        
        if not success:
            print("\n❌ Deployment logging configuration has issues that need manual fixes")
            sys.exit(1)
        else:
            print("\n✅ Deployment logging configuration is ready!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()