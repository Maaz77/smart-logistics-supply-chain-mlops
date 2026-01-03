#!/bin/bash
# ============================================
# Initialize Monitoring Database
# ============================================
# Creates the 'monitoring' database in the existing mlflow-postgres container
# This script is idempotent - safe to run multiple times
# ============================================

set -e

# Colors for output
CYAN='\033[36m'
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
RESET='\033[0m'

# Get PostgreSQL credentials from environment or use defaults
POSTGRES_USER=${POSTGRES_USER:-mlflow}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-mlflow}
POSTGRES_DB=${POSTGRES_DB:-mlflow}
MONITORING_DB=${MONITORING_DB:-monitoring}

CONTAINER_NAME="mlflow-postgres"

echo -e "${CYAN}Initializing monitoring database...${RESET}"
echo ""

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}✗ Container '${CONTAINER_NAME}' is not running${RESET}"
    echo -e "${YELLOW}  Please start infrastructure first: make infra-up${RESET}"
    exit 1
fi

echo -e "${CYAN}Container '${CONTAINER_NAME}' is running${RESET}"

# Create monitoring database if it doesn't exist
echo -e "${CYAN}Creating database '${MONITORING_DB}' if it doesn't exist...${RESET}"

docker exec -i "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -d postgres <<EOF
-- Create database if it doesn't exist (idempotent)
SELECT 'CREATE DATABASE ${MONITORING_DB}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${MONITORING_DB}')\gexec

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE ${MONITORING_DB} TO ${POSTGRES_USER};
EOF

# Verify database was created
if docker exec "${CONTAINER_NAME}" psql -U "${POSTGRES_USER}" -lqt | cut -d \| -f 1 | grep -qw "${MONITORING_DB}"; then
    echo -e "${GREEN}✓ Database '${MONITORING_DB}' is ready${RESET}"
    echo ""
    echo -e "${GREEN}Database Details:${RESET}"
    echo "  • Database: ${MONITORING_DB}"
    echo "  • User: ${POSTGRES_USER}"
    echo "  • Host: mlflow-postgres:5432 (from containers)"
    echo "  • Host: localhost:5432 (from host machine)"
else
    echo -e "${RED}✗ Failed to create database '${MONITORING_DB}'${RESET}"
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Monitoring database initialization complete!${RESET}"
