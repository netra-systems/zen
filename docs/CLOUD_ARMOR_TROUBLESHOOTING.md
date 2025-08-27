# Cloud Armor Troubleshooting Guide

## Quick Reference for 403 Errors

### Immediate Investigation Steps

1. **Check Recent Blocks**
   ```bash
   python scripts/analyze_cloud_armor_logs.py --denied --limit 20
   ```

2. **Check OAuth Specific Issues**
   ```bash
   python scripts/analyze_cloud_armor_logs.py --oauth
   ```

3. **Get Summary of Blocked Patterns**
   ```bash
   python scripts/analyze_cloud_armor_logs.py --summary --limit 100
   ```

### Common False Positives

| Pattern | Rule Triggered | Solution |
|---------|---------------|----------|
| OAuth callbacks with `4%2F0...` codes | `owasp-crs-v030001-id942432-sqli` | Exception rule for `/auth/callback` |
| WebSocket connections | `owasp-crs-v030001-id942421-sqli` | May need exception for `/ws` |
| URL-encoded parameters | Various SQL injection rules | Path-based exceptions |

### GCloud Commands

```bash
# View current security policy
gcloud compute security-policies describe staging-security-policy --project=netra-staging

# List all rules with priorities
gcloud compute security-policies rules list --security-policy=staging-security-policy --project=netra-staging

# Add exception rule (example)
gcloud compute security-policies rules create <PRIORITY> \
  --security-policy=staging-security-policy \
  --action=allow \
  --description="<DESCRIPTION>" \
  --expression="<EXPRESSION>" \
  --project=netra-staging

# Query raw logs
gcloud logging read "resource.type=\"http_load_balancer\" AND jsonPayload.statusDetails=\"denied_by_security_policy\"" --limit=20 --project=netra-staging
```

### Rule Priority Guide

- **1-49**: Critical exceptions (OAuth, health checks)
- **50-99**: Application-specific exceptions
- **100-199**: OWASP protection rules
- **500-999**: Geographic/rate limiting
- **1000+**: General rate limiting
- **2147483647**: Default allow rule

### Debugging Process

1. **Identify the Pattern**
   - Check URL path
   - Check query parameters
   - Check headers
   - Note the triggered rule ID

2. **Analyze the Rule**
   ```bash
   python scripts/analyze_cloud_armor_logs.py --rule "<RULE_ID>"
   ```

3. **Determine if Legitimate**
   - Is this a known endpoint?
   - Are the parameters expected?
   - Is the source IP legitimate?

4. **Create Exception if Needed**
   - Use most specific match possible
   - Document the business reason
   - Set appropriate priority

### Testing After Changes

1. **Verify Rule is Active**
   ```bash
   gcloud compute security-policies rules describe <PRIORITY> \
     --security-policy=staging-security-policy \
     --project=netra-staging
   ```

2. **Test the Specific Flow**
   - For OAuth: Attempt login
   - For API: Make test requests
   - For WebSocket: Establish connection

3. **Monitor for Side Effects**
   ```bash
   python scripts/analyze_cloud_armor_logs.py --denied --limit 50
   ```

### Emergency Procedures

If legitimate traffic is being blocked in production:

1. **Quick Mitigation** (NOT RECOMMENDED for production)
   ```bash
   # Temporarily allow specific path
   gcloud compute security-policies rules create 1 \
     --security-policy=<POLICY> \
     --action=allow \
     --expression="request.path == '<PATH>'" \
     --project=<PROJECT>
   ```

2. **Proper Fix**
   - Analyze the logs thoroughly
   - Create targeted exception
   - Test in staging first
   - Document the change

### Related Files

- **Specification**: `SPEC/cloud_armor_security.xml`
- **Learnings**: `SPEC/learnings/cloud_armor_oauth_comprehensive.xml`
- **Analysis Tool**: `scripts/analyze_cloud_armor_logs.py`
- **Deployment Config**: Check terraform files for Cloud Armor configuration

### Support Contacts

For Cloud Armor policy changes in production:
- Review with security team first
- Document in incident ticket
- Update this guide with new patterns