# Unified Test Configuration - Phase 1

## Overview

The Unified Test Configuration system provides consistent, tier-based testing infrastructure for all Netra Apex customer segments (Free, Early, Mid, Enterprise). This Phase 1 implementation focuses on configuration management.

## Business Value Justification (BVJ)

- **Segment**: All customer tiers (Free, Early, Mid, Enterprise)
- **Business Goal**: Ensure reliable testing infrastructure for value creation features
- **Value Impact**: Prevents production bugs that could impact customer trust and conversion
- **Revenue Impact**: Testing reliability directly supports revenue protection

## Architecture Compliance

✅ **450-line file limit**: All files ≤300 lines  
✅ **25-line function limit**: All functions ≤8 lines  
✅ **Modular design**: Clear separation of concerns  
✅ **Type safety**: Strong typing throughout  

## Components

### Core Configuration (`config.py`)
- Environment variable management
- JWT secrets and encryption keys
- WebSocket and API endpoint configuration
- Test user management for all customer tiers
- Fixture factories for consistent test data

### Key Classes

#### `UnifiedTestConfig`
Main configuration manager that sets up:
- Test environment variables
- JWT and encryption secrets
- API and WebSocket endpoints
- Tier-based test users

#### `TestTier` (Enum)
Customer tier enumeration:
- `FREE` - Free tier users
- `EARLY` - Early adopter users  
- `MID` - Mid-tier users
- `ENTERPRISE` - Enterprise users

#### `TestDataFactory`
Static factory methods for creating:
- Message data with timestamps and IDs
- WebSocket authentication headers
- API request headers
- Plan data with expiry dates

#### `TestTokenManager`
JWT token management:
- Create test tokens for users
- Handle mock tokens for isolated testing

#### `TestDatabaseManager`
Database configuration:
- In-memory SQLite URLs for isolation
- Test database configuration
- Session management settings

## Usage Examples

### Basic Configuration Access
```python
from netra_backend.tests.unified.config import TEST_CONFIG, TEST_USERS, TEST_ENDPOINTS

# Access WebSocket URL
ws_url = TEST_ENDPOINTS.ws_url  # ws://localhost:8000/ws

# Get free tier user
free_user = TEST_USERS["free"]  # test-free@unified-test.com
```

### Tier-Based Testing
```python
from netra_backend.tests.unified.config import get_test_user, TestTier

# Get specific tier user
enterprise_user = get_test_user("enterprise")

# Test all tiers
for tier in TestTier:
    user = TEST_USERS[tier.value]
    # Run tier-specific tests
```

### Test Data Generation
```python
from netra_backend.tests.unified.config import TestDataFactory, TestTokenManager

# Create test message
message = TestDataFactory.create_message_data(user_id, "Hello!")

# Generate auth token
token_manager = TestTokenManager(TEST_SECRETS)
token = token_manager.create_user_token(user)

# Create API headers
headers = TestDataFactory.create_api_headers(token)
```

## Environment Variables Set

The configuration automatically sets:
- `TESTING=1`
- `ENVIRONMENT=test`
- `DATABASE_URL=sqlite+aiosqlite:///:memory:`
- `REDIS_HOST=localhost`
- `CLICKHOUSE_HOST=localhost`
- `JWT_SECRET_KEY` (test key)
- `FERNET_KEY` (test key)
- `ENCRYPTION_KEY` (test key)

## Test Users

Each tier has a dedicated test user:

| Tier | Email | Plan Tier |
|------|-------|-----------|
| Free | test-free@unified-test.com | free |
| Early | test-early@unified-test.com | early |
| Mid | test-mid@unified-test.com | mid |
| Enterprise | test-enterprise@unified-test.com | enterprise |

## Integration

### With Existing Tests
```python
# Import in your test files
from netra_backend.tests.unified.config import TEST_USERS, get_test_user

def test_free_tier_limits():
    free_user = get_test_user("free")
    # Test free tier functionality
```

### With Test Runner
The configuration integrates seamlessly with the main test runner:
```bash
python test_runner.py --level integration --no-coverage --fast-fail
```

## Files Structure

```
tests/unified/
├── __init__.py              # Package initialization with exports
├── config.py                # Main configuration implementation
├── test_config_validation.py # Comprehensive validation tests
├── demo_usage.py            # Usage examples and demonstrations
└── README.md               # This documentation
```

## Testing

Run the configuration validation tests:
```bash
python -m pytest tests/unified/test_config_validation.py -v
```

All tests should pass with:
- ✅ Environment variables properly set
- ✅ Test users created for all tiers
- ✅ Endpoints configured correctly
- ✅ Secrets and encryption keys set
- ✅ Factory functions working
- ✅ Database configuration valid
- ✅ Helper functions operational
- ✅ Token generation working
- ✅ Configuration isolation maintained

## Future Phases

**Phase 2**: Test harness integration with service management  
**Phase 3**: WebSocket test client and real-time testing  
**Phase 4**: E2E journey testing for customer conversion flows  
**Phase 5**: Performance and load testing infrastructure  

## Contributing

When extending the unified test configuration:
1. Maintain 450-line file limit
2. Keep all functions ≤8 lines
3. Add comprehensive tests
4. Update documentation
5. Ensure tier-based testing support

---

**Phase 1 Status**: ✅ COMPLETE - Ready for unified testing implementation