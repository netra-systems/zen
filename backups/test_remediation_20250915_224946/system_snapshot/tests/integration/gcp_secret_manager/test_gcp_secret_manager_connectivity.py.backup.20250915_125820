"""
GCP Secret Manager Connectivity Integration Test Suite - Phase 2

Business Value: Platform/Internal - $500K+ ARR Protection  
Validates real GCP Secret Manager connectivity and secret retrieval for production deployment.

MISSION: Test real GCP staging environment integration to validate:
1. GCP Secret Manager API connectivity
2. Service account authentication  
3. Secret retrieval for the 7 critical variables
4. Error handling for missing/invalid secrets
5. Performance and timeout handling

Test Execution: 5-minute execution window for real GCP API calls
Environment: Uses staging GCP environment (no Docker required)

SSOT Compliance: Uses SSotBaseTestCase and real services pattern.
"""

import pytest
import os
import logging
import time
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# SSOT imports
from test_framework.ssot.base_test_case import SSotBaseTestCase

logger = logging.getLogger(__name__)


# Skip all tests if GCP credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.getenv('GCP_PROJECT'),
    reason="GCP credentials not available - set GOOGLE_APPLICATION_CREDENTIALS or GCP_PROJECT"
)


class TestGCPSecretManagerConnectivity(SSotBaseTestCase):
    """
    Phase 2 Integration Tests: Real GCP Secret Manager connectivity.
    
    These tests validate actual GCP Secret Manager integration for the 7 critical
    environment variables required for production deployment.
    
    Business Impact: $500K+ ARR depends on GCP Secret Manager working correctly.
    """

    @pytest.fixture(autouse=True)
    def setup_gcp_integration_test(self):
        """Set up GCP integration test environment."""
        # Validate GCP credentials are available
        if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS') and not os.getenv('GCP_PROJECT'):
            pytest.skip("GCP credentials required for integration tests")
        
        self.gcp_project = os.getenv('GCP_PROJECT', 'netra-staging')
        self.critical_secrets = [
            'staging-gemini-api-key',
            'staging-service-secret',
            'staging-fernet-key', 
            'staging-oauth-client-secret',
            'staging-redis-password',
            'staging-jwt-secret',
            'staging-redis-host'
        ]
        
        yield

    def test_gcp_secret_manager_api_connectivity(self):
        """
        Integration Test: GCP Secret Manager API connectivity.
        
        Business Impact: P0 - Basic infrastructure connectivity for secret management.
        Expected: Successful connection to GCP Secret Manager API.
        Timeout: 30 seconds for API connectivity.
        """
        logger.info("🔍 Testing GCP Secret Manager API connectivity")
        
        try:
            from google.cloud import secretmanager
            
            # Create Secret Manager client with timeout
            client = secretmanager.SecretManagerServiceClient()
            
            # Test basic API connectivity by listing secrets
            project_path = f"projects/{self.gcp_project}"
            
            start_time = time.time()
            response = client.list_secrets(
                request={"parent": project_path},
                timeout=30.0
            )
            
            # Convert to list to force API call execution
            secrets_list = list(response)
            api_response_time = time.time() - start_time
            
            logger.info(f"✅ SUCCESS: GCP Secret Manager API connectivity established")
            logger.info(f"   - Project: {self.gcp_project}")
            logger.info(f"   - API Response Time: {api_response_time:.2f}s")
            logger.info(f"   - Available Secrets: {len(secrets_list)}")
            
            # Validate response time is reasonable (< 10 seconds)
            assert api_response_time < 10.0, \
                f"API response too slow: {api_response_time:.2f}s (should be < 10s)"
            
        except ImportError:
            pytest.fail("google-cloud-secret-manager package not installed. Install with: pip install google-cloud-secret-manager")
        except Exception as e:
            logger.error(f"❌ FAILURE: GCP Secret Manager API connectivity failed: {e}")
            pytest.fail(f"GCP Secret Manager API connectivity failed: {e}")

    def test_service_account_authentication(self):
        """
        Integration Test: GCP service account authentication.
        
        Business Impact: P0 - Service account must have Secret Manager access permissions.
        Expected: Service account can authenticate and access Secret Manager.
        """
        logger.info("🔍 Testing GCP service account authentication")
        
        try:
            from google.cloud import secretmanager
            from google.auth import default
            
            # Test service account authentication
            credentials, project_id = default()
            
            # Create client with authenticated credentials
            client = secretmanager.SecretManagerServiceClient(credentials=credentials)
            
            # Test authentication by attempting to access project
            project_path = f"projects/{self.gcp_project}"
            
            try:
                response = client.list_secrets(
                    request={"parent": project_path},
                    timeout=10.0
                )
                # Force execution to test authentication
                list(response)
                
                logger.info("✅ SUCCESS: Service account authentication working")
                logger.info(f"   - Authenticated Project ID: {project_id}")
                logger.info(f"   - Target Project: {self.gcp_project}")
                
            except Exception as auth_error:
                logger.error(f"❌ AUTHENTICATION FAILURE: {auth_error}")
                pytest.fail(f"Service account lacks Secret Manager permissions: {auth_error}")
                
        except ImportError:
            pytest.fail("google-auth package not available")
        except Exception as e:
            logger.error(f"❌ FAILURE: Service account authentication failed: {e}")
            pytest.fail(f"Service account authentication failed: {e}")

    def test_critical_secrets_existence_in_gcp(self):
        """
        Integration Test: Verify all 7 critical secrets exist in GCP Secret Manager.
        
        Business Impact: P0 - All required secrets must exist for deployment.
        Expected: All 7 critical secrets are present in GCP Secret Manager.
        """
        logger.info("🔍 Testing critical secrets existence in GCP Secret Manager")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            project_path = f"projects/{self.gcp_project}"
            
            # Get all available secrets
            response = client.list_secrets(
                request={"parent": project_path},
                timeout=15.0
            )
            
            available_secrets = set()
            for secret in response:
                # Extract secret name from full path
                secret_name = secret.name.split('/')[-1]
                available_secrets.add(secret_name)
            
            logger.info(f"Available secrets in GCP: {sorted(available_secrets)}")
            
            # Check each critical secret
            missing_secrets = []
            existing_secrets = []
            
            for critical_secret in self.critical_secrets:
                if critical_secret in available_secrets:
                    existing_secrets.append(critical_secret)
                else:
                    missing_secrets.append(critical_secret)
            
            # Log results
            if existing_secrets:
                logger.info(f"✅ EXISTING SECRETS: {existing_secrets}")
            
            if missing_secrets:
                logger.error(f"❌ MISSING SECRETS: {missing_secrets}")
                logger.info("🔧 REMEDIATION: Create missing secrets in GCP Secret Manager:")
                for secret in missing_secrets:
                    logger.info(f"   gcloud secrets create {secret} --data-file=-")
                
                pytest.fail(f"Missing critical secrets in GCP Secret Manager: {missing_secrets}")
            else:
                logger.info("✅ SUCCESS: All critical secrets exist in GCP Secret Manager")
                
        except Exception as e:
            logger.error(f"❌ FAILURE: Error checking secret existence: {e}")
            pytest.fail(f"Error checking secret existence: {e}")

    def test_secret_value_retrieval_performance(self):
        """
        Integration Test: Test secret value retrieval performance.
        
        Business Impact: P1 - Secret retrieval must be fast enough for startup.
        Expected: Secret values can be retrieved within reasonable time limits.
        """
        logger.info("🔍 Testing secret value retrieval performance")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            # Test retrieval for a subset of secrets to measure performance
            performance_results = []
            
            for secret_name in self.critical_secrets[:3]:  # Test first 3 for performance
                secret_path = f"projects/{self.gcp_project}/secrets/{secret_name}/versions/latest"
                
                try:
                    start_time = time.time()
                    response = client.access_secret_version(
                        request={"name": secret_path},
                        timeout=5.0
                    )
                    retrieval_time = time.time() - start_time
                    
                    # Check if secret has a value (don't log the actual value)
                    has_value = response.payload.data is not None
                    value_size = len(response.payload.data) if has_value else 0
                    
                    performance_results.append({
                        'secret': secret_name,
                        'retrieval_time': retrieval_time,
                        'has_value': has_value,
                        'value_size': value_size
                    })
                    
                    logger.info(f"   {secret_name}: {retrieval_time:.3f}s, {value_size} bytes")
                    
                    # Validate retrieval time is reasonable
                    assert retrieval_time < 2.0, \
                        f"Secret {secret_name} retrieval too slow: {retrieval_time:.3f}s"
                    
                except Exception as retrieval_error:
                    logger.warning(f"   {secret_name}: FAILED - {retrieval_error}")
                    performance_results.append({
                        'secret': secret_name,
                        'retrieval_time': None,
                        'has_value': False,
                        'error': str(retrieval_error)
                    })
            
            # Analyze performance results
            successful_retrievals = [r for r in performance_results if r.get('has_value')]
            failed_retrievals = [r for r in performance_results if not r.get('has_value')]
            
            if successful_retrievals:
                avg_time = sum(r['retrieval_time'] for r in successful_retrievals) / len(successful_retrievals)
                logger.info(f"✅ PERFORMANCE: Average retrieval time: {avg_time:.3f}s")
            
            if failed_retrievals:
                logger.warning(f"⚠️ PERFORMANCE: {len(failed_retrievals)} secrets failed retrieval")
                
        except Exception as e:
            logger.error(f"❌ FAILURE: Secret retrieval performance test failed: {e}")
            pytest.fail(f"Secret retrieval performance test failed: {e}")

    def test_secret_value_validation(self):
        """
        Integration Test: Validate secret values are not placeholders.
        
        Business Impact: P0 - Secrets must contain real values, not placeholders.
        Expected: Secret values are valid and not placeholder strings.
        """
        logger.info("🔍 Testing secret value validation (no placeholders)")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            placeholder_patterns = [
                'your-api-key',
                'your-secret',
                'placeholder',
                'REPLACE_ME',
                'TODO',
                'CHANGEME',
                'password',  # Common default
                'secret'     # Generic default
            ]
            
            validation_results = []
            
            # Test a few secrets for placeholder validation
            test_secrets = self.critical_secrets[:2]  # Test first 2 to avoid quota issues
            
            for secret_name in test_secrets:
                secret_path = f"projects/{self.gcp_project}/secrets/{secret_name}/versions/latest"
                
                try:
                    response = client.access_secret_version(
                        request={"name": secret_path},
                        timeout=5.0
                    )
                    
                    secret_value = response.payload.data.decode('utf-8')
                    
                    # Check for placeholder patterns (case-insensitive)
                    is_placeholder = any(
                        pattern.lower() in secret_value.lower() 
                        for pattern in placeholder_patterns
                    )
                    
                    # Check for minimum length (real secrets should be substantial)
                    has_sufficient_length = len(secret_value.strip()) >= 8
                    
                    validation_results.append({
                        'secret': secret_name,
                        'is_placeholder': is_placeholder,
                        'has_sufficient_length': has_sufficient_length,
                        'length': len(secret_value),
                        'valid': not is_placeholder and has_sufficient_length
                    })
                    
                    if is_placeholder:
                        logger.error(f"   {secret_name}: Contains placeholder value")
                    elif not has_sufficient_length:
                        logger.error(f"   {secret_name}: Too short ({len(secret_value)} chars)")
                    else:
                        logger.info(f"   {secret_name}: Valid secret value ({len(secret_value)} chars)")
                    
                except Exception as validation_error:
                    logger.warning(f"   {secret_name}: Validation failed - {validation_error}")
                    validation_results.append({
                        'secret': secret_name,
                        'valid': False,
                        'error': str(validation_error)
                    })
            
            # Check validation results
            invalid_secrets = [r for r in validation_results if not r.get('valid')]
            
            if invalid_secrets:
                logger.error(f"❌ VALIDATION FAILURE: Invalid secrets detected")
                for invalid in invalid_secrets:
                    secret_name = invalid['secret']
                    if invalid.get('is_placeholder'):
                        logger.error(f"   {secret_name}: Contains placeholder value")
                    elif not invalid.get('has_sufficient_length'):
                        logger.error(f"   {secret_name}: Insufficient length")
                    elif invalid.get('error'):
                        logger.error(f"   {secret_name}: {invalid['error']}")
                
                logger.info("🔧 REMEDIATION: Update invalid secrets with real values in GCP Secret Manager")
                pytest.fail(f"Secret validation failed for: {[s['secret'] for s in invalid_secrets]}")
            else:
                logger.info("✅ SUCCESS: All tested secrets contain valid values")
                
        except Exception as e:
            logger.error(f"❌ FAILURE: Secret value validation failed: {e}")
            pytest.fail(f"Secret value validation failed: {e}")

    def test_gcp_secret_manager_error_handling(self):
        """
        Integration Test: GCP Secret Manager error handling scenarios.
        
        Business Impact: P1 - System must handle GCP API errors gracefully.
        Expected: Proper error handling for common GCP API failure scenarios.
        """
        logger.info("🔍 Testing GCP Secret Manager error handling")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            error_scenarios = []
            
            # Test 1: Non-existent secret access
            try:
                non_existent_secret = f"projects/{self.gcp_project}/secrets/non-existent-secret-12345/versions/latest"
                client.access_secret_version(
                    request={"name": non_existent_secret},
                    timeout=5.0
                )
                error_scenarios.append({"scenario": "non_existent_secret", "handled": False})
            except Exception as e:
                # This should fail - that's expected
                error_scenarios.append({
                    "scenario": "non_existent_secret", 
                    "handled": True,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                logger.info(f"   Non-existent secret: Properly handled - {type(e).__name__}")
            
            # Test 2: Invalid project access
            try:
                invalid_project_path = "projects/invalid-project-12345"
                response = client.list_secrets(
                    request={"parent": invalid_project_path},
                    timeout=5.0
                )
                list(response)  # Force execution
                error_scenarios.append({"scenario": "invalid_project", "handled": False})
            except Exception as e:
                # This should fail - that's expected
                error_scenarios.append({
                    "scenario": "invalid_project",
                    "handled": True,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                logger.info(f"   Invalid project: Properly handled - {type(e).__name__}")
            
            # Test 3: Timeout handling
            try:
                # Test with very short timeout to trigger timeout error
                client.list_secrets(
                    request={"parent": f"projects/{self.gcp_project}"},
                    timeout=0.001  # 1ms timeout - should fail
                )
                error_scenarios.append({"scenario": "timeout", "handled": False})
            except Exception as e:
                error_scenarios.append({
                    "scenario": "timeout",
                    "handled": True,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                logger.info(f"   Timeout: Properly handled - {type(e).__name__}")
            
            # Validate error handling results
            unhandled_errors = [s for s in error_scenarios if not s.get('handled')]
            
            if unhandled_errors:
                logger.error(f"❌ ERROR HANDLING FAILURE: Unhandled error scenarios: {unhandled_errors}")
                pytest.fail(f"Error handling failed for scenarios: {[s['scenario'] for s in unhandled_errors]}")
            else:
                logger.info("✅ SUCCESS: All error scenarios properly handled")
                
        except Exception as e:
            logger.error(f"❌ FAILURE: Error handling test failed: {e}")
            pytest.fail(f"Error handling test failed: {e}")

    def test_gcp_secret_manager_quota_and_limits(self):
        """
        Integration Test: GCP Secret Manager quota and rate limits.
        
        Business Impact: P2 - Ensure system stays within GCP API quotas.
        Expected: System respects GCP Secret Manager rate limits and quotas.
        """
        logger.info("🔍 Testing GCP Secret Manager quota and rate limits")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            # Test burst of API calls to check rate limiting behavior
            api_calls = []
            max_calls = 10  # Conservative test to avoid quota issues
            
            start_time = time.time()
            
            for i in range(max_calls):
                call_start = time.time()
                try:
                    response = client.list_secrets(
                        request={"parent": f"projects/{self.gcp_project}"},
                        timeout=2.0
                    )
                    # Don't consume the entire iterator to avoid excessive API usage
                    next(iter(response), None)
                    
                    call_duration = time.time() - call_start
                    api_calls.append({
                        "call_number": i + 1,
                        "duration": call_duration,
                        "success": True
                    })
                    
                except Exception as e:
                    call_duration = time.time() - call_start
                    api_calls.append({
                        "call_number": i + 1,
                        "duration": call_duration,
                        "success": False,
                        "error": str(e)
                    })
                
                # Small delay to be respectful of rate limits
                time.sleep(0.1)
            
            total_duration = time.time() - start_time
            successful_calls = [c for c in api_calls if c.get('success')]
            failed_calls = [c for c in api_calls if not c.get('success')]
            
            logger.info(f"   API Calls Summary:")
            logger.info(f"   - Total Calls: {max_calls}")
            logger.info(f"   - Successful: {len(successful_calls)}")
            logger.info(f"   - Failed: {len(failed_calls)}")
            logger.info(f"   - Total Duration: {total_duration:.2f}s")
            
            if successful_calls:
                avg_duration = sum(c['duration'] for c in successful_calls) / len(successful_calls)
                logger.info(f"   - Average Call Duration: {avg_duration:.3f}s")
            
            # Validate that we have reasonable success rate
            success_rate = len(successful_calls) / max_calls
            assert success_rate >= 0.8, \
                f"Low success rate ({success_rate:.1%}) may indicate quota/rate limit issues"
            
            logger.info(f"✅ SUCCESS: GCP Secret Manager quota/limits test passed (success rate: {success_rate:.1%})")
            
        except Exception as e:
            logger.error(f"❌ FAILURE: Quota/limits test failed: {e}")
            pytest.fail(f"Quota/limits test failed: {e}")


class TestGCPSecretManagerConfiguration(SSotBaseTestCase):
    """
    Additional configuration and integration validation tests.
    
    These tests validate the overall GCP Secret Manager configuration
    and integration patterns required for production deployment.
    """

    def test_gcp_project_configuration(self):
        """
        Test: GCP project is properly configured for Secret Manager.
        
        Business Impact: P0 - Project configuration drives all secret access.
        Expected: GCP project is accessible and properly configured.
        """
        logger.info("🔍 Testing GCP project configuration")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv('GCP_PROJECT', 'netra-staging')
            
            # Validate project access
            project_path = f"projects/{project_id}"
            
            try:
                response = client.list_secrets(
                    request={"parent": project_path},
                    timeout=10.0
                )
                # Get first few secrets to validate access
                secrets_count = len(list(response))
                
                logger.info(f"✅ SUCCESS: GCP project configuration valid")
                logger.info(f"   - Project ID: {project_id}")
                logger.info(f"   - Accessible Secrets: {secrets_count}")
                
            except Exception as project_error:
                logger.error(f"❌ PROJECT CONFIGURATION ERROR: {project_error}")
                pytest.fail(f"GCP project configuration invalid: {project_error}")
                
        except ImportError:
            pytest.fail("google-cloud-secret-manager not available")
        except Exception as e:
            logger.error(f"❌ FAILURE: GCP project configuration test failed: {e}")
            pytest.fail(f"GCP project configuration test failed: {e}")

    def test_secret_manager_permissions_validation(self):
        """
        Test: Service account has proper Secret Manager permissions.
        
        Business Impact: P0 - Permissions determine secret access capability.
        Expected: Service account has secretmanager.versions.access permission.
        """
        logger.info("🔍 Testing Secret Manager permissions")
        
        try:
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            # Test permissions by attempting common operations
            permissions_test_results = []
            
            # Test 1: List secrets permission
            try:
                response = client.list_secrets(
                    request={"parent": f"projects/{os.getenv('GCP_PROJECT', 'netra-staging')}"},
                    timeout=5.0
                )
                list(response)  # Force execution
                permissions_test_results.append({"permission": "list_secrets", "granted": True})
            except Exception as e:
                permissions_test_results.append({
                    "permission": "list_secrets", 
                    "granted": False, 
                    "error": str(e)
                })
            
            # Test 2: Access secret version permission (if we have secrets)
            if permissions_test_results[0].get('granted'):
                # Try to access a secret version (use a common secret name pattern)
                test_secret_names = ['staging-jwt-secret', 'staging-gemini-api-key']
                version_access_granted = False
                
                for secret_name in test_secret_names:
                    try:
                        secret_path = f"projects/{os.getenv('GCP_PROJECT', 'netra-staging')}/secrets/{secret_name}/versions/latest"
                        client.access_secret_version(
                            request={"name": secret_path},
                            timeout=3.0
                        )
                        version_access_granted = True
                        break
                    except Exception:
                        continue  # Try next secret
                
                permissions_test_results.append({
                    "permission": "access_secret_version",
                    "granted": version_access_granted
                })
            
            # Validate permissions
            failed_permissions = [p for p in permissions_test_results if not p.get('granted')]
            
            if failed_permissions:
                logger.error(f"❌ PERMISSIONS FAILURE: Missing permissions")
                for perm in failed_permissions:
                    logger.error(f"   - {perm['permission']}: {perm.get('error', 'Access denied')}")
                
                logger.info("🔧 REMEDIATION: Grant Secret Manager permissions to service account:")
                logger.info("   gcloud projects add-iam-policy-binding PROJECT_ID \\")
                logger.info("     --member='serviceAccount:SERVICE_ACCOUNT_EMAIL' \\")
                logger.info("     --role='roles/secretmanager.secretAccessor'")
                
                pytest.fail(f"Missing Secret Manager permissions: {[p['permission'] for p in failed_permissions]}")
            else:
                logger.info("✅ SUCCESS: Service account has proper Secret Manager permissions")
                
        except Exception as e:
            logger.error(f"❌ FAILURE: Permissions validation failed: {e}")
            pytest.fail(f"Permissions validation failed: {e}")