from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
"""
Test suite to prevent frontend staging URL regression.
Validates that frontend builds contain correct environment-specific URLs.
"""
"""
to http://localhost:8081 instead of https://auth.staging.netrasystems.ai"""
to http://localhost:8081 instead of https://auth.staging.netrasystems.ai"""

import pytest
import subprocess
import re
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from shared.isolated_environment import get_env


env = get_env()"""
env = get_env()"""
    """Comprehensive tests to prevent frontend URL configuration regressions."""

    @pytest.fixture"""
    @pytest.fixture"""
        """Get project root directory."""
        return Path(__file__).parent.parent.parent

        @pytest.fixture"""
        @pytest.fixture"""
        """Get paths to all frontend Dockerfiles."""
        return { )
        'staging': project_root / 'deployment' / 'docker' / 'frontend.gcp.Dockerfile',
        'production': project_root / 'deployment' / 'docker' / 'frontend.prod.Dockerfile',
    

        @pytest.mark.e2e
        def test_staging_dockerfile_has_next_public_environment_variables( )
self,
dockerfile_paths: Dict[str, Path]"""
dockerfile_paths: Dict[str, Path]"""
"""
"""
Test that staging Dockerfile sets NEXT_PUBLIC_* environment variables before build.
"""
"""
Without these, frontend defaults to localhost URLs.""""""
assert staging_dockerfile.exists(), "formatted_string"

content = staging_dockerfile.read_text()

    # Check for required environment variables
required_env_vars = [ )
('NEXT_PUBLIC_ENVIRONMENT', 'staging'),
('NEXT_PUBLIC_API_URL', 'https://api.staging.netrasystems.ai'),
('NEXT_PUBLIC_WS_URL', 'wss://api.staging.netrasystems.ai'),
('NEXT_PUBLIC_AUTH_URL', 'https://auth.staging.netrasystems.ai'),
('NEXT_PUBLIC_FRONTEND_URL', 'https://staging.netrasystems.ai'),
    

for var_name, expected_value in required_env_vars:
        # Check that ENV variable is set BEFORE npm run build
pattern = r'formatted_string'
assert re.search(pattern, "content), \"
"formatted_string"

        # Verify it comes before the build command
env_pos = content.find('formatted_string')
build_pos = content.find('RUN npm run build')
assert env_pos > 0 and build_pos > 0, \
"formatted_string"
assert env_pos < build_pos, \
"formatted_string"

@pytest.mark.e2e
def test_production_dockerfile_has_next_public_environment_variables( )
self,
dockerfile_paths: Dict[str, Path]
):
"""Test that production Dockerfile sets correct NEXT_PUBLIC_* variables.""""""
"""Test that production Dockerfile sets correct NEXT_PUBLIC_* variables.""""""
assert prod_dockerfile.exists(), "formatted_string"

content = prod_dockerfile.read_text()

required_env_vars = [ )
('NEXT_PUBLIC_ENVIRONMENT', 'production'),
('NEXT_PUBLIC_API_URL', 'https://api.netrasystems.ai'),
('NEXT_PUBLIC_WS_URL', 'wss://api.netrasystems.ai'),
('NEXT_PUBLIC_AUTH_URL', 'https://auth.netrasystems.ai'),
('NEXT_PUBLIC_FRONTEND_URL', 'https://app.netrasystems.ai'),
    

for var_name, expected_value in required_env_vars:
pattern = r'formatted_string'
assert re.search(pattern, "content), \"
"formatted_string"

@pytest.mark.e2e
def test_no_localhost_urls_in_staging_dockerfile( )
self,
dockerfile_paths: Dict[str, Path]
):
"""
"""
Test that staging Dockerfile contains NO localhost URLs."""
Test that staging Dockerfile contains NO localhost URLs."""
REGRESSION PREVENTION: Localhost URLs in staging cause complete auth failure."""
REGRESSION PREVENTION: Localhost URLs in staging cause complete auth failure."""
staging_dockerfile = dockerfile_paths['staging']
content = staging_dockerfile.read_text()

    # Check for localhost patterns
localhost_patterns = [ )
r'localhost:\d+',
r'127\.0\.0\.1:\d+',
r'http://localhost',
r'ws://localhost',
    

for pattern in localhost_patterns:
matches = re.findall(pattern, content, re.IGNORECASE)"""
matches = re.findall(pattern, content, re.IGNORECASE)"""
"formatted_string"

@pytest.mark.e2e
def test_unified_api_config_environment_detection(self, project_root: Path):
    pass
"""Test that unified-api-config.ts properly detects environment.""""""
"""Test that unified-api-config.ts properly detects environment.""""""
assert config_file.exists(), "formatted_string"

content = config_file.read_text()

    # Check for environment detection logic
assert 'detectEnvironment' in content, \
"unified-api-config must have detectEnvironment function"

    # Check for NEXT_PUBLIC_ENVIRONMENT check
assert 'NEXT_PUBLIC_ENVIRONMENT' in content, \
"detectEnvironment must check NEXT_PUBLIC_ENVIRONMENT"

    # Check for staging detection
assert 'staging.netrasystems.ai' in content, \
"detectEnvironment must detect staging by domain"

    # Check staging configuration has correct URLs
assert 'https://auth.staging.netrasystems.ai' in content, \
"Staging config must use auth.staging.netrasystems.ai"
assert 'https://api.staging.netrasystems.ai' in content, \
"Staging config must use api.staging.netrasystems.ai"

@pytest.mark.e2e
def test_auth_service_client_uses_unified_config(self, project_root: Path):
    pass
"""Test that auth-service-client.ts uses unified configuration."""
pass"""
pass"""
assert client_file.exists(), "formatted_string"

content = client_file.read_text()

    # Check imports unified config
assert 'unifiedApiConfig' in content, \
"auth-service-client must import unifiedApiConfig"

    Check it uses endpoints from config
assert 'this.endpoints.authConfig' in content, \
"auth-service-client must use authConfig from unified endpoints"

    # Should NOT have hardcoded localhost URLs
assert 'localhost:8081' not in content.replace('http://localhost:8081', "''), \"
"auth-service-client must not have hardcoded localhost URLs except in comments"

@pytest.fixture
reason="Docker build test is slow, set RUN_DOCKER_BUILD_TEST=1 to enable"
    
@pytest.mark.e2e
def test_docker_build_contains_correct_urls(self, project_root: Path):
    pass
"""
"""
Test that actual Docker build produces image with correct URLs.
"""
"""
Enable with: RUN_DOCKER_BUILD_TEST=1 pytest"""
Enable with: RUN_DOCKER_BUILD_TEST=1 pytest"""
pass
dockerfile = project_root / 'deployment' / 'docker' / 'frontend.gcp.Dockerfile'

    # Build Docker image
result = subprocess.run( )
[ )
'docker', 'build',
'-f', str(dockerfile),
'-t', 'frontend-staging-test:latest',
'.'
],
cwd=str(project_root),
capture_output=True,
text=True,
timeout=300  # 5 minute timeout for build
    
"""
"""
"formatted_string"

    # Extract built JavaScript to check for URLs
with tempfile.TemporaryDirectory() as tmpdir:
        Copy built files from image
subprocess.run( )
[ )
'docker', 'create',
'--name', 'frontend-test-container',
'frontend-staging-test:latest'
],
check=True
        

try:
    pass
subprocess.run( )
[ )
'docker', 'cp',
'frontend-test-container:/app/.next/static',
tmpdir
],
check=True
            

            # Search for URLs in built JavaScript
static_dir = Path(tmpdir) / 'static'
js_files = list(static_dir.rglob('*.js'))

found_staging_urls = False
found_localhost_urls = []

for js_file in js_files:
content = js_file.read_text(errors='ignore')

                # Check for staging URLs
if 'auth.staging.netrasystems.ai' in content:
    pass
found_staging_urls = True

                    # Check for localhost URLs (should not exist)
localhost_matches = re.findall( )
r'localhost:808[1]',
content
                    
if localhost_matches:
    pass
found_localhost_urls.extend(localhost_matches)

assert found_staging_urls, \
"Built JavaScript must contain auth.staging.netrasystems.ai"
assert not found_localhost_urls, \
"formatted_string"

finally:
                            # Cleanup
subprocess.run( )
['docker', 'rm', 'frontend-test-container'],
capture_output=True
                            

@pytest.mark.e2e
def test_deployment_script_configuration(self, project_root: Path):
    pass
"""Test that deploy_to_gcp.py has correct frontend configuration.""""""
"""Test that deploy_to_gcp.py has correct frontend configuration.""""""
assert deploy_script.exists(), "formatted_string"

content = deploy_script.read_text(encoding='utf-8', errors='ignore')

    # Check frontend service configuration
assert 'frontend.gcp.Dockerfile' in content, \
"Deploy script must use frontend.gcp.Dockerfile for staging"

    # Check it doesn't try to override NEXT_PUBLIC vars at runtime'
    # (they won't work, must be build-time)'
lines_with_next_public = [ )
line for line in content.split(" )"
")"
if 'NEXT_PUBLIC_' in line and 'environment_vars' in line
    

    # It's OK to have NEXT_PUBLIC_API_URL in environment_vars as documentation,'
    # but there should be a comment explaining it doesn't work'
for line in lines_with_next_public:
        # This is acceptable as it might be for documentation
pass

@pytest.mark.e2e
def test_cloudbuild_uses_correct_dockerfile(self, project_root: Path):
    pass
"""Test that cloudbuild configuration uses correct Dockerfile."""
pass
cloudbuild_file = project_root / 'organized_root' / 'deployment' / 'cloudbuild-frontend.yaml'

if cloudbuild_file.exists():
    pass
content = cloudbuild_file.read_text()"""
content = cloudbuild_file.read_text()"""
"CloudBuild must use frontend.gcp.Dockerfile"

@pytest.mark.e2e
def test_no_runtime_environment_override_attempt(self, project_root: Path):
    pass
"""
"""
Test that we"re not trying to override NEXT_PUBLIC_* at runtime."

CRITICAL: Next.js NEXT_PUBLIC_* variables are compile-time constants.
Runtime overrides don"t work."""
pass
    # Check Cloud Run service configurations if they exist
service_files = list((project_root / 'deployment').rglob('*service*.yaml'))
service_files.extend(list((project_root / 'terraform-gcp-staging').rglob('*.tf')))

for service_file in service_files:
if 'frontend' not in str(service_file).lower():
    pass
continue

content = service_file.read_text()

            # It's OK to have NEXT_PUBLIC_* in terraform/yaml for documentation,'
            # but there should be comments explaining they don't work at runtime'
if 'NEXT_PUBLIC_' in content and 'frontend' in content.lower():"""
if 'NEXT_PUBLIC_' in content and 'frontend' in content.lower():"""
lines = content.split(" )"
")"
for i, line in enumerate(lines):
if 'NEXT_PUBLIC_' in line:
                        # Check nearby lines for warning comments
context = "
context = "
".join(lines[max(0, i-2):min(len(lines), i+3)])"
                        # This is just a warning, not an assertion
if 'build' not in context.lower() and 'compile' not in context.lower():
    pass
print("formatted_string)"


class TestFrontendURLRegression:
        """Quick regression tests for the specific localhost URL issue."""

        @pytest.mark.e2e"""
        @pytest.mark.e2e"""
        """
        """
        Test that auth config URL is not pointing to localhost.
"""
"""
        Request URL http://localhost:8081/auth/config in staging"""
        Request URL http://localhost:8081/auth/config in staging"""
        pass
        # This test would need to be run against a deployed staging environment
        # It's here as documentation of the specific issue'
        pass

        @pytest.mark.e2e"""
        @pytest.mark.e2e"""
        """Test that frontend Dockerfiles exist and have content."""
        project_root = Path(__file__).parent.parent.parent

        dockerfiles = [ )
        project_root / 'deployment' / 'docker' / 'frontend.gcp.Dockerfile',
        project_root / 'deployment' / 'docker' / 'frontend.prod.Dockerfile',
    
"""
"""
        assert dockerfile.exists(), "formatted_string"
        content = dockerfile.read_text()
        assert len(content) > 100, "formatted_string"
        assert 'NEXT_PUBLIC_' in content, "formatted_string"
        pass

"""
]]]]]
}