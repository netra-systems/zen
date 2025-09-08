#!/usr/bin/env python3
"""
Database Integration Test Validation Script

This script validates that the database integration tests are properly structured
and all required imports are available.
"""

import sys
import traceback

def validate_imports():
    """Validate all imports required by the database integration tests."""
    print("=> Validating database integration test imports...")
    
    try:
        # Test framework imports
        from test_framework.ssot.base_test_case import SSotBaseTestCase
        from shared.isolated_environment import get_env
        print("[OK] SSOT test framework imports successful")
        
        # Database connection imports
        from netra_backend.app.db.postgres_core import AsyncDatabase
        from auth_service.auth_core.database.connection import AuthDatabaseConnection
        print("[OK] Database connection imports successful")
        
        # Backend model imports
        from netra_backend.app.db.models_user import User, Secret, ToolUsageLog
        from netra_backend.app.db.models_agent import Thread, Message, Run, Assistant
        from netra_backend.app.db.models_content import CorpusAuditLog, Analysis
        print("[OK] Backend model imports successful")
        
        # Auth service model imports
        from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog
        print("[OK] Auth service model imports successful")
        
        # Database URL imports
        from netra_backend.app.database import get_database_url as get_backend_db_url
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        print("[OK] Database URL imports successful")
        
        # SQLAlchemy imports
        from sqlalchemy import text, select, delete
        from sqlalchemy.exc import IntegrityError
        print("[OK] SQLAlchemy imports successful")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Import validation failed: {e}")
        traceback.print_exc()
        return False

def validate_test_structure():
    """Validate the test class structure."""
    print("\n=> Validating test class structure...")
    
    try:
        # Import the test class
        from tests.integration.test_database_cross_service_integration import TestDatabaseCrossServiceIntegration
        
        # Check class inheritance
        from test_framework.ssot.base_test_case import SSotBaseTestCase
        assert issubclass(TestDatabaseCrossServiceIntegration, SSotBaseTestCase), "Test class must inherit from SSotBaseTestCase"
        print("[OK] Test class inheritance correct")
        
        # Check test methods exist
        test_class = TestDatabaseCrossServiceIntegration()
        required_methods = [
            'test_user_data_persistence_across_services',
            'test_thread_message_storage_chat_continuity', 
            'test_transaction_integrity_rollback_scenarios',
            'test_multi_user_data_isolation_enterprise_security',
            'test_foreign_key_constraints_referential_integrity',
            'test_concurrent_access_race_condition_prevention',
            'test_database_connection_pooling_performance',
            'test_audit_logging_cross_service_compliance',
            'test_business_data_flows_existing_features',
            'test_database_migration_scenarios_service_updates',
            'test_tool_usage_tracking_business_analytics'
        ]
        
        for method_name in required_methods:
            assert hasattr(test_class, method_name), f"Missing test method: {method_name}"
            method = getattr(test_class, method_name)
            assert callable(method), f"Method {method_name} is not callable"
            
        print(f"[OK] All {len(required_methods)} test methods present and callable")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Test structure validation failed: {e}")
        traceback.print_exc()
        return False

def validate_business_value_justifications():
    """Validate that all tests have proper Business Value Justifications."""
    print("\n=> Validating Business Value Justifications...")
    
    try:
        # Read the test file and check for BVJ comments
        with open("tests/integration/test_database_cross_service_integration.py", "r") as f:
            content = f.read()
            
        # Check for BVJ patterns
        bvj_patterns = [
            "BVJ: Enterprise",
            "BVJ: Platform", 
            "BVJ: All Segments",
            "BVJ: Free/Pro/Enterprise"
        ]
        
        bvj_count = 0
        for pattern in bvj_patterns:
            bvj_count += content.count(pattern)
            
        assert bvj_count >= 10, f"Expected at least 10 BVJ comments, found {bvj_count}"
        print(f"[OK] Found {bvj_count} Business Value Justifications")
        
        # Check for required BVJ elements
        required_elements = [
            "Business Goal:",
            "Value Impact:",
            "Strategic Impact:"
        ]
        
        for element in required_elements:
            assert element in content, f"Missing BVJ element: {element}"
            
        print("[OK] All required BVJ elements present")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] BVJ validation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validations."""
    print(" Database Integration Test Validation")
    print("=" * 50)
    
    validations = [
        validate_imports,
        validate_test_structure, 
        validate_business_value_justifications
    ]
    
    all_passed = True
    for validation in validations:
        if not validation():
            all_passed = False
            
    print("\n" + "=" * 50)
    if all_passed:
        print("[SUCCESS] All validations passed! Database integration tests are ready.")
        print("\nTo run the tests with real services:")
        print("python tests/unified_test_runner.py --pattern 'test_database_cross_service_integration.py' --real-services --category integration")
        return 0
    else:
        print("[ERROR] Some validations failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())