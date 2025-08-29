# Google Analytics 4 Automation Report
## Complete Configuration for Netra Apex Platform

**Generated**: 2025-08-29
**GA4 Measurement ID**: G-522Q06C6M5
**GTM Container ID**: GTM-WKP28PNQ
**Account ID**: 6310197060

---

## Executive Summary

This report contains all specifications required to automatically configure Google Analytics 4 for the Netra Apex platform. The configuration has been designed to track user behavior, conversions, and engagement metrics across all customer tiers (Free, Early, Mid, Enterprise).

---

## 1. Property Configuration

### Basic Settings
```json
{
  "property_name": "Netra Apex Platform",
  "industry_category": "Technology",
  "reporting_time_zone": "America/Los_Angeles",
  "currency": "USD",
  "data_retention": "14 months",
  "ads_personalization": true,
  "enhanced_measurement": true
}
```

### Data Stream Configuration
```json
{
  "stream_name": "Netra Web Platform",
  "stream_url": "https://netrasystems.ai",
  "measurement_id": "G-522Q06C6M5",
  "enhanced_measurement_settings": {
    "page_views": true,
    "scrolls": true,
    "outbound_clicks": true,
    "site_search": true,
    "video_engagement": true,
    "file_downloads": true,
    "form_interactions": true,
    "page_changes_based_on_browser_history": true
  }
}
```

---

## 2. Custom Dimensions

### User-Scoped Dimensions
These persist across all events for a user:

| Dimension Name | API Name | Description | Scope |
|---------------|----------|-------------|-------|
| User Tier | user_tier | Subscription level (free/early/mid/enterprise) | USER |
| User ID | user_id | Unique identifier for cross-device tracking | USER |
| First Touch Source | first_touch_source | Original acquisition source | USER |
| Account Created Date | account_created_date | Timestamp of account creation | USER |

### Event-Scoped Dimensions
These are specific to individual events:

| Dimension Name | API Name | Description | Scope |
|---------------|----------|-------------|-------|
| Agent Type | agent_type | AI agent being used | EVENT |
| Feature Type | feature_type | Platform feature being used | EVENT |
| Auth Method | auth_method | Authentication method (email/google/oauth) | EVENT |
| Thread ID | thread_id | Chat conversation identifier | EVENT |
| Session Duration | session_duration | Length of user session | EVENT |
| Message Length | message_length | Character count of messages | EVENT |
| Plan Type | plan_type | Target plan for upgrades | EVENT |
| Conversion Source | conversion_source | Campaign/source of conversion | EVENT |

---

## 3. Custom Metrics

| Metric Name | API Name | Type | Unit | Scope | Description |
|------------|----------|------|------|-------|-------------|
| Session Duration | session_duration_seconds | NUMBER | STANDARD | EVENT | Time spent in session |
| Message Count | message_count | NUMBER | STANDARD | EVENT | Messages sent per session |
| Agent Activations | agent_activation_count | NUMBER | STANDARD | EVENT | Number of AI agents used |
| Feature Usage Score | feature_usage_score | NUMBER | STANDARD | EVENT | Weighted feature engagement |
| API Calls | api_call_count | NUMBER | STANDARD | EVENT | API requests per session |
| Thread Length | thread_message_count | NUMBER | STANDARD | EVENT | Messages per thread |

---

## 4. Conversion Events

Events that should be marked as conversions in GA4:

```json
{
  "conversion_events": [
    {
      "event_name": "sign_up",
      "description": "New user registration",
      "value_parameter": null,
      "counting_method": "ONCE_PER_EVENT"
    },
    {
      "event_name": "trial_start",
      "description": "Free trial activation",
      "value_parameter": null,
      "counting_method": "ONCE_PER_EVENT"
    },
    {
      "event_name": "purchase",
      "description": "Successful payment completion",
      "value_parameter": "value",
      "counting_method": "ONCE_PER_EVENT"
    },
    {
      "event_name": "plan_upgraded",
      "description": "Subscription tier upgrade",
      "value_parameter": "value",
      "counting_method": "ONCE_PER_EVENT"
    },
    {
      "event_name": "demo_requested",
      "description": "Enterprise demo request",
      "value_parameter": null,
      "counting_method": "ONCE_PER_EVENT"
    },
    {
      "event_name": "first_agent_activation",
      "description": "First AI agent usage",
      "value_parameter": null,
      "counting_method": "ONCE_PER_EVENT"
    }
  ]
}
```

---

## 5. Event Taxonomy

### Authentication Events
```json
{
  "user_login": {
    "parameters": ["auth_method", "user_tier", "is_new_user"],
    "trigger": "User successfully logs in"
  },
  "user_signup": {
    "parameters": ["auth_method", "referral_source"],
    "trigger": "New account created"
  },
  "user_logout": {
    "parameters": ["session_duration"],
    "trigger": "User logs out"
  },
  "oauth_complete": {
    "parameters": ["provider", "is_new_user"],
    "trigger": "OAuth flow completed"
  }
}
```

### Engagement Events
```json
{
  "chat_started": {
    "parameters": ["thread_id", "session_id", "user_tier"],
    "trigger": "New chat session initiated"
  },
  "message_sent": {
    "parameters": ["thread_id", "message_length", "message_count"],
    "trigger": "User sends message"
  },
  "agent_activated": {
    "parameters": ["agent_type", "thread_id", "activation_count"],
    "trigger": "AI agent triggered"
  },
  "thread_created": {
    "parameters": ["thread_id", "initial_prompt_length"],
    "trigger": "New conversation thread"
  },
  "feature_used": {
    "parameters": ["feature_type", "feature_category", "usage_count"],
    "trigger": "Platform feature interaction"
  }
}
```

### Conversion Events
```json
{
  "trial_started": {
    "parameters": ["plan_type", "trial_length"],
    "trigger": "Free trial activated"
  },
  "plan_upgraded": {
    "parameters": ["plan_type", "previous_plan", "value"],
    "trigger": "Subscription upgrade"
  },
  "payment_completed": {
    "parameters": ["transaction_id", "value", "currency", "plan_type"],
    "trigger": "Successful payment"
  },
  "demo_requested": {
    "parameters": ["company_size", "industry", "contact_email"],
    "trigger": "Enterprise demo form submitted"
  }
}
```

---

## 6. Audiences

### Predefined Audiences to Create

```json
{
  "audiences": [
    {
      "name": "Active Free Users",
      "description": "Free tier users active in last 7 days",
      "conditions": {
        "user_tier": "free",
        "days_since_last_active": "<=7"
      }
    },
    {
      "name": "Trial Ready to Convert",
      "description": "Trial users with high engagement",
      "conditions": {
        "user_tier": "free",
        "event_count": ">=10",
        "days_since_signup": ">=3"
      }
    },
    {
      "name": "Paid Users",
      "description": "All paying customers",
      "conditions": {
        "user_tier": ["early", "mid", "enterprise"]
      }
    },
    {
      "name": "High Value Prospects",
      "description": "Users showing enterprise behaviors",
      "conditions": {
        "agent_activation_count": ">=5",
        "session_duration": ">=300",
        "feature_usage_score": ">=50"
      }
    },
    {
      "name": "Churn Risk",
      "description": "Paid users with declining usage",
      "conditions": {
        "user_tier": ["early", "mid"],
        "days_since_last_active": ">=14"
      }
    },
    {
      "name": "Power Users",
      "description": "Highly engaged users",
      "conditions": {
        "message_count": ">=50",
        "agent_activation_count": ">=20",
        "days_active_last_30": ">=15"
      }
    }
  ]
}
```

---

## 7. User Properties

Properties to set at the user level:

```json
{
  "user_properties": {
    "user_id": {
      "description": "Unique user identifier",
      "type": "string"
    },
    "user_tier": {
      "description": "Subscription level",
      "type": "string",
      "values": ["free", "early", "mid", "enterprise"]
    },
    "signup_date": {
      "description": "Account creation timestamp",
      "type": "number"
    },
    "first_touch_source": {
      "description": "Original acquisition channel",
      "type": "string"
    },
    "lifetime_value": {
      "description": "Total revenue from user",
      "type": "number"
    },
    "company_size": {
      "description": "For B2B segmentation",
      "type": "string",
      "values": ["1-10", "11-50", "51-200", "201-1000", "1000+"]
    }
  }
}
```

---

## 8. Explorations (Reports) to Create

### Key Reports Configuration

```json
{
  "explorations": [
    {
      "name": "User Journey Analysis",
      "type": "path_exploration",
      "dimensions": ["event_name", "user_tier", "page_path"],
      "metrics": ["event_count", "users", "conversion_rate"],
      "segments": ["paid_users", "trial_users"]
    },
    {
      "name": "Conversion Funnel",
      "type": "funnel_exploration",
      "steps": [
        "sign_up",
        "first_agent_activation",
        "trial_started",
        "payment_completed"
      ],
      "breakdown_dimension": "first_touch_source"
    },
    {
      "name": "Cohort Retention",
      "type": "cohort_exploration",
      "cohort_dimension": "first_touch_date",
      "return_criterion": "agent_activated",
      "granularity": "week"
    },
    {
      "name": "Feature Adoption Matrix",
      "type": "free_form",
      "dimensions": ["feature_type", "user_tier"],
      "metrics": ["users", "event_count", "avg_engagement_time"]
    },
    {
      "name": "Revenue Attribution",
      "type": "free_form",
      "dimensions": ["source_medium", "campaign"],
      "metrics": ["purchase_revenue", "conversions", "ROAS"]
    }
  ]
}
```

---

## 9. Google Analytics Admin API Configuration

### API Scopes Required
```
https://www.googleapis.com/auth/analytics.edit
https://www.googleapis.com/auth/analytics.manage.users
https://www.googleapis.com/auth/analytics.readonly
```

### Service Account Permissions
The service account `netra-staging-deploy@netra-staging.iam.gserviceaccount.com` needs:
- Editor access to GA4 property
- User management permissions

### API Endpoints to Use

```json
{
  "api_version": "v1beta",
  "base_url": "https://analyticsadmin.googleapis.com",
  "key_endpoints": {
    "custom_dimensions": "/properties/{property}/customDimensions",
    "custom_metrics": "/properties/{property}/customMetrics",
    "conversion_events": "/properties/{property}/conversionEvents",
    "audiences": "/properties/{property}/audiences",
    "data_streams": "/properties/{property}/dataStreams"
  }
}
```

---

## 10. Implementation Checklist

### Pre-Implementation
- [ ] GA4 property exists with ID: G-522Q06C6M5
- [ ] Service account has Editor access to GA4
- [ ] Google Analytics Admin API is enabled in GCP
- [ ] GTM container is published and live

### Configuration Steps
1. [ ] Configure enhanced measurement settings
2. [ ] Create all custom dimensions (user & event scoped)
3. [ ] Create all custom metrics
4. [ ] Mark conversion events
5. [ ] Configure user properties
6. [ ] Create audiences
7. [ ] Set up explorations/reports
8. [ ] Configure data retention settings
9. [ ] Set up BigQuery export (optional)
10. [ ] Configure attribution settings

### Post-Implementation Testing
- [ ] Verify events flow from GTM to GA4
- [ ] Check custom dimensions are populating
- [ ] Validate conversion tracking
- [ ] Test audience building
- [ ] Verify reports are generating data

---

## 11. Monitoring & Alerts

### Custom Insights to Configure

```json
{
  "alerts": [
    {
      "name": "Traffic Drop Alert",
      "condition": "users decrease by 30% day over day",
      "frequency": "daily",
      "recipients": ["analytics@netrasystems.ai"]
    },
    {
      "name": "Conversion Rate Change",
      "condition": "conversion_rate changes by 20% week over week",
      "frequency": "weekly",
      "recipients": ["analytics@netrasystems.ai"]
    },
    {
      "name": "New User Spike",
      "condition": "new_users increase by 100% day over day",
      "frequency": "hourly",
      "recipients": ["analytics@netrasystems.ai"]
    },
    {
      "name": "Revenue Goal",
      "condition": "purchase_revenue >= 10000",
      "frequency": "daily",
      "recipients": ["leadership@netrasystems.ai"]
    }
  ]
}
```

---

## 12. Data Quality Validation

### Required Validations

```json
{
  "validations": [
    {
      "test": "Event Volume",
      "expected": ">1000 events per day",
      "query": "SELECT COUNT(*) FROM events WHERE date = CURRENT_DATE"
    },
    {
      "test": "User ID Population",
      "expected": ">90% events have user_id",
      "query": "SELECT AVG(CASE WHEN user_id IS NOT NULL THEN 1 ELSE 0 END) FROM events"
    },
    {
      "test": "Conversion Tracking",
      "expected": "All conversion events firing",
      "query": "SELECT event_name, COUNT(*) FROM events WHERE is_conversion = true GROUP BY event_name"
    },
    {
      "test": "Custom Dimension Population",
      "expected": "All custom dimensions have data",
      "query": "SELECT dimension_name, COUNT(DISTINCT value) FROM custom_dimensions GROUP BY dimension_name"
    }
  ]
}
```

---

## Notes for Implementation

1. **Rate Limits**: GA4 Admin API has rate limits. Implement exponential backoff.
2. **Dimension Limits**: GA4 allows 25 user-scoped and 50 event-scoped custom dimensions.
3. **Metric Limits**: GA4 allows 50 custom metrics per property.
4. **Audience Limits**: GA4 allows 100 audiences per property.
5. **Data Freshness**: Custom dimensions take 24-48 hours to populate in reports.
6. **BigQuery Export**: Recommended for advanced analysis and data retention beyond 14 months.

---

**Report Generated By**: GTM/GA4 Automation System
**Last Updated**: 2025-08-29
**Status**: Ready for Implementation