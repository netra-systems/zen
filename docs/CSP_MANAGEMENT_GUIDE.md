# Content Security Policy (CSP) Management Guide

## Overview
This guide documents the Content Security Policy (CSP) configuration for the Netra Apex platform and provides procedures for maintaining and updating CSP directives.

## CSP Configuration Locations

### Primary Configuration
- **File:** `frontend/next.config.ts`
- **Environments:** Development, Staging, Production
- **Method:** Next.js headers configuration

### Secondary Configuration
- **File:** `frontend/middleware.ts`
- **Purpose:** Additional security headers (not CSP in production)
- **Note:** CSP is handled by next.config.ts for proper nonce support

## CSP Directives Reference

### Critical Directives

#### script-src
Controls which scripts can be executed:
- `'self'` - Same origin scripts
- `'unsafe-inline'` - Inline scripts (required for Next.js)
- `blob:` - Worker scripts from blob URLs
- External domains for analytics/monitoring

#### worker-src
Controls Web Worker sources:
- `'self'` - Same origin workers
- `blob:` - Dynamic worker creation

#### connect-src
Controls which URLs can be fetched:
- `'self'` - Same origin requests
- WebSocket connections (wss://)
- External APIs (analytics, monitoring, features)

## Common CSP Issues and Solutions

### Issue: Worker Creation Blocked
**Error:** `Refused to create a worker from 'blob:...'`
**Solution:** Add `blob:` to script-src and/or add explicit worker-src directive

### Issue: External API Blocked
**Error:** `Refused to connect to '<URL>'`
**Solution:** Add domain to connect-src directive

### Issue: Image Loading Blocked
**Error:** `Refused to load the image`
**Solution:** Add source to img-src directive

## Update Process

### Before Adding Dependencies

1. **Review External Resources**
   - Identify all external domains the dependency uses
   - Check for worker creation requirements
   - Note any special CSP requirements

2. **Update CSP Configuration**
   ```typescript
   // Example: Adding a new analytics service
   "connect-src 'self' ... https://new-analytics.com",
   ```

3. **Test in Development**
   - Check browser console for CSP violations
   - Verify functionality works as expected

4. **Deploy to Staging**
   - Monitor for CSP violations
   - Test all affected features

### CSP Update Checklist

- [ ] Identify all external resources required
- [ ] Update development CSP configuration
- [ ] Update staging CSP configuration
- [ ] Test worker creation if applicable
- [ ] Test external API connections
- [ ] Check browser console for violations
- [ ] Deploy to staging for testing
- [ ] Document changes in this guide
- [ ] Update production configuration after validation

## Environment-Specific Configurations

### Development
- More permissive for local development
- Allows localhost and 127.0.0.1
- Includes 'unsafe-eval' for hot reload

### Staging
- Production-like restrictions
- Specific to *.staging.netrasystems.ai
- No 'unsafe-eval'

### Production
- Most restrictive configuration
- Production domains only
- Minimal required permissions

## Security Best Practices

1. **Principle of Least Privilege**
   - Only add sources that are absolutely necessary
   - Avoid wildcards when possible
   - Be specific with domain names

2. **Regular Audits**
   - Review CSP reports regularly
   - Remove unused external sources
   - Update deprecated domains

3. **Testing Protocol**
   - Always test in development first
   - Verify in staging before production
   - Monitor CSP violation reports

## Monitoring CSP Violations

### Browser Console
Check for CSP violations in browser developer console:
```
Content Security Policy: The page's settings blocked the loading of a resource
```

### CSP Reporting (Future Enhancement)
Consider implementing CSP reporting:
```typescript
"report-uri /api/csp-report",
"report-to csp-endpoint"
```

## Common External Services

### Analytics & Monitoring
- Google Analytics: `https://www.google-analytics.com`
- Google Tag Manager: `https://www.googletagmanager.com`
- Microsoft Clarity: `https://*.clarity.ms`
- Sentry: `https://*.ingest.sentry.io`

### Feature Management
- Feature Flags: `https://featureassets.org`
- Registry: `https://prodregistryv2.org`

### Infrastructure
- CloudFlare DNS: `https://cloudflare-dns.com`

## Troubleshooting Guide

### Steps to Debug CSP Issues

1. **Open Browser Console**
   - Look for red CSP violation errors
   - Note the directive that's blocking

2. **Identify Required Resource**
   - Check the blocked URL
   - Determine if it's necessary

3. **Update Configuration**
   - Add to appropriate directive
   - Follow update process above

4. **Test Thoroughly**
   - Clear browser cache
   - Test in incognito mode
   - Verify across browsers

## References

- [MDN CSP Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [Next.js Security Headers](https://nextjs.org/docs/advanced-features/security-headers)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)

## Change Log

### 2025-01-07
- Added `blob:` to script-src for worker support
- Added explicit worker-src directive
- Added featureassets.org and cloudflare-dns.com to connect-src
- Created this management guide