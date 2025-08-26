# Cloud Armor & Load Balancer Implementation Plan for GCP Staging

## Executive Summary
Add Cloud Armor DDoS protection and HTTP(S) Load Balancer to protect and distribute traffic across Cloud Run services in staging environment.

## Current State Analysis

### Existing Infrastructure
- **Services**: 3 Cloud Run services deployed (backend, auth, frontend)
  - `netra-backend-staging`: Main API service
  - `netra-auth-service`: Authentication microservice  
  - `netra-frontend-staging`: Next.js frontend
- **Terraform**: Basic infrastructure exists in `terraform-gcp-staging/`
- **Deployment**: Using `scripts/deploy_to_gcp.py` for orchestration
- **Region**: us-central1
- **Project**: netra-staging

### Current Gaps
- No load balancer (direct Cloud Run URLs exposed)
- No DDoS protection
- No centralized traffic management
- No custom domain routing
- No security policies

## Implementation Plan

### Phase 1: Terraform Module Structure (Week 1)
Create modular Terraform configuration for load balancer and Cloud Armor:

```
terraform-gcp-staging/
├── modules/
│   ├── load-balancer/
│   │   ├── main.tf          # LB resources
│   │   ├── variables.tf     # Input variables
│   │   ├── outputs.tf       # Output values
│   │   └── backend.tf       # Backend services
│   └── cloud-armor/
│       ├── main.tf          # Security policies
│       ├── variables.tf     # Policy parameters
│       ├── outputs.tf       # Policy outputs
│       └── rules.tf         # Security rules
├── load-balancer.tf         # Root module implementation
├── cloud-armor.tf           # Security policy attachment
└── dns.tf                   # DNS configuration
```

### Phase 2: Load Balancer Implementation (Week 1-2)

#### 2.1 Create Network Endpoint Groups (NEGs)
```hcl
# terraform-gcp-staging/modules/load-balancer/backend.tf
resource "google_compute_region_network_endpoint_group" "backend_neg" {
  name                  = "netra-backend-neg"
  network_endpoint_type = "SERVERLESS"
  region               = var.region
  
  cloud_run {
    service = "netra-backend-staging"
  }
}

resource "google_compute_region_network_endpoint_group" "auth_neg" {
  name                  = "netra-auth-neg"
  network_endpoint_type = "SERVERLESS"
  region               = var.region
  
  cloud_run {
    service = "netra-auth-service"
  }
}

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "netra-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region               = var.region
  
  cloud_run {
    service = "netra-frontend-staging"
  }
}
```

#### 2.2 Configure Backend Services
```hcl
resource "google_compute_backend_service" "api_backend" {
  name                  = "netra-api-backend"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  
  backend {
    group = google_compute_region_network_endpoint_group.backend_neg.id
  }
  
  security_policy = google_compute_security_policy.cloud_armor.id
  
  health_checks = [google_compute_health_check.http.id]
  
  log_config {
    enable = true
    sample_rate = 1.0
  }
}
```

#### 2.3 URL Map Configuration
```hcl
resource "google_compute_url_map" "https_lb" {
  name            = "netra-https-lb"
  default_service = google_compute_backend_service.frontend_backend.id
  
  host_rule {
    hosts        = ["api.staging.netrasystems.ai"]
    path_matcher = "api-paths"
  }
  
  path_matcher {
    name            = "api-paths"
    default_service = google_compute_backend_service.api_backend.id
    
    path_rule {
      paths   = ["/auth/*"]
      service = google_compute_backend_service.auth_backend.id
    }
  }
}
```

### Phase 3: Cloud Armor Security Policies (Week 2)

#### 3.1 Base Security Policy
```hcl
# terraform-gcp-staging/modules/cloud-armor/main.tf
resource "google_compute_security_policy" "cloud_armor" {
  name = "netra-staging-security-policy"
  
  # Default rule
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "Default allow rule"
  }
  
  # Rate limiting rule
  rule {
    action   = "rate_based_ban"
    priority = "1000"
    
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      
      enforce_on_key = "IP"
      
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
      
      ban_duration_sec = 600
    }
    
    description = "Rate limit rule"
  }
}
```

#### 3.2 DDoS Protection Rules
```hcl
# terraform-gcp-staging/modules/cloud-armor/rules.tf
locals {
  security_rules = [
    {
      action      = "deny(403)"
      priority    = 100
      description = "Block known malicious IPs"
      expression  = "origin.region_code == 'XX'"
    },
    {
      action      = "deny(403)"  
      priority    = 200
      description = "Block SQL injection attempts"
      expression  = "evaluatePreconfiguredExpr('sqli-stable')"
    },
    {
      action      = "deny(403)"
      priority    = 300
      description = "Block XSS attempts"
      expression  = "evaluatePreconfiguredExpr('xss-stable')"
    },
    {
      action      = "deny(403)"
      priority    = 400
      description = "Block protocol attacks"
      expression  = "evaluatePreconfiguredExpr('protocolattack-stable')"
    },
    {
      action      = "throttle"
      priority    = 500
      description = "Throttle requests from suspicious regions"
      expression  = "origin.region_code in ['CN', 'RU', 'KP']"
      rate_limit = {
        count        = 10
        interval_sec = 60
      }
    }
  ]
}

resource "google_compute_security_policy_rule" "rules" {
  for_each = { for idx, rule in local.security_rules : idx => rule }
  
  security_policy = google_compute_security_policy.cloud_armor.name
  
  action      = each.value.action
  priority    = each.value.priority
  description = each.value.description
  
  match {
    expr {
      expression = each.value.expression
    }
  }
  
  dynamic "rate_limit_options" {
    for_each = lookup(each.value, "rate_limit", null) != null ? [each.value.rate_limit] : []
    content {
      rate_limit_threshold {
        count        = rate_limit_options.value.count
        interval_sec = rate_limit_options.value.interval_sec
      }
    }
  }
}
```

### Phase 4: SSL Certificate & Domain Setup (Week 2-3)

#### 4.1 Managed SSL Certificate
```hcl
resource "google_compute_managed_ssl_certificate" "staging" {
  name = "netra-staging-ssl-cert"
  
  managed {
    domains = [
      "staging.netrasystems.ai",
      "api.staging.netrasystems.ai",
      "auth.staging.netrasystems.ai"
    ]
  }
}
```

#### 4.2 HTTPS Proxy
```hcl
resource "google_compute_target_https_proxy" "https_lb" {
  name             = "netra-https-lb-proxy"
  url_map          = google_compute_url_map.https_lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.staging.id]
}
```

#### 4.3 Global Forwarding Rule
```hcl
resource "google_compute_global_forwarding_rule" "https" {
  name       = "netra-https-forwarding-rule"
  target     = google_compute_target_https_proxy.https_lb.id
  port_range = "443"
  ip_protocol = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address = google_compute_global_address.lb_ip.address
}

resource "google_compute_global_address" "lb_ip" {
  name = "netra-lb-ip"
  address_type = "EXTERNAL"
}
```

### Phase 5: Monitoring & Observability (Week 3)

#### 5.1 Cloud Armor Metrics
- Configure alerts for blocked requests
- Monitor rate limiting effectiveness
- Track security rule triggers

#### 5.2 Load Balancer Metrics
- Request latency percentiles
- Backend health status
- Error rate monitoring
- Traffic distribution analysis

#### 5.3 Logging Configuration
```hcl
resource "google_logging_log_sink" "security_events" {
  name        = "cloud-armor-security-events"
  destination = "pubsub.googleapis.com/projects/${var.project_id}/topics/security-alerts"
  
  filter = <<-EOT
    resource.type="http_load_balancer"
    jsonPayload.enforcedSecurityPolicy.name="netra-staging-security-policy"
    jsonPayload.enforcedSecurityPolicy.outcome="DENY"
  EOT
}
```

### Phase 6: Integration & Testing (Week 3-4)

#### 6.1 Update deploy_to_gcp.py Script
- Add load balancer URL discovery
- Update health check endpoints
- Modify service discovery logic

#### 6.2 Test Cases
1. **DDoS Protection Testing**
   - Simulate high-volume attacks
   - Verify rate limiting
   - Test IP blocking

2. **Load Distribution Testing**
   - Multi-region traffic simulation
   - Backend failover scenarios
   - Health check validation

3. **Security Rule Testing**
   - SQL injection attempts
   - XSS payload testing
   - Protocol attack simulation

#### 6.3 Performance Testing
- Baseline latency measurements
- Load testing with various traffic patterns
- CDN cache hit ratio analysis

## Migration Strategy

### Step 1: Deploy Infrastructure (No Traffic)
```bash
cd terraform-gcp-staging
terraform init
terraform plan -target=module.load_balancer
terraform apply -target=module.load_balancer
```

### Step 2: Test with Subdomain
- Point test.staging.netrasystems.ai to load balancer
- Run comprehensive test suite
- Monitor metrics and logs

### Step 3: Gradual Traffic Migration
- Use weighted routing (10% -> 50% -> 100%)
- Monitor error rates and latency
- Keep Cloud Run URLs as fallback

### Step 4: Full Cutover
- Update DNS for all domains
- Disable direct Cloud Run access
- Enable full security policies

## Cost Estimation

### Monthly Costs (USD)
- **Load Balancer**: ~$18/month (forwarding rules)
- **Cloud Armor**: ~$5/month (base) + $1 per million requests
- **SSL Certificates**: Free (Google-managed)
- **Logging/Monitoring**: ~$10-20/month
- **Total Estimated**: ~$35-50/month + usage

## Security Improvements
1. **DDoS Protection**: Automatic mitigation of volumetric attacks
2. **WAF Capabilities**: Protection against OWASP Top 10
3. **Geographic Restrictions**: Block traffic from high-risk regions
4. **Rate Limiting**: Per-IP and per-session limits
5. **Bot Detection**: ML-based bot traffic identification

## Performance Benefits
1. **Global Anycast IP**: Reduced latency worldwide
2. **Connection Pooling**: Efficient backend connections
3. **HTTP/2 & QUIC**: Modern protocol support
4. **CDN Integration**: Static content caching
5. **Automatic Scaling**: Handle traffic spikes

## Rollback Plan
If issues arise:
1. Update DNS to point directly to Cloud Run URLs
2. Disable security policies temporarily
3. Investigate and fix issues
4. Re-enable gradually

## Success Metrics
- **Security**: <1% malicious traffic reaching backends
- **Performance**: <100ms P95 latency improvement  
- **Availability**: >99.9% uptime
- **Cost**: <$100/month for infrastructure

## Timeline
- **Week 1**: Terraform modules development
- **Week 2**: Security policy configuration  
- **Week 3**: Integration and testing
- **Week 4**: Production migration

## Next Steps
1. Review and approve plan
2. Set up staging-lb project for testing
3. Begin Terraform module development
4. Schedule security testing resources