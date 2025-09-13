"""

Audit Trail Test Data Factory

Creates audit test data for compliance testing across all audit trail test modules.



Business Value Justification (BVJ):

- Segment: Enterprise

- Business Goal: Support compliance testing infrastructure

- Value Impact: Enables comprehensive audit trail validation for Enterprise requirements

- Revenue Impact: Part of compliance testing that unlocks Enterprise sales

"""



from datetime import datetime, timezone

from typing import Any, Dict





class AuditTestDataFactory:

    """Factory for creating audit test data with all required compliance fields."""

    

    @staticmethod

    def create_login_success_data(user_id: str) -> Dict[str, Any]:

        """Create login success audit data."""

        return {

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "user_id": user_id,

            "action": "login_success",

            "ip_address": "127.0.0.1",

            "user_agent": "test-client"

        }

    

    @staticmethod

    def create_admin_action_data(action: str, user_id: str) -> Dict[str, Any]:

        """Create admin action audit data."""

        return {

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "user_id": user_id,

            "action": f"admin_{action}",

            "ip_address": "127.0.0.1",

            "user_agent": "admin-client"

        }

    

    @staticmethod  

    def create_data_access_data(access_type: str, user_id: str) -> Dict[str, Any]:

        """Create data access audit data."""

        return {

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "user_id": user_id,

            "action": f"data_{access_type}",

            "ip_address": "127.0.0.1",

            "user_agent": "data-client"

        }

    

    @staticmethod

    def create_test_log_entry() -> Dict[str, Any]:

        """Create test log entry for integrity testing."""

        return {

            "timestamp": "2025-08-19T10:00:00Z",

            "user_id": "test-user",

            "action": "data_access",

            "resource": "user_table"

        }

    

    @staticmethod

    def create_sample_audit_logs():

        """Create sample audit logs for testing."""

        return [

            AuditTestDataFactory.create_login_success_data("user1"),

            AuditTestDataFactory.create_admin_action_data("user_delete", "admin1"),

            AuditTestDataFactory.create_data_access_data("export", "user2")

        ]

