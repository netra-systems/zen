# Google Tag Manager Integration - User Guide

## Overview
Google Tag Manager (GTM) has been integrated into the Netra Apex platform to provide comprehensive analytics tracking, conversion monitoring, and marketing optimization capabilities.

**Container ID:** `GTM-WKP28PNQ`

## Table of Contents
- [For Developers](#for-developers)
- [For Marketing Teams](#for-marketing-teams)
- [For Product Managers](#for-product-managers)
- [Troubleshooting](#troubleshooting)

---

## For Developers

### Quick Start
The GTM integration is already configured in the application. No additional setup is required for basic functionality.

### Tracking Events in Your Components

#### 1. Basic Event Tracking
```typescript
import { useGTMEvent } from '@/hooks/useGTMEvent';

function MyComponent() {
  const { trackEngagement } = useGTMEvent();
  
  const handleFeatureClick = () => {
    trackEngagement('feature_used', {
      feature_name: 'advanced_search',
      session_id: sessionId
    });
  };
  
  return <button onClick={handleFeatureClick}>Use Feature</button>;
}
```

#### 2. Authentication Events
```typescript
import { useGTMEvent } from '@/hooks/useGTMEvent';

function LoginComponent() {
  const { trackLogin, trackSignup } = useGTMEvent();
  
  const handleLogin = async (method: string) => {
    // Your login logic
    await authenticateUser();
    
    // Track the login event
    trackLogin(method, isNewUser);
  };
  
  const handleSignup = async () => {
    // Your signup logic
    await createUser();
    
    // Track the signup event
    trackSignup('email');
  };
}
```

#### 3. Conversion Events
```typescript
import { useGTMEvent } from '@/hooks/useGTMEvent';

function PricingPage() {
  const { trackTrialStart, trackPlanUpgrade } = useGTMEvent();
  
  const handleTrialStart = () => {
    trackTrialStart();
  };
  
  const handleUpgrade = (plan: string, value: number) => {
    trackPlanUpgrade(plan, value);
  };
}
```

#### 4. Custom Events
```typescript
import { useGTM } from '@/hooks/useGTM';

function CustomComponent() {
  const { events } = useGTM();
  
  const trackCustomEvent = () => {
    events.trackCustom({
      event: 'custom_interaction',
      event_category: 'engagement',
      custom_param_1: 'value1',
      custom_param_2: 'value2'
    });
  };
}
```

### Debug Mode

#### Enable Debug Mode
Set the environment variable:
```bash
NEXT_PUBLIC_GTM_DEBUG=true
```

#### Using Debug Tools
```typescript
import { useGTMDebug } from '@/hooks/useGTMDebug';

function DebugComponent() {
  const { exportDebugData, validateEvent } = useGTMDebug();
  
  // Export all GTM data to console
  const handleDebug = () => {
    const data = exportDebugData();
    console.log('GTM Debug Data:', data);
  };
  
  // Validate an event before sending
  const sendValidatedEvent = () => {
    const event = { event: 'test_event', value: 100 };
    if (validateEvent(event)) {
      // Event is valid, proceed
    }
  };
}
```

### Environment Configuration

#### Development
```env
NEXT_PUBLIC_GTM_ENABLED=false
NEXT_PUBLIC_GTM_DEBUG=true
```

#### Staging
```env
NEXT_PUBLIC_GTM_ENABLED=true
NEXT_PUBLIC_GTM_DEBUG=true
```

#### Production
```env
NEXT_PUBLIC_GTM_ENABLED=true
NEXT_PUBLIC_GTM_DEBUG=false
```

---

## For Marketing Teams

### Accessing GTM Data

#### 1. Google Tag Manager Console
1. Log in to [Google Tag Manager](https://tagmanager.google.com/)
2. Select container: **GTM-WKP28PNQ**
3. View real-time data in the Preview mode

#### 2. Google Analytics Integration
1. Events automatically flow to Google Analytics (if configured)
2. Access reports at [Google Analytics](https://analytics.google.com/)
3. View conversions, user behavior, and custom reports

### Key Events to Track

#### User Journey Events
| Event Name | Description | When It Fires |
|------------|-------------|---------------|
| `user_signup` | New user registration | User completes signup |
| `user_login` | User authentication | User logs in successfully |
| `demo_completed` | Enterprise demo completion | User finishes demo |
| `first_agent_activation` | First AI agent usage | User activates any agent |

#### Conversion Events
| Event Name | Description | Value Tracking |
|------------|-------------|----------------|
| `trial_started` | Free trial activation | Trial type |
| `plan_upgraded` | Subscription upgrade | Plan value, currency |
| `payment_completed` | Payment processed | Transaction amount |
| `demo_requested` | Sales demo request | Lead information |

#### Engagement Events
| Event Name | Description | Key Parameters |
|------------|-------------|----------------|
| `chat_started` | Chat session begins | Thread ID, Session ID |
| `message_sent` | User sends message | Message count |
| `agent_activated` | AI agent triggered | Agent type |
| `feature_used` | Feature interaction | Feature name |

### Creating Marketing Campaigns

#### UTM Parameters
Add UTM parameters to your campaign URLs:
```
https://app.netrasystems.ai/?utm_source=email&utm_medium=newsletter&utm_campaign=q4_2024
```

These are automatically tracked and associated with user events.

#### A/B Testing
GTM supports A/B testing through:
1. Google Optimize integration
2. Custom event parameters for test variants
3. Conversion tracking per variant

---

## For Product Managers

### Analyzing User Behavior

#### Feature Adoption Metrics
Track how users interact with new features:
```javascript
// Automatically tracked events
- feature_discovered
- feature_first_use
- feature_repeated_use
- feature_mastery
```

#### User Segments
Data is automatically segmented by:
- Customer tier (Free, Early, Mid, Enterprise)
- Authentication status
- User lifecycle stage
- Geographic location

### Setting Up Custom Reports

#### 1. Conversion Funnels
Monitor the complete user journey:
```
Landing Page → Signup → First Login → Feature Discovery → First Value → Conversion
```

#### 2. Cohort Analysis
Track user cohorts over time:
- Weekly/Monthly cohorts
- Feature adoption rates
- Retention metrics
- Revenue per cohort

#### 3. Product Health Metrics
- Daily Active Users (DAU)
- Feature usage frequency
- Error rates and recovery
- Performance metrics

### Data Privacy & Compliance

#### GDPR Compliance
- User consent is managed automatically
- PII is never sent to GTM
- Users can opt-out via settings

#### Data Retention
- Event data: 14 months (Google Analytics default)
- User data: Configurable based on requirements
- Aggregated data: Unlimited

---

## Troubleshooting

### Common Issues

#### Events Not Appearing
1. **Check if GTM is enabled:**
   ```typescript
   import { useGTM } from '@/hooks/useGTM';
   const { isEnabled } = useGTM();
   console.log('GTM Enabled:', isEnabled);
   ```

2. **Verify in GTM Preview Mode:**
   - Open GTM console
   - Click "Preview" button
   - Navigate to your site
   - Check the debug panel

3. **Check browser console:**
   ```javascript
   // In browser console
   console.log(window.dataLayer);
   ```

#### Performance Issues
1. **Monitor Core Web Vitals:**
   - GTM should add < 100ms to page load
   - Check Network tab in DevTools

2. **Reduce event frequency:**
   - Batch similar events
   - Use sampling for high-frequency events

#### Debug Mode Not Working
1. Clear browser cache
2. Restart development server
3. Verify environment variable is set

### Testing GTM Implementation

#### Manual Testing
1. Enable GTM Preview Mode
2. Perform user actions
3. Verify events in Preview panel
4. Check Google Analytics real-time reports

#### Automated Testing
```bash
# Run GTM-specific tests
npm test -- --grep gtm

# Run integration tests
npm run test:integration

# Run E2E tests with Cypress
npm run cypress:open
```

### Support & Resources

#### Internal Resources
- Technical issues: Contact Engineering Team
- Analytics questions: Contact Data Team
- Marketing setup: Contact Marketing Ops

#### External Resources
- [GTM Documentation](https://developers.google.com/tag-manager)
- [Google Analytics Help](https://support.google.com/analytics)
- [GTM Community](https://www.gtm-community.com)

### Best Practices

#### Do's ✅
- Always test events in Preview Mode first
- Use consistent event naming conventions
- Include relevant context in event parameters
- Monitor performance impact
- Document custom events

#### Don'ts ❌
- Never send PII (emails, passwords, etc.)
- Don't track events in tight loops
- Avoid blocking code on GTM operations
- Don't create duplicate events
- Never hardcode sensitive data

---

## Appendix: Event Reference

### Complete Event Taxonomy

```typescript
// Authentication Events
'user_login'          // User signs in
'user_signup'         // New user registration
'user_logout'         // User signs out
'oauth_complete'      // OAuth flow completed

// Engagement Events
'chat_started'        // Chat session initiated
'message_sent'        // Message sent in chat
'agent_activated'     // AI agent triggered
'thread_created'      // New thread created
'feature_used'        // Feature interaction

// Conversion Events
'trial_started'       // Trial activated
'plan_upgraded'       // Plan upgrade completed
'payment_completed'   // Payment processed
'demo_requested'      // Demo request submitted

// Custom Events
'custom_event'        // Your custom events
```

### Testing Checklist

- [ ] GTM script loads successfully
- [ ] Events appear in Preview Mode
- [ ] Events flow to Google Analytics
- [ ] No console errors
- [ ] Performance metrics acceptable
- [ ] Privacy compliance verified
- [ ] Cross-browser compatibility confirmed
- [ ] Mobile functionality tested

---

*Last Updated: 2025-08-28*
*Version: 1.0.0*