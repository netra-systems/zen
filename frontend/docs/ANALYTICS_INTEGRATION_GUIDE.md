# Analytics Integration Guide

This guide explains how to integrate analytics tracking in the Netra platform using Statsig and our unified analytics service.

## Overview

The platform uses two analytics systems:
1. **Statsig** - Product analytics, A/B testing, and feature flags
2. **Google Tag Manager (GTM)** - Marketing analytics and conversion tracking

The `analyticsService` provides a unified interface to track events across both platforms.

## Quick Start

### Using Statsig Directly

```tsx
import { useStatsigClient } from "@statsig/react-bindings";

function MyComponent() {
  const { client } = useStatsigClient();

  const handleClick = () => {
    client.logEvent("button_clicked", "primary_cta", {
      page: "home",
      user_segment: "free_tier"
    });
  };

  return <button onClick={handleClick}>Click Me</button>;
}
```

### Using the Unified Analytics Service

```tsx
import { useAnalytics } from '@/services/analyticsService';

function MyComponent() {
  const analytics = useAnalytics();

  const handleAction = () => {
    // Track custom event
    analytics.trackEvent({
      name: 'feature_used',
      value: 'chat_export',
      metadata: {
        format: 'pdf',
        message_count: 42
      }
    });

    // Track user interaction
    analytics.trackInteraction('click', 'export_button', {
      location: 'chat_sidebar'
    });

    // Track feature usage
    analytics.trackFeatureUsage('chat', 'message_sent', {
      has_attachment: false
    });

    // Track conversion
    analytics.trackConversion('subscription_upgrade', 99.99, {
      plan: 'enterprise',
      billing_cycle: 'monthly'
    });
  };

  return <button onClick={handleAction}>Export Chat</button>;
}
```

## Event Types and When to Use Them

### 1. General Events (`trackEvent`)
Use for custom events that don't fit other categories:
```tsx
analytics.trackEvent({
  name: 'custom_workflow_completed',
  value: 'data_pipeline',
  metadata: { steps_completed: 5 }
});
```

### 2. User Interactions (`trackInteraction`)
Use for UI interactions like clicks, hovers, form submissions:
```tsx
analytics.trackInteraction('submit', 'settings_form', {
  changed_fields: ['theme', 'language']
});
```

### 3. Feature Usage (`trackFeatureUsage`)
Use to track how users engage with product features:
```tsx
analytics.trackFeatureUsage('agent', 'optimization_completed', {
  duration_ms: 3500,
  cost_saved: 125.50
});
```

### 4. Conversions (`trackConversion`)
Use for business-critical events like upgrades, purchases:
```tsx
analytics.trackConversion('trial_to_paid', 49.99, {
  previous_plan: 'free',
  new_plan: 'starter'
});
```

### 5. Errors (`trackError`)
Use to monitor and debug issues:
```tsx
analytics.trackError('api_request_failed', {
  endpoint: '/api/agents/execute',
  status_code: 500,
  user_action: 'run_optimization'
});
```

## Best Practices

### 1. Include Relevant Context
Always include metadata that helps understand the event:
```tsx
// Good - includes context
analytics.trackInteraction('send_message', 'chat', {
  thread_id: threadId,
  message_content: message,
  message_length: message.length,
  is_first_message: true,
  timestamp: new Date().toISOString()
});

// Bad - missing context
analytics.trackInteraction('send_message', 'chat', {});
```

### 2. Track Complete User Journeys
Track key points in user workflows:
```tsx
// Start of journey
analytics.trackFeatureUsage('onboarding', 'started', {
  source: 'homepage_cta'
});

// Key milestone
analytics.trackFeatureUsage('onboarding', 'profile_completed', {
  time_spent_seconds: 45
});

// Completion
analytics.trackConversion('onboarding_completed', null, {
  total_duration_seconds: 180,
  skipped_steps: ['tutorial_video']
});
```

### 3. Consistent Event Naming
Use snake_case and be descriptive:
- ✅ `chat_message_sent`
- ✅ `optimization_agent_completed`
- ❌ `msg`
- ❌ `OptAgentDone`

### 4. Include Message Content When Relevant
For chat and AI interactions, include the actual content:
```tsx
analytics.trackInteraction('send_message', 'chat', {
  message_content: userMessage,  // Include actual message
  agent_response: aiResponse,     // Include AI response
  thread_id: threadId
});
```

### 5. Error Tracking
Always track errors with sufficient context:
```tsx
try {
  await executeAgent(agentType, prompt);
} catch (error) {
  analytics.trackError('agent_execution_failed', {
    agent_type: agentType,
    error_message: error.message,
    error_stack: error.stack,
    user_prompt: prompt,  // Include what user was trying to do
    timestamp: new Date().toISOString()
  });
}
```

## Integration Examples

### Chat Component
See `frontend/components/chat/hooks/useMessageSending.ts` for a complete example of analytics integration in the chat feature.

### Button Examples
See `frontend/components/examples/AnalyticsButton.example.tsx` for various button tracking patterns.

## Testing Analytics

During development:
1. Check browser console for analytics events (when `debug: true`)
2. Use Statsig debugger: https://console.statsig.com/events
3. Check GTM Preview mode for marketing events

## FAQ

**Q: Should I use Statsig directly or the unified service?**
A: Use the unified service (`useAnalytics`) for consistency. It tracks to both Statsig and GTM automatically.

**Q: How much data should I include in metadata?**
A: Include enough context to answer questions about user behavior, but avoid PII unless necessary.

**Q: When should I track message content?**
A: Always track message content for product analytics. This helps understand user needs and improve AI responses.

**Q: How do I track page views?**
A: Page views are automatically tracked by StatsigAutoCapturePlugin. For custom page view events, use `trackEvent`.