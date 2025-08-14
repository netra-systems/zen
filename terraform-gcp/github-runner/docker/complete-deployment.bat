@echo off
REM Complete deployment script for GitHub Runner on Cloud Run (Windows)

set PROJECT_ID=cryptic-net-466001-n0
set REGION=us-central1
set IMAGE_URL=%REGION%-docker.pkg.dev/%PROJECT_ID%/github-runners/runner:latest

echo GitHub Runner Cloud Run Deployment - Final Steps
echo ================================================
echo.

REM Step 1: Authenticate
echo Step 1: Authenticating with Google Cloud...
echo Please complete the authentication flow if prompted:
gcloud auth login

REM Step 2: Set project
echo.
echo Step 2: Setting project to %PROJECT_ID%...
gcloud config set project %PROJECT_ID%

REM Step 3: Configure Docker authentication  
echo.
echo Step 3: Configuring Docker authentication...
gcloud auth configure-docker %REGION%-docker.pkg.dev

REM Step 4: Build and push Docker image
echo.
echo Step 4: Building and pushing Docker image...
cd /d "%~dp0"

REM Use Cloud Build
echo Submitting build to Cloud Build...
gcloud builds submit --config cloudbuild.yaml --project %PROJECT_ID% .

REM Step 5: Complete Terraform deployment
echo.
echo Step 5: Completing Terraform deployment...
set /p GITHUB_TOKEN=Enter GitHub PAT (ghp_...): 

set TF_VAR_github_token=%GITHUB_TOKEN%
terraform init
terraform apply -auto-approve

REM Step 6: Show results
echo.
echo ================================================
echo Deployment Complete!
echo ================================================
echo.
echo Outputs:
terraform output

echo.
echo To view logs:
echo   gcloud run services logs read github-runner --region=%REGION%

echo.
echo To check runner status:
echo   Visit: https://github.com/netra-systems/netra-apex/settings/actions/runners

pause