# Shim module for real services test fixtures
from test_framework.fixtures.real_services import *

# Import local services for non-Docker testing
from test_framework.fixtures.local_real_services import (
    local_real_services_fixture, 
    local_postgres_connection,
    local_redis_connection,
    local_database_session
)

# COMPATIBILITY ALIAS: Export real_database_session as real_db_fixture for backward compatibility  
real_db_fixture = real_database_session

# Compatibility aliases for integration tests (Issue #308)
from test_framework.real_services import RealServicesManager
RealServicesTestFixtures = RealServicesManager  # Integration test compatibility alias

# Override real_services_fixture to use local services when USE_REAL_SERVICES=true
# This allows Golden Path tests to work without Docker
import os
if os.getenv("USE_REAL_SERVICES", "false").lower() == "true":
    real_services_fixture = local_real_services_fixture
