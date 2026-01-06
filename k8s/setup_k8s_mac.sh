#!/bin/bash
# ============================================
# Kubernetes Setup Script for Mac
# ============================================
# Creates Kind cluster and installs ArgoCD
# ============================================

set -e

# Colors
CYAN='\033[36m'
GREEN='\033[32m'
RED='\033[31m'
YELLOW='\033[33m'
BOLD='\033[1m'
RESET='\033[0m'

CLUSTER_NAME="modelserving-cluster"
ARGOCD_NAMESPACE="argocd"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "${BOLD}${CYAN}🚀 Setting up Kubernetes Infrastructure${RESET}"
echo ""

# Check prerequisites
echo "${CYAN}Checking prerequisites...${RESET}"
if ! command -v kind &> /dev/null; then
    echo "${RED}✗ kind not found${RESET}"
    echo "  Install: ${CYAN}brew install kind${RESET}"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "${RED}✗ kubectl not found${RESET}"
    echo "  Install: ${CYAN}brew install kubectl${RESET}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "${RED}✗ Docker is not running${RESET}"
    echo "  Please start Docker Desktop and try again"
    exit 1
fi

echo "  ${GREEN}✓${RESET} Prerequisites met"
echo ""

# Delete existing cluster if it exists
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "${CYAN}Deleting existing cluster...${RESET}"
    kind delete cluster --name "${CLUSTER_NAME}"
fi

# Create Kind cluster
echo "${CYAN}Creating Kind cluster...${RESET}"
kind create cluster --name "${CLUSTER_NAME}" --config "${SCRIPT_DIR}/kind-cluster.yaml"
echo "  ${GREEN}✓${RESET} Cluster created"
echo ""

# Wait for cluster to be ready
echo "${CYAN}Waiting for cluster to be ready...${RESET}"
kubectl wait --for=condition=Ready nodes --all --timeout=180s
echo "  ${GREEN}✓${RESET} Cluster ready"
echo ""

# Install ArgoCD
echo "${CYAN}Installing ArgoCD...${RESET}"
kubectl apply -f "${SCRIPT_DIR}/argocd/namespace.yaml"
kubectl apply -n "${ARGOCD_NAMESPACE}" -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "  ${CYAN}Waiting for ArgoCD pods...${RESET}"
kubectl wait --for=condition=Ready pods --all -n "${ARGOCD_NAMESPACE}" --timeout=300s || true
echo "  ${GREEN}✓${RESET} ArgoCD installed"
echo ""

# Create ArgoCD Application (tells ArgoCD to manage your apps)
echo "${CYAN}Creating ArgoCD Application...${RESET}"
kubectl apply -f "${SCRIPT_DIR}/argocd/app.yaml"
echo "  ${GREEN}✓${RESET} ArgoCD Application created"
echo ""

# Patch ArgoCD service
# The patch to LoadBalancer/NodePort is:
# Useful on cloud providers (AWS, GCP, Azure)
# Not effective on Kind for direct access
# Port-forwarding is still needed on Kind
echo "${CYAN}Patching ArgoCD service...${RESET}"
kubectl patch svc argocd-server -n "${ARGOCD_NAMESPACE}" -p '{"spec":{"type":"LoadBalancer"}}' || \
kubectl patch svc argocd-server -n "${ARGOCD_NAMESPACE}" -p '{"spec":{"type":"NodePort"}}' || true
echo "  ${GREEN}✓${RESET} ArgoCD service patched"
echo ""

echo "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
echo "${GREEN}${BOLD}✓ Setup complete!${RESET}"
echo "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
echo ""
echo "${YELLOW}ArgoCD Access:${RESET}"
echo "  • Get admin password: ${CYAN}kubectl -n ${ARGOCD_NAMESPACE} get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d${RESET}"
echo "  • Port forward: ${CYAN}kubectl port-forward svc/argocd-server -n ${ARGOCD_NAMESPACE} 8088:443${RESET}"
echo "  • Then access: ${CYAN}https://localhost:8088${RESET}"
echo ""
