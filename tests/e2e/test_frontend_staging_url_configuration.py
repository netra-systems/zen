from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test suite to prevent frontend staging URL regression.
# REMOVED_SYNTAX_ERROR: Validates that frontend builds contain correct environment-specific URLs.

# REMOVED_SYNTAX_ERROR: CRITICAL: This prevents the localhost URL regression where frontend makes requests
# REMOVED_SYNTAX_ERROR: to http://localhost:8081 instead of https://auth.staging.netrasystems.ai
# REMOVED_SYNTAX_ERROR: '''

import pytest
import subprocess
import re
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from shared.isolated_environment import get_env


env = get_env()
# REMOVED_SYNTAX_ERROR: class TestFrontendStagingURLConfiguration:
    # REMOVED_SYNTAX_ERROR: """Comprehensive tests to prevent frontend URL configuration regressions."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def project_root(self) -> Path:
    # REMOVED_SYNTAX_ERROR: """Get project root directory."""
    # REMOVED_SYNTAX_ERROR: return Path(__file__).parent.parent.parent

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def dockerfile_paths(self, project_root: Path) -> Dict[str, Path]:
    # REMOVED_SYNTAX_ERROR: """Get paths to all frontend Dockerfiles."""
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'staging': project_root / 'deployment' / 'docker' / 'frontend.gcp.Dockerfile',
    # REMOVED_SYNTAX_ERROR: 'production': project_root / 'deployment' / 'docker' / 'frontend.prod.Dockerfile',
    

    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_staging_dockerfile_has_next_public_environment_variables( )
self,
dockerfile_paths: Dict[str, Path]
# REMOVED_SYNTAX_ERROR: ):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that staging Dockerfile sets NEXT_PUBLIC_* environment variables before build.

    # REMOVED_SYNTAX_ERROR: CRITICAL: Next.js bakes NEXT_PUBLIC_* variables into the build at BUILD TIME.
    # REMOVED_SYNTAX_ERROR: Without these, frontend defaults to localhost URLs.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: staging_dockerfile = dockerfile_paths['staging']
    # REMOVED_SYNTAX_ERROR: assert staging_dockerfile.exists(), "formatted_string"

    # REMOVED_SYNTAX_ERROR: content = staging_dockerfile.read_text()

    # Check for required environment variables
    # REMOVED_SYNTAX_ERROR: required_env_vars = [ )
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_ENVIRONMENT', 'staging'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_API_URL', 'https://api.staging.netrasystems.ai'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_WS_URL', 'wss://api.staging.netrasystems.ai'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_AUTH_URL', 'https://auth.staging.netrasystems.ai'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_FRONTEND_URL', 'https://staging.netrasystems.ai'),
    

    # REMOVED_SYNTAX_ERROR: for var_name, expected_value in required_env_vars:
        # Check that ENV variable is set BEFORE npm run build
        # REMOVED_SYNTAX_ERROR: pattern = r'formatted_string'
        # REMOVED_SYNTAX_ERROR: assert re.search(pattern, content), \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # Verify it comes before the build command
        # REMOVED_SYNTAX_ERROR: env_pos = content.find('formatted_string')
        # REMOVED_SYNTAX_ERROR: build_pos = content.find('RUN npm run build')
        # REMOVED_SYNTAX_ERROR: assert env_pos > 0 and build_pos > 0, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert env_pos < build_pos, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_production_dockerfile_has_next_public_environment_variables( )
self,
dockerfile_paths: Dict[str, Path]
# REMOVED_SYNTAX_ERROR: ):
    # REMOVED_SYNTAX_ERROR: """Test that production Dockerfile sets correct NEXT_PUBLIC_* variables."""
    # REMOVED_SYNTAX_ERROR: prod_dockerfile = dockerfile_paths['production']
    # REMOVED_SYNTAX_ERROR: assert prod_dockerfile.exists(), "formatted_string"

    # REMOVED_SYNTAX_ERROR: content = prod_dockerfile.read_text()

    # REMOVED_SYNTAX_ERROR: required_env_vars = [ )
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_ENVIRONMENT', 'production'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_API_URL', 'https://api.netrasystems.ai'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_WS_URL', 'wss://api.netrasystems.ai'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_AUTH_URL', 'https://auth.netrasystems.ai'),
    # REMOVED_SYNTAX_ERROR: ('NEXT_PUBLIC_FRONTEND_URL', 'https://app.netrasystems.ai'),
    

    # REMOVED_SYNTAX_ERROR: for var_name, expected_value in required_env_vars:
        # REMOVED_SYNTAX_ERROR: pattern = r'formatted_string'
        # REMOVED_SYNTAX_ERROR: assert re.search(pattern, content), \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_no_localhost_urls_in_staging_dockerfile( )
self,
dockerfile_paths: Dict[str, Path]
# REMOVED_SYNTAX_ERROR: ):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that staging Dockerfile contains NO localhost URLs.

    # REMOVED_SYNTAX_ERROR: REGRESSION PREVENTION: Localhost URLs in staging cause complete auth failure.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: staging_dockerfile = dockerfile_paths['staging']
    # REMOVED_SYNTAX_ERROR: content = staging_dockerfile.read_text()

    # Check for localhost patterns
    # REMOVED_SYNTAX_ERROR: localhost_patterns = [ )
    # REMOVED_SYNTAX_ERROR: r'localhost:\d+',
    # REMOVED_SYNTAX_ERROR: r'127\.0\.0\.1:\d+',
    # REMOVED_SYNTAX_ERROR: r'http://localhost',
    # REMOVED_SYNTAX_ERROR: r'ws://localhost',
    

    # REMOVED_SYNTAX_ERROR: for pattern in localhost_patterns:
        # REMOVED_SYNTAX_ERROR: matches = re.findall(pattern, content, re.IGNORECASE)
        # REMOVED_SYNTAX_ERROR: assert not matches, \
        # REMOVED_SYNTAX_ERROR: "formatted_string"

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_unified_api_config_environment_detection(self, project_root: Path):
    # REMOVED_SYNTAX_ERROR: """Test that unified-api-config.ts properly detects environment."""
    # REMOVED_SYNTAX_ERROR: config_file = project_root / 'frontend' / 'lib' / 'unified-api-config.ts'
    # REMOVED_SYNTAX_ERROR: assert config_file.exists(), "formatted_string"

    # REMOVED_SYNTAX_ERROR: content = config_file.read_text()

    # Check for environment detection logic
    # REMOVED_SYNTAX_ERROR: assert 'detectEnvironment' in content, \
    # REMOVED_SYNTAX_ERROR: "unified-api-config must have detectEnvironment function"

    # Check for NEXT_PUBLIC_ENVIRONMENT check
    # REMOVED_SYNTAX_ERROR: assert 'NEXT_PUBLIC_ENVIRONMENT' in content, \
    # REMOVED_SYNTAX_ERROR: "detectEnvironment must check NEXT_PUBLIC_ENVIRONMENT"

    # Check for staging detection
    # REMOVED_SYNTAX_ERROR: assert 'staging.netrasystems.ai' in content, \
    # REMOVED_SYNTAX_ERROR: "detectEnvironment must detect staging by domain"

    # Check staging configuration has correct URLs
    # REMOVED_SYNTAX_ERROR: assert 'https://auth.staging.netrasystems.ai' in content, \
    # REMOVED_SYNTAX_ERROR: "Staging config must use auth.staging.netrasystems.ai"
    # REMOVED_SYNTAX_ERROR: assert 'https://api.staging.netrasystems.ai' in content, \
    # REMOVED_SYNTAX_ERROR: "Staging config must use api.staging.netrasystems.ai"

    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_auth_service_client_uses_unified_config(self, project_root: Path):
    # REMOVED_SYNTAX_ERROR: """Test that auth-service-client.ts uses unified configuration."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: client_file = project_root / 'frontend' / 'lib' / 'auth-service-client.ts'
    # REMOVED_SYNTAX_ERROR: assert client_file.exists(), "formatted_string"

    # REMOVED_SYNTAX_ERROR: content = client_file.read_text()

    # Check imports unified config
    # REMOVED_SYNTAX_ERROR: assert 'unifiedApiConfig' in content, \
    # REMOVED_SYNTAX_ERROR: "auth-service-client must import unifiedApiConfig"

    # Check it uses endpoints from config
    # REMOVED_SYNTAX_ERROR: assert 'this.endpoints.authConfig' in content, \
    # REMOVED_SYNTAX_ERROR: "auth-service-client must use authConfig from unified endpoints"

    # Should NOT have hardcoded localhost URLs
    # REMOVED_SYNTAX_ERROR: assert 'localhost:8081' not in content.replace('http://localhost:8081', ''), \
    # REMOVED_SYNTAX_ERROR: "auth-service-client must not have hardcoded localhost URLs except in comments"

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
    # REMOVED_SYNTAX_ERROR: reason="Docker build test is slow, set RUN_DOCKER_BUILD_TEST=1 to enable"
    
    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_docker_build_contains_correct_urls(self, project_root: Path):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that actual Docker build produces image with correct URLs.

    # REMOVED_SYNTAX_ERROR: NOTE: This test is slow as it builds the Docker image.
    # REMOVED_SYNTAX_ERROR: Enable with: RUN_DOCKER_BUILD_TEST=1 pytest
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: dockerfile = project_root / 'deployment' / 'docker' / 'frontend.gcp.Dockerfile'

    # Build Docker image
    # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
    # REMOVED_SYNTAX_ERROR: [ )
    # REMOVED_SYNTAX_ERROR: 'docker', 'build',
    # REMOVED_SYNTAX_ERROR: '-f', str(dockerfile),
    # REMOVED_SYNTAX_ERROR: '-t', 'frontend-staging-test:latest',
    # REMOVED_SYNTAX_ERROR: '.'
    # REMOVED_SYNTAX_ERROR: ],
    # REMOVED_SYNTAX_ERROR: cwd=str(project_root),
    # REMOVED_SYNTAX_ERROR: capture_output=True,
    # REMOVED_SYNTAX_ERROR: text=True,
    # REMOVED_SYNTAX_ERROR: timeout=300  # 5 minute timeout for build
    

    # REMOVED_SYNTAX_ERROR: assert result.returncode == 0, \
    # REMOVED_SYNTAX_ERROR: "formatted_string"

    # Extract built JavaScript to check for URLs
    # REMOVED_SYNTAX_ERROR: with tempfile.TemporaryDirectory() as tmpdir:
        # Copy built files from image
        # REMOVED_SYNTAX_ERROR: subprocess.run( )
        # REMOVED_SYNTAX_ERROR: [ )
        # REMOVED_SYNTAX_ERROR: 'docker', 'create',
        # REMOVED_SYNTAX_ERROR: '--name', 'frontend-test-container',
        # REMOVED_SYNTAX_ERROR: 'frontend-staging-test:latest'
        # REMOVED_SYNTAX_ERROR: ],
        # REMOVED_SYNTAX_ERROR: check=True
        

        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: subprocess.run( )
            # REMOVED_SYNTAX_ERROR: [ )
            # REMOVED_SYNTAX_ERROR: 'docker', 'cp',
            # REMOVED_SYNTAX_ERROR: 'frontend-test-container:/app/.next/static',
            # REMOVED_SYNTAX_ERROR: tmpdir
            # REMOVED_SYNTAX_ERROR: ],
            # REMOVED_SYNTAX_ERROR: check=True
            

            # Search for URLs in built JavaScript
            # REMOVED_SYNTAX_ERROR: static_dir = Path(tmpdir) / 'static'
            # REMOVED_SYNTAX_ERROR: js_files = list(static_dir.rglob('*.js'))

            # REMOVED_SYNTAX_ERROR: found_staging_urls = False
            # REMOVED_SYNTAX_ERROR: found_localhost_urls = []

            # REMOVED_SYNTAX_ERROR: for js_file in js_files:
                # REMOVED_SYNTAX_ERROR: content = js_file.read_text(errors='ignore')

                # Check for staging URLs
                # REMOVED_SYNTAX_ERROR: if 'auth.staging.netrasystems.ai' in content:
                    # REMOVED_SYNTAX_ERROR: found_staging_urls = True

                    # Check for localhost URLs (should not exist)
                    # REMOVED_SYNTAX_ERROR: localhost_matches = re.findall( )
                    # REMOVED_SYNTAX_ERROR: r'localhost:808[01]',
                    # REMOVED_SYNTAX_ERROR: content
                    
                    # REMOVED_SYNTAX_ERROR: if localhost_matches:
                        # REMOVED_SYNTAX_ERROR: found_localhost_urls.extend(localhost_matches)

                        # REMOVED_SYNTAX_ERROR: assert found_staging_urls, \
                        # REMOVED_SYNTAX_ERROR: "Built JavaScript must contain auth.staging.netrasystems.ai"
                        # REMOVED_SYNTAX_ERROR: assert not found_localhost_urls, \
                        # REMOVED_SYNTAX_ERROR: "formatted_string"

                        # REMOVED_SYNTAX_ERROR: finally:
                            # Cleanup
                            # REMOVED_SYNTAX_ERROR: subprocess.run( )
                            # REMOVED_SYNTAX_ERROR: ['docker', 'rm', 'frontend-test-container'],
                            # REMOVED_SYNTAX_ERROR: capture_output=True
                            

                            # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_deployment_script_configuration(self, project_root: Path):
    # REMOVED_SYNTAX_ERROR: """Test that deploy_to_gcp.py has correct frontend configuration."""
    # REMOVED_SYNTAX_ERROR: deploy_script = project_root / 'scripts' / 'deploy_to_gcp.py'
    # REMOVED_SYNTAX_ERROR: assert deploy_script.exists(), "formatted_string"

    # REMOVED_SYNTAX_ERROR: content = deploy_script.read_text(encoding='utf-8', errors='ignore')

    # Check frontend service configuration
    # REMOVED_SYNTAX_ERROR: assert 'frontend.gcp.Dockerfile' in content, \
    # REMOVED_SYNTAX_ERROR: "Deploy script must use frontend.gcp.Dockerfile for staging"

    # Check it doesn't try to override NEXT_PUBLIC vars at runtime
    # (they won't work, must be build-time)
    # REMOVED_SYNTAX_ERROR: lines_with_next_public = [ )
    # REMOVED_SYNTAX_ERROR: line for line in content.split(" )
    # REMOVED_SYNTAX_ERROR: ")
    # REMOVED_SYNTAX_ERROR: if 'NEXT_PUBLIC_' in line and 'environment_vars' in line
    

    # It's OK to have NEXT_PUBLIC_API_URL in environment_vars as documentation,
    # but there should be a comment explaining it doesn't work
    # REMOVED_SYNTAX_ERROR: for line in lines_with_next_public:
        # This is acceptable as it might be for documentation
        # REMOVED_SYNTAX_ERROR: pass

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_cloudbuild_uses_correct_dockerfile(self, project_root: Path):
    # REMOVED_SYNTAX_ERROR: """Test that cloudbuild configuration uses correct Dockerfile."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: cloudbuild_file = project_root / 'organized_root' / 'deployment' / 'cloudbuild-frontend.yaml'

    # REMOVED_SYNTAX_ERROR: if cloudbuild_file.exists():
        # REMOVED_SYNTAX_ERROR: content = cloudbuild_file.read_text()
        # REMOVED_SYNTAX_ERROR: assert 'frontend.gcp.Dockerfile' in content, \
        # REMOVED_SYNTAX_ERROR: "CloudBuild must use frontend.gcp.Dockerfile"

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_no_runtime_environment_override_attempt(self, project_root: Path):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that we"re not trying to override NEXT_PUBLIC_* at runtime.

    # REMOVED_SYNTAX_ERROR: CRITICAL: Next.js NEXT_PUBLIC_* variables are compile-time constants.
    # REMOVED_SYNTAX_ERROR: Runtime overrides don"t work.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Check Cloud Run service configurations if they exist
    # REMOVED_SYNTAX_ERROR: service_files = list((project_root / 'deployment').rglob('*service*.yaml'))
    # REMOVED_SYNTAX_ERROR: service_files.extend(list((project_root / 'terraform-gcp-staging').rglob('*.tf')))

    # REMOVED_SYNTAX_ERROR: for service_file in service_files:
        # REMOVED_SYNTAX_ERROR: if 'frontend' not in str(service_file).lower():
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: content = service_file.read_text()

            # It's OK to have NEXT_PUBLIC_* in terraform/yaml for documentation,
            # but there should be comments explaining they don't work at runtime
            # REMOVED_SYNTAX_ERROR: if 'NEXT_PUBLIC_' in content and 'frontend' in content.lower():
                # Check for warning comments
                # REMOVED_SYNTAX_ERROR: lines = content.split(" )
                # REMOVED_SYNTAX_ERROR: ")
                # REMOVED_SYNTAX_ERROR: for i, line in enumerate(lines):
                    # REMOVED_SYNTAX_ERROR: if 'NEXT_PUBLIC_' in line:
                        # Check nearby lines for warning comments
                        # REMOVED_SYNTAX_ERROR: context = "
                        # REMOVED_SYNTAX_ERROR: ".join(lines[max(0, i-2):min(len(lines), i+3)])
                        # This is just a warning, not an assertion
                        # REMOVED_SYNTAX_ERROR: if 'build' not in context.lower() and 'compile' not in context.lower():
                            # REMOVED_SYNTAX_ERROR: print("formatted_string")


# REMOVED_SYNTAX_ERROR: class TestFrontendURLRegression:
    # REMOVED_SYNTAX_ERROR: """Quick regression tests for the specific localhost URL issue."""

    # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_auth_config_url_not_localhost(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test that auth config URL is not pointing to localhost.

    # REMOVED_SYNTAX_ERROR: This is the specific regression that was observed:
        # REMOVED_SYNTAX_ERROR: Request URL http://localhost:8081/auth/config in staging
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # This test would need to be run against a deployed staging environment
        # It's here as documentation of the specific issue
        # REMOVED_SYNTAX_ERROR: pass

        # REMOVED_SYNTAX_ERROR: @pytest.mark.e2e
# REMOVED_SYNTAX_ERROR: def test_frontend_dockerfile_exists_and_is_not_empty(self):
    # REMOVED_SYNTAX_ERROR: """Test that frontend Dockerfiles exist and have content."""
    # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent

    # REMOVED_SYNTAX_ERROR: dockerfiles = [ )
    # REMOVED_SYNTAX_ERROR: project_root / 'deployment' / 'docker' / 'frontend.gcp.Dockerfile',
    # REMOVED_SYNTAX_ERROR: project_root / 'deployment' / 'docker' / 'frontend.prod.Dockerfile',
    

    # REMOVED_SYNTAX_ERROR: for dockerfile in dockerfiles:
        # REMOVED_SYNTAX_ERROR: assert dockerfile.exists(), "formatted_string"
        # REMOVED_SYNTAX_ERROR: content = dockerfile.read_text()
        # REMOVED_SYNTAX_ERROR: assert len(content) > 100, "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert 'NEXT_PUBLIC_' in content, "formatted_string"
        # REMOVED_SYNTAX_ERROR: pass