# Issue 1320 - Master Plan: User-Friendly Error Messages

## Executive Summary

**SCOPE DEFINITION:** Create a comprehensive user-friendly error message system that transforms technical failures into actionable user guidance, focusing on common failure scenarios that impact the Golden Path (user login → AI responses).

**DEFINITION OF DONE:**
- Common error types detected and classified with specific error codes
- User-friendly error messages mapped for 20+ identified scenarios
- Clear guidance provided for resolution with fallback to technical details
- Consistent error message formatting across WebSocket, API, and auth flows
- Template-based system for extensible error message management
- Integration with existing ErrorType enum and RecoveryStrategy patterns

## 1. SCOPE DEFINITION

### Primary Focus Areas
1. **Rate Limiting Errors** - API usage limits, time-based restrictions
2. **Authentication Failures** - Token expiry, invalid credentials, OAuth issues
3. **Network & Connectivity** - Timeouts, connection losses, service unavailable
4. **Resource Exhaustion** - Memory limits, queue full, service overload
5. **WebSocket Specific** - Connection drops, message delivery failures
6. **Agent Execution** - Tool failures, processing timeouts, recovery scenarios

### Out of Scope (V1)
- Custom error messages per user tier
- Internationalization/localization
- Error analytics dashboard
- Advanced error routing based on user context

## 2. HOLISTIC RESOLUTION APPROACHES

### 2.1 Infrastructure/Config Changes
**MINIMAL CHANGES REQUIRED:**
- ✅ ErrorType enum already exists with 20+ specific error types
- ✅ RecoveryStrategy enum has 8 recovery approaches
- ✅ WebSocketErrorContext infrastructure in place
- ⚠️ Need to add user_friendly_message field to error response schemas

### 2.2 Code Changes (Primary Implementation)

#### Backend Error Mapping System
```
NEW: /netra_backend/app/core/error_message_service.py
- UserFriendlyErrorMapper class
- Template-based message generation
- Context-aware error classification
- Integration with existing ErrorType/RecoveryStrategy

MODIFY: /netra_backend/app/websocket_core/error_recovery_handler.py
- Add get_user_friendly_message() method to WebSocketErrorRecoveryHandler
- Integrate with UserFriendlyErrorMapper
- Preserve existing error handling logic

MODIFY: /netra_backend/app/schemas/shared_types.py
- Add user_friendly_message field to ErrorContext
- Add recovery_guidance field for actionable steps
```

#### Frontend Error Display Enhancement
```
MODIFY: /frontend/components/ErrorDisplay.tsx
- Add user-friendly message priority display
- Show technical details as expandable section
- Integration with error recovery guidance

NEW: /frontend/components/error/UserFriendlyErrorBoundary.tsx
- Specialized error boundary for user-friendly display
- Context-aware error message selection
- Integration with auth context error tracking
```

#### Auth Service Integration
```
MODIFY: /auth_service/auth_core/oauth/oauth_handler.py
- Extend existing user-friendly error patterns
- Standardize OAuth error message templates
- Align with backend error message service
```

### 2.3 Documentation Updates
- Update API documentation with new error response format
- Create error message style guide for consistency
- Document error classification system for developers

### 2.4 Test Requirements
**Following reports/testing/TEST_CREATION_GUIDE.md patterns:**

#### Unit Tests (Real Service Focus)
```
tests/unit/core/test_user_friendly_error_mapper_unit.py
- Test error classification accuracy
- Validate message template rendering
- Test context-aware message selection

tests/unit/websocket_core/test_error_recovery_user_messages_unit.py
- Test WebSocket error message integration
- Validate recovery guidance generation
- Test fallback behavior for unknown errors
```

#### Integration Tests (Non-Docker)
```
tests/integration/error_handling/test_user_friendly_error_flow_integration.py
- Test complete error flow from WebSocket to frontend
- Validate auth error message consistency
- Test error message delivery across services

tests/integration/api/test_error_response_format_integration.py
- Test API error response format compliance
- Validate error message template consistency
- Test recovery guidance delivery
```

#### E2E Staging Tests
```
tests/e2e/error_handling/test_user_friendly_error_display_e2e.py
- Test actual user-facing error scenarios
- Validate error message display in real browser
- Test error recovery guidance effectiveness
```

### 2.5 Other Approaches
- Error message A/B testing framework (future enhancement)
- User feedback collection on error message clarity (future)
- Integration with monitoring/alerting for error pattern detection

## 3. IMPLEMENTATION STRATEGY

### Phase 1: Core Error Message Service (Week 1)
1. **Create UserFriendlyErrorMapper service**
   - Map existing ErrorType enum to user-friendly messages
   - Implement template-based message system
   - Add context-aware message selection logic

2. **Update error response schemas**
   - Add user_friendly_message to ErrorContext
   - Add recovery_guidance field
   - Maintain backward compatibility

3. **Unit test coverage for error mapping**
   - Test all 20+ ErrorType mappings
   - Validate template rendering accuracy
   - Test context-aware message selection

### Phase 2: WebSocket Integration (Week 2)
1. **Integrate with WebSocket error recovery**
   - Modify WebSocketErrorRecoveryHandler
   - Add get_user_friendly_message() method
   - Preserve existing error handling logic

2. **Frontend error display enhancement**
   - Update ErrorDisplay component
   - Add user-friendly message priority
   - Implement expandable technical details

3. **Integration test coverage**
   - Test WebSocket error message flow
   - Validate frontend error display
   - Test error recovery guidance

### Phase 3: Auth Service Alignment (Week 3)
1. **Standardize OAuth error messages**
   - Align with UserFriendlyErrorMapper patterns
   - Update existing user-friendly error messages
   - Ensure consistency across auth flows

2. **API error response integration**
   - Update REST API error responses
   - Add user-friendly messages to all error endpoints
   - Maintain API backward compatibility

3. **E2E staging test validation**
   - Test complete user-facing error scenarios
   - Validate error message effectiveness
   - Test recovery guidance accuracy

## 4. SPECIFIC ERROR MESSAGE EXAMPLES

### Rate Limiting
```
Technical: "RATE_LIMIT_EXCEEDED: 429 Too Many Requests"
User-Friendly: "5-hour limit reached • resets 2pm /upgrade to increase your usage limit"
Recovery: "Wait until 2pm or upgrade your plan for higher limits"
```

### Authentication
```
Technical: "TOKEN_EXPIRED: JWT token has expired"
User-Friendly: "Session expired • please sign in again"
Recovery: "Click the sign in button to continue"
```

### Network Issues
```
Technical: "CONNECTION_TIMEOUT: WebSocket connection timed out after 30s"
User-Friendly: "Connection timeout • check your internet and try again"
Recovery: "Refresh the page or check your network connection"
```

### Service Unavailable
```
Technical: "SERVICE_UNAVAILABLE: Backend service returning 503"
User-Friendly: "AI service temporarily unavailable • we're working to restore it"
Recovery: "Try again in a few minutes or contact support if this persists"
```

## 5. ARCHITECTURE INTEGRATION

### Existing Infrastructure Leveraged
- ✅ ErrorType enum (20+ error types) in error_recovery_handler.py
- ✅ RecoveryStrategy enum (8 strategies) for guidance generation
- ✅ WebSocketErrorContext for error metadata
- ✅ OAuth user-friendly error patterns in oauth_handler.py
- ✅ Frontend ErrorDisplay component infrastructure
- ✅ Auth context error tracking with trackError()

### New Components Required
- UserFriendlyErrorMapper service (new)
- Error message template system (new)
- Enhanced error response schemas (modification)
- User-friendly error boundary component (new)

### Integration Points
- WebSocket error recovery handler integration
- API error response middleware enhancement
- Frontend error display component updates
- Auth service error message alignment

## 6. TESTING STRATEGY

### Test Philosophy Alignment
- **Real Services > Mocks:** Use actual error scenarios, not mocked failures
- **Business Value Focus:** Test user experience impact, not just technical functionality
- **Factory Pattern Compliance:** Ensure user isolation in error scenarios

### Coverage Requirements
- **Unit Tests:** 95% coverage of error mapping logic
- **Integration Tests:** Complete error flow validation across services
- **E2E Tests:** Real user-facing error scenario validation
- **Mission Critical:** WebSocket agent event error handling validation

### Test Data Strategy
- Use real error scenarios from production logs
- Create reproducible error conditions
- Test error message effectiveness with actual failure modes

## 7. RISKS & MITIGATION

### Implementation Risks
1. **Breaking Changes to Error Handling**
   - Mitigation: Maintain backward compatibility, add fields incrementally

2. **Performance Impact of Error Message Generation**
   - Mitigation: Cache templates, minimize computation overhead

3. **Inconsistent Error Message Quality**
   - Mitigation: Create style guide, implement validation tests

### Business Risks
1. **User Confusion from Poor Error Messages**
   - Mitigation: User testing of error messages, clear recovery guidance

2. **Support Load from Unclear Guidance**
   - Mitigation: Include escalation paths, "contact support" guidance

## 8. SUCCESS METRICS

### Technical Metrics
- Error message coverage: 95% of ErrorType enum mapped
- Response time impact: <10ms overhead for error message generation
- Test coverage: 90%+ for error handling flows

### Business Metrics
- User error recovery success rate increase
- Support ticket reduction for common errors
- User satisfaction with error clarity (future metric)

## 9. NEXT STEPS

1. **Technical Review** - Validate approach with existing error infrastructure
2. **Message Content Review** - Define style guide and message templates
3. **Implementation Start** - Begin Phase 1 with core error mapper service
4. **Stakeholder Feedback** - Collect input on error message effectiveness

This plan leverages existing robust error infrastructure while adding the missing user-friendly layer, ensuring minimal disruption to current error handling while significantly improving user experience during failure scenarios.