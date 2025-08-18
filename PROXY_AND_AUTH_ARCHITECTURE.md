# 🔴 CRITICAL: Proxy, Load Balancer, and Auth Service Architecture

## Production Infrastructure Overview

```
                            Internet
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Cloud CDN/WAF     │
                    │  (CloudFlare/AWS)   │
                    └─────────┬───────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Load Balancer     │
                    │    (GCP/AWS ALB)    │
                    └─────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
        │   Nginx     │ │   Nginx     │ │   Nginx     │
        │  Reverse    │ │  Reverse    │ │  Reverse    │
        │   Proxy     │ │   Proxy     │ │   Proxy     │
        └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
                │              │              │
        ┌───────┴────────┬─────┴────────┬────┴───────┐
        ▼                ▼              ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│Auth Service  │ │Main Backend  │ │Frontend      │ │WebSocket     │
│  Port 8001   │ │  Port 8000   │ │  Port 3000   │ │  Port 8002   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

## Service Endpoints and Routing

### Public-Facing URLs
```
https://app.netrasystems.ai         → Frontend (Next.js)
https://api.netrasystems.ai         → Main Backend API
https://auth.netrasystems.ai        → Auth Service
https://ws.netrasystems.ai          → WebSocket Service
```

### Internal Service Communication
```
http://auth-service:8001            → Auth Service (internal)
http://backend-service:8000         → Main Backend (internal)
http://frontend-service:3000        → Frontend (internal)
```

## Nginx Reverse Proxy Configuration

### Main Nginx Configuration
```nginx
# /etc/nginx/nginx.conf
upstream auth_service {
    least_conn;
    server auth-service-1:8001 max_fails=3 fail_timeout=30s;
    server auth-service-2:8001 max_fails=3 fail_timeout=30s;
    server auth-service-3:8001 backup;
}

upstream backend_service {
    least_conn;
    server backend-service-1:8000 max_fails=3 fail_timeout=30s;
    server backend-service-2:8000 max_fails=3 fail_timeout=30s;
    server backend-service-3:8000 backup;
}

upstream frontend_service {
    least_conn;
    server frontend-service-1:3000;
    server frontend-service-2:3000;
}

# Auth Service Routes
server {
    listen 443 ssl http2;
    server_name auth.netrasystems.ai;
    
    ssl_certificate /etc/ssl/certs/netrasystems.crt;
    ssl_certificate_key /etc/ssl/private/netrasystems.key;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;
    
    # Auth service endpoints
    location / {
        proxy_pass http://auth_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers for auth
        add_header Access-Control-Allow-Origin $http_origin always;
        add_header Access-Control-Allow-Credentials true always;
        
        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://auth_service/health;
        access_log off;
    }
}

# Main API Routes
server {
    listen 443 ssl http2;
    server_name api.netrasystems.ai;
    
    ssl_certificate /etc/ssl/certs/netrasystems.crt;
    ssl_certificate_key /etc/ssl/private/netrasystems.key;
    
    # Rate limiting
    limit_req zone=api_limit burst=20 nodelay;
    
    # API endpoints
    location / {
        # Check auth for protected routes
        auth_request /auth/validate;
        auth_request_set $user_id $upstream_http_x_user_id;
        
        proxy_pass http://backend_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-User-Id $user_id;
        
        # Increase limits for file uploads
        client_max_body_size 100M;
        proxy_request_buffering off;
    }
    
    # Internal auth validation endpoint
    location = /auth/validate {
        internal;
        proxy_pass http://auth_service/validate;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI $request_uri;
        proxy_set_header Authorization $http_authorization;
    }
    
    # WebSocket upgrade
    location /ws {
        proxy_pass http://backend_service;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}

# Frontend Routes
server {
    listen 443 ssl http2;
    server_name app.netrasystems.ai;
    
    ssl_certificate /etc/ssl/certs/netrasystems.crt;
    ssl_certificate_key /etc/ssl/private/netrasystems.key;
    
    location / {
        proxy_pass http://frontend_service;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # Next.js specific
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            proxy_pass http://frontend_service;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

## OAuth Flow Through Proxy

### Complete OAuth Login Flow
```
1. User clicks "Login with Google" on frontend
   https://app.netrasystems.ai/login

2. Frontend redirects to auth service
   https://auth.netrasystems.ai/oauth/google?return_url=...

3. Auth service redirects to Google
   https://accounts.google.com/oauth/authorize?client_id=...

4. Google redirects back to auth service
   https://auth.netrasystems.ai/oauth/callback?code=...

5. Auth service validates and redirects to frontend
   https://app.netrasystems.ai/dashboard?token=...

6. Frontend stores token and makes API calls
   https://api.netrasystems.ai/api/user (with Bearer token)

7. API validates token with auth service (internal)
   http://auth-service:8001/validate
```

## Service Discovery and Health Checks

### Kubernetes Service Discovery
```yaml
# auth-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: auth-service
  namespace: production
spec:
  selector:
    app: auth-service
  ports:
    - port: 8001
      targetPort: 8001
  type: ClusterIP

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
      - name: auth-service
        image: gcr.io/project/auth-service:latest
        ports:
        - containerPort: 8001
        env:
        - name: AUTH_SERVICE_PORT
          value: "8001"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: auth-db-secret
              key: url
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Load Balancer Configuration

### GCP Load Balancer
```yaml
# terraform/gcp/load-balancer.tf
resource "google_compute_global_address" "default" {
  name = "netra-lb-ip"
}

resource "google_compute_health_check" "auth" {
  name = "auth-service-health-check"
  
  http_health_check {
    port = 8001
    request_path = "/health"
  }
  
  check_interval_sec = 5
  timeout_sec = 5
  healthy_threshold = 2
  unhealthy_threshold = 2
}

resource "google_compute_backend_service" "auth" {
  name = "auth-backend-service"
  
  backend {
    group = google_compute_instance_group.auth.self_link
  }
  
  health_checks = [google_compute_health_check.auth.self_link]
  
  # Session affinity for auth service
  session_affinity = "CLIENT_IP"
  affinity_cookie_ttl_sec = 3600
}

resource "google_compute_url_map" "default" {
  name = "netra-url-map"
  
  default_service = google_compute_backend_service.frontend.self_link
  
  host_rule {
    hosts = ["auth.netrasystems.ai"]
    path_matcher = "auth"
  }
  
  host_rule {
    hosts = ["api.netrasystems.ai"]
    path_matcher = "api"
  }
  
  path_matcher {
    name = "auth"
    default_service = google_compute_backend_service.auth.self_link
  }
  
  path_matcher {
    name = "api"
    default_service = google_compute_backend_service.backend.self_link
  }
}
```

## Security Considerations

### Rate Limiting
```nginx
# Rate limiting configuration
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

# Apply to auth endpoints
location /auth/login {
    limit_req zone=auth_limit burst=5 nodelay;
    proxy_pass http://auth_service;
}
```

### DDoS Protection
```nginx
# Connection limits
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 100;

# Request size limits
client_body_buffer_size 1K;
client_header_buffer_size 1k;
large_client_header_buffers 2 1k;
```

### SSL/TLS Configuration
```nginx
# Modern SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;
```

## Monitoring and Logging

### Access Logs
```nginx
# Custom log format for auth tracking
log_format auth '$remote_addr - $remote_user [$time_local] '
                '"$request" $status $body_bytes_sent '
                '"$http_referer" "$http_user_agent" '
                'user_id=$upstream_http_x_user_id '
                'request_time=$request_time';

access_log /var/log/nginx/auth_access.log auth;
```

### Metrics Collection
```nginx
# Prometheus metrics endpoint
location /metrics {
    stub_status;
    access_log off;
    allow 10.0.0.0/8;  # Internal only
    deny all;
}
```

## Development Environment

### Docker Compose Setup
```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/ssl
    depends_on:
      - auth-service
      - backend
      - frontend

  auth-service:
    build: ./app/auth
    ports:
      - "8001:8001"
    environment:
      - AUTH_SERVICE_PORT=8001
      - DATABASE_URL=postgresql://user:pass@db/auth
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  backend:
    build: ./app
    ports:
      - "8000:8000"
    environment:
      - AUTH_SERVICE_URL=http://auth-service:8001
      - DATABASE_URL=postgresql://user:pass@db/netra
    depends_on:
      - auth-service
      - db

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost/api
      - NEXT_PUBLIC_AUTH_URL=http://localhost/auth

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=netra

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Local Development Without Proxy
```bash
# Start services directly
# Terminal 1: Auth Service
cd app/auth && python auth_service.py

# Terminal 2: Main Backend
cd app && python main.py

# Terminal 3: Frontend
cd frontend && npm run dev

# Access directly:
# http://localhost:8001 - Auth Service
# http://localhost:8000 - Main Backend
# http://localhost:3000 - Frontend
```

## Troubleshooting

### Common Issues

1. **502 Bad Gateway**
   - Check if auth service is running
   - Verify upstream configuration
   - Check health endpoint responses

2. **CORS Errors**
   - Verify Access-Control headers
   - Check origin whitelist
   - Ensure credentials are included

3. **Session Issues**
   - Check session affinity settings
   - Verify Redis connectivity
   - Review token expiration

4. **OAuth Redirect Loops**
   - Verify redirect_uri configuration
   - Check state parameter handling
   - Review cookie settings

### Debug Commands
```bash
# Test auth service health
curl http://localhost:8001/health

# Test nginx configuration
nginx -t

# Check upstream status
curl http://localhost/nginx_status

# View auth service logs
docker logs auth-service -f

# Test internal auth validation
curl -H "Authorization: Bearer TOKEN" \
     http://localhost:8001/validate
```

## Deployment Checklist

Before deploying auth changes:
- [ ] Auth service health endpoint working
- [ ] Nginx configuration validated
- [ ] SSL certificates valid
- [ ] Rate limiting configured
- [ ] CORS headers set correctly
- [ ] Session affinity configured
- [ ] Health checks passing
- [ ] Monitoring alerts configured
- [ ] Backup auth service ready
- [ ] Rollback plan documented