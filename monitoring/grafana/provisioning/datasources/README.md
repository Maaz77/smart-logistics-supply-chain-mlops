# Grafana Datasource Provisioning

This directory contains Grafana datasource provisioning configuration.

## Files

- `datasource.yml.template` - Template file with environment variable placeholders
- `datasources.yml` - Generated file (created automatically on container startup)
  - **Note:** Grafana expects the filename to be `datasources.yml` (plural), not `datasource.yml`

## How It Works

1. The template file (`datasource.yml.template`) contains placeholders for environment variables:
   - `${POSTGRES_HOST}` - PostgreSQL hostname (default: `mlflow-postgres`)
   - `${POSTGRES_PORT}` - PostgreSQL port (default: `5432`)
   - `${POSTGRES_DATABASE}` - Database name (default: `monitoring`)
   - `${POSTGRES_USER}` - Database user (default: `mlflow`)
   - `${POSTGRES_PASSWORD}` - Database password (default: `mlflow`)

2. On container startup, the docker-compose command:
   - Waits for PostgreSQL to be ready
   - Processes the template using `envsubst` to substitute environment variables
   - Generates the final `datasource.yml` file
   - Grafana automatically reads this file and creates the datasource

## Configuration

Environment variables can be set in:
- `.env` file in the project root
- Docker compose environment section
- System environment variables

The datasource is automatically created when Grafana starts and is editable through the Grafana UI.
