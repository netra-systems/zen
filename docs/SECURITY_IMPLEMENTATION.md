# Netra Apex Security Implementation - Enterprise Grade

## 🔴 CRITICAL: Revenue Protection Security

**Security breaches directly impact revenue. Enterprise customers require SOC2, GDPR compliance.**

## Compliance Requirements by Tier

| Customer Tier | Compliance | Audit Frequency | Encryption | Data Residency |
|--------------|------------|-----------------|------------|----------------|
| **Free** | Basic | None | TLS 1.3 | Shared |
| **Early** | GDPR | Annual | TLS 1.3 + AES-256 | Regional |
| **Mid** | GDPR, CCPA | Quarterly | + Field encryption | Regional |
| **Enterprise** | SOC2, ISO27001 | Continuous | + HSM | Customer choice |

## Table of Contents

1. [Revenue Protection Security](#revenue-protection-security) **← Financial Data**
2. [Security Architecture](#security-architecture)
3. [Authentication & Authorization](#authentication--authorization)
4. [API Security & Rate Limiting](#api-security--rate-limiting) **← By Tier**
5. [Secret Management](#secret-management)
6. [Data Protection](#data-protection) **← Customer AI Models**
7. [Audit & Compliance](#audit--compliance) **← Enterprise Requirements**
8. [Incident Response](#incident-response)
9. [Security Testing](#security-testing)
10. [Zero Trust Architecture](#zero-trust-architecture)

## Security Architecture

## Revenue Protection Security

### Critical Financial Data Protection

```python
# Revenue-critical data requiring maximum protection
CRITICAL_DATA = {
    'usage_metrics': 'ENCRYPTION_REQUIRED',  # Billing data
    'savings_calculations': 'AUDIT_TRAIL_REQUIRED',  # Revenue basis
    'api_keys': 'HSM_STORAGE',  # Customer access
    'model_selections': 'ENCRYPTED_LOGS',  # Optimization IP
    'customer_workloads': 'FIELD_LEVEL_ENCRYPTION'  # Customer data
}

# Security levels by customer tier
SECURITY_TIERS = {
    'enterprise': {
        'encryption': 'AES-256-GCM',
        'key_rotation': 'daily',
        'audit_retention': '7_years',
        'data_residency': 'customer_region',
        'compliance': ['SOC2', 'ISO27001', 'GDPR']
    },
    'mid': {
        'encryption': 'AES-256',
        'key_rotation': 'weekly',
        'audit_retention': '3_years',
        'data_residency': 'regional',
        'compliance': ['GDPR', 'CCPA']
    }
}
```

### Multi-Layer Defense Strategy

The security implementation follows a defense-in-depth approach with revenue protection focus:

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Request                          │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Security Headers Middleware                    │
│  • CSP, HSTS, X-Frame-Options                              │
│  • Nonce generation for scripts/styles                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Security Middleware                            │
│  • Rate limiting (IP & User based)                         │
│  • Request size validation                                  │
│  • URL validation                                           │
│  • Input validation & sanitization                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Authentication Layer                           │
│  • JWT token validation                                     │
│  • Session management                                       │
│  • MFA when required                                        │
│  • IP/Device tracking                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              Application Layer                              │
│  • Business logic                                           │
│  • Database access (parameterized queries)                 │
│  • Secret management                                        │
└─────────────────────────────────────────────────────────────┘
```

## Authentication & Authorization

### Enhanced Authentication Security

Location: `app/auth/enhanced_auth_security.py`

#### Features:
- **Multi-factor Authentication (MFA)**: Required for production and suspicious activities
- **Session Management**: Secure sessions with CSRF protection
- **Rate Limiting**: IP and user-based authentication rate limiting
- **Device Tracking**: Detection of new devices and suspicious activities
- **Session Hijacking Protection**: IP consistency checks and user agent validation

#### Implementation:

```python
from app.auth.enhanced_auth_security import enhanced_auth_security

# Authenticate user
result, session_id = enhanced_auth_security.authenticate_user(
    user_id="user123",
    password="secure_password",
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0...",
    additional_factors={"totp": "123456"}  # MFA
)

# Validate session
valid, error = enhanced_auth_security.validate_session(
    session_id=session_id,
    ip_address="192.168.1.1",
    user_agent="Mozilla/5.0..."
)
```

#### Security Features:
- **Max Failed Attempts**: 5 attempts before user lockout
- **Lockout Duration**: 15 minutes for failed authentication
- **Session Timeout**: 8 hours maximum
- **Concurrent Sessions**: Maximum 3 per user
- **MFA Requirements**: Production environment and untrusted IPs

### JWT Token Security

Following `security.xml` specifications:

- **Token Storage**: Single localStorage key `jwt_token`
- **Token Validation**: Signature verification and expiration checks
- **Token Refresh**: Not implemented (re-authentication required)
- **WebSocket Auth**: Token passed as query parameter

## Input Validation & Sanitization

### Enhanced Input Validator

Location: `app/core/enhanced_input_validation.py`

#### Threat Detection:
- **SQL Injection**: Pattern-based detection for SQL keywords and structures
- **XSS**: Script tag detection and dangerous HTML elements
- **Path Traversal**: Directory traversal attempts
- **Command Injection**: Shell command separators and execution patterns
- **LDAP Injection**: LDAP special characters
- **XML Injection**: XML entity and DOCTYPE declarations

#### Validation Levels:
- **BASIC**: 100KB max, basic format validation
- **MODERATE**: 50KB max, security checks
- **STRICT**: 10KB max, maximum security validation
- **PARANOID**: 1KB max, ultra-strict for sensitive data

#### Usage:

```python
from app.core.enhanced_input_validation import strict_validator

# Validate input
result = strict_validator.validate_input(
    input_value="user input",
    field_name="username",
    context={"type": "email"}
)

if result.is_valid:
    # Use sanitized value
    clean_input = result.sanitized_value
else:
    # Handle validation errors
    logger.error(f"Validation failed: {result.errors}")
```

#### Sanitization:
- **HTML Escaping**: For XSS protection
- **SQL Character Removal**: Dangerous SQL characters
- **Path Encoding**: Directory traversal sequences
- **Command Character Removal**: Shell command separators

## Rate Limiting & DDoS Protection

### Security Middleware Rate Limiting

Location: `app/middleware/security_middleware.py`

#### Features:
- **IP-based Rate Limiting**: 100 requests/minute (default), 20 requests/minute (sensitive endpoints)
- **User-based Rate Limiting**: Higher limits for authenticated users
- **Burst Protection**: 5 request burst allowance
- **Automatic IP Blocking**: 5 minutes for excessive requests
- **Rate Limit Headers**: X-RateLimit-* headers in responses

#### Configuration:

```python
class SecurityConfig:
    DEFAULT_RATE_LIMIT = 100    # requests per minute
    STRICT_RATE_LIMIT = 20      # for sensitive endpoints
    BURST_LIMIT = 5             # burst allowance
```

#### Sensitive Endpoints:
- `/api/auth/login`
- `/api/auth/logout`
- `/api/auth/token`
- `/api/admin`
- `/api/tools`
- `/api/synthetic-data`

### WebSocket Rate Limiting

Location: `app/websocket/rate_limiter.py`

#### Features:
- **Adaptive Rate Limiting**: Adjusts based on connection behavior
- **Connection-specific Limits**: Per-connection rate tracking
- **Automatic Promotion/Demotion**: Good connections get higher limits

## Secret Management

### Enhanced Secret Manager

Location: `app/core/enhanced_secret_manager.py`

#### Environment Isolation:
Following `PRODUCTION_SECRETS_ISOLATION.xml`:

- **Production Secrets**: `prod-*` pattern, 30-day rotation
- **Staging Secrets**: `staging-*` pattern, 60-day rotation  
- **Development Secrets**: `dev-*` pattern, 180-day rotation

#### Access Levels:
- **PUBLIC**: Non-sensitive configuration
- **INTERNAL**: Internal app secrets
- **RESTRICTED**: Database passwords, API keys
- **CRITICAL**: Production secrets, encryption keys

#### Security Features:
- **Encryption**: All secrets encrypted at rest using Fernet
- **Access Logging**: Complete audit trail of secret access
- **Component Blocking**: Block components with excessive failed attempts
- **Rotation Tracking**: Automatic rotation alerts
- **Environment Validation**: Cross-environment access prevention

#### Usage:

```python
from app.core.enhanced_secret_manager import enhanced_secret_manager

# Get secret with access control
secret_value = enhanced_secret_manager.get_secret(
    secret_name="prod-api-key",
    component="auth-service"
)

# Rotate secret
success = enhanced_secret_manager.rotate_secret(
    secret_name="prod-api-key",
    new_value="new-secret-value"
)
```

## Security Headers

### Comprehensive Security Headers

Location: `app/middleware/security_headers.py`

#### Production Headers:
- **HSTS**: `max-age=31536000; includeSubDomains; preload`
- **CSP**: Strict Content Security Policy with nonces
- **X-Frame-Options**: `DENY`
- **X-Content-Type-Options**: `nosniff`
- **X-XSS-Protection**: `1; mode=block`
- **Referrer-Policy**: `strict-origin-when-cross-origin`
- **Permissions-Policy**: Disabled sensitive features

#### CSP Configuration:

**Production:**
```
default-src 'self';
script-src 'self' 'unsafe-inline' https://apis.google.com;
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: https:;
connect-src 'self' https://api.netrasystems.ai wss://api.netrasystems.ai;
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
upgrade-insecure-requests
```

**Development:**
```
default-src 'self' 'unsafe-inline' 'unsafe-eval';
script-src 'self' 'unsafe-inline' 'unsafe-eval' http: https:;
connect-src 'self' http: https: ws: wss:;
```

#### Nonce Generation:
- **Cryptographically Secure**: Using `secrets.token_urlsafe(16)`
- **Per-Request**: Unique nonce for each request
- **Template Integration**: Available via `request.state.csp_nonce`

## CORS Configuration

### Environment-based CORS

Location: `app/core/middleware_setup.py`

#### Production CORS:
- **Allowed Origins**: Explicit domain whitelist from `CORS_ORIGINS` env var
- **Default**: `https://netrasystems.ai`
- **Credentials**: Allowed
- **Methods**: `GET, POST, PUT, DELETE, OPTIONS, PATCH`

#### Development CORS:
- **Allowed Origins**: `*` (wildcard) or from `CORS_ORIGINS`
- **Local Development**: `http://localhost:3000`, `http://127.0.0.1:3000`

#### Security Features:
- **Preflight Handling**: Automatic OPTIONS handling
- **Header Validation**: Restricted allowed headers
- **Credential Security**: Only allowed for trusted origins

## SQL Injection Prevention

### Database Security

#### Parameterized Queries:
All database interactions use SQLAlchemy ORM with parameterized queries:

```python
# SAFE - Using ORM
user = session.query(User).filter(User.id == user_id).first()

# SAFE - Using bound parameters
result = session.execute(
    text("SELECT * FROM users WHERE id = :user_id"),
    {"user_id": user_id}
)
```

#### Input Validation:
SQL injection patterns are detected and blocked by the input validator:

```python
SQL_PATTERNS = [
    r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
    r'(-{2}|/\*|\*/)',  # SQL comments
    r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
    r'(\bxp_cmdshell\b)',  # SQL Server command execution
]
```

#### Database Configuration:
- **Connection Limits**: Maximum 100 connections
- **Statement Timeout**: 30 seconds
- **Idle Timeout**: 60 seconds
- **Lock Timeout**: 10 seconds

## XSS Protection

### Multi-layer XSS Prevention:

#### 1. Content Security Policy:
- **Nonce-based Scripts**: All inline scripts require nonces
- **Strict CSP**: No `unsafe-eval` in production
- **Frame Protection**: `frame-ancestors 'none'`

#### 2. Input Validation:
XSS patterns detected and blocked:

```python
XSS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\w+\s*=',  # Event handlers
    r'<iframe[^>]*>',
    r'data:[^;]*;base64',  # Data URLs
]
```

#### 3. Output Encoding:
- **HTML Escaping**: All user content HTML-escaped
- **Attribute Encoding**: URL and attribute encoding where appropriate
- **JSON Encoding**: Safe JSON serialization

#### 4. Security Headers:
- **X-XSS-Protection**: Browser XSS filter enabled
- **X-Content-Type-Options**: Prevents MIME type sniffing

## Session Security

### Secure Session Management:

#### Session Properties:
- **Secure ID Generation**: Cryptographically random session IDs
- **CSRF Protection**: Per-session CSRF tokens
- **IP Validation**: Session bound to original IP
- **User Agent Tracking**: Device consistency checks
- **Expiration**: 8-hour maximum session lifetime

#### Session Security Features:
- **Concurrent Limits**: Maximum 3 sessions per user
- **Hijacking Detection**: Geographic and device analysis
- **Automatic Revocation**: Suspicious activity triggers revocation
- **Secure Storage**: Sessions stored server-side only

#### Implementation:

```python
@dataclass
class SecuritySession:
    session_id: str
    user_id: str
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    status: SessionStatus
    security_flags: Dict[str, Any]
    csrf_token: str
```

## Monitoring & Alerting

### Security Metrics:

#### Authentication Metrics:
- **Failed Login Attempts**: Track by IP and user
- **Successful Logins**: Success rate monitoring
- **Blocked Attempts**: Rate limiting effectiveness
- **Session Hijacking**: Suspicious session activities

#### Input Validation Metrics:
- **Threat Detection**: Count by threat type
- **Validation Failures**: Input rejection rates
- **Sanitization**: How often inputs are cleaned

#### Rate Limiting Metrics:
- **Rate Limit Hits**: Requests blocked
- **IP Blocking**: Automatic IP blocks
- **Burst Detection**: Burst traffic patterns

### Security Alerts:

#### Critical Alerts:
- **Repeated Failed Logins**: 5+ failures in 5 minutes
- **SQL Injection Attempts**: Any detected SQL injection
- **XSS Attempts**: Any detected XSS
- **Session Hijacking**: Suspicious session changes
- **Rate Limit Exceeded**: Potential DDoS

#### Monitoring Integration:
- **Structured Logging**: JSON-formatted security events
- **Metric Collection**: Prometheus-compatible metrics
- **Alert Routing**: Critical events to security team

## Security Testing

### Comprehensive Test Suite:

Location: `app/tests/security/test_comprehensive_security.py`

#### Test Coverage:
- **Authentication Flow Testing**: Login, logout, session validation
- **Input Validation Testing**: All threat types and edge cases
- **Rate Limiting Testing**: IP and user-based limits
- **Security Headers Testing**: All headers and CSP
- **Secret Management Testing**: Access control and encryption
- **Integration Testing**: End-to-end security flows

#### Test Categories:
- **Unit Tests**: Individual security components
- **Integration Tests**: Security middleware stack
- **Performance Tests**: Security under load
- **Penetration Tests**: Simulated attacks

#### Running Security Tests:

```bash
# Run all security tests
pytest app/tests/security/ -v

# Run specific security test categories
pytest app/tests/security/test_comprehensive_security.py::TestInputValidation -v
pytest app/tests/security/test_comprehensive_security.py::TestEnhancedAuthentication -v

# Run with coverage
pytest app/tests/security/ --cov=app.middleware --cov=app.auth --cov=app.core
```

## Deployment Security

### Environment Configuration:

#### Production Deployment:
- **HTTPS Only**: All traffic over TLS 1.3
- **Environment Variables**: All secrets via environment variables
- **Secret Manager Integration**: Google Cloud Secret Manager
- **Network Security**: VPC isolation and firewall rules
- **Container Security**: Distroless containers, non-root user

#### Security Checklist:
- [ ] All secrets rotated before deployment
- [ ] Security headers configured for production
- [ ] Rate limits appropriately set
- [ ] CORS origins restricted to production domains
- [ ] Database connections secured with TLS
- [ ] Audit logging enabled
- [ ] Monitoring and alerting configured

### Infrastructure Security:

Following `PRODUCTION_SECRETS_ISOLATION.xml`:

#### GCP Security:
- **Project Isolation**: Separate projects for prod/staging/dev
- **IAM Deny Policies**: Block cross-environment access
- **VPC Service Controls**: Network perimeter security
- **Workload Identity**: No service account keys
- **Cloud KMS**: Separate encryption keys per environment

#### Network Security:
- **Private Networks**: No public database access
- **Load Balancer**: HTTPS termination and DDoS protection
- **Firewall Rules**: Minimal required ports
- **VPN Access**: Secure admin access only

## Security Best Practices

### Developer Guidelines:

#### Code Security:
1. **Never hardcode secrets** - Use environment variables or secret manager
2. **Validate all inputs** - Use the enhanced input validator
3. **Use parameterized queries** - No string concatenation for SQL
4. **Escape outputs** - HTML escape all user content
5. **Check authentication** - Verify user permissions for all operations

#### Configuration Security:
1. **Environment-specific configs** - Different settings per environment
2. **Minimal permissions** - Principle of least privilege
3. **Regular rotation** - Rotate secrets and credentials regularly
4. **Audit logging** - Log all security-relevant events
5. **Monitor metrics** - Watch for security anomalies

### Security Review Process:

#### Code Review Checklist:
- [ ] No hardcoded secrets or credentials
- [ ] Input validation for all user inputs
- [ ] Authentication checks for protected endpoints
- [ ] Proper error handling without information disclosure
- [ ] SQL queries use parameterized statements
- [ ] Output encoding for user content
- [ ] Security headers configured
- [ ] Rate limiting applied where appropriate

#### Deployment Checklist:
- [ ] Security tests passing
- [ ] Environment variables configured
- [ ] Secrets rotated and secure
- [ ] Monitoring and alerting enabled
- [ ] Security headers verified
- [ ] HTTPS certificate valid
- [ ] Firewall rules applied
- [ ] Backup and recovery tested

## Incident Response

### Security Incident Classification:

#### Critical (P0):
- Active data breach
- Compromised admin accounts
- SQL injection exploitation
- RCE (Remote Code Execution)

#### High (P1):
- Suspicious admin activity
- Failed authentication spikes
- XSS exploitation
- Unauthorized data access

#### Medium (P2):
- Rate limiting triggered
- Input validation failures
- Session anomalies
- Configuration issues

#### Low (P3):
- Security warnings
- Audit log anomalies
- Performance degradation
- Policy violations

### Response Procedures:

#### Immediate Response (0-15 minutes):
1. **Assess Impact**: Determine scope and severity
2. **Contain Threat**: Block IPs, revoke sessions, disable accounts
3. **Preserve Evidence**: Capture logs and system state
4. **Notify Team**: Alert security team and stakeholders

#### Investigation (15 minutes - 2 hours):
1. **Analyze Logs**: Review security logs and metrics
2. **Identify Root Cause**: Determine attack vector
3. **Assess Damage**: Evaluate what was compromised
4. **Document Findings**: Create incident report

#### Recovery (2-24 hours):
1. **Patch Vulnerabilities**: Fix security issues
2. **Restore Services**: Bring systems back online
3. **Reset Credentials**: Rotate compromised secrets
4. **Validate Security**: Verify fixes are effective

#### Post-Incident (24-72 hours):
1. **Complete Investigation**: Finalize incident report
2. **Update Procedures**: Improve security based on lessons learned
3. **Customer Communication**: Notify affected users if required
4. **Compliance Reporting**: Submit required regulatory reports

## Conclusion

The Netra AI Optimization Platform implements comprehensive security measures across all layers of the application. The security implementation follows industry best practices and provides defense-in-depth protection against common attack vectors.

Key security features include:
- Enhanced authentication with MFA and session security
- Comprehensive input validation and sanitization
- Rate limiting and DDoS protection
- Secure secret management with environment isolation
- Security headers and CORS protection
- SQL injection and XSS prevention
- Comprehensive monitoring and alerting

Regular security testing, monitoring, and incident response procedures ensure the platform maintains a strong security posture. The modular security architecture allows for easy updates and improvements as new threats emerge.

For questions or security concerns, contact the security team or refer to the security specifications in `SPEC/security.xml` and `SPEC/PRODUCTION_SECRETS_ISOLATION.xml`.