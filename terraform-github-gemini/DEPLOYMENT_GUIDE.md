# Terraform Deployment Guide

This guide explains how to deploy the Terraform infrastructure using the provided GitHub Action workflow.

## Prerequisites

1.  **Google Cloud Platform (GCP) Project:** You need a GCP project with the necessary APIs enabled.
2.  **GCP Service Account:** Create a GCP service account with the `Editor` role or a custom role with the necessary permissions to create the resources defined in the Terraform configuration.
3.  **GCP Service Account Key:** Create a JSON key for the service account and encode it in Base64.

## GitHub Secrets

You need to configure the following secret in your GitHub repository settings:

*   `GCP_SA_KEY`: The Base64 encoded JSON key for your GCP service account.

To add the secret:

1.  Go to your GitHub repository.
2.  Click on `Settings` > `Secrets and variables` > `Actions`.
3.  Click on `New repository secret`.
4.  Enter `GCP_SA_KEY` as the name and the Base64 encoded key as the value.

## GitHub Action Workflow

The GitHub Action workflow is defined in `.github/workflows/deploy.yml`. It automates the process of initializing, planning, and applying Terraform changes.

### Workflow Triggers

The workflow is triggered by the following events:

*   **Push to `main` branch:** When changes are pushed to the `main` branch, the workflow will automatically initialize, plan, and apply the Terraform changes.
*   **Pull Request:** When a pull request is created or updated, the workflow will initialize, validate, and create a Terraform plan. This allows you to review the planned changes before merging the pull request.

### Workflow Steps

1.  **Checkout:** Checks out the repository code.
2.  **Set up Terraform:** Sets up the specified version of Terraform.
3.  **Terraform Init:** Initializes the Terraform working directory.
4.  **Terraform Validate:** Validates the Terraform configuration.
5.  **Terraform Plan:** Creates a Terraform plan. The plan is saved as an artifact for pull requests.
6.  **Terraform Apply:** Applies the Terraform changes. This step is only executed on pushes to the `main` branch.

## Manual Deployment

To manually trigger a deployment, you can push a change to the `main` branch. For example, you can create an empty commit:

```bash
git commit --allow-empty -m "Trigger deployment"
git push origin main
```

## Approving Deployments

For pull requests, the workflow will automatically generate a Terraform plan. You can review the plan in the pull request to ensure that the changes are expected. To approve the deployment, you need to merge the pull request into the `main` branch. Once the pull request is merged, the workflow will automatically apply the changes.
