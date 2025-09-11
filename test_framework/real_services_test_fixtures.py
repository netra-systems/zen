# Shim module for real services test fixtures
from test_framework.fixtures.real_services import *

# COMPATIBILITY ALIAS: Export real_database_session as real_db_fixture for backward compatibility  
real_db_fixture = real_database_session

# Compatibility aliases for integration tests (Issue #308)
from test_framework.real_services import RealServicesManager
RealServicesTestFixtures = RealServicesManager  # Integration test compatibility alias
