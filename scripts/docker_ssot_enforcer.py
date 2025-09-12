#!/usr/bin/env python3
"""
Docker SSOT Enforcer - Validates Docker configurations against SSOT Matrix
CRITICAL: Prevents Docker configuration confusion by enforcing the SSOT matrix

This script validates that:
1. Only SSOT-approved Docker configurations are present
2. No fallback logic exists in Docker management code
3. Required SSOT configurations are available
4. Obsolete Docker files are identified for deletion

Usage:
    python scripts/docker_ssot_enforcer.py validate      # Validate current state
    python scripts/docker_ssot_enforcer.py cleanup       # List files to delete
    python scripts/docker_ssot_enforcer.py enforce       # Hard fail if violations found
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Tuple
import logging
import json
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

class DockerSSOTEnforcer:
    """Enforces Docker SSOT matrix compliance"""
    
    def __init__(self):
        self.project_root = project_root
        
        # SSOT Matrix: The ONE configuration per use case
        self.ssot_matrix = {
            'LOCAL_DEVELOPMENT': {
                'dockerfiles': [
                    'docker/backend.Dockerfile',
                    'docker/auth.Dockerfile', 
                    'docker/frontend.Dockerfile'
                ],
                'compose_files': ['docker-compose.yml'],
                'ports': [5432, 6379, 8000, 8081],
                'environment': 'DEV'
            },
            'AUTOMATED_TESTING': {
                'dockerfiles': [
                    'docker/backend.alpine.Dockerfile',
                    'docker/auth.alpine.Dockerfile',
                    'docker/frontend.alpine.Dockerfile'
                ],
                'compose_files': ['docker-compose.alpine-test.yml'],
                'ports': [5435, 6381, 8002, 8083],
                'environment': 'TEST'
            },
            'STAGING_DEPLOYMENT': {
                'dockerfiles': [
                    'docker/backend.staging.Dockerfile',
                    'docker/auth.staging.Dockerfile',
                    'docker/frontend.staging.Dockerfile'
                ],
                'compose_files': ['docker-compose.staging.yml'],
                'ports': [5432, 6379, 8000, 8081],
                'environment': 'STAGING'
            }
        }
        
        # Files that MUST be deleted (violate SSOT principles)
        self.obsolete_files = {
            'compose_files': [
                'docker-compose.alpine.yml',
                'docker-compose.base.yml', 
                'docker-compose.dev-optimized.yml',
                'docker-compose.podman.yml',
                'docker-compose.podman-mac.yml',
                'docker-compose.podman-no-dns.yml',
                'docker-compose.pytest.yml',
                'docker-compose.resource-optimized.yml',
                'docker-compose.test.yml',
                'docker-compose.unified.yml'
            ],
            'dockerfiles': [
                'docker/analytics.Dockerfile',
                'docker/auth.development.Dockerfile',
                'docker/auth.podman.Dockerfile',
                'docker/auth.test.Dockerfile',
                'docker/backend.development.Dockerfile',
                'docker/backend.optimized.Dockerfile',
                'docker/backend.podman.Dockerfile',
                'docker/backend.podman-optimized.Dockerfile',
                'docker/backend.test.Dockerfile',
                'docker/frontend.development.Dockerfile',
                'docker/frontend.podman.Dockerfile',
                'docker/frontend.podman-dev.Dockerfile',
                'docker/frontend.test.Dockerfile',
                'docker/load-tester.Dockerfile',
                'docker/pytest.collection.Dockerfile',
                'docker/pytest.execution.Dockerfile',
                'docker/pytest.stress.Dockerfile',
                'docker/test-monitor.Dockerfile',
                'docker/test-seeder.Dockerfile'
            ],
            'root_files': [
                'Dockerfile.collection-demo',
                'Dockerfile.comparison-test',
                'Dockerfile.final-demo',
                'Dockerfile.memory-test',
                'Dockerfile.pytest-optimized'
            ]
        }
        
        # Critical patterns that indicate fallback logic
        self.forbidden_patterns = [
            r'try.*docker.*except',
            r'if.*compose.*else.*compose',
            r'compose_files.*=.*\[.*,.*\].*#.*fallback',
            r'^[^#]*Final fallback',  # Not in comments
            r'^[^#]*Fallback to.*compose',  # Not in comments
            r'^[^#]*Using.*fallback',  # Not in comments  
            r'^[^#]*Fall back to',  # Not in comments
            r'logger\.info.*[Ff]allback',  # Actual fallback usage in code
            r'return.*fallback'  # Actual fallback returns
        ]

    def validate_ssot_compliance(self) -> Dict[str, List[str]]:
        """Validate current Docker configuration against SSOT matrix"""
        logger.info(" SEARCH:  Validating Docker SSOT compliance...")
        
        violations = {
            'missing_required': [],
            'obsolete_present': [],
            'fallback_logic': [],
            'unauthorized_configs': []
        }
        
        # Check required SSOT files exist
        for use_case, config in self.ssot_matrix.items():
            for dockerfile in config['dockerfiles']:
                if not (self.project_root / dockerfile).exists():
                    violations['missing_required'].append(f"{use_case}: {dockerfile}")
            
            for compose_file in config['compose_files']:
                if not (self.project_root / compose_file).exists():
                    violations['missing_required'].append(f"{use_case}: {compose_file}")
        
        # Check for obsolete files that should be deleted
        all_obsolete = (
            self.obsolete_files['compose_files'] + 
            self.obsolete_files['dockerfiles'] + 
            self.obsolete_files['root_files']
        )
        
        for obsolete_file in all_obsolete:
            if (self.project_root / obsolete_file).exists():
                violations['obsolete_present'].append(obsolete_file)
        
        # Scan for forbidden fallback logic
        violations['fallback_logic'] = self._scan_for_fallback_logic()
        
        # Check for unauthorized Docker configurations
        violations['unauthorized_configs'] = self._find_unauthorized_configs()
        
        return violations

    def _scan_for_fallback_logic(self) -> List[str]:
        """Scan code for forbidden fallback patterns"""
        fallback_violations = []
        
        # Files to scan for fallback logic
        scan_files = [
            'test_framework/unified_docker_manager.py',
            'scripts/docker_manual.py'
        ]
        
        for file_path in scan_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                continue
                
            try:
                content = full_path.read_text(encoding='utf-8')
                for pattern in self.forbidden_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        fallback_violations.append(f"{file_path}:{line_num} - {match.group()}")
            except Exception as e:
                logger.warning(f"Could not scan {file_path}: {e}")
        
        return fallback_violations

    def _find_unauthorized_configs(self) -> List[str]:
        """Find Docker configs not in SSOT matrix"""
        unauthorized = []
        
        # Get all existing Docker files
        existing_dockerfiles = list(self.project_root.glob('docker/*.Dockerfile'))
        existing_compose = list(self.project_root.glob('docker-compose*.yml'))
        existing_compose.extend(self.project_root.glob('docker-compose*.yaml'))
        
        # Collect all authorized files from SSOT matrix
        authorized_dockerfiles = set()
        authorized_compose = set()
        
        for config in self.ssot_matrix.values():
            for dockerfile in config['dockerfiles']:
                authorized_dockerfiles.add(self.project_root / dockerfile)
            for compose_file in config['compose_files']:
                authorized_compose.add(self.project_root / compose_file)
        
        # Find unauthorized files (not in SSOT matrix, not in obsolete list)
        for dockerfile in existing_dockerfiles:
            rel_path = dockerfile.relative_to(self.project_root)
            if dockerfile not in authorized_dockerfiles and str(rel_path) not in self.obsolete_files['dockerfiles']:
                unauthorized.append(str(rel_path))
        
        for compose_file in existing_compose:
            rel_path = compose_file.relative_to(self.project_root)  
            if compose_file not in authorized_compose and str(rel_path) not in self.obsolete_files['compose_files']:
                unauthorized.append(str(rel_path))
        
        return unauthorized

    def list_files_to_delete(self) -> List[str]:
        """List all obsolete files that should be deleted"""
        files_to_delete = []
        
        all_obsolete = (
            self.obsolete_files['compose_files'] +
            self.obsolete_files['dockerfiles'] +
            self.obsolete_files['root_files']
        )
        
        for file_path in all_obsolete:
            full_path = self.project_root / file_path
            if full_path.exists():
                files_to_delete.append(file_path)
        
        return files_to_delete

    def enforce_ssot_compliance(self) -> bool:
        """Hard fail if any SSOT violations exist"""
        violations = self.validate_ssot_compliance()
        
        has_violations = any(len(v) > 0 for v in violations.values())
        
        if has_violations:
            logger.error(" ALERT:  DOCKER SSOT VIOLATIONS DETECTED")
            logger.error("=" * 50)
            
            if violations['missing_required']:
                logger.error(" FAIL:  MISSING REQUIRED SSOT FILES:")
                for missing in violations['missing_required']:
                    logger.error(f"   {missing}")
                logger.error("   Solution: Restore files from SSOT matrix")
                logger.error("   See: docker/DOCKER_SSOT_MATRIX.md")
            
            if violations['obsolete_present']:
                logger.error(" FAIL:  OBSOLETE FILES PRESENT (MUST DELETE):")
                for obsolete in violations['obsolete_present']:
                    logger.error(f"   {obsolete}")
                logger.error("   Solution: python scripts/docker_ssot_enforcer.py cleanup")
            
            if violations['fallback_logic']:
                logger.error(" FAIL:  FORBIDDEN FALLBACK LOGIC DETECTED:")
                for fallback in violations['fallback_logic']:
                    logger.error(f"   {fallback}")
                logger.error("   Solution: Replace with hard fail logic")
            
            if violations['unauthorized_configs']:
                logger.error(" FAIL:  UNAUTHORIZED DOCKER CONFIGS:")
                for unauthorized in violations['unauthorized_configs']:
                    logger.error(f"   {unauthorized}")
                logger.error("   Solution: Add to SSOT matrix or obsolete list")
            
            logger.error("=" * 50)
            logger.error("DOCKER SSOT ENFORCEMENT FAILED")
            return False
        
        logger.info(" PASS:  Docker SSOT compliance validated successfully")
        return True

    def generate_report(self) -> Dict:
        """Generate detailed SSOT compliance report"""
        violations = self.validate_ssot_compliance()
        files_to_delete = self.list_files_to_delete()
        
        return {
            'timestamp': subprocess.check_output(['date'], text=True).strip(),
            'ssot_matrix': self.ssot_matrix,
            'violations': violations,
            'files_to_delete': files_to_delete,
            'compliance_status': 'PASS' if not any(len(v) > 0 for v in violations.values()) else 'FAIL'
        }


def main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        logger.error("Usage: python scripts/docker_ssot_enforcer.py [validate|cleanup|enforce]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    enforcer = DockerSSOTEnforcer()
    
    if command == 'validate':
        logger.info(" SEARCH:  Validating Docker SSOT compliance...")
        violations = enforcer.validate_ssot_compliance()
        
        if any(len(v) > 0 for v in violations.values()):
            logger.warning(" WARNING: [U+FE0F] SSOT violations found:")
            for category, items in violations.items():
                if items:
                    logger.warning(f"  {category}: {len(items)} violations")
        else:
            logger.info(" PASS:  All Docker configurations are SSOT compliant")
    
    elif command == 'cleanup':
        logger.info("[U+1F9F9] Listing obsolete Docker files to delete...")
        files_to_delete = enforcer.list_files_to_delete()
        
        if files_to_delete:
            logger.warning("The following files violate SSOT and should be deleted:")
            for file_path in files_to_delete:
                logger.warning(f"  rm {file_path}")
            logger.warning(f"\nTotal: {len(files_to_delete)} obsolete files")
            logger.warning("Run: rm " + " ".join(files_to_delete))
        else:
            logger.info(" PASS:  No obsolete Docker files found")
    
    elif command == 'enforce':
        logger.info(" ALERT:  Enforcing Docker SSOT compliance...")
        if not enforcer.enforce_ssot_compliance():
            logger.error("SSOT enforcement failed - see violations above")
            sys.exit(1)
        logger.info(" PASS:  Docker SSOT enforcement passed")
    
    elif command == 'report':
        logger.info(" CHART:  Generating Docker SSOT compliance report...")
        report = enforcer.generate_report()
        print(json.dumps(report, indent=2))
    
    else:
        logger.error(f"Unknown command: {command}")
        logger.error("Available commands: validate, cleanup, enforce, report")
        sys.exit(1)


if __name__ == '__main__':
    main()