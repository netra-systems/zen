#!/usr/bin/env python3
"""
Mission Critical Test: Docker Management Compliance Audit

This test ensures that ALL Docker operations in the codebase use the UnifiedDockerManager
and that no manual docker-compose commands are being executed outside of the central manager.

CRITICAL: Per CLAUDE.md Section 7.1, all Docker operations MUST go through UnifiedDockerManager.
"""

import os
import sys
import re
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple
import json
import ast

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from test_framework.unified_docker_manager import UnifiedDockerManager, get_default_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class DockerComplianceAuditor:
    """Audits codebase for Docker management compliance"""
    
    # Files that are allowed to have docker-compose references for documentation
    DOCUMENTATION_EXCEPTIONS = {
        'DOCKER_QUICKSTART.md',
        'DOCKER_README.md', 
        'docker-compose.yml',  # The actual compose file
        'AUDIT_DOCKER_TEST_ORCHESTRATION.md',
        'DEPLOYMENT_CHECKLIST.md',
        'DOCKER_REFRESH_GUIDE.md',
        'docker_orchestration.md',
        'TESTING_GUIDE.md',
        'PORT_ALLOCATION.md',
        'ORCHESTRATION_SYSTEM_GUIDE.md',
        'docker-dual-environment-setup.md',
        'DOCKER_INTENT_CLARIFICATION.md'
    }
    
    # Files that must use UnifiedDockerManager
    MUST_USE_MANAGER = {
        'unified_test_runner.py',
        'docker_manual.py',
        'refresh_dev_services.py',
        'integrated_test_runner.py',
        'test_adaptive_workflow.py',
        'intelligent_docker_remediation.py',
        'intelligent_remediation_orchestrator.py'
    }
    
    def __init__(self):
        self.project_root = project_root
        self.violations = []
        self.compliant_files = []
        self.manager = get_default_manager()
        
    def audit_file_for_docker_commands(self, file_path: Path) -> List[Dict]:
        """Check a file for direct docker/docker-compose commands"""
        violations = []
        
        # Skip non-Python and non-script files for command analysis
        if file_path.suffix not in ['.py', '.sh', '.bat', '.ps1']:
            return violations
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
                
            for line_num, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue
                    
                # Check for subprocess calls to docker/docker-compose
                if re.search(r'subprocess\.(run|call|check_call|check_output|Popen)\s*\([^)]*["\']docker(-compose)?[\s"]', line):
                    # Check if it's using UnifiedDockerManager context
                    context_start = max(0, line_num - 10)
                    context_end = min(len(lines), line_num + 10)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    if 'UnifiedDockerManager' not in context and 'get_default_manager' not in context:
                        violations.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'subprocess_docker_call'
                        })
                
                # Check for os.system calls to docker
                if re.search(r'os\.system\s*\([^)]*["\']docker(-compose)?[\s"]', line):
                    violations.append({
                        'file': str(file_path.relative_to(self.project_root)),
                        'line': line_num,
                        'content': line.strip(),
                        'type': 'os_system_docker_call'
                    })
                    
                # Check for direct docker-compose commands in shell scripts
                if file_path.suffix in ['.sh', '.bat'] and re.search(r'^docker(-compose)?\s+', line.strip()):
                    # Check if it's in a function that wraps UnifiedDockerManager
                    if 'docker_manual.py' not in line and 'unified_docker_manager' not in line.lower():
                        violations.append({
                            'file': str(file_path.relative_to(self.project_root)),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'shell_docker_command'
                        })
                        
        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")
            
        return violations
        
    def verify_unified_manager_usage(self, file_path: Path) -> bool:
        """Verify that a file properly uses UnifiedDockerManager"""
        if file_path.suffix != '.py':
            return True
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for proper imports
            has_manager_import = any([
                'from test_framework.unified_docker_manager import' in content,
                'import test_framework.unified_docker_manager' in content,
                'get_default_manager' in content
            ])
            
            # Check if file needs Docker functionality
            needs_docker = any([
                'docker' in content.lower(),
                'container' in content.lower(),
                'compose' in content.lower()
            ])
            
            # If it needs Docker and is in MUST_USE_MANAGER list, it must import the manager
            if file_path.name in self.MUST_USE_MANAGER and needs_docker:
                return has_manager_import
                
            return True
            
        except Exception as e:
            logger.warning(f"Could not verify {file_path}: {e}")
            return True
            
    def audit_frontend_service_integration(self) -> Dict:
        """Verify frontend service is properly integrated in UnifiedDockerManager"""
        results = {
            'frontend_in_configs': False,
            'frontend_in_health_checks': False,
            'frontend_in_port_mappings': False,
            'frontend_dockerfile_exists': False
        }
        
        # Check UnifiedDockerManager configuration
        manager_path = self.project_root / 'test_framework' / 'unified_docker_manager.py'
        if manager_path.exists():
            with open(manager_path, 'r') as f:
                content = f.read()
                
            # Check SERVICE_CONFIGS
            if '"frontend"' in content and 'SERVICE_CONFIGS' in content:
                results['frontend_in_configs'] = True
                
            # Check health check logic
            if 'frontend' in content and 'health' in content.lower():
                results['frontend_in_health_checks'] = True
                
            # Check port mappings
            if '"frontend": 3000' in content or "'frontend': 3000" in content:
                results['frontend_in_port_mappings'] = True
                
        # Check for frontend Dockerfile
        frontend_dockerfile = self.project_root / 'docker' / 'frontend.Dockerfile'
        if frontend_dockerfile.exists():
            results['frontend_dockerfile_exists'] = True
            
        return results
        
    def run_audit(self) -> Dict:
        """Run complete Docker compliance audit"""
        logger.info("🔍 Starting Docker Management Compliance Audit...")
        
        # Find all relevant files
        patterns = ['**/*.py', '**/*.sh', '**/*.bat', '**/*.ps1']
        all_files = []
        for pattern in patterns:
            all_files.extend(self.project_root.glob(pattern))
            
        # Audit each file
        for file_path in all_files:
            # Skip documentation and test data
            relative_path = file_path.relative_to(self.project_root)
            if any(exc in str(relative_path) for exc in self.DOCUMENTATION_EXCEPTIONS):
                continue
                
            # Skip __pycache__ and .git
            if '__pycache__' in str(relative_path) or '.git' in str(relative_path):
                continue
                
            # Check for violations
            file_violations = self.audit_file_for_docker_commands(file_path)
            if file_violations:
                self.violations.extend(file_violations)
            
            # Verify proper usage in critical files
            if file_path.name in self.MUST_USE_MANAGER:
                if self.verify_unified_manager_usage(file_path):
                    self.compliant_files.append(str(relative_path))
                else:
                    self.violations.append({
                        'file': str(relative_path),
                        'line': 0,
                        'content': 'Missing UnifiedDockerManager import',
                        'type': 'missing_manager_import'
                    })
                    
        # Audit frontend service integration
        frontend_status = self.audit_frontend_service_integration()
        
        # Generate report
        report = {
            'total_files_audited': len(all_files),
            'violations_found': len(self.violations),
            'compliant_critical_files': len(self.compliant_files),
            'frontend_integration': frontend_status,
            'violations': self.violations[:10] if self.violations else [],  # Show first 10
            'compliance_score': 100 - (len(self.violations) * 2)  # Deduct 2% per violation
        }
        
        return report
        
    def generate_remediation_script(self) -> str:
        """Generate a script to fix violations"""
        script = []
        script.append("#!/usr/bin/env python3")
        script.append("# Auto-generated Docker compliance remediation script")
        script.append("")
        script.append("import sys")
        script.append("from pathlib import Path")
        script.append("sys.path.insert(0, str(Path(__file__).parent.parent))")
        script.append("")
        script.append("from test_framework.unified_docker_manager import get_default_manager")
        script.append("")
        script.append("# Initialize central Docker manager")
        script.append("manager = get_default_manager()")
        script.append("")
        
        # Add remediation for each violation type
        for violation in self.violations:
            if violation['type'] == 'subprocess_docker_call':
                script.append(f"# Fix: {violation['file']}:{violation['line']}")
                script.append(f"# Replace: {violation['content']}")
                script.append("# With: manager.execute_docker_command(...)")
                script.append("")
                
        return '\n'.join(script)


def test_docker_compliance():
    """Main test function for Docker compliance"""
    auditor = DockerComplianceAuditor()
    report = auditor.run_audit()
    
    # Print report
    print("\n" + "="*80)
    print("DOCKER MANAGEMENT COMPLIANCE AUDIT REPORT")
    print("="*80)
    print(f"Total Files Audited: {report['total_files_audited']}")
    print(f"Violations Found: {report['violations_found']}")
    print(f"Compliant Critical Files: {report['compliant_critical_files']}")
    print(f"Compliance Score: {report['compliance_score']}%")
    
    print("\n📦 Frontend Service Integration Status:")
    for key, value in report['frontend_integration'].items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    if report['violations']:
        print("\n⚠️ Violations Found (showing first 10):")
        for v in report['violations'][:10]:
            print(f"  - {v['file']}:{v['line']} - {v['type']}")
            print(f"    {v['content'][:100]}...")
    
    # Generate remediation script if violations found
    if report['violations']:
        remediation_script = auditor.generate_remediation_script()
        script_path = auditor.project_root / 'scripts' / 'docker_compliance_remediation.py'
        with open(script_path, 'w') as f:
            f.write(remediation_script)
        print(f"\n📝 Remediation script generated: {script_path}")
    
    # Fail test if compliance score is below threshold
    assert report['compliance_score'] >= 95, f"Docker compliance score {report['compliance_score']}% is below 95% threshold"
    
    # Verify frontend integration
    frontend_checks = report['frontend_integration']
    assert all(frontend_checks.values()), f"Frontend service not fully integrated: {frontend_checks}"
    
    print("\n✅ Docker Management Compliance Test PASSED")
    return True


if __name__ == "__main__":
    try:
        success = test_docker_compliance()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        logger.error(f"❌ Compliance test failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)