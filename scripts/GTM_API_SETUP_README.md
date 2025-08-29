# Google Tag Manager API Configuration

## Overview
This suite of scripts provides automated configuration of Google Tag Manager (GTM) containers via the GTM API, enabling complete integration with Google Analytics 4 and the Netra Apex platform.

## Components

### 1. `gtm_api_setup.py`
Main configuration script that creates:
- **Variables**: All data layer variables, URL variables, JavaScript variables, and constants
- **Triggers**: Event triggers for authentication, engagement, and conversion events
- **Tags**: Google Analytics 4 configuration and event tags

### 2. `gtm_config.json`
Configuration file containing:
- Account and container IDs
- Service account details
- Variable definitions
- Event taxonomy
- Google Analytics settings

### 3. `run_gtm_setup.py`
Simplified runner script that:
- Checks and installs dependencies
- Locates service account credentials
- Executes the configuration

## Prerequisites

### 1. Enable GTM API
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project (netra-staging)
3. Navigate to APIs & Services > Library
4. Search for "Tag Manager API"
5. Click Enable

### 2. Service Account Setup
The existing service account `netra-staging-deploy@netra-staging.iam.gserviceaccount.com` needs GTM permissions:

1. Go to [Google Tag Manager](https://tagmanager.google.com)
2. Navigate to Admin > User Management
3. Add the service account email
4. Grant "Publish" permission level

### 3. Python Dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## Quick Start

### Using the Simplified Runner
```bash
python scripts/run_gtm_setup.py
```

### Manual Configuration
```bash
python scripts/gtm_api_setup.py \
  --account-id 6000000000 \
  --container-id GTM-WKP28PNQ \
  --credentials path/to/netra-staging-sa-key.json \
  --ga4-id G-XXXXXXXXXX
```

## Configuration Details

### Variables Created

#### Data Layer Variables
- `DLV - Event Category`: Event categorization
- `DLV - Event Action`: Specific action taken
- `DLV - Event Label`: Additional context
- `DLV - Event Value`: Numeric value
- `DLV - User ID`: Cross-session tracking
- `DLV - Session ID`: Session identification
- `DLV - User Tier`: Subscription level
- `DLV - Auth Method`: Authentication type
- `DLV - Feature Type`: Feature being used
- `DLV - Agent Type`: AI agent type
- `DLV - Thread ID`: Chat thread ID
- `DLV - Transaction ID`: Purchase identifier
- `DLV - Transaction Value`: Monetary amount
- `DLV - Plan Type`: Subscription plan
- `DLV - Currency`: Currency code

#### JavaScript Variables
- `JS - Timestamp`: Current ISO timestamp
- `JS - Client ID`: Persistent GA client ID
- `JS - Session Duration`: Time in session

#### URL Variables
- `URL - Full`: Complete page URL
- `URL - Path`: URL path only
- `URL - Hostname`: Domain name

#### Constants
- `Const - GA4 Measurement ID`: Your GA4 property ID
- `Const - GTM Container ID`: GTM-WKP28PNQ
- `Const - Environment`: Current environment

### Triggers Created

#### Authentication Events
- User Login
- User Signup
- User Logout
- OAuth Complete

#### Engagement Events
- Chat Started
- Message Sent
- Agent Activated
- Thread Created
- Feature Used

#### Conversion Events
- Trial Started
- Plan Upgraded
- Payment Completed
- Demo Requested

### Tags Created

#### GA4 Configuration
- Base configuration tag with user ID and session tracking

#### Event Tags
- Authentication events (login, signup)
- Engagement events (chat, agent activation)
- Conversion events (trial, purchase)
- Generic event handler for custom events

## Google Analytics 4 Integration

### Setting Up GA4

1. **Create GA4 Property** (if not exists):
   - Go to [Google Analytics](https://analytics.google.com)
   - Admin > Create Property
   - Select "Web" platform
   - Enter property details

2. **Get Measurement ID**:
   - Admin > Data Streams
   - Select your web stream
   - Copy the Measurement ID (G-XXXXXXXXXX)

3. **Update Configuration**:
   ```json
   {
     "ga4_measurement_id": "G-YOUR_ACTUAL_ID"
   }
   ```

### Custom Dimensions & Metrics

The script configures custom dimensions and metrics for enhanced tracking:

#### Custom Dimensions
- User Tier (User-scoped)
- Agent Type (Event-scoped)
- Feature Type (Event-scoped)
- Thread ID (Session-scoped)

#### Custom Metrics
- Session Duration (Time format)
- Message Count (Integer format)

## Testing & Validation

### 1. Preview Mode Testing
```javascript
// In browser console
window.dataLayer.push({
  event: 'user_login',
  event_category: 'authentication',
  auth_method: 'email',
  user_tier: 'free'
});
```

### 2. GTM Preview
1. Open GTM console
2. Click "Preview" button
3. Enter your website URL
4. Verify events fire correctly

### 3. GA4 Real-Time
1. Open GA4 property
2. Navigate to Reports > Real-time
3. Trigger test events
4. Verify data appears

## Troubleshooting

### Common Issues

#### Authentication Errors
```bash
# Set credentials explicitly
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/netra-staging-sa-key.json
```

#### Permission Denied
- Verify service account has GTM Editor/Publisher role
- Check container ID is correct
- Ensure API is enabled in GCP

#### Variables Not Capturing Data
- Check data layer push format matches variable names
- Verify variable names in GTM match code exactly
- Use GTM Preview mode to debug

#### Events Not Reaching GA4
- Confirm GA4 Measurement ID is correct
- Check network tab for collect requests
- Verify no ad blockers are interfering

### Debug Commands

```bash
# Test API access
python -c "from googleapiclient.discovery import build; print('API accessible')"

# Verify credentials
gcloud auth application-default print-access-token

# List GTM containers
python scripts/gtm_api_setup.py --list-containers
```

## Best Practices

### 1. Version Control
- Always create versions before major changes
- Use descriptive version names
- Document changes in version notes

### 2. Testing Workflow
1. Create changes in workspace
2. Test in Preview mode
3. Create version
4. Publish to limited percentage
5. Monitor for issues
6. Full publish

### 3. Naming Conventions
- Variables: `DLV - ` for data layer, `JS - ` for JavaScript
- Triggers: Descriptive event names
- Tags: `GA4 - ` prefix for Analytics tags

### 4. Performance
- Minimize custom JavaScript
- Use built-in variables when possible
- Batch similar events
- Set appropriate trigger conditions

## Security Considerations

### Service Account Key Management
- Never commit keys to version control
- Use environment variables or secret managers
- Rotate keys periodically
- Limit key permissions to minimum required

### Data Privacy
- Never send PII to GTM/GA4
- Hash user IDs before sending
- Respect user consent preferences
- Implement data retention policies

## Support & Resources

### Internal Documentation
- [GTM Usage Guide](../docs/GTM_USAGE_GUIDE.md)
- [Frontend GTM Types](../frontend/types/gtm.types.ts)
- [GTM Hooks](../frontend/hooks/useGTM.ts)

### External Resources
- [GTM API Reference](https://developers.google.com/tag-manager/api/v2)
- [GA4 Documentation](https://developers.google.com/analytics/devguides/collection/ga4)
- [GTM Templates Gallery](https://gtm-templates.com/)

## Maintenance

### Regular Tasks
- Review and clean up unused variables/tags
- Update GA4 configuration for new features
- Monitor performance impact
- Audit data quality

### Upgrade Path
1. Test changes in development workspace
2. Create staged rollout plan
3. Monitor key metrics during rollout
4. Document lessons learned

---

*Last Updated: 2025-08-29*
*Version: 1.0.0*