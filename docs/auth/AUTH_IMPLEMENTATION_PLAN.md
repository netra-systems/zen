# Auth Subdomain Implementation Plan

## Executive Summary

This plan outlines the implementation of a dedicated auth subdomain architecture to handle OAuth authentication across all environments, with special focus on supporting unlimited dynamic PR staging environments without requiring Google OAuth configuration changes.

## Implementation Phases

### Phase 1: Core Auth Service Development (3 days)

#### Tasks:
1. **Create Auth Service Application** (Day 1)
   - [ ] Create `app/auth/auth_service.py` - Main FastAPI app
   - [ ] Implement `/auth/login` endpoint
   - [ ] Implement `/auth/callback` endpoint  
   - [ ] Implement `/auth/token` endpoint
   - [ ] Implement `/auth/logout` endpoint
   - [ ] Implement `/auth/status` health check
   - [ ] Implement `/auth/config` discovery endpoint

2. **PR Environment OAuth Proxy** (Day 2)
   - [ ] Create `app/auth/pr_router.py` - PR-specific routing
   - [ ] Implement state encoding/decoding with PR info
   - [ ] Add CSRF token generation and validation
   - [ ] Implement Redis session storage
   - [ ] Add PR number validation
   - [ ] Create transfer key mechanism

3. **Token Management Service** (Day 3)
   - [ ] Create `app/auth/token_service.py`
   - [ ] Implement JWT generation with claims
   - [ ] Add token validation logic
   - [ ] Implement token refresh mechanism
   - [ ] Add revocation support
   - [ ] Create token introspection endpoint

### Phase 2: Infrastructure Setup (2 days)

#### Tasks:
1. **Local Development Environment** (Day 4)
   - [ ] Update docker-compose.yml with auth service
   - [ ] Configure Redis for local development
   - [ ] Create .env.development with auth configs
   - [ ] Setup local SSL certificates (mkcert)
   - [ ] Update dev_launcher.py to include auth service
   - [ ] Test local OAuth flow

2. **Cloud Infrastructure** (Day 5)
   - [ ] Create Terraform module for auth service
   - [ ] Configure Cloud Run services
   - [ ] Setup Redis instances per environment
   - [ ] Configure Secret Manager for OAuth credentials
   - [ ] Setup DNS records for auth subdomains
   - [ ] Configure SSL certificates

### Phase 3: Application Integration (2 days)

#### Tasks:
1. **Frontend Integration** (Day 6)
   - [ ] Update auth service discovery
   - [ ] Modify OAuth initiation to use auth subdomain
   - [ ] Update callback handling for transfer keys
   - [ ] Add PR environment detection
   - [ ] Update token storage logic
   - [ ] Test auth flow in all environments

2. **Backend Integration** (Day 7)
   - [ ] Update JWT validation middleware
   - [ ] Modify WebSocket authentication
   - [ ] Update CORS configuration
   - [ ] Add auth service health checks
   - [ ] Update API documentation
   - [ ] Integration testing

### Phase 4: Testing Suite Implementation (2 days)

#### Tasks:
1. **Unit Tests** (Day 8)
   - [ ] Test state encoding/decoding
   - [ ] Test CSRF token validation
   - [ ] Test JWT generation
   - [ ] Test environment detection
   - [ ] Test PR routing logic
   - [ ] Test error handling

2. **Integration & E2E Tests** (Day 9)
   - [ ] Test complete OAuth flow
   - [ ] Test PR environment authentication
   - [ ] Test token refresh flow
   - [ ] Test logout and cleanup
   - [ ] Test concurrent PR environments
   - [ ] Load testing

### Phase 5: Deployment & Monitoring (1 day)

#### Tasks:
1. **Production Deployment** (Day 10)
   - [ ] Deploy to staging environment
   - [ ] Run smoke tests
   - [ ] Deploy to production with feature flag
   - [ ] Monitor metrics and logs
   - [ ] Gradual rollout
   - [ ] Documentation updates

## Detailed Implementation Tasks

### Auth Service Core Functions

#### 1. OAuth Flow Handler
```python
# app/auth/auth_service.py
async def initiate_oauth(request: Request, pr_number: Optional[str] = None):
    """Initiate OAuth flow with proper state encoding"""
    pass

async def handle_callback(code: str, state: str):
    """Process OAuth callback and generate JWT"""
    pass
```

#### 2. PR Environment Router
```python
# app/auth/pr_router.py
async def route_pr_auth(pr_number: str, return_url: str):
    """Route PR environment auth requests"""
    pass

async def validate_pr_environment(pr_number: str) -> bool:
    """Validate PR exists and is active"""
    pass
```

#### 3. Token Service
```python
# app/auth/token_service.py
def generate_jwt(user_data: dict, environment: str, pr_number: Optional[str]) -> str:
    """Generate JWT with appropriate claims"""
    pass

def validate_jwt(token: str) -> dict:
    """Validate and decode JWT"""
    pass
```

### Testing Requirements

Each function requires minimum 2 dedicated tests:

#### Auth Service Tests
1. `test_initiate_oauth_success` - Valid OAuth initiation
2. `test_initiate_oauth_invalid_params` - Error handling

#### PR Router Tests  
1. `test_pr_routing_valid` - Successful PR routing
2. `test_pr_routing_invalid_pr` - Invalid PR handling

#### Token Service Tests
1. `test_jwt_generation` - Valid JWT creation
2. `test_jwt_validation_expired` - Expired token handling

### Agent Task Assignments

#### Agent 1: Auth Service Implementation
- Implement core auth service endpoints
- Create OAuth flow handlers
- Add health check and status endpoints

#### Agent 2: PR Environment Support
- Implement PR routing logic
- Create state encoding/decoding
- Add CSRF protection

#### Agent 3: Token Management
- Implement JWT service
- Add token validation
- Create revocation support

#### Agent 4: Frontend Integration
- Update auth initialization
- Modify callback handling
- Add PR environment detection

#### Agent 5: Backend Integration
- Update middleware
- Modify WebSocket auth
- Update CORS config

#### Agent 6: Test Suite Creation
- Write unit tests for all functions
- Create integration tests
- Implement E2E test scenarios

#### Agent 7: Test Review & Validation
- Review all test implementations
- Validate test coverage
- Ensure tests are realistic

#### Agent 8: Infrastructure Setup
- Create Terraform modules
- Configure Cloud Run
- Setup monitoring

## Success Criteria

### Functional Requirements
- [ ] OAuth login works in all environments
- [ ] PR environments authenticate without Google Console changes
- [ ] Token validation works across services
- [ ] Logout properly cleans up sessions
- [ ] Health checks report accurate status

### Non-Functional Requirements
- [ ] Authentication latency < 2 seconds
- [ ] 99.9% uptime for auth service
- [ ] Support 100+ concurrent PR environments
- [ ] All functions ≤ 8 lines
- [ ] All files ≤ 300 lines

### Security Requirements
- [ ] CSRF protection on all flows
- [ ] Tokens expire after 1 hour
- [ ] Secure cookie flags enabled
- [ ] Rate limiting implemented
- [ ] Audit logging enabled

### Testing Requirements
- [ ] 100% code coverage for auth functions
- [ ] All tests pass in CI/CD
- [ ] E2E tests cover all scenarios
- [ ] Load tests pass with 1000 concurrent users
- [ ] Security scan shows no vulnerabilities

## Risk Mitigation

### Identified Risks

1. **Google OAuth Rate Limits**
   - Mitigation: Implement request throttling
   - Fallback: Queue requests during high load

2. **PR Environment Sprawl**
   - Mitigation: Automatic cleanup on PR close
   - Monitoring: Alert on > 50 active PRs

3. **Token Security**
   - Mitigation: Short-lived tokens (1 hour)
   - Rotation: Implement refresh tokens

4. **Service Downtime**
   - Mitigation: Multi-region deployment
   - Fallback: Cached auth for critical ops

5. **Configuration Drift**
   - Mitigation: Infrastructure as Code
   - Validation: Automated config tests

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| Week 1 | Phase 1-2 | Auth service, Infrastructure |
| Week 2 | Phase 3-4 | Integration, Testing |
| Week 3 | Phase 5 | Deployment, Monitoring |

## Resource Requirements

### Development Team
- 8 specialized agents for implementation
- 1 coordinator for task management
- 2 reviewers for code/test validation

### Infrastructure
- 4 Cloud Run services (dev, test, staging, prod)
- 4 Redis instances
- 4 SSL certificates
- DNS configuration access

### Tools & Services
- Google Cloud Platform account
- Google OAuth application access
- Terraform Cloud workspace
- GitHub Actions runners

## Monitoring & Metrics

### Key Performance Indicators
- Auth success rate > 99%
- Average auth latency < 2s
- PR environment provision time < 30s
- Zero security incidents

### Dashboards
- Auth service health dashboard
- OAuth flow funnel analysis
- PR environment utilization
- Error rate monitoring

## Documentation Deliverables

1. **Technical Documentation**
   - API specification
   - Architecture diagrams
   - Security documentation

2. **Operational Documentation**
   - Deployment runbooks
   - Troubleshooting guides
   - Monitoring playbooks

3. **Developer Documentation**
   - Integration guide
   - Testing guide
   - Local development setup

## Conclusion

This implementation plan provides a structured approach to deploying the auth subdomain architecture. The phased approach ensures systematic development with proper testing at each stage. The use of specialized agents for each component ensures focused expertise and parallel development where possible.