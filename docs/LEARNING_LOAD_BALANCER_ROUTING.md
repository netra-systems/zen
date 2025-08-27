# Learning: Load Balancer Subdomain Routing vs Cloud Run Domain Mapping

## Key Concept: How Load Balancer Routes Subdomains

The Load Balancer uses **HTTP Host headers** to route traffic to different backend services. This is fundamentally different from Cloud Run domain mappings.

### Cloud Run Domain Mapping (OLD WAY)
```
DNS Record: api.staging.netrasystems.ai → Cloud Run IP (direct)
DNS Record: auth.staging.netrasystems.ai → Cloud Run IP (direct)
DNS Record: app.staging.netrasystems.ai → Cloud Run IP (direct)
```
- Each subdomain points directly to its own Cloud Run service
- No central control point
- No security filtering
- Each service needs its own SSL certificate

### Load Balancer Routing (NEW WAY)
```
DNS Record: *.staging.netrasystems.ai → 34.54.41.44 (Load Balancer IP)
```
- ALL subdomains point to the SAME Load Balancer IP
- Load Balancer examines the Host header to determine routing
- Central security enforcement via Cloud Armor
- Single SSL certificate covers all subdomains

## How Load Balancer Routing Works

### 1. DNS Resolution
```
User types: api.staging.netrasystems.ai
DNS returns: 34.54.41.44 (Load Balancer IP)
```

### 2. HTTP Request
```http
GET /endpoint HTTP/1.1
Host: api.staging.netrasystems.ai  <-- This header tells LB where to route
```

### 3. Load Balancer Decision Tree
```yaml
Host Header: api.staging.netrasystems.ai
  → Matches host_rule for "api.staging.netrasystems.ai"
  → Uses path_matcher: "api-paths"
  → Routes to: staging-api-backend
  → Forwards to: Cloud Run netra-backend-staging

Host Header: auth.staging.netrasystems.ai
  → Matches host_rule for "auth.staging.netrasystems.ai"
  → Uses path_matcher: "auth-paths"
  → Routes to: staging-auth-backend
  → Forwards to: Cloud Run netra-auth-service

Host Header: app.staging.netrasystems.ai
  → Matches host_rule for "app.staging.netrasystems.ai"
  → Uses path_matcher: "frontend-paths"
  → Routes to: staging-frontend-backend
  → Forwards to: Cloud Run netra-frontend-staging
```

## Terraform Configuration

The routing is defined in `load-balancer.tf`:

```hcl
resource "google_compute_url_map" "https_lb" {
  name = "${var.environment}-https-lb"
  
  # Define which hosts go to which path matcher
  host_rule {
    hosts        = ["api.staging.netrasystems.ai"]
    path_matcher = "api-paths"
  }
  
  host_rule {
    hosts        = ["auth.staging.netrasystems.ai"]
    path_matcher = "auth-paths"
  }
  
  host_rule {
    hosts        = ["app.staging.netrasystems.ai", "staging.netrasystems.ai"]
    path_matcher = "frontend-paths"
  }
  
  # Define what backend each path matcher uses
  path_matcher {
    name            = "api-paths"
    default_service = google_compute_backend_service.api_backend.id
  }
  
  path_matcher {
    name            = "auth-paths"
    default_service = google_compute_backend_service.auth_backend.id
  }
  
  path_matcher {
    name            = "frontend-paths"
    default_service = google_compute_backend_service.frontend_backend.id
  }
}
```

## Benefits of Load Balancer Routing

1. **Centralized Security**: All traffic passes through Cloud Armor
2. **Single IP Address**: Easier DNS management
3. **Path-Based Routing**: Can route `/api/*` to one service, `/auth/*` to another
4. **Traffic Management**: Can do weighted routing, A/B testing
5. **Global CDN**: Static content cached at edge locations
6. **DDoS Protection**: Automatic mitigation at Google's edge

## Migration Process

### Step 1: Remove Cloud Run Domain Mappings
Cloud Run domain mappings must be removed to avoid routing conflicts:
```bash
gcloud beta run domain-mappings delete api.staging.netrasystems.ai --region=us-central1
gcloud beta run domain-mappings delete app.staging.netrasystems.ai --region=us-central1
gcloud beta run domain-mappings delete auth.staging.netrasystems.ai --region=us-central1
```

### Step 2: Update DNS
Point all subdomains to Load Balancer:
```
A Record: staging.netrasystems.ai → 34.54.41.44
A Record: *.staging.netrasystems.ai → 34.54.41.44
```
Or individually:
```
A Record: api.staging.netrasystems.ai → 34.54.41.44
A Record: auth.staging.netrasystems.ai → 34.54.41.44
A Record: app.staging.netrasystems.ai → 34.54.41.44
```

### Step 3: SSL Certificate Provisioning
The Load Balancer's managed SSL certificate will automatically provision for all configured domains once DNS propagates.

## Key Learning Points

1. **Load Balancer doesn't need separate IPs per subdomain** - It uses HTTP Host headers
2. **Cloud Run domain mappings conflict with Load Balancer** - Can't have both
3. **The routing logic is in the Load Balancer configuration**, not in DNS
4. **DNS just points everything to one IP** - Load Balancer does the smart routing
5. **This is how all major cloud providers handle multi-service architectures** (AWS ALB, Azure Application Gateway, etc.)

## Emergency Access

Even after removing domain mappings, Cloud Run services remain accessible via their direct URLs:
- `https://netra-backend-staging-[hash]-uc.a.run.app`
- `https://netra-auth-service-[hash]-uc.a.run.app`
- `https://netra-frontend-staging-[hash]-uc.a.run.app`

These can be used for:
- Bypassing Load Balancer for debugging
- Emergency access if Load Balancer fails
- Internal service-to-service communication

## Verification Commands

```bash
# Check Load Balancer routing
gcloud compute url-maps describe staging-https-lb

# Test routing (after DNS update)
curl -H "Host: api.staging.netrasystems.ai" http://34.54.41.44
curl -H "Host: auth.staging.netrasystems.ai" http://34.54.41.44
curl -H "Host: app.staging.netrasystems.ai" http://34.54.41.44

# Monitor Load Balancer logs
gcloud logging read "resource.type=http_load_balancer" --limit=10
```

## Common Misconceptions

❌ "Each subdomain needs its own IP address"
✅ Load Balancer uses Host headers to route from a single IP

❌ "Removing Cloud Run domain mappings will break the services"
✅ Services remain accessible through Load Balancer and direct Cloud Run URLs

❌ "DNS does the routing to different services"
✅ DNS only resolves to IP; Load Balancer does the routing

This architecture is the standard pattern for modern cloud applications, providing security, scalability, and centralized management.