# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Test Cloud Run Secret Configuration
# REMOVED_SYNTAX_ERROR: Validates that Cloud Run services have properly configured secrets.

# REMOVED_SYNTAX_ERROR: This test prevents deployment failures due to missing secret name fields in secretKeyRef.
# REMOVED_SYNTAX_ERROR: Issue discovered: 2025-08-29 - All secrets were missing the 'name' field causing startup failures.
# REMOVED_SYNTAX_ERROR: '''
import subprocess
import json
import yaml
from typing import Dict, List, Tuple
from shared.isolated_environment import IsolatedEnvironment


# REMOVED_SYNTAX_ERROR: class CloudRunSecretValidator:
    # REMOVED_SYNTAX_ERROR: """Validates Cloud Run service secret configurations."""

    # REMOVED_SYNTAX_ERROR: REQUIRED_BACKEND_SECRETS = [ )
    # REMOVED_SYNTAX_ERROR: "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_USER", "POSTGRES_PASSWORD",
    # REMOVED_SYNTAX_ERROR: "JWT_SECRET_KEY", "SECRET_KEY", "OPENAI_API_KEY",
    # REMOVED_SYNTAX_ERROR: "FERNET_KEY", "REDIS_URL"
    

    # REMOVED_SYNTAX_ERROR: REQUIRED_AUTH_SECRETS = [ )
    # REMOVED_SYNTAX_ERROR: "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
    # REMOVED_SYNTAX_ERROR: "POSTGRES_USER", "POSTGRES_PASSWORD",
    # REMOVED_SYNTAX_ERROR: "JWT_SECRET_KEY", "JWT_SECRET",
    # REMOVED_SYNTAX_ERROR: "SERVICE_SECRET", "SERVICE_ID"
    

    # REMOVED_SYNTAX_ERROR: SERVICE_MAPPINGS = { )
    # REMOVED_SYNTAX_ERROR: "backend": "netra-backend-staging",
    # REMOVED_SYNTAX_ERROR: "auth": "netra-auth-service",
    # REMOVED_SYNTAX_ERROR: "frontend": "netra-frontend-staging"
    

# REMOVED_SYNTAX_ERROR: def __init__(self, project: str = "netra-staging", region: str = "us-central1"):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.project = project
    # REMOVED_SYNTAX_ERROR: self.region = region
    # REMOVED_SYNTAX_ERROR: self.errors = []

# REMOVED_SYNTAX_ERROR: def get_service_config(self, service_name: str) -> Dict:
    # REMOVED_SYNTAX_ERROR: """Fetch Cloud Run service configuration."""
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: result = subprocess.run( )
        # REMOVED_SYNTAX_ERROR: "formatted_string"
        # REMOVED_SYNTAX_ERROR: "formatted_string",
        # REMOVED_SYNTAX_ERROR: capture_output=True,
        # REMOVED_SYNTAX_ERROR: text=True,
        # REMOVED_SYNTAX_ERROR: check=True,
        # REMOVED_SYNTAX_ERROR: shell=True
        
        # REMOVED_SYNTAX_ERROR: return json.loads(result.stdout)
        # REMOVED_SYNTAX_ERROR: except subprocess.CalledProcessError as e:
            # REMOVED_SYNTAX_ERROR: self.errors.append("formatted_string")
            # REMOVED_SYNTAX_ERROR: return {}

# REMOVED_SYNTAX_ERROR: def validate_secret_refs(self, config: Dict, service_type: str) -> List[str]:
    # REMOVED_SYNTAX_ERROR: """Validate secretKeyRef configurations have proper name fields."""
    # REMOVED_SYNTAX_ERROR: issues = []

    # Navigate to container env vars
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: containers = config["spec"]["template"]["spec"]["containers"]
        # REMOVED_SYNTAX_ERROR: if not containers:
            # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")
            # REMOVED_SYNTAX_ERROR: return issues

            # REMOVED_SYNTAX_ERROR: env_vars = containers[0].get("env", [])

            # Check required secrets based on service type
            # REMOVED_SYNTAX_ERROR: required_secrets = ( )
            # REMOVED_SYNTAX_ERROR: self.REQUIRED_BACKEND_SECRETS if service_type == "backend"
            # REMOVED_SYNTAX_ERROR: else self.REQUIRED_AUTH_SECRETS if service_type == "auth"
            # REMOVED_SYNTAX_ERROR: else []
            

            # REMOVED_SYNTAX_ERROR: for required_secret in required_secrets:
                # REMOVED_SYNTAX_ERROR: found = False
                # REMOVED_SYNTAX_ERROR: for env_var in env_vars:
                    # REMOVED_SYNTAX_ERROR: if env_var.get("name") == required_secret:
                        # REMOVED_SYNTAX_ERROR: found = True
                        # Check if it has secretKeyRef
                        # REMOVED_SYNTAX_ERROR: if "valueFrom" in env_var:
                            # REMOVED_SYNTAX_ERROR: secret_ref = env_var["valueFrom"].get("secretKeyRe"formatted_string"name"):
                                # REMOVED_SYNTAX_ERROR: expected_name = "formatted_string"
                                # REMOVED_SYNTAX_ERROR: issues.append( )
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                # REMOVED_SYNTAX_ERROR: "formatted_string"
                                
                                # REMOVED_SYNTAX_ERROR: elif not secret_ref.get("key"):
                                    # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: break

                                    # REMOVED_SYNTAX_ERROR: if not found:
                                        # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")

                                        # REMOVED_SYNTAX_ERROR: except KeyError as e:
                                            # REMOVED_SYNTAX_ERROR: issues.append("formatted_string")

                                            # REMOVED_SYNTAX_ERROR: return issues

# REMOVED_SYNTAX_ERROR: def validate_all_services(self) -> Tuple[bool, Dict[str, List[str]]]:
    # REMOVED_SYNTAX_ERROR: """Validate all Cloud Run services."""
    # REMOVED_SYNTAX_ERROR: all_issues = {}

    # REMOVED_SYNTAX_ERROR: for service_type, cloud_run_name in self.SERVICE_MAPPINGS.items():
        # REMOVED_SYNTAX_ERROR: print("formatted_string")

        # REMOVED_SYNTAX_ERROR: config = self.get_service_config(cloud_run_name)
        # REMOVED_SYNTAX_ERROR: if not config:
            # REMOVED_SYNTAX_ERROR: all_issues[service_type] = [f"Could not fetch service configuration"]
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: issues = self.validate_secret_refs(config, service_type)
            # REMOVED_SYNTAX_ERROR: if issues:
                # REMOVED_SYNTAX_ERROR: all_issues[service_type] = issues
                # REMOVED_SYNTAX_ERROR: else:
                    # REMOVED_SYNTAX_ERROR: print("formatted_string")

                    # REMOVED_SYNTAX_ERROR: return len(all_issues) == 0, all_issues

# REMOVED_SYNTAX_ERROR: def generate_fix_commands(self, issues: Dict[str, List[str]]) -> List[str]:
    # REMOVED_SYNTAX_ERROR: """Generate gcloud commands to fix the issues."""
    # REMOVED_SYNTAX_ERROR: fix_commands = []

    # REMOVED_SYNTAX_ERROR: for service_type, service_issues in issues.items():
        # REMOVED_SYNTAX_ERROR: if not service_issues:
            # REMOVED_SYNTAX_ERROR: continue

            # REMOVED_SYNTAX_ERROR: cloud_run_name = self.SERVICE_MAPPINGS[service_type]
            # REMOVED_SYNTAX_ERROR: secrets_to_fix = []

            # REMOVED_SYNTAX_ERROR: for issue in service_issues:
                # REMOVED_SYNTAX_ERROR: if "Missing 'name' field" in issue:
                    # Extract the secret name from the issue
                    # REMOVED_SYNTAX_ERROR: secret_var = issue.split(":")[0]
                    # REMOVED_SYNTAX_ERROR: secret_name = "formatted_string"
                    # REMOVED_SYNTAX_ERROR: secrets_to_fix.append("formatted_string")

                    # REMOVED_SYNTAX_ERROR: if secrets_to_fix:
                        # REMOVED_SYNTAX_ERROR: cmd = ( )
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        # REMOVED_SYNTAX_ERROR: "formatted_string"
                        
                        # REMOVED_SYNTAX_ERROR: fix_commands.append(cmd)

                        # REMOVED_SYNTAX_ERROR: return fix_commands


# REMOVED_SYNTAX_ERROR: def test_cloud_run_secret_configuration():
    # REMOVED_SYNTAX_ERROR: """Test that Cloud Run services have properly configured secrets."""
    # REMOVED_SYNTAX_ERROR: validator = CloudRunSecretValidator()

    # REMOVED_SYNTAX_ERROR: print("=" * 80)
    # REMOVED_SYNTAX_ERROR: print("CLOUD RUN SECRET CONFIGURATION VALIDATION")
    # REMOVED_SYNTAX_ERROR: print("=" * 80)

    # REMOVED_SYNTAX_ERROR: is_valid, issues = validator.validate_all_services()

    # REMOVED_SYNTAX_ERROR: if not is_valid:
        # REMOVED_SYNTAX_ERROR: print(" )
        # REMOVED_SYNTAX_ERROR: [X] VALIDATION FAILED - Issues found:")
        # REMOVED_SYNTAX_ERROR: for service, service_issues in issues.items():
            # REMOVED_SYNTAX_ERROR: print("formatted_string")
            # REMOVED_SYNTAX_ERROR: for issue in service_issues:
                # REMOVED_SYNTAX_ERROR: print("formatted_string")

                # Generate fix commands
                # REMOVED_SYNTAX_ERROR: fix_commands = validator.generate_fix_commands(issues)
                # REMOVED_SYNTAX_ERROR: if fix_commands:
                    # REMOVED_SYNTAX_ERROR: print(" )
                    # REMOVED_SYNTAX_ERROR: [FIX] COMMANDS:")
                    # REMOVED_SYNTAX_ERROR: for cmd in fix_commands:
                        # REMOVED_SYNTAX_ERROR: print("formatted_string")

                        # Fail the test
                        # REMOVED_SYNTAX_ERROR: assert False, "formatted_string"
                        # REMOVED_SYNTAX_ERROR: else:
                            # REMOVED_SYNTAX_ERROR: print(" )
                            # REMOVED_SYNTAX_ERROR: [OK] All services have properly configured secrets")
                            # REMOVED_SYNTAX_ERROR: return True


                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                # Run the validation
                                # REMOVED_SYNTAX_ERROR: try:
                                    # REMOVED_SYNTAX_ERROR: test_cloud_run_secret_configuration()
                                    # REMOVED_SYNTAX_ERROR: print(" )
                                    # REMOVED_SYNTAX_ERROR: [OK] All validations passed!")
                                    # REMOVED_SYNTAX_ERROR: except AssertionError as e:
                                        # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                        # REMOVED_SYNTAX_ERROR: exit(1)
                                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                                            # REMOVED_SYNTAX_ERROR: print("formatted_string")
                                            # REMOVED_SYNTAX_ERROR: exit(1)
                                            # REMOVED_SYNTAX_ERROR: pass