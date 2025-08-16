# Learnings Module Structure

This directory contains modularized learnings organized by category for better navigation and maintenance.

## Structure

- **index.xml** - Main index with all categories, learning IDs, and file mappings
- **Category files** - Individual XML files for each category containing related learnings

## Categories

| Category | File | Description |
|----------|------|-------------|
| Configuration/Secrets | `configuration_secrets.xml` | Secret management and configuration issues |
| Database/AsyncIO | `database_asyncio.xml` | Database and async/await patterns |
| Demo Readiness | `demo_readiness.xml` | Demo preparation and requirements |
| Development/Git | `development_git.xml` | Git workflow and branch management |
| Infrastructure | `infrastructure.xml` | General infrastructure configuration |
| Infrastructure/Cloud Run | `infrastructure_cloud_run.xml` | Cloud Run deployment issues |
| Infrastructure/Secret Management | `infrastructure_secret_management.xml` | Secret Manager specific issues |
| Type Safety | `type_safety.xml` | Type safety patterns and fixes |

## Usage

1. **Finding a specific learning**: Check `index.xml` for learning IDs and their categories
2. **Category-specific search**: Open the relevant category file directly
3. **Adding new learnings**: Add to the appropriate category file and update index.xml

## Benefits

- **Faster loading** - Smaller files load quicker than one large file
- **Better organization** - Related learnings are grouped together
- **Easier maintenance** - Updates affect only relevant category files
- **Improved searchability** - Target specific domains without scanning entire file

## Migration

The original `learnings.xml` has been split into these modular files. All existing learnings have been preserved with their original IDs and content.