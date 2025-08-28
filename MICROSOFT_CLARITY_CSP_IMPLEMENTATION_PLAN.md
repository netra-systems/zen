# Microsoft Clarity CSP Implementation Plan for Staging

## Issue Summary
Microsoft Clarity scripts are being blocked on staging due to Content Security Policy (CSP) restrictions:
```
Refused to load the script 'https://www.clarity.ms/tag/t1zfqtpve5?ref=gtm' 
because it violates the following Content Security Policy directive: 
"script-src 'self' 'unsafe-inline' https://*.staging.netrasystems.ai https://www.googletagmanager.com https://tagmanager.google.com"
```

## Current CSP Configuration Analysis

### Location of CSP Settings
The CSP configuration is managed in two locations:

1. **Frontend (Next.js)**: `/frontend/next.config.ts` (lines 96-106)
   - Handles CSP for the Next.js application
   - Currently configured for staging environment
   - Already includes Google Tag Manager domains

2. **Backend**: `/netra_backend/app/middleware/security_headers_config.py` (lines 126-140)
   - Handles CSP for backend API responses
   - Uses environment-based configuration

### Current Staging CSP Directives (Frontend)
```javascript
script-src 'self' 'unsafe-inline' https://*.staging.netrasystems.ai https://www.googletagmanager.com https://tagmanager.google.com
connect-src 'self' https://*.staging.netrasystems.ai wss://*.staging.netrasystems.ai https://www.google-analytics.com https://analytics.google.com https://www.googletagmanager.com
```

## Microsoft Clarity Requirements

Based on Microsoft documentation, Clarity requires the following domains:

### Required Domains
- **Script Loading**: `https://www.clarity.ms`
- **Data Collection**: `https://*.clarity.ms` (subdomains a-z for load balancing)
- **Analytics Integration**: `https://c.bing.com` (optional but recommended)

### CSP Directives Needed
- `script-src`: For loading the Clarity JavaScript
- `connect-src`: For sending analytics data
- `img-src`: For tracking pixels (if used)

## Implementation Plan

### Phase 1: Update Frontend CSP Configuration

#### File: `/frontend/next.config.ts`
Update the staging CSP configuration to include Microsoft Clarity domains:

```javascript
// Lines 98-101 - Update script-src
"script-src 'self' 'unsafe-inline' https://*.staging.netrasystems.ai https://www.googletagmanager.com https://tagmanager.google.com https://www.clarity.ms https://*.clarity.ms",

// Line 101 - Update connect-src
"connect-src 'self' https://*.staging.netrasystems.ai wss://*.staging.netrasystems.ai https://www.google-analytics.com https://analytics.google.com https://www.googletagmanager.com https://*.clarity.ms https://c.bing.com",

// Line 100 - Update img-src (if not already sufficient)
"img-src 'self' data: blob: https://*.staging.netrasystems.ai https://www.googletagmanager.com https://*.clarity.ms",
```

### Phase 2: Update Backend CSP Configuration (if needed)

#### File: `/netra_backend/app/middleware/security_headers_config.py`
Update the staging CSP configuration method:

```python
@staticmethod
def _get_staging_base_directives() -> list:
    """Get base staging CSP directives."""
    return [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: https://www.clarity.ms https://*.clarity.ms",
        "style-src 'self' 'unsafe-inline' https:",
        "font-src 'self' https: data:",
        "img-src 'self' data: https: https://*.clarity.ms",
        "connect-src 'self' https: wss: https://*.clarity.ms https://c.bing.com"
    ]
```

### Phase 3: Testing & Validation

1. **Local Testing**
   - Test the CSP changes in development environment
   - Verify Clarity loads through GTM
   - Check browser console for CSP violations

2. **Staging Deployment**
   - Deploy changes to staging environment
   - Verify Clarity initialization
   - Monitor for any CSP violations in browser console

3. **Validation Checklist**
   - [ ] Clarity script loads without CSP errors
   - [ ] Data is being sent to Clarity (network tab verification)
   - [ ] No other services are affected by CSP changes
   - [ ] GTM continues to work properly
   - [ ] All existing functionality remains intact

## Security Implications

### Benefits
1. **Enhanced Analytics**: Microsoft Clarity provides session recordings and heatmaps for UX optimization
2. **GTM Integration**: Works seamlessly with existing Google Tag Manager setup
3. **Privacy Compliant**: Clarity is GDPR/CCPA compliant with automatic PII masking

### Risks & Mitigations
1. **Expanded Attack Surface**: Adding new domains to CSP increases potential attack vectors
   - **Mitigation**: Use specific domains instead of wildcards where possible
   - **Mitigation**: Regularly review and audit third-party scripts

2. **Data Privacy**: Session recordings could potentially capture sensitive information
   - **Mitigation**: Clarity automatically masks sensitive form fields
   - **Mitigation**: Configure Clarity to exclude specific pages if needed
   - **Mitigation**: Implement consent management for EU users

3. **Performance Impact**: Additional scripts may affect page load performance
   - **Mitigation**: Clarity loads asynchronously through GTM
   - **Mitigation**: Monitor Core Web Vitals after implementation

## Recommended Implementation

### Option 1: Minimal Changes (Recommended)
Add only the essential Clarity domains to the existing CSP:
- Add `https://www.clarity.ms` to script-src
- Add `https://*.clarity.ms` to connect-src
- This provides the minimum required access for Clarity to function

### Option 2: Full Clarity Support
Add all Clarity-related domains including Bing integration:
- Add `https://www.clarity.ms https://*.clarity.ms` to script-src
- Add `https://*.clarity.ms https://c.bing.com` to connect-src
- Add `https://*.clarity.ms` to img-src
- This provides full functionality including Microsoft's enhanced analytics

## Rollback Plan
If issues arise after implementation:
1. Remove Clarity domains from CSP configuration
2. Redeploy the application
3. Clear CDN cache if applicable
4. Verify Clarity is blocked again (expected behavior)

## Next Steps
1. Review this plan with the team
2. Choose implementation option (Minimal vs Full)
3. Implement changes in development environment
4. Test thoroughly before staging deployment
5. Monitor staging for 24-48 hours after deployment
6. Document any issues or learnings

## References
- [Microsoft Clarity CSP Documentation](https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-csp)
- [OWASP CSP Guidelines](https://owasp.org/www-project-secure-headers/#content-security-policy)
- [Next.js Security Headers](https://nextjs.org/docs/advanced-features/security-headers)