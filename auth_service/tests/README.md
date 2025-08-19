# Auth Service OAuth Tests

Comprehensive test suite for OAuth flows in the Netra Auth Service.

## Test Coverage

### OAuth Providers
- ✅ Google OAuth complete flow
- ✅ GitHub OAuth complete flow (placeholder for future implementation)
- ✅ Microsoft OAuth complete flow (placeholder for future implementation)

### Test Categories

#### 1. Integration Tests (`tests/integration/test_oauth_flows.py`)
- **Google OAuth Flow**: Complete end-to-end OAuth flow with Google
- **GitHub OAuth Flow**: Placeholder tests for GitHub implementation
- **Microsoft OAuth Flow**: Placeholder tests for Microsoft implementation
- **Error Handling**: Invalid state, denied access, token exchange failures
- **State Validation**: OAuth state parameter security validation
- **Callback Handling**: OAuth callback parameter validation and processing
- **Token Exchange**: OAuth authorization code to token exchange
- **Token Refresh**: OAuth token refresh flow
- **Logout & Cleanup**: Session cleanup on logout

#### 2. Unit Tests (`tests/unit/test_oauth_models.py`)
- **Pydantic Models**: Validation of OAuth-related data models
- **AuthProvider Enum**: Provider type validation
- **Login/Token Models**: Request/response model validation
- **Configuration Models**: Auth configuration validation

## Running Tests

### Quick Run
```bash
# Run all OAuth tests
python tests/run_oauth_tests.py

# Run specific test file
pytest tests/integration/test_oauth_flows.py -v

# Run with coverage
pytest tests/ --cov=auth_core --cov-report=html
```

### Individual Test Categories
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only  
pytest tests/integration/ -v

# Specific test class
pytest tests/integration/test_oauth_flows.py::TestGoogleOAuthFlow -v
```

## Test Requirements

Install test dependencies:
```bash
pip install -r tests/requirements-test.txt
```

## Test Configuration

Tests use environment variables for configuration:
- `ENVIRONMENT=test` - Sets test mode
- `JWT_SECRET` - Test JWT secret key
- `GOOGLE_CLIENT_ID` - Test Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Test Google OAuth client secret
- `DATABASE_URL` - Test database URL (SQLite in-memory)
- `REDIS_URL` - Test Redis URL

## Mock Strategy

### External Services
- **OAuth Providers**: HTTP requests to Google/GitHub/Microsoft are mocked
- **Database**: Uses in-memory SQLite for isolated testing  
- **Redis**: Session management is mocked
- **User Data**: Consistent test user data across tests

### Security Testing
- State parameter generation and validation
- Token validation and expiration
- Session security and cleanup
- CORS configuration validation

## Business Value Justification (BVJ)

**Segment**: Enterprise & Growth  
**Business Goal**: Ensure reliable authentication for customer retention  
**Value Impact**: Prevents authentication failures that could lose customers  
**Revenue Impact**: Protects user acquisition and prevents churn from auth issues

## Test Architecture

### Fixtures (`conftest.py`)
- Database setup/teardown
- Mock OAuth responses  
- Test user data
- Environment configuration

### Test Data
- Consistent mock OAuth responses
- Valid/invalid token examples
- Error scenarios for edge cases
- Security validation data

## Current Implementation Status

### Implemented ✅
- Google OAuth complete flow tests
- OAuth error handling tests
- State parameter validation tests
- Token validation tests
- Model validation tests

### Planned 📋
- GitHub OAuth provider implementation
- Microsoft OAuth provider implementation  
- Multi-provider session management
- Advanced security tests

## Running in CI/CD

Tests are designed to run in CI environments:
- No external dependencies 
- Mocked HTTP requests
- In-memory databases
- Deterministic test data

```yaml
# Example GitHub Actions step
- name: Run OAuth Tests
  run: |
    cd auth_service
    python tests/run_oauth_tests.py
```

## Security Considerations

### OAuth Security Tests
- State parameter cryptographic randomness
- Token expiration validation
- Session hijacking prevention
- CSRF protection validation

### Test Security
- No real OAuth credentials in tests
- Isolated test environment
- Mock sensitive operations
- Clean environment between tests

## Troubleshooting

### Common Issues
1. **Import errors**: Ensure `PYTHONPATH` includes `auth_service` directory
2. **Database errors**: Check SQLite permissions for in-memory database
3. **Mock failures**: Verify `httpx` and `unittest.mock` are installed
4. **Async test issues**: Ensure `pytest-asyncio` is installed

### Debug Mode
```bash
# Run with verbose output and no capture
pytest tests/integration/test_oauth_flows.py -v -s --tb=long
```

## Contributing

When adding new OAuth tests:
1. Follow the existing test patterns
2. Use appropriate mocking for external services
3. Include both success and failure scenarios
4. Add documentation for new test categories
5. Ensure functions remain ≤ 8 lines each
6. Keep test files ≤ 300 lines