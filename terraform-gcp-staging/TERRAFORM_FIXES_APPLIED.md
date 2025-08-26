# Terraform Configuration Fixes Applied

## Summary of All Terraform Fixes

This document details all the fixes applied to the Terraform configuration files to successfully deploy the Load Balancer and Cloud Armor.

## File: variables.tf

### Added Missing Variable
```hcl
# Added at line 249
variable "notification_channels" {
  description = "List of notification channel IDs for alerts"
  type        = list(string)
  default     = []  # Add notification channel IDs once created in GCP
}
```

## File: cloud-armor.tf

### Fix 1: Removed Duplicate adaptive_protection_config
**Location**: Line 266-270
**Original**:
```hcl
  # Log configuration
  log_config {
    enable      = true
    sample_rate = 1.0
  }
  
  # Another adaptive_protection_config block here (duplicate)
  adaptive_protection_config {
    layer_7_ddos_defense_config {
      enable = true
    }
  }
```
**Fixed to**:
```hcl
  # Removed duplicate block, kept only the one at the beginning of the resource
```

### Fix 2: Fixed Region Code Expression
**Location**: Line 205
**Original**:
```hcl
expression = "origin.region_code in ['CN', 'RU', 'KP', 'IR']"
```
**Fixed to**:
```hcl
expression = "origin.region_code == 'CN' || origin.region_code == 'RU' || origin.region_code == 'KP' || origin.region_code == 'IR'"
```

### Fix 3: Fixed User Agent Detection
**Location**: Line 230
**Original**:
```hcl
expression = "request.headers['user-agent'].matches('(?i)(bot|crawler|spider|scraper|scanner)')"
```
**Fixed to**:
```hcl
expression = "request.headers['user-agent'].lower().contains('bot') || request.headers['user-agent'].lower().contains('crawler') || request.headers['user-agent'].lower().contains('spider') || request.headers['user-agent'].lower().contains('scraper') || request.headers['user-agent'].lower().contains('scanner')"
```

### Fix 4: Changed Log Sink Resource Type
**Location**: Line 273
**Original**:
```hcl
resource "google_logging_log_sink" "security_events" {
```
**Fixed to**:
```hcl
resource "google_logging_project_sink" "security_events" {
```

### Fix 5: Updated IAM Member Reference
**Location**: Line 319
**Original**:
```hcl
member = google_logging_log_sink.security_events.writer_identity
```
**Fixed to**:
```hcl
member = google_logging_project_sink.security_events.writer_identity
```

## File: load-balancer.tf

### Fix 1: Removed Health Checks from Serverless NEGs
**Location**: Lines 86, 109, 132
**Original** (appeared in all three backend services):
```hcl
health_checks = [google_compute_health_check.http_health_check.id]
```
**Fixed to**:
```hcl
# Health checks not supported for serverless NEGs
```

### Fix 2: Fixed SSL Certificate Domains
**Location**: Lines 219-222
**Original**:
```hcl
managed {
  domains = [
    "staging.netrasystems.ai",
    "*.staging.netrasystems.ai"  # Wildcards not supported
  ]
}
```
**Fixed to**:
```hcl
managed {
  domains = [
    "staging.netrasystems.ai",
    "api.staging.netrasystems.ai",
    "auth.staging.netrasystems.ai",
    "www.staging.netrasystems.ai"
  ]
}
```

### Fix 3: Added CDN Configuration
**Location**: Line 134 (frontend backend service)
**Added**:
```hcl
enable_cdn = true

cdn_policy {
  cache_mode                   = "CACHE_ALL_STATIC"
  default_ttl                  = 3600
  client_ttl                   = 7200
  max_ttl                      = 86400
  negative_caching             = true
  serve_while_stale            = 86400
  
  cache_key_policy {
    include_host          = true
    include_protocol      = true
    include_query_string  = false
  }
  
  negative_caching_policy {
    code = 404
    ttl  = 120
  }
}
```

## Validation Results

### Before Fixes
- ❌ Multiple terraform plan errors
- ❌ Cloud Armor expression syntax errors
- ❌ Backend service configuration errors
- ❌ SSL certificate validation errors

### After Fixes
- ✅ All Terraform resources successfully created
- ✅ 16 compute resources deployed
- ✅ Cloud Armor policy active with 15 security rules
- ✅ Load Balancer accessible at 34.54.41.44
- ✅ SSL certificates in provisioning state

## Commands Used for Validation

```bash
# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan deployment
terraform plan

# Apply with specific targets
terraform apply -target=<resource>

# Verify deployment
terraform state list
gcloud compute backend-services list
gcloud compute security-policies describe staging-security-policy
```

## Lessons Learned

1. **Always check for resource-specific limitations** (e.g., no health checks for serverless NEGs)
2. **Cloud Armor expressions have strict syntax requirements** - no regex flags or array operators
3. **Google-managed SSL certificates require explicit domain listing** - no wildcards
4. **Use terraform import for existing resources** rather than recreating
5. **Deploy incrementally with -target flag** for complex infrastructure

## Resource Dependencies

The correct order of deployment:
1. Security policy and IP address (can be parallel)
2. SSL certificate and NEGs (can be parallel)
3. Backend services (depends on NEGs and security policy)
4. URL maps (depends on backend services)
5. Target proxies (depends on URL maps and SSL cert)
6. Forwarding rules (depends on target proxies and IP)

This order ensures all dependencies are satisfied during deployment.