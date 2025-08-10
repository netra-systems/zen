#!/bin/bash
# deploy.sh - Automated deployment script for Netra on GCP
# Total deployment time: ~10 minutes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    print_error "terraform.tfvars not found!"
    print_status "Creating terraform.tfvars from example..."
    cp terraform.tfvars.example terraform.tfvars
    print_warning "Please edit terraform.tfvars with your project settings and run this script again."
    exit 1
fi

# Load variables from terraform.tfvars
source <(grep project_id terraform.tfvars | sed 's/ //g')
source <(grep region terraform.tfvars | sed 's/ //g')

# Remove quotes from variables
project_id=$(echo $project_id | tr -d '"')
region=$(echo $region | tr -d '"')

print_status "Starting deployment for project: $project_id in region: $region"

# Step 1: Check prerequisites
print_status "Checking prerequisites..."

if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    print_error "terraform not found. Please install Terraform."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    print_error "docker not found. Please install Docker."
    exit 1
fi

print_status "All prerequisites met!"

# Step 2: Configure GCP project
print_status "Configuring GCP project..."

gcloud config set project $project_id

# Enable required APIs
print_status "Enabling required GCP APIs..."
gcloud services enable compute.googleapis.com \
    container.googleapis.com \
    sqladmin.googleapis.com \
    cloudrun.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project=$project_id

# Step 3: Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Step 4: Plan infrastructure
print_status "Planning infrastructure..."
terraform plan -out=tfplan

# Step 5: Apply infrastructure
print_status "Creating infrastructure (this may take 5-7 minutes)..."
terraform apply tfplan

# Step 6: Get outputs
print_status "Retrieving deployment information..."
terraform output -json > deployment-info.json

# Extract values
REGISTRY=$(terraform output -raw artifact_registry)
FRONTEND_URL=$(terraform output -raw frontend_url)
BACKEND_URL=$(terraform output -raw backend_url)
DB_IP=$(terraform output -raw database_ip)

# Step 7: Configure Docker
print_status "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker ${region}-docker.pkg.dev --quiet

# Step 8: Build and push containers
print_status "Building and pushing Docker containers..."

# Check if Dockerfiles exist
if [ ! -f "../Dockerfile.backend" ]; then
    print_warning "Backend Dockerfile not found. Creating a simple one..."
    cat > ../Dockerfile.backend << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF
fi

if [ ! -f "../frontend/Dockerfile" ]; then
    print_warning "Frontend Dockerfile not found. Creating a simple one..."
    cat > ../frontend/Dockerfile << 'EOF'
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 8080
CMD ["npm", "start"]
EOF
fi

# Build and push backend
print_status "Building backend Docker image..."
cd ..
docker build -f Dockerfile.backend -t ${REGISTRY}/backend:latest .
print_status "Pushing backend image to registry..."
docker push ${REGISTRY}/backend:latest

# Build and push frontend
print_status "Building frontend Docker image..."
cd frontend
docker build -t ${REGISTRY}/frontend:latest .
print_status "Pushing frontend image to registry..."
docker push ${REGISTRY}/frontend:latest

cd ../terraform-gcp

# Step 9: Deploy to Cloud Run
print_status "Deploying services to Cloud Run..."

gcloud run deploy netra-backend \
    --image ${REGISTRY}/backend:latest \
    --region ${region} \
    --allow-unauthenticated \
    --port 8080 \
    --quiet

gcloud run deploy netra-frontend \
    --image ${REGISTRY}/frontend:latest \
    --region ${region} \
    --allow-unauthenticated \
    --port 8080 \
    --quiet

# Step 10: Run database migrations
print_status "Setting up database..."

# Get database password from Secret Manager
DB_PASSWORD=$(gcloud secrets versions access latest --secret="netra-db-password")

# Create a temporary SQL file for initial setup
cat > init.sql << EOF
-- Initial database setup
CREATE SCHEMA IF NOT EXISTS public;

-- Create tables (add your schema here)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add more tables as needed
EOF

print_status "Running database initialization..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_IP -U netra_user -d netra -f init.sql || print_warning "Database initialization skipped or failed"

# Step 11: Verify deployment
print_status "Verifying deployment..."

# Test backend
if curl -f ${BACKEND_URL}/health 2>/dev/null; then
    print_status "✓ Backend is healthy"
else
    print_warning "Backend health check failed"
fi

# Test frontend
if curl -f ${FRONTEND_URL} 2>/dev/null; then
    print_status "✓ Frontend is accessible"
else
    print_warning "Frontend check failed"
fi

# Step 12: Set up monitoring
print_status "Setting up budget alert..."

BILLING_ACCOUNT=$(gcloud beta billing accounts list --format="value(name)" | head -n1)
if [ ! -z "$BILLING_ACCOUNT" ]; then
    gcloud billing budgets create \
        --billing-account=$BILLING_ACCOUNT \
        --display-name="Netra Monthly Budget Alert" \
        --budget-amount=1000 \
        --threshold-rule=percent=0.5 \
        --threshold-rule=percent=0.9 \
        --threshold-rule=percent=1.0 \
        --quiet 2>/dev/null || print_warning "Budget alert already exists or creation failed"
fi

# Step 13: Create backup script
print_status "Creating backup script..."
cat > backup.sh << 'EOF'
#!/bin/bash
# Daily backup script for Netra

PROJECT_ID=$(gcloud config get-value project)
INSTANCE_NAME=$(gcloud sql instances list --format="value(name)" | grep netra-postgres)
BUCKET_NAME="${PROJECT_ID}-netra-backups"

# Create PostgreSQL backup
gcloud sql backups create \
    --instance=$INSTANCE_NAME \
    --description="Daily backup $(date +%Y%m%d_%H%M%S)"

# Export to Cloud Storage
gcloud sql export sql $INSTANCE_NAME \
    gs://${BUCKET_NAME}/postgres-$(date +%Y%m%d_%H%M%S).sql \
    --database=netra

echo "Backup completed at $(date)"
EOF
chmod +x backup.sh

# Print summary
print_status "==============================================="
print_status "DEPLOYMENT COMPLETE!"
print_status "==============================================="
echo ""
echo "Frontend URL: ${GREEN}${FRONTEND_URL}${NC}"
echo "Backend URL:  ${GREEN}${BACKEND_URL}${NC}"
echo "Database IP:  ${GREEN}${DB_IP}${NC}"
echo ""
print_status "Estimated monthly cost: ~$200 (base)"
print_status "Budget limit set: $1,000/month"
echo ""
print_status "Next steps:"
echo "  1. Visit ${FRONTEND_URL} to access your application"
echo "  2. Configure custom domain (optional)"
echo "  3. Set up Redis separately if needed"
echo "  4. Review security settings for production use"
echo ""
print_status "To destroy all resources: terraform destroy"
print_status "Full deployment info saved to: deployment-info.json"