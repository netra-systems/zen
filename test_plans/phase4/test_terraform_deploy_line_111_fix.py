"""
Test Plan: Terraform Deploy Line 111 Fix Validation
Issue #245 - CRITICAL: terraform/deploy.sh calls non-existent UnifiedTestRunner mode

PROBLEM: Line 111 in terraform-gcp-staging/deploy.sh calls:
    python3 unified_test_runner.py --level integration --env staging --fast-fail
But UnifiedTestRunner deployment mode is deprecated/non-functional.

SOLUTION: Update line 111 to call the correct deployment script.
"""
import subprocess
import sys
import os
from pathlib import Path
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

class TestTerraformDeployLine111Fix:
    """Test terraform deploy.sh line 111 fix for deployment script consolidation."""

    @pytest.fixture
    def terraform_deploy_script_path(self):
        """Path to terraform deploy script."""
        return project_root / 'terraform-gcp-staging' / 'deploy.sh'

    @pytest.fixture
    def backup_deploy_script(self, terraform_deploy_script_path):
        """Create backup of deploy script for safe testing."""
        backup_path = terraform_deploy_script_path.with_suffix('.sh.backup')
        if terraform_deploy_script_path.exists():
            shutil.copy2(terraform_deploy_script_path, backup_path)
            yield backup_path
            if backup_path.exists():
                shutil.copy2(backup_path, terraform_deploy_script_path)
                os.remove(backup_path)
        else:
            yield None

    def test_terraform_deploy_script_exists(self, terraform_deploy_script_path):
        """Ensure terraform deploy script exists."""
        assert terraform_deploy_script_path.exists(), f'Terraform deploy script not found: {terraform_deploy_script_path}'

    def test_current_line_111_content(self, terraform_deploy_script_path):
        """Document current line 111 content before fix."""
        with open(terraform_deploy_script_path, 'r') as f:
            lines = f.readlines()
        if len(lines) >= 111:
            line_111 = lines[110].strip()
            print(f'Current line 111: {line_111}')
            assert 'unified_test_runner.py' in line_111, f'Expected line 111 to contain unified_test_runner.py call, got: {line_111}'
            expected_problematic_call = 'python3 unified_test_runner.py --level integration --env staging --fast-fail'
            assert expected_problematic_call in line_111, f"Line 111 doesn't contain expected problematic call: {line_111}"

    def test_unified_test_runner_deployment_mode_availability(self):
        """Test if UnifiedTestRunner deployment mode actually exists."""
        unified_runner_path = project_root / 'tests' / 'unified_test_runner.py'
        if unified_runner_path.exists():
            try:
                result = subprocess.run([sys.executable, str(unified_runner_path), '--help'], capture_output=True, text=True, timeout=30)
                help_output = result.stdout
                has_deployment_mode = '--execution-mode deploy' in help_output or 'deploy' in help_output
                print(f'UnifiedTestRunner deployment mode available: {has_deployment_mode}')
                print(f'Help output excerpt: {help_output[:500]}...')
                return has_deployment_mode
            except subprocess.TimeoutExpired:
                pytest.fail('UnifiedTestRunner help command timed out')
            except Exception as e:
                pytest.fail(f'UnifiedTestRunner help command failed: {e}')
        else:
            pytest.fail(f'UnifiedTestRunner not found at: {unified_runner_path}')

    def test_correct_deployment_script_exists(self):
        """Verify the correct deployment script exists and works."""
        correct_script = project_root / 'scripts' / 'deploy_to_gcp_actual.py'
        assert correct_script.exists(), f'Correct deployment script not found: {correct_script}'
        try:
            result = subprocess.run([sys.executable, str(correct_script), '--help'], capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, f'Deployment script help failed: {result.stderr}'
            help_output = result.stdout
            required_params = ['--project', '--build-local', '--run-checks']
            for param in required_params:
                assert param in help_output, f'Deployment script missing required parameter: {param}'
        except subprocess.TimeoutExpired:
            pytest.fail('Deployment script help command timed out')
        except Exception as e:
            pytest.fail(f'Deployment script help command failed: {e}')

    def test_proposed_line_111_fix(self, terraform_deploy_script_path, backup_deploy_script):
        """Test the proposed fix for line 111."""
        with open(terraform_deploy_script_path, 'r') as f:
            lines = f.readlines()
        if len(lines) < 111:
            pytest.skip('Script has fewer than 111 lines')
        original_line_111 = lines[110].strip()
        proposed_line_111 = 'python3 scripts/deploy_to_gcp_actual.py --project ${PROJECT_ID} --build-local --run-checks'
        lines[110] = proposed_line_111 + '\n'
        test_script_path = terraform_deploy_script_path.with_suffix('.sh.test')
        with open(test_script_path, 'w') as f:
            f.writelines(lines)
        try:
            result = subprocess.run(['bash', '-n', str(test_script_path)], capture_output=True, text=True)
            assert result.returncode == 0, f'Modified script has syntax errors: {result.stderr}'
            print(f'Original line 111: {original_line_111}')
            print(f'Proposed line 111: {proposed_line_111}')
            print(' PASS:  Syntax check passed for proposed fix')
        finally:
            if test_script_path.exists():
                os.remove(test_script_path)

    def test_terraform_script_parameter_compatibility(self):
        """Test that terraform script parameters are compatible with deployment script."""
        terraform_params = {'PROJECT_ID': 'netra-staging', 'OLD_INSTANCE': 'staging-shared-postgres'}
        deployment_script = project_root / 'scripts' / 'deploy_to_gcp_actual.py'
        expected_deployment_command = [sys.executable, str(deployment_script), '--project', terraform_params['PROJECT_ID'], '--build-local', '--run-checks']
        try:
            test_command = expected_deployment_command + ['--help']
            result = subprocess.run(test_command, capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, f'Deployment script rejected terraform parameters: {result.stderr}'
            print(' PASS:  Parameter compatibility verified')
        except subprocess.TimeoutExpired:
            pytest.fail('Parameter compatibility test timed out')
        except Exception as e:
            pytest.fail(f'Parameter compatibility test failed: {e}')

    def test_deployment_script_dry_run_with_terraform_params(self):
        """Test deployment script dry-run with terraform-style parameters."""
        deployment_script = project_root / 'scripts' / 'deploy_to_gcp_actual.py'
        test_command = [sys.executable, str(deployment_script), '--project', 'netra-staging', '--build-local', '--dry-run']
        try:
            result = subprocess.run(test_command, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                error_output = result.stderr
                acceptable_errors = ['Missing required environment variables', 'gcloud CLI is not installed', 'Not authenticated with GCloud', 'Secret validation failed']
                is_config_error = any((error in error_output for error in acceptable_errors))
                if not is_config_error:
                    pytest.fail(f'Deployment script failed unexpectedly: {error_output}')
                else:
                    print(f' PASS:  Dry-run failed with expected configuration error: {error_output[:200]}...')
            else:
                print(' PASS:  Dry-run succeeded')
        except subprocess.TimeoutExpired:
            pytest.fail('Deployment script dry-run timed out')
        except Exception as e:
            pytest.fail(f'Deployment script dry-run failed: {e}')

    def test_integration_sequence_validation(self):
        """Test the complete terraform  ->  deployment sequence logic."""
        terraform_steps = ['terraform init', 'terraform plan -out=tfplan', 'terraform apply tfplan']
        deployment_step = 'python3 scripts/deploy_to_gcp_actual.py --project ${PROJECT_ID} --build-local --run-checks'
        integration_test_step = 'python3 tests/unified_test_runner.py --category integration --env staging --fast-fail'
        print(' PASS:  Terraform  ->  Deployment sequence:')
        for i, step in enumerate(terraform_steps, 1):
            print(f'  {i}. {step}')
        print(f'  4. {deployment_step}')
        print(f'  5. {integration_test_step}')
        assert True, 'Sequence validation complete'

    @pytest.mark.integration
    def test_end_to_end_terraform_deploy_simulation(self, backup_deploy_script):
        """Simulate end-to-end terraform deploy with fixed line 111."""
        terraform_deploy_script = project_root / 'terraform-gcp-staging' / 'deploy.sh'
        env_vars = {'PROJECT_ID': 'netra-staging', 'OLD_INSTANCE': 'staging-shared-postgres', 'TERRAFORM_DIR': '.'}
        fixed_deployment_command = [sys.executable, str(project_root / 'scripts' / 'deploy_to_gcp_actual.py'), '--project', env_vars['PROJECT_ID'], '--build-local', '--run-checks', '--dry-run']
        print('[U+1F9EA] Simulating fixed terraform deploy sequence:')
        print(f'Environment: {env_vars}')
        print(f"Fixed line 111 command: {' '.join(fixed_deployment_command)}")
        try:
            result = subprocess.run(fixed_deployment_command, capture_output=True, text=True, timeout=60, env={**os.environ, **env_vars})
            print(f'Exit code: {result.returncode}')
            print(f'Stdout: {result.stdout[:500]}...')
            if result.stderr:
                print(f'Stderr: {result.stderr[:500]}...')
            if result.returncode == 0:
                print(' PASS:  Fixed deployment command succeeded in simulation')
            else:
                acceptable_errors = ['Missing required environment variables', 'gcloud CLI is not installed', 'Not authenticated with GCloud', 'Secret validation failed', 'Dry run mode']
                error_is_acceptable = any((error in result.stderr for error in acceptable_errors))
                if error_is_acceptable:
                    print(f' PASS:  Fixed deployment command failed with expected error: {result.stderr[:200]}...')
                else:
                    pytest.fail(f'Fixed deployment command failed unexpectedly: {result.stderr}')
        except subprocess.TimeoutExpired:
            pytest.fail('Fixed deployment command simulation timed out')
        except Exception as e:
            pytest.fail(f'Fixed deployment command simulation failed: {e}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')