# Domain Migration Steps: Cloud Run to Load Balancer

## Current State
- Cloud Run domain mappings exist for api/app/auth.staging.netrasystems.ai
- Load Balancer is ready at IP: 34.54.41.44
- Both are competing for the same domain names

## Migration Steps (In Order)

### Step 1: Remove Cloud Run Domain Mappings
```bash
# Remove the domain mappings to avoid conflicts
gcloud beta run domain-mappings delete api.staging.netrasystems.ai --region=us-central1
gcloud beta run domain-mappings delete app.staging.netrasystems.ai --region=us-central1
gcloud beta run domain-mappings delete auth.staging.netrasystems.ai --region=us-central1
```

### Step 2: Update DNS Records
Point all staging domains to the Load Balancer IP (34.54.41.44):
- staging.netrasystems.ai → 34.54.41.44
- api.staging.netrasystems.ai → 34.54.41.44
- auth.staging.netrasystems.ai → 34.54.41.44
- app.staging.netrasystems.ai → 34.54.41.44
- www.staging.netrasystems.ai → 34.54.41.44

### Step 3: Update Cloud Run Ingress Settings
Configure Cloud Run services to accept traffic from anywhere (since Load Balancer will handle security):
```bash
gcloud run services update netra-backend-staging \
  --ingress=all \
  --region=us-central1

gcloud run services update netra-auth-service \
  --ingress=all \
  --region=us-central1

gcloud run services update netra-frontend-staging \
  --ingress=all \
  --region=us-central1
```

### Step 4: Keep Direct Cloud Run URLs for Emergency Access
The direct Cloud Run URLs will remain available for emergency bypass:
- https://netra-backend-staging-[hash]-uc.a.run.app
- https://netra-auth-service-[hash]-uc.a.run.app  
- https://netra-frontend-staging-[hash]-uc.a.run.app

These can be used for:
- Emergency access if Load Balancer has issues
- Internal testing without going through Cloud Armor
- Debugging specific service issues

## Benefits After Migration

1. **Single Entry Point**: All traffic flows through Load Balancer
2. **Security Enforcement**: All requests pass through Cloud Armor
3. **Consistent Monitoring**: All metrics in one place
4. **Performance**: CDN caching for static content
5. **Flexibility**: Can still access services directly via Cloud Run URLs if needed

## Rollback Plan

If issues occur after migration:
1. Re-create Cloud Run domain mappings:
```bash
gcloud beta run domain-mappings create \
  --service=netra-backend-staging \
  --domain=api.staging.netrasystems.ai \
  --region=us-central1

gcloud beta run domain-mappings create \
  --service=netra-auth-service \
  --domain=auth.staging.netrasystems.ai \
  --region=us-central1

gcloud beta run domain-mappings create \
  --service=netra-frontend-staging \
  --domain=app.staging.netrasystems.ai \
  --region=us-central1
```

2. Update DNS back to Cloud Run IPs

## Recommendation
**Remove Cloud Run domain mappings** to ensure all traffic flows through the Load Balancer with Cloud Armor protection. This provides better security, monitoring, and performance.