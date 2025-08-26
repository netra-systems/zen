"""Critical Auth Service ID Configuration Failures - Failing Tests
Tests that replicate Service ID configuration issues found in staging logs.

CRITICAL SERVICE ID ISSUES TO REPLICATE:
1. Service ID showing literal shell command instead of executed value (e.g. "$(whoami)")
2. Environment variable substitution failures in containerized environments  
3. Service ID containing invalid characters causing authentication failures
4. Missing or malformed service identification in staging deployment

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Service identification and authentication reliability
- Value Impact: Prevents service-to-service auth failures due to ID misconfiguration
- Strategic Impact: Ensures proper service mesh authentication for enterprise deployments
"""

import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock

from auth_service.auth_core.config import AuthConfig
from test_framework.environment_markers import env, staging_only, env_requires

logger = logging.getLogger(__name__)


@env("staging")
@env_requires(services=["auth_service"], features=["service_id_configured"])
class TestCriticalServiceIDConfigurationFailures:
    """Test suite for Service ID configuration failures found in staging."""
    
    def test_service_id_shows_literal_shell_command_whoami(self):
        """FAILING TEST: Replicates Service ID showing '$(whoami)' instead of actual username.
        
        This is a critical error where shell command substitution fails in containerized
        environments, leaving literal shell commands in the service configuration.
        """
        # Environment that would cause shell command to not be executed
        problematic_env = {
            'ENVIRONMENT': 'staging',
            'SERVICE_ID': '$(whoami)',  # Literal shell command instead of executed value
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, problematic_env):
            # This should fail because SERVICE_ID contains literal shell command
            service_id = AuthConfig.get_service_id()
            
            # The service ID should NOT contain literal shell commands
            assert service_id != '$(whoami)', \
                f"Service ID contains literal shell command '$(whoami)' instead of executed value: {service_id}"
            
            # Should also not contain other shell command patterns
            shell_patterns = ['$(', '`', '${', '$USER', '$HOSTNAME']
            for pattern in shell_patterns:
                if pattern in service_id:
                    pytest.fail(f"Service ID contains unprocessed shell pattern '{pattern}': {service_id}")
            
            # Log the problematic service ID for debugging
            logger.error(f"Service ID literal shell command error replicated: '{service_id}'")
    
    def test_service_id_shows_literal_shell_command_hostname(self):
        """FAILING TEST: Tests Service ID showing '$(hostname)' instead of actual hostname.
        
        Related issue where hostname shell command is not executed properly.
        """
        problematic_env = {
            'ENVIRONMENT': 'staging', 
            'SERVICE_ID': '$(hostname)',  # Another common shell command pattern
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, problematic_env):
            service_id = AuthConfig.get_service_id()
            
            # Should not contain literal $(hostname) command
            assert service_id != '$(hostname)', \
                f"Service ID contains literal shell command '$(hostname)': {service_id}"
            
            logger.error(f"Service ID hostname shell command error replicated: '{service_id}'")
    
    def test_service_id_complex_shell_command_patterns(self):
        """FAILING TEST: Tests various shell command patterns that might appear literally.
        
        Tests multiple shell command patterns that could appear in SERVICE_ID due to
        improper environment variable processing in containers.
        """
        problematic_shell_commands = [
            '$(uname -n)',           # Get hostname
            '$(date +%s)',           # Get timestamp 
            '$(echo $USER)',         # Get username with nested variable
            '`hostname`',            # Backtick syntax
            '${HOSTNAME}',           # Variable expansion
            '$(whoami)-$(hostname)', # Combined commands
            '$RANDOM',               # Bash random variable
            '$(id -un)',             # Get username
        ]
        
        for shell_cmd in problematic_shell_commands:
            problematic_env = {
                'ENVIRONMENT': 'staging',
                'SERVICE_ID': shell_cmd,
                'AUTH_FAST_TEST_MODE': 'false'
            }
            
            with patch.dict(os.environ, problematic_env):
                service_id = AuthConfig.get_service_id()
                
                # Service ID should not contain the literal shell command
                if service_id == shell_cmd:
                    pytest.fail(f"Service ID contains unprocessed shell command: '{shell_cmd}'")
                
                # Should not contain shell metacharacters that indicate unprocessed commands
                shell_metacharacters = ['$(', '${', '`']
                for meta in shell_metacharacters:
                    if meta in service_id:
                        pytest.fail(f"Service ID contains shell metacharacter '{meta}' from command '{shell_cmd}': {service_id}")
                
                logger.warning(f"Tested shell command pattern: {shell_cmd} -> {service_id}")
    
    def test_service_id_container_environment_variable_failure(self):
        """FAILING TEST: Tests environment variable processing failure in containerized deployment.
        
        In containers, environment variables might not be processed the same way as in
        shell environments, causing literal values to be used.
        """
        # Simulate containerized environment where shell processing doesn't work
        container_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-staging',  # Cloud Run service name
            'SERVICE_ID': '$(echo "${K_SERVICE}-${HOSTNAME}")',  # Complex shell command
            'HOSTNAME': 'auth-container-abc123',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, container_env):
            service_id = AuthConfig.get_service_id()
            
            # In a properly configured system, this should resolve to something like:
            # "netra-auth-staging-auth-container-abc123"
            expected_pattern = 'netra-auth-staging'
            
            # But if shell processing fails, we get the literal command
            literal_command = '$(echo "${K_SERVICE}-${HOSTNAME}")'
            
            if service_id == literal_command:
                pytest.fail(f"Service ID shows literal shell command in container: {service_id}")
            
            # Should also not contain unprocessed variable references
            if '${K_SERVICE}' in service_id or '${HOSTNAME}' in service_id:
                pytest.fail(f"Service ID contains unprocessed environment variables: {service_id}")
            
            logger.error(f"Container environment processing test - Service ID: {service_id}")
    
    def test_service_id_invalid_characters_from_shell_failure(self):
        """FAILING TEST: Tests invalid characters in Service ID from failed shell command processing.
        
        When shell commands fail to execute, they might leave invalid characters that
        cause issues in service-to-service authentication.
        """
        problematic_env = {
            'ENVIRONMENT': 'staging',
            'SERVICE_ID': '$(whoami | tr -d "\\n")',  # Command with pipes and special chars
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, problematic_env):
            service_id = AuthConfig.get_service_id()
            
            # Check for invalid characters that would cause auth issues
            invalid_chars = ['$', '(', ')', '|', '"', '\\', '\n', '\t']
            
            for invalid_char in invalid_chars:
                if invalid_char in service_id:
                    pytest.fail(f"Service ID contains invalid character '{invalid_char}': {service_id}")
            
            # Should not be the literal command
            literal_cmd = '$(whoami | tr -d "\\n")'
            if service_id == literal_cmd:
                pytest.fail(f"Service ID is literal shell command: {service_id}")
            
            logger.error(f"Invalid characters test - Service ID: '{service_id}'")


@env("staging")
class TestServiceIDEnvironmentProcessing:
    """Test environment variable processing for Service ID configuration."""
    
    def test_service_id_environment_variable_expansion_failure(self):
        """FAILING TEST: Tests environment variable expansion failures in SERVICE_ID.
        
        Environment variables within SERVICE_ID might not be expanded properly,
        causing literal variable references to remain.
        """
        expansion_env = {
            'ENVIRONMENT': 'staging',
            'INSTANCE_ID': 'auth-instance-001',
            'REGION': 'us-central1',
            'SERVICE_ID': '${INSTANCE_ID}-${REGION}',  # Should expand to "auth-instance-001-us-central1"
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, expansion_env):
            service_id = AuthConfig.get_service_id()
            
            # Should not contain literal variable references
            if '${INSTANCE_ID}' in service_id:
                pytest.fail(f"Service ID contains unexpanded variable ${{INSTANCE_ID}}: {service_id}")
            
            if '${REGION}' in service_id:
                pytest.fail(f"Service ID contains unexpanded variable ${{REGION}}: {service_id}")
            
            # Should not be the literal template
            if service_id == '${INSTANCE_ID}-${REGION}':
                pytest.fail(f"Service ID is unexpanded template: {service_id}")
            
            logger.error(f"Environment expansion test - Service ID: {service_id}")
    
    def test_service_id_nested_environment_variable_failure(self):
        """FAILING TEST: Tests nested environment variable processing failures.
        
        Complex nested variable references might not be processed correctly.
        """
        nested_env = {
            'ENVIRONMENT': 'staging',
            'BASE_SERVICE': 'netra-auth',
            'ENV_SUFFIX': 'staging',
            'SERVICE_ID': '$(echo "${BASE_SERVICE}-${ENV_SUFFIX}")',  # Nested variables in command
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, nested_env):
            service_id = AuthConfig.get_service_id()
            
            # Should not contain the literal command with nested variables
            literal_nested_cmd = '$(echo "${BASE_SERVICE}-${ENV_SUFFIX}")'
            if service_id == literal_nested_cmd:
                pytest.fail(f"Service ID shows literal nested command: {service_id}")
            
            # Should not contain unprocessed nested variables
            if '${BASE_SERVICE}' in service_id or '${ENV_SUFFIX}' in service_id:
                pytest.fail(f"Service ID contains unprocessed nested variables: {service_id}")
            
            logger.error(f"Nested environment variable test - Service ID: {service_id}")
    
    def test_service_id_cloud_run_metadata_command_failure(self):
        """FAILING TEST: Tests Cloud Run metadata command failures in SERVICE_ID.
        
        In Cloud Run, SERVICE_ID might try to use metadata service commands that
        fail in the container environment.
        """
        cloud_run_env = {
            'ENVIRONMENT': 'staging',
            'K_SERVICE': 'netra-auth-staging',
            'K_REVISION': 'netra-auth-staging-001',
            # This command would work in Cloud Run but might fail during initialization
            'SERVICE_ID': '$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/id)',
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, cloud_run_env):
            service_id = AuthConfig.get_service_id()
            
            # Should not be the literal curl command
            curl_command = '$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/id)'
            if service_id == curl_command:
                pytest.fail(f"Service ID shows literal Cloud Run metadata command: {service_id}")
            
            # Should not contain curl command remnants
            if 'curl' in service_id or 'metadata' in service_id:
                pytest.fail(f"Service ID contains curl command remnants: {service_id}")
            
            logger.error(f"Cloud Run metadata command test - Service ID: {service_id}")


@env("staging")
class TestServiceIDValidation:
    """Test Service ID validation and format requirements."""
    
    def test_service_id_format_validation_with_shell_artifacts(self):
        """FAILING TEST: Tests Service ID format validation when shell artifacts are present.
        
        Service IDs with shell artifacts should fail validation checks.
        """
        # Test various malformed Service IDs that could result from shell processing failures
        malformed_service_ids = [
            '$(whoami)',                    # Literal shell command
            'user-$(hostname',              # Incomplete shell command
            'auth-${USER',                  # Incomplete variable expansion  
            'service`hostname`',            # Backtick command
            'auth-$(echo hello',            # Unclosed shell command
            'service-\nname',               # Contains newline
            'auth-\t-service',              # Contains tab
            'service-name$',                # Ends with dollar
            '',                             # Empty string
            '   ',                          # Only whitespace
        ]
        
        for malformed_id in malformed_service_ids:
            test_env = {
                'ENVIRONMENT': 'staging',
                'SERVICE_ID': malformed_id,
                'AUTH_FAST_TEST_MODE': 'false'
            }
            
            with patch.dict(os.environ, test_env):
                # The current implementation might not properly validate these
                try:
                    service_id = AuthConfig.get_service_id()
                    
                    # If we get the malformed ID back, validation is not working
                    if service_id == malformed_id:
                        pytest.fail(f"Service ID validation failed for malformed ID: '{malformed_id}'")
                    
                    # Check for shell artifacts in the result
                    shell_artifacts = ['$', '`', '(', ')', '{', '}', '\n', '\t']
                    for artifact in shell_artifacts:
                        if artifact in service_id:
                            pytest.fail(f"Service ID contains shell artifact '{artifact}' from input '{malformed_id}': '{service_id}'")
                    
                    logger.warning(f"Malformed Service ID '{malformed_id}' -> '{service_id}'")
                    
                except ValueError as e:
                    # If it raises ValueError, that's expected for malformed IDs
                    logger.info(f"Correctly rejected malformed Service ID '{malformed_id}': {e}")
    
    def test_service_id_length_validation_with_expanded_commands(self):
        """FAILING TEST: Tests Service ID length limits when shell commands expand to long values.
        
        Shell commands might expand to very long strings that exceed reasonable limits.
        """
        long_expansion_env = {
            'ENVIRONMENT': 'staging',
            'LONG_VALUE': 'a' * 200,  # Very long value
            'SERVICE_ID': '$(echo "${LONG_VALUE}-${LONG_VALUE}-${LONG_VALUE}")',  # Would be 600+ chars
            'AUTH_FAST_TEST_MODE': 'false'
        }
        
        with patch.dict(os.environ, long_expansion_env):
            try:
                service_id = AuthConfig.get_service_id()
                
                # If shell command executed, result would be very long
                if len(service_id) > 255:  # Reasonable limit for service IDs
                    pytest.fail(f"Service ID too long from shell expansion: {len(service_id)} chars")
                
                # If it's the literal command, that's also a problem
                literal_cmd = '$(echo "${LONG_VALUE}-${LONG_VALUE}-${LONG_VALUE}")'
                if service_id == literal_cmd:
                    pytest.fail(f"Service ID is literal long shell command: {service_id[:50]}...")
                
                logger.warning(f"Long Service ID test result: {len(service_id)} chars")
                
            except ValueError as e:
                # Length validation should catch this
                logger.info(f"Correctly rejected overly long Service ID: {e}")


# Mark all tests as staging-specific integration tests
pytestmark = [pytest.mark.integration, pytest.mark.staging]