"""Test comprehensive environment configuration issues found in staging.



These tests validate all critical environment variables and configuration

settings that are required for proper staging operation but may be missing

or incorrectly configured.



Based on staging audit findings:

- Missing or incorrect environment variables

- Configuration inconsistencies between services  

- Environment-specific settings not properly configured for staging

"""



import pytest

import os

import asyncio

import json

from typing import Dict, List, Optional, Any

from test_framework.environment_markers import staging_only, env_requires

from shared.isolated_environment import IsolatedEnvironment



from shared.isolated_environment import get_env





class TestEnvironmentConfiguration:

    """Test comprehensive environment configuration issues in staging."""



    @staging_only

    @pytest.mark.e2e

    def test_critical_environment_variables_missing(self):

        """Test that critical environment variables are missing from staging.

        

        This test SHOULD FAIL, demonstrating that required environment

        variables for staging operation are not set or configured incorrectly.

        

        Expected failure: Multiple required environment variables missing

        """

        # Critical environment variables required for staging

        critical_env_vars = {

            # Database configuration

            "DATABASE_URL": {

                "required": True,

                "description": "Main database connection string",

                "example": "postgresql://user:pass@host:5432/db"

            },

            "STAGING_DATABASE_URL": {

                "required": True, 

                "description": "Staging-specific database URL",

                "example": "postgresql://staging_user:pass@staging-host:5432/staging_db"

            },

            

            # Authentication & Security

            "SECRET_KEY": {

                "required": True,

                "description": "JWT/session secret key (min 32 chars)",

                "min_length": 32

            },

            "JWT_SECRET": {

                "required": True,

                "description": "JWT signing secret",

                "min_length": 32

            },

            

            # OAuth Configuration

            "GOOGLE_CLIENT_ID": {

                "required": True,

                "description": "Google OAuth client ID",

                "pattern": "*.apps.googleusercontent.com"

            },

            "GOOGLE_CLIENT_SECRET": {

                "required": True,

                "description": "Google OAuth client secret",

                "min_length": 20

            },

            

            # Service URLs

            "BACKEND_URL": {

                "required": True,

                "description": "Backend service URL",

                "example": "https://api.staging.netrasystems.ai"

            },

            "AUTH_SERVICE_URL": {

                "required": True,

                "description": "Authentication service URL", 

                "example": "https://auth.staging.netrasystems.ai"

            },

            "FRONTEND_URL": {

                "required": True,

                "description": "Frontend application URL",

                "example": "https://staging.netrasystems.ai"

            },

            

            # Environment identification

            "ENVIRONMENT": {

                "required": True,

                "description": "Environment identifier",

                "expected": "staging"

            }

        }

        

        missing_env_vars = []

        invalid_env_vars = []

        

        for var_name, config in critical_env_vars.items():

            env_value = get_env().get(var_name)

            

            if not env_value:

                missing_env_vars.append({

                    "variable": var_name,

                    "description": config["description"],

                    "required": config["required"],

                    "impact": "Service functionality compromised"

                })

            else:

                # Validate configured values

                if config.get("min_length") and len(env_value) < config["min_length"]:

                    invalid_env_vars.append({

                        "variable": var_name,

                        "issue": f"Value too short (min {config['min_length']} chars)",

                        "actual_length": len(env_value),

                        "value_preview": env_value[:10] + "..." if len(env_value) > 10 else env_value

                    })

                

                if config.get("expected") and env_value != config["expected"]:

                    invalid_env_vars.append({

                        "variable": var_name,

                        "issue": f"Unexpected value",

                        "expected": config["expected"],

                        "actual": env_value

                    })

        

        # This test SHOULD FAIL - expecting missing critical environment variables

        total_config_issues = len(missing_env_vars) + len(invalid_env_vars)

        assert total_config_issues > 0, (

            f"Expected critical environment configuration issues in staging "

            f"(causing service failures), but all {len(critical_env_vars)} "

            f"critical environment variables are properly configured. "

            f"This suggests the environment configuration issues have been resolved."

        )

        

        # Verify we have missing variables specifically (most common staging issue)

        assert len(missing_env_vars) >= 3, (

            f"Expected at least 3 missing critical environment variables "

            f"(typical staging configuration gap), but only {len(missing_env_vars)} missing: "

            f"{[v['variable'] for v in missing_env_vars]}. "

            f"Invalid vars: {[v['variable'] for v in invalid_env_vars]}. "

            f"Staging typically has multiple missing environment variables."

        )



    @staging_only

    @env_requires(services=["backend_service", "auth_service"])

    @pytest.mark.e2e

    def test_service_url_configuration_mismatch(self):

        """Test service URL configuration mismatches between services.

        

        This test should FAIL, showing that services are configured with

        incorrect URLs for communicating with each other in staging.

        """

        # Service URL configuration mapping

        service_url_config = {

            "backend": {

                "env_vars": ["BACKEND_URL", "BACKEND_SERVICE_URL", "API_URL"],

                "expected_patterns": ["staging", "api"],

                "should_contain": ["https://", "staging"]

            },

            "auth": {

                "env_vars": ["AUTH_SERVICE_URL", "AUTH_URL"],

                "expected_patterns": ["staging", "auth"],

                "should_contain": ["https://", "staging"]

            },

            "frontend": {

                "env_vars": ["FRONTEND_URL", "NEXT_PUBLIC_FRONTEND_URL"],

                "expected_patterns": ["staging"],

                "should_contain": ["https://", "staging"]

            }

        }

        

        url_configuration_issues = []

        

        for service, config in service_url_config.items():

            # Find configured URL for this service

            service_url = None

            for env_var in config["env_vars"]:

                if get_env().get(env_var):

                    service_url = get_env().get(env_var)

                    break

            

            if not service_url:

                url_configuration_issues.append({

                    "service": service,

                    "issue": "Service URL not configured",

                    "missing_vars": config["env_vars"],

                    "impact": f"{service} service URL unknown"

                })

                continue

            

            # Validate URL configuration

            for required_content in config["should_contain"]:

                if required_content not in service_url:

                    url_configuration_issues.append({

                        "service": service,

                        "issue": f"URL missing required content: {required_content}",

                        "url": service_url,

                        "expected": f"URL should contain '{required_content}'"

                    })

            

            # Check for localhost/development URLs in staging

            if "localhost" in service_url or "127.0.0.1" in service_url:

                url_configuration_issues.append({

                    "service": service,

                    "issue": "Using localhost URL in staging",

                    "url": service_url,

                    "impact": "Service unreachable from other containers/services"

                })

        

        # Check cross-service URL consistency

        backend_url = get_env().get("BACKEND_URL", "")

        auth_url = get_env().get("AUTH_SERVICE_URL", "")

        

        if backend_url and auth_url:

            # URLs should use same domain/environment

            backend_domain = backend_url.split("//")[1].split("/")[0] if "//" in backend_url else ""

            auth_domain = auth_url.split("//")[1].split("/")[0] if "//" in auth_url else ""

            

            if backend_domain and auth_domain:

                backend_env = "staging" if "staging" in backend_domain else "dev" if "dev" in backend_domain else "unknown"

                auth_env = "staging" if "staging" in auth_domain else "dev" if "dev" in auth_domain else "unknown"

                

                if backend_env != auth_env:

                    url_configuration_issues.append({

                        "issue": "Cross-service environment mismatch",

                        "backend_env": backend_env,

                        "auth_env": auth_env,

                        "backend_domain": backend_domain,

                        "auth_domain": auth_domain,

                        "impact": "Services in different environments cannot communicate"

                    })

        

        # This test SHOULD FAIL - expecting service URL configuration issues

        assert len(url_configuration_issues) > 0, (

            f"Expected service URL configuration mismatches in staging "

            f"(causing inter-service communication failures), but all service URLs "

            f"appear properly configured. Backend: '{backend_url}', Auth: '{auth_url}'. "

            f"This suggests service URL configuration has been corrected."

        )

        

        # Verify we found localhost/development URL issues specifically

        localhost_issues = [

            issue for issue in url_configuration_issues

            if "localhost" in issue.get("issue", "")

        ]

        

        assert len(localhost_issues) >= 1, (

            f"Expected localhost URL configuration issues (common staging problem), "

            f"but got other URL issues: {url_configuration_issues}. "

            f"Localhost URLs are a typical staging configuration mistake."

        )



    @staging_only

    @pytest.mark.e2e

    def test_database_configuration_inconsistent_across_services(self):

        """Test database configuration inconsistencies across services.

        

        This test should FAIL, showing that different services have

        different or conflicting database configuration in staging.

        """

        # Database configuration variables used by different services

        database_config_vars = [

            "DATABASE_URL",

            "STAGING_DATABASE_URL", 

            "POSTGRES_URL",

            "DB_URL",

            "POSTGRES_DATABASE_URL",

            "AUTH_DATABASE_URL",

            "BACKEND_DATABASE_URL"

        ]

        

        # Collect all database configurations

        database_configs = {}

        for var in database_config_vars:

            value = get_env().get(var)

            if value:

                database_configs[var] = {

                    "url": value,

                    "host": self._extract_db_host(value),

                    "database": self._extract_db_name(value),

                    "port": self._extract_db_port(value)

                }

        

        database_consistency_issues = []

        

        # Check if any database configuration exists

        if not database_configs:

            database_consistency_issues.append({

                "issue": "No database configuration found",

                "missing_vars": database_config_vars,

                "impact": "All services will fail to connect to database"

            })

        

        # Check for configuration inconsistencies

        if len(database_configs) > 1:

            # Multiple database configurations - check consistency

            hosts = set(config["host"] for config in database_configs.values() if config["host"])

            databases = set(config["database"] for config in database_configs.values() if config["database"])

            ports = set(config["port"] for config in database_configs.values() if config["port"])

            

            if len(hosts) > 1:

                database_consistency_issues.append({

                    "issue": "Multiple database hosts configured",

                    "hosts": list(hosts),

                    "variables": list(database_configs.keys()),

                    "impact": "Services connecting to different databases"

                })

            

            if len(databases) > 1:

                database_consistency_issues.append({

                    "issue": "Multiple database names configured",

                    "databases": list(databases),

                    "impact": "Services using different databases"

                })

            

            if len(ports) > 1:

                database_consistency_issues.append({

                    "issue": "Multiple database ports configured",

                    "ports": list(ports),

                    "impact": "Port configuration inconsistency"

                })

        

        # Check for development database URLs in staging

        for var, config in database_configs.items():

            url = config["url"]

            if any(dev_indicator in url.lower() for dev_indicator in ["localhost", "127.0.0.1", "dev", "test"]):

                if "staging" not in url.lower():

                    database_consistency_issues.append({

                        "variable": var,

                        "issue": "Development database URL in staging",

                        "url": url[:50] + "...",  # Truncate for security

                        "impact": "Staging using development database"

                    })

        

        # This test SHOULD FAIL - expecting database configuration issues

        assert len(database_consistency_issues) > 0, (

            f"Expected database configuration inconsistencies in staging "

            f"(causing database connection issues), but database configuration "

            f"appears consistent. Configured DBs: {len(database_configs)}, "

            f"Variables: {list(database_configs.keys())}. "

            f"This suggests database configuration has been standardized."

        )

        

        # Verify we found missing database configuration specifically

        missing_db_issues = [

            issue for issue in database_consistency_issues

            if "No database configuration" in issue.get("issue", "")

        ]

        

        if len(database_configs) == 0:

            assert len(missing_db_issues) >= 1, (

                f"Expected missing database configuration to be identified, "

                f"but got other database issues: {database_consistency_issues}. "

                f"Missing database configuration is a critical staging issue."

            )



    @staging_only

    @pytest.mark.e2e

    def test_environment_variable_type_validation_failures(self):

        """Test environment variable type validation failures.

        

        This test should FAIL, showing that environment variables have

        incorrect types or formats that cause runtime validation errors.

        """

        # Environment variables with type requirements

        typed_env_vars = {

            "PORT": {"type": int, "min": 1, "max": 65535, "default": 8000},

            "AUTH_PORT": {"type": int, "min": 1, "max": 65535, "default": 8001},

            "FRONTEND_PORT": {"type": int, "min": 1, "max": 65535, "default": 3000},

            "DATABASE_POOL_SIZE": {"type": int, "min": 1, "max": 100, "default": 10},

            "JWT_EXPIRES_IN": {"type": int, "min": 300, "max": 86400, "default": 3600},

            "DEBUG": {"type": bool, "default": False},

            "STAGING": {"type": bool, "default": True},

            "OAUTH_ENABLED": {"type": bool, "default": True},

            "REDIS_TTL": {"type": int, "min": 60, "max": 86400, "default": 3600},

        }

        

        type_validation_failures = []

        

        for var_name, constraints in typed_env_vars.items():

            env_value_str = get_env().get(var_name)

            

            if not env_value_str:

                # Use default for missing variables

                continue

            

            expected_type = constraints["type"]

            

            # Attempt type conversion

            try:

                if expected_type == bool:

                    # Boolean conversion from string

                    if env_value_str.lower() in ["true", "1", "yes", "on"]:

                        converted_value = True

                    elif env_value_str.lower() in ["false", "0", "no", "off"]:

                        converted_value = False

                    else:

                        raise ValueError(f"Invalid boolean value: {env_value_str}")

                elif expected_type == int:

                    converted_value = int(env_value_str)

                elif expected_type == float:

                    converted_value = float(env_value_str)

                else:

                    converted_value = str(env_value_str)

                

                # Validate range constraints

                if expected_type in [int, float]:

                    if "min" in constraints and converted_value < constraints["min"]:

                        type_validation_failures.append({

                            "variable": var_name,

                            "value": env_value_str,

                            "issue": f"Value {converted_value} below minimum {constraints['min']}",

                            "type": "RANGE_ERROR"

                        })

                    

                    if "max" in constraints and converted_value > constraints["max"]:

                        type_validation_failures.append({

                            "variable": var_name,

                            "value": env_value_str,

                            "issue": f"Value {converted_value} above maximum {constraints['max']}",

                            "type": "RANGE_ERROR"

                        })

                        

            except (ValueError, TypeError) as e:

                type_validation_failures.append({

                    "variable": var_name,

                    "value": env_value_str,

                    "expected_type": expected_type.__name__,

                    "error": str(e),

                    "type": "TYPE_CONVERSION_ERROR"

                })

        

        # Check for common type conversion issues

        common_type_issues = [

            ("PORT", "eight thousand"),  # String instead of number

            ("DEBUG", "True"),           # String "True" instead of boolean true

            ("STAGING", "yes"),          # String "yes" instead of boolean

        ]

        

        for var_name, problematic_value in common_type_issues:

            actual_value = get_env().get(var_name)

            if actual_value == problematic_value:

                type_validation_failures.append({

                    "variable": var_name,

                    "value": actual_value,

                    "issue": "Common type configuration error",

                    "type": "COMMON_MISTAKE"

                })

        

        # This test SHOULD FAIL - expecting type validation failures

        assert len(type_validation_failures) > 0, (

            f"Expected environment variable type validation failures in staging "

            f"(causing runtime configuration errors), but all typed environment "

            f"variables validate correctly. This suggests type configuration "

            f"issues have been resolved."

        )

        

        # Verify we found type conversion errors specifically

        conversion_errors = [

            failure for failure in type_validation_failures

            if failure.get("type") == "TYPE_CONVERSION_ERROR"

        ]

        

        assert len(conversion_errors) >= 1, (

            f"Expected type conversion errors (common staging configuration issue), "

            f"but got other validation failures: {type_validation_failures}. "

            f"Type conversion errors are typical when environment variables "

            f"are set as strings but expected as other types."

        )



    def _extract_db_host(self, db_url: str) -> Optional[str]:

        """Extract database host from connection URL."""

        try:

            # Format: postgresql://user:pass@host:port/db

            if "@" in db_url:

                host_part = db_url.split("@")[1].split("/")[0]

                return host_part.split(":")[0]

        except Exception:

            pass

        return None

    

    def _extract_db_name(self, db_url: str) -> Optional[str]:

        """Extract database name from connection URL."""

        try:

            if "/" in db_url:

                return db_url.split("/")[-1].split("?")[0]

        except Exception:

            pass

        return None

    

    def _extract_db_port(self, db_url: str) -> Optional[str]:

        """Extract database port from connection URL."""

        try:

            if "@" in db_url and ":" in db_url.split("@")[1]:

                host_part = db_url.split("@")[1].split("/")[0]

                if ":" in host_part:

                    return host_part.split(":")[1]

        except Exception:

            pass

        return None



    @staging_only

    @pytest.mark.e2e

    def test_staging_specific_configuration_missing(self):

        """Test staging-specific configuration that should exist but is missing.

        

        This test should FAIL, demonstrating that configuration specific

        to staging environment (vs dev/prod) is not properly set.

        """

        # Staging-specific configuration requirements

        staging_specific_config = {

            "ENVIRONMENT": {

                "expected": "staging",

                "description": "Must explicitly identify staging environment"

            },

            "STAGING_MODE": {

                "expected": "true", 

                "description": "Enable staging-specific features"

            },

            "LOG_LEVEL": {

                "expected": ["DEBUG", "INFO"],

                "description": "Staging should use DEBUG or INFO logging"

            },

            "CORS_ORIGINS": {

                "should_contain": ["staging.netrasystems.ai"],

                "description": "CORS should allow staging domain"

            },

            "ALLOWED_HOSTS": {

                "should_contain": ["staging.netrasystems.ai"],

                "description": "Staging domain should be in allowed hosts"

            }

        }

        

        staging_config_issues = []

        

        for var_name, requirements in staging_specific_config.items():

            env_value = get_env().get(var_name)

            

            if not env_value:

                staging_config_issues.append({

                    "variable": var_name,

                    "issue": "Staging-specific variable not set",

                    "description": requirements["description"],

                    "impact": "Staging environment not properly identified"

                })

                continue

            

            # Check expected values

            if "expected" in requirements:

                expected = requirements["expected"]

                if isinstance(expected, list):

                    if env_value not in expected:

                        staging_config_issues.append({

                            "variable": var_name,

                            "issue": f"Value '{env_value}' not in expected values",

                            "expected": expected,

                            "actual": env_value

                        })

                else:

                    if env_value != expected:

                        staging_config_issues.append({

                            "variable": var_name,

                            "issue": f"Expected '{expected}', got '{env_value}'",

                            "expected": expected,

                            "actual": env_value

                        })

            

            # Check content requirements

            if "should_contain" in requirements:

                required_content = requirements["should_contain"]

                for content in required_content:

                    if content not in env_value:

                        staging_config_issues.append({

                            "variable": var_name,

                            "issue": f"Missing required content: {content}",

                            "value": env_value,

                            "required_content": content

                        })

        

        # Check for production configuration accidentally used in staging

        prod_indicators = ["prod", "production", "live"]

        for var_name in get_env().as_dict():

            env_value = get_env().get(var_name).lower()

            for indicator in prod_indicators:

                if indicator in env_value and "staging" not in env_value:

                    staging_config_issues.append({

                        "variable": var_name,

                        "issue": "Production configuration detected in staging",

                        "value": get_env().get(var_name)[:50],  # Truncate for security

                        "indicator": indicator,

                        "risk": "Staging using production resources"

                    })

        

        # This test SHOULD FAIL - expecting staging-specific configuration issues  

        assert len(staging_config_issues) > 0, (

            f"Expected staging-specific configuration to be missing or incorrect "

            f"(causing environment identification issues), but all staging "

            f"configuration appears proper. This suggests staging configuration "

            f"has been correctly set up."

        )

        

        # Verify environment identification is the primary issue

        env_identification_issues = [

            issue for issue in staging_config_issues

            if issue.get("variable") == "ENVIRONMENT" or "environment" in issue.get("issue", "").lower()

        ]

        

        assert len(env_identification_issues) >= 1, (

            f"Expected ENVIRONMENT variable configuration issues (critical for "

            f"staging identification), but got other staging config issues: "

            f"{staging_config_issues}. Environment identification is fundamental."

        )

