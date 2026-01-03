#!/bin/bash
# ============================================
# Generate Grafana Datasource Configuration
# ============================================
# This script generates the datasource.yml file from the template
# using environment variables before Grafana starts.

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROVISIONING_DIR="$PROJECT_ROOT/monitoring/grafana/provisioning/datasources"
TEMPLATE_FILE="$PROVISIONING_DIR/datasource.yml.template"
OUTPUT_FILE="$PROVISIONING_DIR/datasources.yml"

# Default values
POSTGRES_HOST=${POSTGRES_HOST:-mlflow-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DATABASE=${POSTGRES_DATABASE:-monitoring}
POSTGRES_USER=${POSTGRES_USER:-mlflow}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-mlflow}

echo "Generating Grafana datasource configuration..."
echo "  Template: $TEMPLATE_FILE"
echo "  Output: $OUTPUT_FILE"

# Check if template exists
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "Error: Template file not found: $TEMPLATE_FILE"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$PROVISIONING_DIR"

# Substitute environment variables
export POSTGRES_HOST POSTGRES_PORT POSTGRES_DATABASE POSTGRES_USER POSTGRES_PASSWORD

# Use envsubst if available, otherwise use sed
if command -v envsubst >/dev/null 2>&1; then
    envsubst < "$TEMPLATE_FILE" > "$OUTPUT_FILE"
else
    # Fallback to sed (less robust but works)
    sed -e "s|\${POSTGRES_HOST}|${POSTGRES_HOST}|g" \
        -e "s|\${POSTGRES_PORT}|${POSTGRES_PORT}|g" \
        -e "s|\${POSTGRES_DATABASE}|${POSTGRES_DATABASE}|g" \
        -e "s|\${POSTGRES_USER}|${POSTGRES_USER}|g" \
        -e "s|\${POSTGRES_PASSWORD}|${POSTGRES_PASSWORD}|g" \
        "$TEMPLATE_FILE" > "$OUTPUT_FILE"
fi

echo "✓ Datasource configuration generated"
echo "  Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "  Database: ${POSTGRES_DATABASE}"
echo "  User: ${POSTGRES_USER}"

# Verify the file was created
if [ -f "$OUTPUT_FILE" ]; then
    echo "✓ File created successfully"
    echo ""
    echo "Generated content:"
    cat "$OUTPUT_FILE"
else
    echo "✗ Error: Failed to create output file"
    exit 1
fi
