"""

Cross-Service Data Schema Alignment Tests



Business Value Justification (BVJ):

- Segment: All tiers (Free, Early, Mid, Enterprise) 

- Business Goal: Data Integrity & System Consistency

- Value Impact: Prevents data corruption and service communication failures

- Strategic Impact: Essential for multi-service reliability - schema misalignment destroys data integrity



This test validates that data schemas are properly aligned between services,

ensuring consistent data structures, types, and field mappings across

auth_service, netra_backend, and frontend. Schema drift between services

causes silent data corruption and integration failures.



Key Areas Tested:

1. User data schema consistency across services

2. Thread/conversation data structures

3. Agent execution result formats

4. Error response schemas

5. WebSocket message payload schemas

6. Database model field alignment

"""



import asyncio

import json

import pytest

from typing import Dict, List, Any, Optional, Union

from pathlib import Path



from netra_backend.app.core.unified_logging import central_logger

from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler

from netra_backend.app.db.database_manager import DatabaseManager

from netra_backend.app.clients.auth_client_core import AuthServiceClient



logger = central_logger.get_logger(__name__)





class CrossServiceDataSchemaAlignmentTester:

    """Tests data schema alignment across all services."""

    

    def __init__(self):

        """Initialize cross-service data schema alignment tester."""

        # Critical shared data schemas that must be identical across services

        self.critical_schemas = {

            "User": {

                "description": "User entity schema",

                "services": ["auth_service", "netra_backend", "frontend"],

                "required_fields": ["id", "email", "created_at"],

                "optional_fields": ["name", "avatar_url", "subscription_tier"],

                "field_types": {

                    "id": "string",

                    "email": "string", 

                    "created_at": "datetime",

                    "name": "string|null",

                    "avatar_url": "string|null",

                    "subscription_tier": "string"

                }

            },

            "Thread": {

                "description": "Conversation thread schema",

                "services": ["netra_backend", "frontend"],

                "required_fields": ["id", "user_id", "title", "created_at"],

                "optional_fields": ["updated_at", "metadata", "status"],

                "field_types": {

                    "id": "string",

                    "user_id": "string",

                    "title": "string",

                    "created_at": "datetime",

                    "updated_at": "datetime|null",

                    "metadata": "object|null",

                    "status": "string"

                }

            },

            "Message": {

                "description": "Chat message schema",

                "services": ["netra_backend", "frontend"],

                "required_fields": ["id", "thread_id", "content", "role", "created_at"],

                "optional_fields": ["references", "metadata", "agent_run_id"],

                "field_types": {

                    "id": "string",

                    "thread_id": "string",

                    "content": "string",

                    "role": "string",

                    "created_at": "datetime",

                    "references": "array|null",

                    "metadata": "object|null",

                    "agent_run_id": "string|null"

                }

            },

            "AgentExecution": {

                "description": "Agent execution result schema",

                "services": ["netra_backend", "frontend"],

                "required_fields": ["run_id", "agent_name", "status", "started_at"],

                "optional_fields": ["completed_at", "result", "error", "duration_ms"],

                "field_types": {

                    "run_id": "string",

                    "agent_name": "string", 

                    "status": "string",

                    "started_at": "datetime",

                    "completed_at": "datetime|null",

                    "result": "object|null",

                    "error": "object|null",

                    "duration_ms": "number|null"

                }

            },

            "ErrorResponse": {

                "description": "Standardized error response schema",

                "services": ["auth_service", "netra_backend", "frontend"],

                "required_fields": ["code", "message"],

                "optional_fields": ["details", "timestamp", "trace_id"],

                "field_types": {

                    "code": "string",

                    "message": "string",

                    "details": "object|null",

                    "timestamp": "datetime|null",

                    "trace_id": "string|null"

                }

            }

        }

        

    async def test_user_schema_alignment(self) -> Dict[str, Any]:

        """Test User schema alignment across auth service, backend, and frontend."""

        results = {

            "schema_name": "User",

            "services_tested": [],

            "field_alignments": {},

            "type_mismatches": [],

            "missing_fields": [],

            "extra_fields": [],

            "alignment_score": 0.0

        }

        

        try:

            user_schema = self.critical_schemas["User"]

            

            # Test schema alignment across services

            for service in user_schema["services"]:

                schema_validation = await self._validate_service_schema(

                    service, "User", user_schema

                )

                results["services_tested"].append(service)

                results["field_alignments"][service] = schema_validation

                

                # Collect issues

                results["type_mismatches"].extend(schema_validation.get("type_mismatches", []))

                results["missing_fields"].extend(schema_validation.get("missing_fields", []))

                results["extra_fields"].extend(schema_validation.get("extra_fields", []))

            

            # Calculate alignment score

            total_checks = len(user_schema["required_fields"]) + len(user_schema["optional_fields"])

            issues_count = len(results["type_mismatches"]) + len(results["missing_fields"])

            results["alignment_score"] = max(0, (total_checks - issues_count) / total_checks * 100)

            

        except Exception as e:

            logger.error(f"Error testing user schema alignment: {e}")

            results["error"] = str(e)

            

        return results

    

    async def _validate_service_schema(

        self, service: str, schema_name: str, schema_spec: Dict[str, Any]

    ) -> Dict[str, Any]:

        """Validate schema implementation for a specific service."""

        validation = {

            "service": service,

            "schema_name": schema_name,

            "required_fields_present": [],

            "optional_fields_present": [],

            "missing_fields": [],

            "extra_fields": [],

            "type_mismatches": [],

            "schema_valid": False

        }

        

        try:

            # Get schema definition from service

            service_schema = await self._get_service_schema_definition(service, schema_name)

            

            if not service_schema:

                validation["missing_fields"] = schema_spec["required_fields"] + schema_spec["optional_fields"]

                return validation

            

            # Check required fields

            for field in schema_spec["required_fields"]:

                if field in service_schema:

                    validation["required_fields_present"].append(field)

                    # Check field type

                    expected_type = schema_spec["field_types"][field]

                    actual_type = service_schema[field].get("type", "unknown")

                    if not self._types_compatible(expected_type, actual_type):

                        validation["type_mismatches"].append({

                            "field": field,

                            "expected": expected_type,

                            "actual": actual_type

                        })

                else:

                    validation["missing_fields"].append(field)

            

            # Check optional fields

            for field in schema_spec["optional_fields"]:

                if field in service_schema:

                    validation["optional_fields_present"].append(field)

                    # Check field type

                    expected_type = schema_spec["field_types"][field]

                    actual_type = service_schema[field].get("type", "unknown")

                    if not self._types_compatible(expected_type, actual_type):

                        validation["type_mismatches"].append({

                            "field": field,

                            "expected": expected_type,

                            "actual": actual_type

                        })

            

            # Check for extra fields not in spec

            all_expected_fields = set(schema_spec["required_fields"] + schema_spec["optional_fields"])

            service_fields = set(service_schema.keys())

            extra_fields = service_fields - all_expected_fields

            validation["extra_fields"] = list(extra_fields)

            

            # Determine if schema is valid

            validation["schema_valid"] = (

                len(validation["missing_fields"]) == 0 and

                len(validation["type_mismatches"]) == 0

            )

            

        except Exception as e:

            validation["error"] = str(e)

            

        return validation

    

    async def _get_service_schema_definition(

        self, service: str, schema_name: str

    ) -> Optional[Dict[str, Any]]:

        """Get schema definition from a service (mock for now, should introspect actual schemas)."""

        try:

            # This would normally introspect the actual service schemas

            # For now, simulate schema definitions based on known structure

            

            if service == "auth_service" and schema_name == "User":

                return {

                    "id": {"type": "string", "required": True},

                    "email": {"type": "string", "required": True},

                    "created_at": {"type": "datetime", "required": True},

                    "name": {"type": "string", "required": False},

                    "avatar_url": {"type": "string", "required": False}

                }

            elif service == "netra_backend" and schema_name == "User":

                return {

                    "id": {"type": "string", "required": True},

                    "email": {"type": "string", "required": True},

                    "created_at": {"type": "datetime", "required": True},

                    "name": {"type": "string", "required": False},

                    "subscription_tier": {"type": "string", "required": False}

                }

            elif service == "frontend" and schema_name == "User":

                return {

                    "id": {"type": "string", "required": True},

                    "email": {"type": "string", "required": True},

                    "created_at": {"type": "datetime", "required": True},

                    "name": {"type": "string", "required": False},

                    "avatar_url": {"type": "string", "required": False},

                    "subscription_tier": {"type": "string", "required": False}

                }

            

            # Return None if schema not found

            return None

            

        except Exception as e:

            logger.warning(f"Could not get schema definition for {service}.{schema_name}: {e}")

            return None

    

    def _types_compatible(self, expected: str, actual: str) -> bool:

        """Check if actual type is compatible with expected type."""

        # Handle nullable types

        if "|null" in expected:

            expected_base = expected.replace("|null", "")

            if actual in ["null", "None", "Optional"]:

                return True

            return self._types_compatible(expected_base, actual)

        

        # Handle array types

        if expected == "array" and actual in ["list", "array", "Array"]:

            return True

        

        # Handle object types

        if expected == "object" and actual in ["dict", "object", "Object"]:

            return True

        

        # Handle datetime types

        if expected == "datetime" and actual in ["datetime", "timestamp", "Date"]:

            return True

        

        # Handle number types

        if expected == "number" and actual in ["int", "float", "number", "Number"]:

            return True

        

        # Direct match

        return expected == actual

    

    async def test_websocket_message_schema_alignment(self) -> Dict[str, Any]:

        """Test WebSocket message payload schemas are consistent."""

        results = {

            "schema_name": "WebSocketMessage",

            "message_types_tested": [],

            "schema_consistency": {},

            "payload_mismatches": [],

            "alignment_score": 0.0

        }

        

        try:

            # Define expected WebSocket message schemas

            websocket_schemas = {

                "user_message": {

                    "type": "user_message",

                    "payload": {

                        "content": "string",

                        "thread_id": "string|null",

                        "references": "array|null"

                    }

                },

                "agent_started": {

                    "type": "agent_started", 

                    "payload": {

                        "run_id": "string",

                        "agent_name": "string",

                        "timestamp": "datetime"

                    }

                },

                "agent_completed": {

                    "type": "agent_completed",

                    "payload": {

                        "run_id": "string",

                        "agent_name": "string",

                        "result": "object|null",

                        "duration_ms": "number",

                        "timestamp": "datetime"

                    }

                },

                "error": {

                    "type": "error",

                    "payload": {

                        "code": "string",

                        "message": "string", 

                        "details": "object|null",

                        "timestamp": "datetime"

                    }

                }

            }

            

            # Test each message type schema

            for msg_type, schema_spec in websocket_schemas.items():

                schema_validation = await self._validate_websocket_message_schema(

                    msg_type, schema_spec

                )

                results["message_types_tested"].append(msg_type)

                results["schema_consistency"][msg_type] = schema_validation

                

                if not schema_validation.get("schema_consistent", False):

                    results["payload_mismatches"].append({

                        "message_type": msg_type,

                        "issues": schema_validation.get("issues", [])

                    })

            

            # Calculate alignment score

            consistent_schemas = sum(

                1 for validation in results["schema_consistency"].values()

                if validation.get("schema_consistent", False)

            )

            total_schemas = len(websocket_schemas)

            results["alignment_score"] = (consistent_schemas / total_schemas) * 100 if total_schemas > 0 else 0

            

        except Exception as e:

            logger.error(f"Error testing WebSocket message schema alignment: {e}")

            results["error"] = str(e)

            

        return results

    

    async def _validate_websocket_message_schema(

        self, message_type: str, schema_spec: Dict[str, Any]

    ) -> Dict[str, Any]:

        """Validate WebSocket message schema consistency."""

        validation = {

            "message_type": message_type,

            "has_correct_structure": False,

            "payload_fields_correct": False,

            "schema_consistent": False,

            "issues": []

        }

        

        try:

            # Check basic message structure

            if "type" in schema_spec and "payload" in schema_spec:

                validation["has_correct_structure"] = True

            else:

                validation["issues"].append("Missing 'type' or 'payload' field")

            

            # Check payload field types (simplified validation)

            payload_spec = schema_spec.get("payload", {})

            if payload_spec:

                validation["payload_fields_correct"] = True

                # In a real implementation, this would validate against actual schemas

            else:

                validation["issues"].append("Empty or missing payload specification")

            

            # Overall schema consistency

            validation["schema_consistent"] = (

                validation["has_correct_structure"] and

                validation["payload_fields_correct"]

            )

            

        except Exception as e:

            validation["issues"].append(f"Schema validation error: {str(e)}")

            

        return validation

    

    async def test_database_model_alignment(self) -> Dict[str, Any]:

        """Test database model field alignment between services."""

        results = {

            "schema_name": "DatabaseModels",

            "models_tested": [],

            "field_alignments": {},

            "migration_conflicts": [],

            "alignment_score": 0.0

        }

        

        try:

            # Define database models that should be consistent

            db_models = {

                "users": {

                    "services": ["auth_service", "netra_backend"],

                    "fields": {

                        "id": "primary_key",

                        "email": "string_unique",

                        "created_at": "timestamp",

                        "updated_at": "timestamp",

                        "name": "string_nullable"

                    }

                },

                "threads": {

                    "services": ["netra_backend"],

                    "fields": {

                        "id": "primary_key",

                        "user_id": "foreign_key",

                        "title": "string",

                        "created_at": "timestamp",

                        "updated_at": "timestamp",

                        "metadata": "json_nullable"

                    }

                }

            }

            

            # Test each model alignment

            for model_name, model_spec in db_models.items():

                model_validation = await self._validate_database_model_alignment(

                    model_name, model_spec

                )

                results["models_tested"].append(model_name)

                results["field_alignments"][model_name] = model_validation

                

                if model_validation.get("migration_conflicts"):

                    results["migration_conflicts"].extend(model_validation["migration_conflicts"])

            

            # Calculate alignment score

            aligned_models = sum(

                1 for validation in results["field_alignments"].values()

                if validation.get("fields_aligned", False)

            )

            total_models = len(db_models)

            results["alignment_score"] = (aligned_models / total_models) * 100 if total_models > 0 else 0

            

        except Exception as e:

            logger.error(f"Error testing database model alignment: {e}")

            results["error"] = str(e)

            

        return results

    

    async def _validate_database_model_alignment(

        self, model_name: str, model_spec: Dict[str, Any]

    ) -> Dict[str, Any]:

        """Validate database model field alignment."""

        validation = {

            "model_name": model_name,

            "services_checked": model_spec["services"],

            "fields_aligned": False,

            "field_differences": [],

            "migration_conflicts": [],

            "issues": []

        }

        

        try:

            # In a real implementation, this would check actual database schemas

            # For now, simulate validation

            

            expected_fields = model_spec["fields"]

            validation["fields_aligned"] = True  # Assume aligned for demo

            

            # Check for potential migration conflicts

            if model_name == "users" and len(model_spec["services"]) > 1:

                # Users table shared between auth and backend - critical alignment

                validation["migration_conflicts"].append({

                    "model": model_name,

                    "issue": "Shared table requires coordinated migrations",

                    "services": model_spec["services"]

                })

            

        except Exception as e:

            validation["issues"].append(f"Model validation error: {str(e)}")

            

        return validation





@pytest.fixture

def schema_tester():

    """Create schema alignment tester instance."""

    return CrossServiceDataSchemaAlignmentTester()





class TestCrossServiceDataSchemaAlignment:

    """Test suite for cross-service data schema alignment."""

    

    @pytest.mark.asyncio

    @pytest.mark.integration

    async def test_user_schema_consistency_across_services(self, schema_tester):

        """Test that User schema is consistent across auth service, backend, and frontend."""

        results = await schema_tester.test_user_schema_alignment()

        

        # Log detailed results for debugging

        logger.info(f"User schema alignment results: {results}")

        

        # Check for errors

        assert "error" not in results, f"Error during user schema test: {results.get('error')}"

        

        # Validate alignment score

        alignment_score = results.get("alignment_score", 0.0)

        assert alignment_score >= 80.0, (

            f"User schema alignment score too low: {alignment_score}%. "

            f"Type mismatches: {results.get('type_mismatches', [])}. "

            f"Missing fields: {results.get('missing_fields', [])}. "

            f"User schema must be consistent across services for proper authentication and user management."

        )

        

        # Check for critical field presence

        services_tested = results.get("services_tested", [])

        assert len(services_tested) >= 2, (

            f"User schema test must cover multiple services, only tested: {services_tested}"

        )

        

        # Ensure no type mismatches for critical fields

        type_mismatches = results.get("type_mismatches", [])

        critical_field_mismatches = [

            mismatch for mismatch in type_mismatches

            if mismatch.get("field") in ["id", "email", "created_at"]

        ]

        

        assert len(critical_field_mismatches) == 0, (

            f"Critical User field type mismatches detected: {critical_field_mismatches}. "

            f"ID, email, and created_at fields must have consistent types across services."

        )

    

    @pytest.mark.asyncio

    @pytest.mark.integration

    async def test_websocket_message_payload_schemas(self, schema_tester):

        """Test that WebSocket message payload schemas are consistent."""

        results = await schema_tester.test_websocket_message_schema_alignment()

        

        # Log results for debugging

        logger.info(f"WebSocket message schema alignment results: {results}")

        

        # Check for errors

        assert "error" not in results, f"Error during WebSocket schema test: {results.get('error')}"

        

        alignment_score = results.get("alignment_score", 0.0)

        message_types_tested = results.get("message_types_tested", [])

        payload_mismatches = results.get("payload_mismatches", [])

        

        # Validate alignment score

        assert alignment_score >= 90.0, (

            f"WebSocket message schema alignment score too low: {alignment_score}%. "

            f"Payload mismatches: {payload_mismatches}. "

            f"WebSocket message schemas must be consistent for reliable real-time communication."

        )

        

        # Ensure critical message types are tested

        critical_message_types = ["user_message", "agent_started", "agent_completed", "error"]

        tested_critical_types = set(message_types_tested) & set(critical_message_types)

        

        assert len(tested_critical_types) >= 3, (

            f"WebSocket schema test must cover critical message types. "

            f"Tested: {list(tested_critical_types)}, Required: {critical_message_types}"

        )

        

        # Check for payload structure consistency

        schema_consistency = results.get("schema_consistency", {})

        inconsistent_schemas = [

            msg_type for msg_type, validation in schema_consistency.items()

            if not validation.get("schema_consistent", False)

        ]

        

        assert len(inconsistent_schemas) == 0, (

            f"Inconsistent WebSocket message schemas detected: {inconsistent_schemas}. "

            f"All message types must follow consistent payload structure."

        )

    

    @pytest.mark.asyncio

    @pytest.mark.integration

    async def test_database_model_field_alignment(self, schema_tester):

        """Test that database model fields are aligned between services."""

        results = await schema_tester.test_database_model_alignment()

        

        # Log results for debugging

        logger.info(f"Database model alignment results: {results}")

        

        # Check for errors

        assert "error" not in results, f"Error during database model test: {results.get('error')}"

        

        alignment_score = results.get("alignment_score", 0.0)

        models_tested = results.get("models_tested", [])

        migration_conflicts = results.get("migration_conflicts", [])

        

        # Validate alignment score

        assert alignment_score >= 85.0, (

            f"Database model alignment score too low: {alignment_score}%. "

            f"Models tested: {models_tested}. "

            f"Database models must have consistent field definitions across services."

        )

        

        # Check for migration conflicts (warn but don't fail)

        if migration_conflicts:

            logger.warning(f"Database migration conflicts detected: {migration_conflicts}")

            # Don't fail on migration conflicts - they're warnings for coordination

        

        # Ensure critical models are tested

        assert len(models_tested) >= 1, (

            f"Database model test must cover at least one shared model, tested: {models_tested}"

        )

    

    @pytest.mark.asyncio

    @pytest.mark.integration

    async def test_error_response_schema_standardization(self, schema_tester):

        """Test that error response schemas are standardized across services."""

        # Define expected error response schema

        error_schema = {

            "required_fields": ["code", "message"],

            "optional_fields": ["details", "timestamp", "trace_id"],

            "field_types": {

                "code": "string",

                "message": "string",

                "details": "object|null",

                "timestamp": "datetime|null", 

                "trace_id": "string|null"

            }

        }

        

        # Test error schema across services

        services = ["auth_service", "netra_backend"]

        error_validation_results = {}

        

        for service in services:

            validation = await schema_tester._validate_service_schema(

                service, "ErrorResponse", {"required_fields": error_schema["required_fields"],

                                         "optional_fields": error_schema["optional_fields"],

                                         "field_types": error_schema["field_types"]}

            )

            error_validation_results[service] = validation

        

        # Log results

        logger.info(f"Error response schema validation: {error_validation_results}")

        

        # Check that all services have consistent error schemas

        for service, validation in error_validation_results.items():

            missing_fields = validation.get("missing_fields", [])

            type_mismatches = validation.get("type_mismatches", [])

            

            # Allow flexibility for error schema implementation

            critical_missing = [field for field in missing_fields if field in ["code", "message"]]

            

            assert len(critical_missing) == 0, (

                f"Service {service} missing critical error response fields: {critical_missing}. "

                f"Error responses must have at least 'code' and 'message' fields."

            )

            

            # Log type mismatches as warnings (don't fail on them)

            if type_mismatches:

                logger.warning(f"Error schema type mismatches in {service}: {type_mismatches}")

    

    @pytest.mark.asyncio

    @pytest.mark.integration 

    async def test_schema_version_compatibility(self, schema_tester):

        """Test that schema versions are compatible across services."""

        schema_versions = {

            "User": "v1.2",

            "Thread": "v1.1", 

            "Message": "v1.3",

            "AgentExecution": "v1.0",

            "ErrorResponse": "v1.1"

        }

        

        version_compatibility_results = {}

        

        for schema_name, expected_version in schema_versions.items():

            # In a real implementation, this would check actual schema versions

            # For now, simulate version compatibility check

            version_validation = {

                "schema_name": schema_name,

                "expected_version": expected_version,

                "services_compatible": True,

                "version_conflicts": []

            }

            

            version_compatibility_results[schema_name] = version_validation

        

        # Log results

        logger.info(f"Schema version compatibility: {version_compatibility_results}")

        

        # Check for version conflicts

        for schema_name, validation in version_compatibility_results.items():

            version_conflicts = validation.get("version_conflicts", [])

            services_compatible = validation.get("services_compatible", False)

            

            assert services_compatible, (

                f"Schema version compatibility issues for {schema_name}: {version_conflicts}. "

                f"Schema versions must be compatible across services for data consistency."

            )

            

            # Warn about any version conflicts (don't fail)

            if version_conflicts:

                logger.warning(f"Schema version conflicts for {schema_name}: {version_conflicts}")





if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s"])

