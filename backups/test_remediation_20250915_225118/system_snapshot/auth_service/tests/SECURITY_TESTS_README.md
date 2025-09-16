# Security Tests for Auth Service

## Overview

Comprehensive security test suite for the auth service covering critical security vulnerabilities and attack vectors.

## Test Coverage

### 1. SQL Injection Prevention (`TestSQLInjectionPrevention`)
- **Login endpoint**: Tests malicious SQL in email/password fields
- **Token validation**: Tests SQL injection through JWT tokens  
- **Service tokens**: Tests SQL injection in service authentication

**Attack vectors tested:**
- `'; DROP TABLE users; --`
- `' OR '1'='1`
- `UNION SELECT` attacks

### 2. XSS Prevention (`TestXSSPrevention`)
- **Login inputs**: Tests XSS in login form fields
- **User-Agent headers**: Tests XSS through HTTP headers
- **OAuth callback**: Tests XSS in OAuth parameters

**Attack vectors tested:**
- `<script>alert('XSS')</script>`
- `javascript:alert('XSS')`
- `<img src=x onerror=alert('XSS')>`

### 3. CSRF Protection (`TestCSRFProtection`)
- **Security headers**: Validates security headers are set
- **CSRF tokens**: Tests CSRF protection mechanisms
- **Method override**: Tests HTTP method override prevention

### 4. Input Validation (`TestInputValidation`)
- **Email validation**: Tests email format validation
- **Password limits**: Tests password length restrictions
- **Payload size**: Tests protection against large payloads

### 5. Security Logging (`TestSecurityLogging`)
- **Failed logins**: Verifies failed attempts are logged
- **Attack attempts**: Tests logging of malicious activity
- **Audit trail**: Validates comprehensive audit logging

### 6. Token Security (`TestTokenSecurity`)
- **Format validation**: Tests JWT token format validation
- **Injection prevention**: Tests token injection attacks

### 7. Rate Limiting (`TestRateLimiting`)
- **Login limiting**: Tests rate limiting on login attempts
- **Token validation**: Tests rate limiting on token requests

## Running Security Tests

### Using pytest directly:
```bash
cd auth_service
pytest tests/test_security.py -v
```

### Using main test runner:
```bash
python test_runner.py --level unit --no-coverage --fast-fail
```

### Run specific test class:
```bash
pytest tests/test_security.py::TestSQLInjectionPrevention -v
```

## Test Results Interpretation

### Expected Behaviors:
- **400/422**: Input validation errors (expected for malicious input)
- **401**: Authentication failures (expected for invalid credentials)
- **413**: Payload too large (expected for oversized requests)
- **429**: Rate limiting (expected after many requests)

### Failure Indicators:
- **500**: Server crashes (should never happen)
- **200**: Successful processing of malicious input (security vulnerability)
- Missing audit logs for attack attempts

## Security Test Architecture

Each test class follows the pattern:
1. **Setup**: Mock dependencies and create test clients
2. **Attack**: Send malicious payloads to endpoints
3. **Verify**: Ensure attacks are blocked and logged
4. **Cleanup**: Verify service remains stable

## Attack Payloads

The test suite uses realistic attack vectors:

### SQL Injection:
- Table dropping attempts
- Authentication bypasses
- Data extraction attempts

### XSS Payloads:
- Script injection
- Event handlers
- Data URIs

### Malicious Headers:
- Cookie manipulation
- Path traversal
- LDAP injection

## Business Value

These security tests ensure:
- **Customer Trust**: Protecting user data and credentials
- **Compliance**: Meeting security standards and regulations
- **Risk Mitigation**: Preventing data breaches and service downtime
- **Revenue Protection**: Avoiding security incident costs

## Integration with CI/CD

Security tests should be:
- Run on every commit
- Required to pass before deployment
- Include in security audits
- Monitor for new vulnerabilities

## Extending Security Tests

To add new security tests:
1. Identify new attack vectors
2. Add to relevant test class
3. Include realistic payloads
4. Verify defensive measures
5. Update this documentation

## Security Test Maintenance

Regular updates needed for:
- New OWASP Top 10 vulnerabilities
- Emerging attack patterns
- Updated security libraries
- Compliance requirements

---

**Note**: These tests verify that the auth service properly handles malicious input without compromising security. They do not perform actual attacks on production systems.