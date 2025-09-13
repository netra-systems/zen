from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

#!/usr/bin/env python3

"""

Frontend Build Script Staging Regression Tests



Tests to replicate frontend build issues found in GCP staging audit:

- Build script errors during deployment

- Missing proper build configurations

- Frontend service deployment failures due to build issues



Business Value: Prevents user access failures costing $25K+ MRR

Critical for frontend availability and user experience.



Root Cause from Staging Audit:  

- Frontend build scripts fail during GCP staging deployment

- Missing build dependencies or configuration files

- Build process doesn't validate required assets are generated



These tests will FAIL initially to confirm the issues exist, then PASS after fixes.

"""



import os

import subprocess

import pytest

from pathlib import Path

from typing import Dict, List, Any



# Get the project root directory

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent





@pytest.mark.staging

@pytest.mark.critical  

class TestFrontendBuildScriptRegression:

    """Tests that replicate frontend build script issues from staging audit"""



    @pytest.mark.e2e

    def test_frontend_build_script_exists_regression(self):

        """

        REGRESSION TEST: Frontend build script missing or not executable

        

        This test should FAIL initially if build scripts are missing.

        Root cause: Build scripts not present in expected locations.

        

        Expected failure: Build script files don't exist or aren't executable

        """

        # Arrange - Check for expected build script locations

        expected_build_scripts = [

            PROJECT_ROOT / "frontend" / "package.json",

            PROJECT_ROOT / "frontend" / "build.sh", 

            PROJECT_ROOT / "frontend" / "Dockerfile",

            PROJECT_ROOT / "scripts" / "build_frontend.py",

            PROJECT_ROOT / "scripts" / "deploy_to_gcp.py"

        ]

        

        # Act & Assert - Check if build scripts exist

        missing_scripts = []

        non_executable_scripts = []

        

        for script_path in expected_build_scripts:

            if not script_path.exists():

                missing_scripts.append(str(script_path))

            elif script_path.suffix in ['.sh', '.py'] and not os.access(script_path, os.X_OK):

                # Check if script is executable (Unix systems)

                if hasattr(os, 'X_OK') and not script_path.name.endswith('.json'):

                    non_executable_scripts.append(str(script_path))

        

        # This should FAIL if build scripts are missing

        if missing_scripts:

            pytest.fail(f"Missing frontend build scripts: {missing_scripts}")

        if non_executable_scripts:

            pytest.fail(f"Build scripts not executable: {non_executable_scripts}")



    @pytest.mark.e2e

    def test_frontend_build_dependencies_missing_regression(self):

        """

        REGRESSION TEST: Frontend build dependencies not properly configured

        

        This test should FAIL initially if dependencies are missing.

        Root cause: package.json missing dependencies or wrong versions.

        

        Expected failure: Required build dependencies not available

        """

        # Arrange - Check package.json for required dependencies

        package_json_path = PROJECT_ROOT / "frontend" / "package.json"

        

        if not package_json_path.exists():

            pytest.fail("package.json missing - cannot validate dependencies")

        

        # Read package.json

        import json

        try:

            with open(package_json_path, 'r') as f:

                package_data = json.load(f)

        except (json.JSONDecodeError, FileNotFoundError) as e:

            pytest.fail(f"Cannot read package.json: {e}")

        

        # Act & Assert - Check for critical build dependencies

        required_deps = [

            "react",

            "typescript", 

            "@types/react",

            "vite"  # or "webpack" depending on build tool

        ]

        

        all_deps = {

            **package_data.get("dependencies", {}),

            **package_data.get("devDependencies", {})

        }

        

        missing_deps = [dep for dep in required_deps if dep not in all_deps]

        

        # This should FAIL if critical dependencies are missing

        if missing_deps:

            pytest.fail(f"Missing critical frontend dependencies: {missing_deps}")



    @pytest.mark.e2e

    def test_frontend_build_script_execution_regression(self):

        """

        REGRESSION TEST: Frontend build script fails during execution

        

        This test should FAIL initially if build process has errors.

        Root cause: Build script contains errors or missing configurations.

        

        Expected failure: Build script execution returns non-zero exit code

        """

        # Arrange - Prepare build environment

        frontend_dir = PROJECT_ROOT / "frontend"

        

        if not frontend_dir.exists():

            pytest.fail("Frontend directory missing")

        

        # Mock build environment variables that might be missing in staging

        build_env = {

            **os.environ,

            'NODE_ENV': 'production',

            'ENVIRONMENT': 'staging',

            'BUILD_TARGET': 'staging'

        }

        

        # Act & Assert - Try to run build process

        build_commands = [

            ["npm", "install"],

            ["npm", "run", "build"],

            ["npm", "run", "type-check"]  # TypeScript validation

        ]

        

        for cmd in build_commands:

            try:

                # This should FAIL if build process has issues

                result = subprocess.run(

                    cmd,

                    cwd=frontend_dir,

                    env=build_env,

                    capture_output=True,

                    text=True,

                    timeout=300  # 5 minute timeout

                )

                

                if result.returncode != 0:

                    pytest.fail(f"Build command failed: {' '.join(cmd)}\n"

                              f"stdout: {result.stdout}\n"

                              f"stderr: {result.stderr}")

                              

            except subprocess.TimeoutExpired:

                pytest.fail(f"Build command timed out: {' '.join(cmd)}")

            except FileNotFoundError:

                pytest.fail(f"Build command not found: {' '.join(cmd)} - npm may not be installed")



    @pytest.mark.e2e

    def test_frontend_build_output_validation_regression(self):

        """

        REGRESSION TEST: Frontend build doesn't generate required output files

        

        This test should FAIL initially if build output is incomplete.

        Root cause: Build process completes but doesn't generate all needed files.

        

        Expected failure: Required build artifacts missing after build

        """

        # Arrange - Define expected build outputs

        frontend_dir = PROJECT_ROOT / "frontend"

        expected_build_outputs = [

            frontend_dir / "dist" / "index.html",

            frontend_dir / "dist" / "assets",  # Directory should exist

            frontend_dir / "dist" / "favicon.ico"

        ]

        

        # Also check for JS/CSS bundles (pattern-based)

        dist_dir = frontend_dir / "dist"

        

        # Act - Check if build outputs exist

        missing_outputs = []

        

        for output_path in expected_build_outputs:

            if not output_path.exists():

                missing_outputs.append(str(output_path))

        

        # Check for JS/CSS bundle files

        if dist_dir.exists():

            js_files = list(dist_dir.rglob("*.js"))

            css_files = list(dist_dir.rglob("*.css"))

            

            if not js_files:

                missing_outputs.append("JavaScript bundle files (*.js)")

            if not css_files:

                missing_outputs.append("CSS bundle files (*.css)")

        else:

            missing_outputs.append("dist directory")

        

        # Assert - This should FAIL if build outputs are missing

        if missing_outputs:

            pytest.fail(f"Missing frontend build outputs: {missing_outputs}")



    @pytest.mark.e2e

    def test_frontend_dockerfile_build_regression(self):

        """

        REGRESSION TEST: Frontend Dockerfile build fails in staging environment

        

        This test should FAIL initially if Dockerfile has build issues.

        Root cause: Dockerfile missing steps or wrong base image for staging.

        

        Expected failure: Docker build fails or produces non-functional image

        """

        # Arrange - Check Dockerfile exists and has required content

        dockerfile_path = PROJECT_ROOT / "frontend" / "Dockerfile"

        

        if not dockerfile_path.exists():

            pytest.fail("Frontend Dockerfile missing")

        

        # Read Dockerfile content

        with open(dockerfile_path, 'r') as f:

            dockerfile_content = f.read()

        

        # Act & Assert - Validate Dockerfile has required sections

        required_dockerfile_elements = [

            "FROM node:",  # Node.js base image

            "WORKDIR",     # Working directory set

            "COPY package",  # Package files copied

            "RUN npm install",  # Dependencies installed  

            "COPY .",       # Source code copied

            "RUN npm run build",  # Build step

            "EXPOSE"        # Port exposed

        ]

        

        missing_elements = []

        for element in required_dockerfile_elements:

            if element not in dockerfile_content:

                missing_elements.append(element)

        

        # This should FAIL if Dockerfile is incomplete

        if missing_elements:

            pytest.fail(f"Dockerfile missing required elements: {missing_elements}")



    @pytest.mark.e2e

    def test_frontend_staging_deployment_script_regression(self):

        """

        REGRESSION TEST: Deployment script fails to deploy frontend to staging

        

        This test should FAIL initially if deployment script has issues.

        Root cause: Deployment script missing frontend-specific configuration.

        

        Expected failure: Deployment script doesn't handle frontend properly

        """

        # Arrange - Check deployment script

        deploy_script_path = PROJECT_ROOT / "scripts" / "deploy_to_gcp.py"

        

        if not deploy_script_path.exists():

            pytest.fail("GCP deployment script missing")

        

        # Read deployment script content

        with open(deploy_script_path, 'r') as f:

            deploy_script_content = f.read()

        

        # Act & Assert - Check if script handles frontend deployment

        required_frontend_deployment_elements = [

            "frontend",  # References frontend service

            "build",     # Has build step

            "Cloud Run", # Deploys to Cloud Run

            "staging"    # Has staging configuration

        ]

        

        missing_elements = []

        for element in required_frontend_deployment_elements:

            if element.lower() not in deploy_script_content.lower():

                missing_elements.append(element)

        

        # This should FAIL if deployment script doesn't handle frontend

        if missing_elements:

            pytest.fail(f"Deployment script missing frontend elements: {missing_elements}")





@pytest.mark.staging

@pytest.mark.critical

class TestFrontendBuildEnvironmentRegression:

    """Tests frontend build environment configuration issues"""



    @pytest.mark.e2e

    def test_frontend_build_environment_variables_regression(self):

        """

        REGRESSION TEST: Frontend build missing required environment variables

        

        This test should FAIL initially if build env vars are missing.

        Root cause: Build process needs staging-specific environment variables.

        

        Expected failure: Build succeeds but runtime configuration is wrong

        """

        # Arrange - Define required staging environment variables for frontend

        required_env_vars = [

            'NETRA_API_URL',  # Backend API URL

            'NETRA_WS_URL',   # WebSocket URL  

            'ENVIRONMENT',    # Environment identifier

            'GOOGLE_CLIENT_ID_STAGING'  # OAuth client ID

        ]

        

        # Act & Assert - Check if environment variables are available during build

        missing_env_vars = []

        invalid_env_vars = []

        

        for env_var in required_env_vars:

            value = get_env().get(env_var)

            

            if value is None:

                missing_env_vars.append(env_var)

            elif env_var.endswith('_URL') and not value.startswith(('http://', 'https://')):

                invalid_env_vars.append(f"{env_var}={value} (invalid URL format)")

            elif env_var == 'ENVIRONMENT' and value != 'staging':

                invalid_env_vars.append(f"{env_var}={value} (should be 'staging')")

        

        # This should FAIL if required environment variables are missing or invalid

        error_messages = []

        if missing_env_vars:

            error_messages.append(f"Missing env vars: {missing_env_vars}")

        if invalid_env_vars:

            error_messages.append(f"Invalid env vars: {invalid_env_vars}")

        

        if error_messages:

            pytest.fail("; ".join(error_messages))



    @pytest.mark.e2e

    def test_frontend_build_asset_optimization_regression(self):

        """

        REGRESSION TEST: Frontend build doesn't optimize assets for production

        

        This test should FAIL initially if build optimization is missing.

        Root cause: Build process doesn't minify/optimize assets for staging.

        

        Expected failure: Build outputs are not optimized for production use

        """

        # Arrange - Check if build produces optimized assets

        frontend_dir = PROJECT_ROOT / "frontend"

        dist_dir = frontend_dir / "dist"

        

        if not dist_dir.exists():

            pytest.fail("Build output directory missing - run build first")

        

        # Act & Assert - Check optimization characteristics

        optimization_issues = []

        

        # Check for minified JavaScript

        js_files = list(dist_dir.rglob("*.js"))

        for js_file in js_files:

            if js_file.stat().st_size > 1024:  # Check files larger than 1KB

                with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:

                    content = f.read(1000)  # Read first 1KB

                    # Check if file appears minified (no excessive whitespace)

                    if content.count('\n') > 10 and not js_file.name.endswith('.map'):

                        optimization_issues.append(f"JS file not minified: {js_file.name}")

        

        # Check for CSS optimization

        css_files = list(dist_dir.rglob("*.css"))

        for css_file in css_files:

            if css_file.stat().st_size > 1024:  # Check files larger than 1KB

                with open(css_file, 'r', encoding='utf-8', errors='ignore') as f:

                    content = f.read(1000)  # Read first 1KB

                    if content.count('\n') > 10:

                        optimization_issues.append(f"CSS file not minified: {css_file.name}")

        

        # Check for source maps (should exist for debugging)

        map_files = list(dist_dir.rglob("*.map"))

        if not map_files:

            optimization_issues.append("Source maps missing for debugging")

        

        # This should FAIL if assets are not properly optimized

        if optimization_issues:

            pytest.fail(f"Build optimization issues: {optimization_issues}")

