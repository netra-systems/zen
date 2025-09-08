"""
Regression test to ensure SERVICE_ID and other authentication identifiers remain stable
and do not contain dynamic values like timestamps or random numbers.

This test prevents regression of the SERVICE_ID timestamp issue discovered on 2025-09-07
where deployment script was appending timestamps to SERVICE_ID causing auth failures.
"""
import re
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ServiceIDStabilityTest:
    """Test suite for ensuring stable service identifiers"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.errors = []
        self.warnings = []
        
    def test_deployment_script_service_id(self):
        """Verify SERVICE_ID in deployment script is stable without timestamps"""
        deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
        
        with open(deploy_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for timestamp patterns in service-id assignments
        timestamp_patterns = [
            r'"service-id-[^"]*":\s*f"[^"]*\{int\(time\.time\(\)\)\}"',
            r'"service-id-[^"]*":\s*f"[^"]*\{time\.time\(\)\}"',
            r'"SERVICE_ID":\s*f"[^"]*\{int\(time\.time\(\)\)\}"',
            r'SERVICE_ID.*=.*int\(time\.time\(\)\)',
            r'service_id.*=.*int\(time\.time\(\)\)'
        ]
        
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                self.errors.append(f"Found timestamp in SERVICE_ID: {matches}")
                
        # Check for random value patterns in service-id
        random_patterns = [
            r'"service-id-[^"]*":\s*f"[^"]*\{random\.[^}]*\}"',
            r'"service-id-[^"]*":\s*f"[^"]*\{uuid\.[^}]*\}"',
            r'SERVICE_ID.*=.*random\.',
            r'SERVICE_ID.*=.*uuid\.'
        ]
        
        for pattern in random_patterns:
            matches = re.findall(pattern, content)
            if matches:
                self.errors.append(f"Found random value in SERVICE_ID: {matches}")
        
        # Verify correct stable SERVICE_ID patterns exist
        expected_patterns = {
            '"service-id-staging": "netra-auth-staging"': 'Staging SERVICE_ID should be stable',
            '"service-id-production": "netra-auth-production"': 'Production SERVICE_ID should be stable (if exists)'
        }
        
        for pattern, description in expected_patterns.items():
            # Make pattern regex-safe
            safe_pattern = re.escape(pattern).replace(r'\ ', r'\s*')
            if not re.search(safe_pattern, content):
                # Only warn for production, error for staging
                if 'staging' in pattern:
                    self.errors.append(f"Missing expected pattern: {pattern} - {description}")
                else:
                    # Production pattern is optional
                    pass
                    
    def test_secrets_config_stability(self):
        """Check deployment/secrets_config.py for stable configurations"""
        secrets_config = self.project_root / "deployment" / "secrets_config.py"
        
        if secrets_config.exists():
            with open(secrets_config, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for dynamic value generation
            dynamic_patterns = [
                r'int\(time\.time\(\)\)',
                r'datetime\.now\(\)',
                r'random\.',
                r'uuid\.',
                r'secrets\.token_[^(]*\(\)'  # Check for dynamic token generation in config
            ]
            
            for pattern in dynamic_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Filter out acceptable uses (like in comments or logging)
                    real_issues = []
                    for match in matches:
                        # Get context around match
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if match in line and not line.strip().startswith('#'):
                                real_issues.append(f"Line {i+1}: {line.strip()}")
                    
                    if real_issues:
                        self.warnings.append(f"Found dynamic values in secrets_config.py: {real_issues}")
                        
    def test_auth_service_expected_ids(self):
        """Verify auth service expects stable SERVICE_IDs"""
        auth_routes = self.project_root / "auth_service" / "auth_core" / "routes" / "auth_routes.py"
        
        if auth_routes.exists():
            with open(auth_routes, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check what SERVICE_ID auth service expects
            expected_id_patterns = [
                r'expected_service_id\s*=\s*["\']([^"\']+)["\']',
                r'SERVICE_ID["\'].*default[^)]*["\']([^"\']+)["\']'
            ]
            
            for pattern in expected_id_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    # Check if the expected ID contains timestamp-like patterns
                    if re.search(r'\d{10}|\d{13}', match):  # Unix timestamp patterns
                        self.errors.append(f"Auth service expects SERVICE_ID with timestamp: {match}")
                        
    def test_backend_service_ids(self):
        """Check backend service ID configuration"""
        backend_files = [
            self.project_root / "netra_backend" / "app" / "clients" / "auth_client_core.py",
            self.project_root / "netra_backend" / "app" / "clients" / "auth_client_cache.py"
        ]
        
        for file_path in backend_files:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for hardcoded SERVICE_IDs with timestamps
                if re.search(r'SERVICE_ID.*\d{10}', content):
                    self.warnings.append(f"Found potential timestamp in SERVICE_ID in {file_path.name}")
                    
    def test_environment_configs(self):
        """Check various environment configuration files"""
        config_patterns = [
            "*.env",
            "*.env.*",
            "*config*.json",
            "*config*.yaml",
            "*config*.yml"
        ]
        
        for pattern in config_patterns:
            for config_file in self.project_root.rglob(pattern):
                # Skip node_modules, venv, etc.
                if any(skip in str(config_file) for skip in ['node_modules', 'venv', '.git', '__pycache__']):
                    continue
                    
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for SERVICE_ID with timestamps
                    if 'SERVICE_ID' in content:
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'SERVICE_ID' in line and re.search(r'\d{10}', line):
                                self.warnings.append(f"Potential timestamp in SERVICE_ID in {config_file.name}:{i+1}")
                except Exception as e:
                    # Skip files that can't be read as text
                    pass
                    
    def test_other_authentication_identifiers(self):
        """Check for other authentication identifiers that might have similar issues"""
        auth_identifiers = [
            'CLIENT_ID',
            'API_KEY',
            'SESSION_ID',
            'REQUEST_ID',
            'TRACE_ID',
            'CORRELATION_ID'
        ]
        
        deployment_files = list((self.project_root / "scripts").glob("*.py"))
        deployment_files.extend((self.project_root / "deployment").glob("*.py"))
        
        for file_path in deployment_files:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for identifier in auth_identifiers:
                    # Check if identifier is being set with timestamp
                    pattern = f'{identifier}.*=.*int\\(time\\.time\\(\\)\\)'
                    if re.search(pattern, content):
                        self.warnings.append(f"Found {identifier} with timestamp in {file_path.name}")
                        
    def test_google_secret_manager_secrets(self):
        """Verify all GSM secrets are defined with stable values"""
        deploy_script = self.project_root / "scripts" / "deploy_to_gcp.py"
        
        with open(deploy_script, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the secrets dictionary
        secrets_pattern = r'staging_secrets\s*=\s*\{([^}]+)\}'
        match = re.search(secrets_pattern, content, re.DOTALL)
        
        if match:
            secrets_content = match.group(1)
            
            # Check each secret for dynamic values
            secret_lines = secrets_content.split('\n')
            for line in secret_lines:
                if ':' in line and not line.strip().startswith('#'):
                    # Check for f-strings with dynamic values
                    if 'f"' in line or "f'" in line:
                        if any(dynamic in line for dynamic in ['time.time()', 'random.', 'uuid.', 'secrets.']):
                            secret_name = line.split(':')[0].strip().strip('"\'')
                            self.errors.append(f"Secret '{secret_name}' uses dynamic value generation")
                            
    def run_all_tests(self):
        """Run all stability tests"""
        print("Running SERVICE_ID Stability Regression Tests...")
        print("=" * 60)
        
        test_methods = [
            ("Deployment Script SERVICE_ID", self.test_deployment_script_service_id),
            ("Secrets Config Stability", self.test_secrets_config_stability),
            ("Auth Service Expected IDs", self.test_auth_service_expected_ids),
            ("Backend Service IDs", self.test_backend_service_ids),
            ("Environment Configs", self.test_environment_configs),
            ("Other Auth Identifiers", self.test_other_authentication_identifiers),
            ("Google Secret Manager", self.test_google_secret_manager_secrets)
        ]
        
        for test_name, test_method in test_methods:
            print(f"\nTesting: {test_name}")
            try:
                test_method()
                print(f"  [PASS] {test_name}")
            except Exception as e:
                self.errors.append(f"{test_name} failed: {str(e)}")
                print(f"  [FAIL] {test_name}: {e}")
                
        # Report results
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)
        
        if self.errors:
            print("\n[ERRORS] Critical issues found:")
            for error in self.errors:
                print(f"  - {error}")
                
        if self.warnings:
            print("\n[WARNINGS] Potential issues to review:")
            for warning in self.warnings:
                print(f"  - {warning}")
                
        if not self.errors and not self.warnings:
            print("\n[SUCCESS] All SERVICE_ID stability tests passed!")
            
        # Return exit code
        return 1 if self.errors else 0


if __name__ == "__main__":
    tester = ServiceIDStabilityTest()
    exit_code = tester.run_all_tests()
    
    if exit_code == 0:
        print("\n[FINAL] All regression tests PASSED - SERVICE_IDs are stable")
    else:
        print("\n[FINAL] Regression tests FAILED - Fix SERVICE_ID stability issues")
        
    sys.exit(exit_code)