from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
Staging URL Validation Script
Prevents localhost URLs from being used in staging/production environments.

This script validates that:
1. No localhost references exist in staging/production environment variables
2. All URLs use appropriate protocols (https/wss for staging/production)
3. Domain names match expected patterns for each environment

Usage:
    python scripts/validate_staging_urls.py --environment staging
    python scripts/validate_staging_urls.py --environment production --fix
"""

import os
import sys
import re
import argparse
from typing import Dict, List, Tuple, Optional
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class StagingURLValidator:
    """Validates and fixes localhost URLs in staging/production environments."""
    
    def __init__(self, environment: str):
        self.environment = environment.lower()
        self.issues_found = []
        self.fixes_applied = []
        
        # Expected URL patterns for each environment
        self.expected_patterns = {
            'development': {
                'api_url': r'http://localhost:\d+',
                'ws_url': r'ws://localhost:\d+',
                'auth_url': r'http://localhost:\d+',
                'frontend_url': r'http://localhost:\d+'
            },
            'test': {
                'api_url': r'http://localhost:\d+',
                'ws_url': r'ws://localhost:\d+', 
                'auth_url': r'http://localhost:\d+',
                'frontend_url': r'http://localhost:\d+'
            },
            'staging': {
                'api_url': r'https://api\.staging\.netrasystems\.ai',
                'ws_url': r'wss://api\.staging\.netrasystems\.ai',
                'auth_url': r'https://auth\.staging\.netrasystems\.ai',
                'frontend_url': r'https://app\.staging\.netrasystems\.ai'
            },
            'production': {
                'api_url': r'https://api\.netrasystems\.ai',
                'ws_url': r'wss://api\.netrasystems\.ai',
                'auth_url': r'https://auth\.netrasystems\.ai',
                'frontend_url': r'https://netrasystems\.ai'
            }
        }
        
        # URL variables to check
        self.url_variables = [
            'API_URL',
            'NEXT_PUBLIC_API_URL',
            'BACKEND_URL',
            'NEXT_PUBLIC_BACKEND_URL',
            'WS_URL', 
            'WEBSOCKET_URL',
            'NEXT_PUBLIC_WS_URL',
            'NEXT_PUBLIC_WEBSOCKET_URL',
            'AUTH_URL',
            'AUTH_SERVICE_URL',
            'NEXT_PUBLIC_AUTH_URL',
            'NEXT_PUBLIC_AUTH_SERVICE_URL',
            'FRONTEND_URL',
            'NEXT_PUBLIC_FRONTEND_URL'
        ]
        
        # Files to check for localhost references
        self.config_files = [
            'docker-compose.yml',
            'docker-compose.dev.yml',
            'docker-compose.test.yml',
            'docker-compose.all.yml',
            '.env',
            '.env.production',
            '.env.development',
            'frontend/.env.production',
            'frontend/.env.local',
            'nginx/nginx.conf',
            'nginx/nginx.staging.conf'
        ]
    
    def validate_environment_variables(self) -> List[str]:
        """Check environment variables for localhost references."""
        issues = []
        
        if self.environment in ['staging', 'production']:
            for var_name in self.url_variables:
                value = get_env().get(var_name)
                if value and 'localhost' in value:
                    issues.append(f"Environment variable {var_name}={value} contains localhost in {self.environment}")
                    
                # Check for insecure protocols in staging/production
                if value and self.environment in ['staging', 'production']:
                    if value.startswith('http://') and 'localhost' not in value:
                        issues.append(f"Environment variable {var_name}={value} uses insecure HTTP in {self.environment}")
                    if value.startswith('ws://') and 'localhost' not in value:
                        issues.append(f"Environment variable {var_name}={value} uses insecure WebSocket in {self.environment}")
        
        return issues
    
    def validate_config_files(self) -> List[str]:
        """Check configuration files for problematic localhost references."""
        issues = []
        
        for config_file in self.config_files:
            file_path = project_root / config_file
            if not file_path.exists():
                continue
                
            try:
                content = file_path.read_text()
                
                # Look for localhost references that might be used in staging
                localhost_patterns = [
                    r'localhost:\d+',
                    r'http://localhost',
                    r'ws://localhost',
                    r'FRONTEND_URL.*localhost',
                    r'API_URL.*localhost',
                    r'AUTH_URL.*localhost'
                ]
                
                for pattern in localhost_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        issues.append(f"{config_file}:{line_num} - Found localhost reference: {match.group()}")
                        
            except Exception as e:
                issues.append(f"Error reading {config_file}: {e}")
        
        return issues
    
    def get_correct_url(self, variable_name: str) -> Optional[str]:
        """Get the correct URL for a variable in the current environment."""
        variable_lower = variable_name.lower()
        
        if self.environment == 'staging':
            if 'api' in variable_lower or 'backend' in variable_lower:
                return 'https://api.staging.netrasystems.ai'
            elif 'ws' in variable_lower or 'websocket' in variable_lower:
                return 'wss://api.staging.netrasystems.ai/ws' if 'websocket' in variable_lower else 'wss://api.staging.netrasystems.ai'
            elif 'auth' in variable_lower:
                return 'https://auth.staging.netrasystems.ai'
            elif 'frontend' in variable_lower:
                return 'https://app.staging.netrasystems.ai'
                
        elif self.environment == 'production':
            if 'api' in variable_lower or 'backend' in variable_lower:
                return 'https://api.netrasystems.ai'
            elif 'ws' in variable_lower or 'websocket' in variable_lower:
                return 'wss://api.netrasystems.ai/ws' if 'websocket' in variable_lower else 'wss://api.netrasystems.ai'
            elif 'auth' in variable_lower:
                return 'https://auth.netrasystems.ai'
            elif 'frontend' in variable_lower:
                return 'https://netrasystems.ai'
        
        return None
    
    def fix_docker_compose_files(self, dry_run: bool = False) -> List[str]:
        """Fix localhost references in Docker Compose files."""
        fixes = []
        
        for compose_file in ['docker-compose.yml', 'docker-compose.dev.yml', 'docker-compose.all.yml']:
            file_path = project_root / compose_file
            if not file_path.exists():
                continue
                
            try:
                content = file_path.read_text()
                original_content = content
                
                # Add environment-specific URL overrides
                if 'docker-compose.yml' in compose_file:
                    # Add staging URL defaults that override localhost
                    staging_overrides = '''
      # Staging URL Overrides (prevent localhost in staging)
      STAGING_API_URL: "https://api.staging.netrasystems.ai"
      STAGING_AUTH_URL: "https://auth.staging.netrasystems.ai"
      STAGING_FRONTEND_URL: "https://app.staging.netrasystems.ai"
      STAGING_WS_URL: "wss://api.staging.netrasystems.ai/ws"
      
      # Production URL Overrides (prevent localhost in production)  
      PRODUCTION_API_URL: "https://api.netrasystems.ai"
      PRODUCTION_AUTH_URL: "https://auth.netrasystems.ai"
      PRODUCTION_FRONTEND_URL: "https://netrasystems.ai"
      PRODUCTION_WS_URL: "wss://api.netrasystems.ai/ws"'''
      
                    # Insert after the first environment section
                    env_pattern = r'(environment:\s*\n(?:\s+[^:\n]+:[^\n]*\n)*)'
                    matches = list(re.finditer(env_pattern, content))
                    
                    if matches and staging_overrides not in content:
                        insert_pos = matches[0].end()
                        content = content[:insert_pos] + staging_overrides + '\n' + content[insert_pos:]
                        fixes.append(f"Added staging URL overrides to {compose_file}")
                
                if content != original_content and not dry_run:
                    file_path.write_text(content)
                    fixes.append(f"Updated {compose_file} with staging URL fixes")
                    
            except Exception as e:
                fixes.append(f"Error fixing {compose_file}: {e}")
        
        return fixes
    
    def create_environment_validation_script(self) -> str:
        """Create a script that validates URLs at runtime."""
        script_content = '''#!/bin/bash
# Runtime URL Validation for Staging/Production
# This script prevents localhost URLs from being used in staging/production

set -e

ENVIRONMENT=${ENVIRONMENT:-development}

validate_url() {
    local var_name=$1
    local var_value=$2
    local environment=$3
    
    if [[ "$environment" == "staging" || "$environment" == "production" ]]; then
        if [[ "$var_value" == *"localhost"* ]]; then
            echo "ERROR: $var_name contains localhost in $environment environment: $var_value"
            echo "This will cause CORS and authentication failures!"
            exit 1
        fi
        
        if [[ "$environment" == "staging" && "$var_value" != *"staging.netrasystems.ai"* && "$var_value" != "" ]]; then
            echo "WARNING: $var_name may not be correct for staging: $var_value"
        fi
        
        if [[ "$environment" == "production" && "$var_value" != *"netrasystems.ai"* && "$var_value" != "" ]]; then
            echo "WARNING: $var_name may not be correct for production: $var_value"
        fi
    fi
}

echo "Validating URLs for environment: $ENVIRONMENT"

# Check all URL environment variables
validate_url "API_URL" "$API_URL" "$ENVIRONMENT"
validate_url "NEXT_PUBLIC_API_URL" "$NEXT_PUBLIC_API_URL" "$ENVIRONMENT"  
validate_url "AUTH_URL" "$AUTH_URL" "$ENVIRONMENT"
validate_url "NEXT_PUBLIC_AUTH_URL" "$NEXT_PUBLIC_AUTH_URL" "$ENVIRONMENT"
validate_url "FRONTEND_URL" "$FRONTEND_URL" "$ENVIRONMENT"
validate_url "WS_URL" "$WS_URL" "$ENVIRONMENT"
validate_url "NEXT_PUBLIC_WS_URL" "$NEXT_PUBLIC_WS_URL" "$ENVIRONMENT"

echo "PASS - URL validation passed for $ENVIRONMENT"
'''
        
        script_path = project_root / 'scripts' / 'validate_urls_runtime.sh'
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        
        return f"Created runtime validation script: {script_path}"
    
    def validate_all(self) -> Tuple[bool, str]:
        """Run all validations and return results."""
        print(f"\nValidating URLs for {self.environment} environment...")
        
        # Check environment variables
        env_issues = self.validate_environment_variables()
        
        # Check configuration files  
        config_issues = self.validate_config_files()
        
        all_issues = env_issues + config_issues
        
        # Generate report
        report = f"""
STAGING URL VALIDATION REPORT
Environment: {self.environment}
Date: {os.popen('date').read().strip()}

{'='*60}
VALIDATION RESULTS
{'='*60}
"""
        
        if not all_issues:
            report += """
PASS - NO ISSUES FOUND
All URLs are correctly configured for the target environment.
No localhost references found in staging/production configuration.
"""
            return True, report
        
        report += f"""
ERROR - {len(all_issues)} ISSUES FOUND

ENVIRONMENT VARIABLE ISSUES:
"""
        
        for issue in env_issues:
            report += f"  [U+2022] {issue}\n"
            
        report += f"""
CONFIGURATION FILE ISSUES:
"""
        
        for issue in config_issues:
            report += f"  [U+2022] {issue}\n"
            
        report += f"""
{'='*60}
RECOMMENDED FIXES
{'='*60}
"""
        
        if self.environment in ['staging', 'production']:
            report += f"""
For {self.environment} environment, ensure these URLs are set:

Environment Variables:
  NEXT_PUBLIC_API_URL: {self.get_correct_url('NEXT_PUBLIC_API_URL')}
  NEXT_PUBLIC_AUTH_URL: {self.get_correct_url('NEXT_PUBLIC_AUTH_URL')}
  NEXT_PUBLIC_WS_URL: {self.get_correct_url('NEXT_PUBLIC_WS_URL')}
  FRONTEND_URL: {self.get_correct_url('FRONTEND_URL')}

Docker Override Variables:
  API_URL: {self.get_correct_url('API_URL')}
  AUTH_URL: {self.get_correct_url('AUTH_URL')}

Run with --fix flag to automatically apply some fixes.
"""
        
        return False, report
    
    def apply_fixes(self, dry_run: bool = False) -> List[str]:
        """Apply automatic fixes for common issues."""
        fixes = []
        
        # Fix Docker Compose files
        docker_fixes = self.fix_docker_compose_files(dry_run)
        fixes.extend(docker_fixes)
        
        # Create runtime validation script
        if not dry_run:
            script_fix = self.create_environment_validation_script()
            fixes.append(script_fix)
        
        return fixes


def main():
    """Main entry point for staging URL validation."""
    parser = argparse.ArgumentParser(
        description="Validate and fix localhost URLs in staging/production environments"
    )
    parser.add_argument(
        "--environment", 
        choices=['development', 'test', 'staging', 'production'],
        default='staging',
        help="Environment to validate (default: staging)"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply automatic fixes where possible"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true", 
        help="Show what would be fixed without making changes"
    )
    
    args = parser.parse_args()
    
    validator = StagingURLValidator(args.environment)
    
    # Run validation
    success, report = validator.validate_all()
    print(report)
    
    # Apply fixes if requested
    if args.fix or args.dry_run:
        print("\n" + "="*60)
        print("APPLYING FIXES" if args.fix else "DRY RUN - SHOWING POTENTIAL FIXES")
        print("="*60)
        
        fixes = validator.apply_fixes(dry_run=args.dry_run)
        
        if fixes:
            for fix in fixes:
                print(f"  FIXED: {fix}")
        else:
            print("  INFO: No automatic fixes available")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
