# Netra AI Platform - Quick Deployment Reference

## 🚀 Quick Start Commands

### Local Development
```bash
# Backend
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

### Docker Deployment
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down -v  # Full cleanup
```

### GCP Production Deployment (10 minutes)
```bash
# 1. Setup
export PROJECT_ID="netra-production"
export REGION="us-central1"
gcloud config set project $PROJECT_ID

# 2. Infrastructure
cd terraform-gcp
terraform init && terraform apply -auto-approve

# 3. Container Registry
export REGISTRY=$(terraform output -raw artifact_registry)
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# 4. Build & Push
docker build -f Dockerfile.backend -t ${REGISTRY}/backend:latest .
docker push ${REGISTRY}/backend:latest
cd frontend && docker build -t ${REGISTRY}/frontend:latest . && docker push ${REGISTRY}/frontend:latest

# 5. Deploy
gcloud run deploy netra-backend --image ${REGISTRY}/backend:latest --region ${REGION}
gcloud run deploy netra-frontend --image ${REGISTRY}/frontend:latest --region ${REGION}

# 6. Get URLs
echo "Frontend: $(terraform output -raw frontend_url)"
echo "Backend: $(terraform output -raw backend_url)"
```

---

## 📋 Pre-Deployment Checklist

- [ ] GCP Project created with billing enabled
- [ ] Required APIs enabled
- [ ] terraform.tfvars configured
- [ ] API keys ready (Gemini, Anthropic, etc.)
- [ ] OAuth credentials configured
- [ ] Docker installed and running
- [ ] Terraform installed (v1.0+)

---

## 🔑 Required Environment Variables

### Critical (Must Set)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/netra
JWT_SECRET_KEY=$(openssl rand -hex 64)
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
```

### API Keys
```bash
GEMINI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-secret
```

### Optional but Recommended
```bash
REDIS_URL=redis://host:6379
CLICKHOUSE_URL=clickhouse://host:9000/netra
FERNET_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
LOG_LEVEL=INFO
```

---

## 🏗️ Infrastructure Sizing

### Budget Options

| Tier | Config | Monthly Cost | Use Case |
|------|--------|--------------|----------|
| **Dev** | f1-micro DB, 0.5 CPU | ~$50 | Development |
| **Starter** | g1-small DB, 1 CPU | ~$150 | Small team |
| **Standard** | custom-2-7680 DB, 2 CPU | ~$300 | Production |
| **Scale** | custom-4-16384 DB, 4 CPU | ~$600 | High traffic |
| **Enterprise** | custom-8-32768 DB, 8 CPU | ~$1200+ | Enterprise |

### Quick Scaling
```bash
# Scale up
gcloud run services update netra-backend --cpu=4 --memory=8Gi --min-instances=2 --max-instances=20

# Scale down
gcloud run services update netra-backend --cpu=1 --memory=2Gi --min-instances=0 --max-instances=5
```

---

## 🔍 Health Checks

```bash
# Quick health check
curl $(terraform output -raw backend_url)/health

# Full system check
./scripts/health-check.sh

# WebSocket test
wscat -c $(terraform output -raw backend_url | sed 's/https/wss/')/ws -x '{"type":"ping"}'
```

---

## 📊 Monitoring Commands

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# View errors only
gcloud logging read "severity>=ERROR" --limit=20

# Check costs
gcloud billing accounts get-iam-policy $(gcloud beta billing accounts list --format="value(name)")

# Database status
gcloud sql instances describe $(terraform output -raw database_connection_name)
```

---

## 🚨 Emergency Procedures

### Immediate Shutdown
```bash
gcloud run services update netra-backend --max-instances=0 --region=${REGION}
gcloud run services update netra-frontend --max-instances=0 --region=${REGION}
```

### Quick Rollback
```bash
# Rollback to previous revision
gcloud run services update-traffic netra-backend --to-revisions=PREVIOUS=100 --region=${REGION}
```

### Database Recovery
```bash
# List backups
gcloud sql backups list --instance=$(terraform output -raw database_connection_name)

# Restore
gcloud sql backups restore BACKUP_ID --restore-instance=$(terraform output -raw database_connection_name)
```

---

## 🛠️ Common Fixes

### Database Connection Failed
```bash
# Check and update authorized networks
gcloud sql instances patch $(terraform output -raw database_connection_name) --authorized-networks=0.0.0.0/0
```

### Out of Memory
```bash
gcloud run services update netra-backend --memory=8Gi --region=${REGION}
```

### High Latency
```bash
# Enable CPU boost
gcloud run services update netra-backend --cpu-boost --region=${REGION}
```

### WebSocket Drops
```bash
gcloud run services update netra-backend --timeout=3600 --use-http2 --region=${REGION}
```

---

## 🔐 Security Quick Tasks

### Rotate Secrets
```bash
# JWT Secret
echo -n $(openssl rand -hex 64) | gcloud secrets versions add jwt-secret-key --data-file=-

# Database Password
NEW_PASS=$(openssl rand -base64 32)
gcloud sql users set-password netra_user --instance=$(terraform output -raw database_connection_name) --password="$NEW_PASS"
```

### Enable Cloud Armor
```bash
gcloud compute security-policies create netra-security --description="DDoS protection"
```

---

## 💰 Cost Optimization

### Quick Wins
```bash
# CPU throttling (save ~40%)
gcloud run services update netra-backend --cpu-throttling --region=${REGION}

# Schedule scaling
gcloud scheduler jobs create http scale-down --schedule="0 22 * * *" --uri="${BACKEND_URL}/admin/scale" --message-body='{"min_instances": 0}'
```

---

## 📝 Useful Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# Netra deployment aliases
alias netra-logs='gcloud logging read "resource.type=cloud_run_revision" --limit=50'
alias netra-errors='gcloud logging read "severity>=ERROR" --limit=20'
alias netra-status='gcloud run services list --region=${REGION}'
alias netra-db='gcloud sql connect $(terraform output -raw database_connection_name) --user=netra_user'
alias netra-urls='terraform output'
alias netra-deploy='./terraform-gcp/deploy.sh'
alias netra-backup='gcloud sql backups create --instance=$(terraform output -raw database_connection_name)'
```

---

## 📞 Support Contacts

- **On-Call**: Check PagerDuty
- **Slack**: #netra-platform
- **Escalation**: devops@netrasystems.ai
- **GCP Support**: [Console](https://console.cloud.google.com/support)

---

## 🔗 Quick Links

- [Full Deployment Guide](./DEPLOYMENT_GUIDE_COMPREHENSIVE.md)
- [GCP Console](https://console.cloud.google.com)
- [Terraform Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Monitoring Dashboard](https://console.cloud.google.com/monitoring)

---

**Print this page and keep it handy during deployments!**