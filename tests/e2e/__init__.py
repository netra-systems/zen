import sys

import os

from pathlib import Path



# Add project root to path for imports  

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))



"""

E2E Test Package for Real Services Testing



This package contains comprehensive end-to-end tests that validate

the complete Netra AI Optimization Platform using real services.



Test Categories:

- Cold Start Flow Validation (< 5 second requirement)

- Cross-Service Data Synchronization 

- Real LLM API Integration Testing

- Redis Cache Coherency Validation

- Database Consistency (PostgreSQL to ClickHouse)



Business Value:

- Platform Stability: Prevents production failures

- Customer Trust: Ensures reliable user experience

- Risk Reduction: Validates critical business flows

- Revenue Protection: Maintains $100K+ MRR platform reliability



Usage:

    pytest tests/e2e/ -v --real-services

    

Environment Setup Required:

    - Real PostgreSQL database

    - Real Redis instance

    - Real Auth Service running

    - Real Backend Service running

    - Valid LLM API keys

"""



__version__ = "1.0.0"

__author__ = "Netra AI Platform Team"



# Test execution metadata

TEST_CATEGORIES = {

    "cold_start": "Complete system initialization flow",

    "cross_service_sync": "Data consistency across services", 

    "llm_integration": "Real LLM API validation",

    "cache_validation": "Redis cache operations",

    "database_consistency": "PostgreSQL to ClickHouse sync"

}



PERFORMANCE_REQUIREMENTS = {

    "cold_start_max_duration": 5.0,  # seconds

    "cross_service_sync_max": 2.0,   # seconds

    "llm_response_max": 10.0,        # seconds

    "cache_operation_max": 1.0,      # seconds

    "database_sync_max": 3.0         # seconds

}



# Export main test classes

# Note: test_real_services_e2e module temporarily disabled due to import issues



__all__ = [

    "TEST_CATEGORIES",

    "PERFORMANCE_REQUIREMENTS"

]

