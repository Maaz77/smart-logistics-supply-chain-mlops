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

# Function to check Docker resources
check_docker_resources() {
    echo "  ${CYAN}Checking Docker resources...${RESET}"
    DOCKER_MEM=$(docker info 2>/dev/null | grep -i "Total Memory" | awk '{print $3}' | sed 's/GiB//' || echo "0")
    DOCKER_CPUS=$(docker info 2>/dev/null | grep -i "CPUs" | awk '{print $2}' || echo "0")

    if [ -n "$DOCKER_MEM" ] && [ "$DOCKER_MEM" != "0" ]; then
        MEM_GB=$(echo "$DOCKER_MEM" | awk '{print int($1)}')
        if [ "$MEM_GB" -lt 4 ]; then
            echo "  ${YELLOW}⚠ Docker has only ${MEM_GB}GB memory allocated (recommended: 4GB+)${RESET}"
        else
            echo "  ${GREEN}✓${RESET} Docker memory: ${MEM_GB}GB"
        fi
    fi

    if [ -n "$DOCKER_CPUS" ] && [ "$DOCKER_CPUS" != "0" ]; then
        CPU_COUNT=$(echo "$DOCKER_CPUS" | awk '{print int($1)}')
        if [ "$CPU_COUNT" -lt 2 ]; then
            echo "  ${YELLOW}⚠ Docker has only ${CPU_COUNT} CPU(s) allocated (recommended: 2+)${RESET}"
        else
            echo "  ${GREEN}✓${RESET} Docker CPUs: ${CPU_COUNT}"
        fi
    fi
}

# Function to cleanup partial cluster
cleanup_partial_cluster() {
    echo "  ${CYAN}Cleaning up any partial cluster state...${RESET}"
    # Delete cluster if it exists (even if broken)
    kind delete cluster --name "${CLUSTER_NAME}" 2>/dev/null || true
    # Clean up any orphaned containers (macOS compatible)
    ORPHANED_CONTAINERS=$(docker ps -a --filter "name=${CLUSTER_NAME}" --format "{{.ID}}" 2>/dev/null)
    if [ -n "$ORPHANED_CONTAINERS" ]; then
        echo "$ORPHANED_CONTAINERS" | while read -r container_id; do
            docker rm -f "$container_id" 2>/dev/null || true
        done
    fi
    # Clean up any orphaned networks (macOS compatible)
    ORPHANED_NETWORKS=$(docker network ls --filter "name=${CLUSTER_NAME}" --format "{{.ID}}" 2>/dev/null)
    if [ -n "$ORPHANED_NETWORKS" ]; then
        echo "$ORPHANED_NETWORKS" | while read -r network_id; do
            docker network rm "$network_id" 2>/dev/null || true
        done
    fi
    sleep 2
}

# Function to create cluster with retry logic
create_cluster_with_retry() {
    local max_attempts=3
    local attempt=1
    local wait_time=5

    while [ $attempt -le $max_attempts ]; do
        echo "  ${CYAN}Attempt $attempt/$max_attempts: Creating cluster...${RESET}"

        # Clean up any partial state before retry
        if [ $attempt -gt 1 ]; then
            cleanup_partial_cluster
            echo "  ${CYAN}Waiting ${wait_time} seconds before retry...${RESET}"
            sleep $wait_time
            wait_time=$((wait_time * 2))  # Exponential backoff
        fi

        set +e  # Temporarily disable exit on error
        cat <<EOF | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
networking:
  # Allow pods to reach host.docker.internal
  # This is the default on Docker Desktop for Mac, but we make it explicit
  apiServerAddress: "127.0.0.1"
  apiServerPort: 6443
nodes:
- role: control-plane
  extraMounts:
  - hostPath: /var/run/docker.sock
    containerPath: /var/run/docker.sock
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
EOF
        CLUSTER_CREATE_STATUS=$?
        set -e  # Re-enable exit on error

        if [ $CLUSTER_CREATE_STATUS -eq 0 ]; then
            echo "  ${GREEN}✓${RESET} Cluster created successfully on attempt $attempt"
            return 0
        else
            echo "  ${YELLOW}⚠ Attempt $attempt failed${RESET}"
            if [ $attempt -lt $max_attempts ]; then
                echo "  ${CYAN}Will retry...${RESET}"
            fi
        fi

        attempt=$((attempt + 1))
    done

    return 1
}

echo ""
echo "${BOLD}${CYAN}🚀 Setting up Kubernetes Infrastructure${RESET}"
echo ""

# Check prerequisites
echo "${CYAN}Step 1/5: Checking prerequisites...${RESET}"
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

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "${RED}✗ Docker is not running${RESET}"
    echo "  Please start Docker Desktop and try again"
    exit 1
fi

# Check if port 6443 is available
if lsof -Pi :6443 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "${YELLOW}⚠ Port 6443 is already in use${RESET}"
    echo "  Attempting to clean up..."
    cleanup_partial_cluster
    sleep 2
    if lsof -Pi :6443 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo "  ${YELLOW}⚠ Port 6443 still in use after cleanup${RESET}"
        echo "  You may need to manually stop other Kubernetes clusters"
    else
        echo "  ${GREEN}✓${RESET} Port 6443 is now available"
    fi
fi

check_docker_resources

echo "  ${GREEN}✓${RESET} kind: $(kind --version)"
echo "  ${GREEN}✓${RESET} kubectl: $(kubectl version --client --short 2>/dev/null | cut -d' ' -f3)"
echo "  ${GREEN}✓${RESET} Docker is running"
echo ""

# Create Kind cluster
echo "${CYAN}Step 2/5: Creating Kind cluster '${CLUSTER_NAME}'...${RESET}"
if kind get clusters | grep -q "^${CLUSTER_NAME}$"; then
    echo "  ${YELLOW}⚠ Cluster '${CLUSTER_NAME}' already exists${RESET}"
    read -p "  Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  ${CYAN}Deleting existing cluster...${RESET}"
        kind delete cluster --name "${CLUSTER_NAME}"
    else
        echo "  ${YELLOW}Skipping cluster creation${RESET}"
        echo ""
        echo "${CYAN}Step 3/5: Checking ArgoCD installation...${RESET}"
        if kubectl get namespace "${ARGOCD_NAMESPACE}" &> /dev/null; then
            echo "  ${GREEN}✓${RESET} ArgoCD namespace exists"
            echo ""
            echo "${CYAN}Step 4/5: Patching ArgoCD service...${RESET}"
            kubectl patch svc argocd-server -n "${ARGOCD_NAMESPACE}" -p '{"spec":{"type":"LoadBalancer"}}' 2>/dev/null || \
            kubectl patch svc argocd-server -n "${ARGOCD_NAMESPACE}" -p '{"spec":{"type":"NodePort"}}' 2>/dev/null || true
            echo "  ${GREEN}✓${RESET} ArgoCD service patched"
            echo ""
            echo "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
            echo "${GREEN}${BOLD}✓ Setup complete!${RESET}"
            echo "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
            echo ""
            echo "${YELLOW}ArgoCD Access:${RESET}"
            echo "  • Get admin password: ${CYAN}kubectl -n ${ARGOCD_NAMESPACE} get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d${RESET}"
            echo "  • Port forward: ${CYAN}kubectl port-forward svc/argocd-server -n ${ARGOCD_NAMESPACE} 8080:443${RESET}"
            echo "  • Then access: ${CYAN}https://localhost:8080${RESET}"
            exit 0
        fi
    fi
fi

# Create cluster config with host.docker.internal support
echo "  ${CYAN}Creating cluster configuration...${RESET}"

if ! create_cluster_with_retry; then
    echo ""
    echo "${RED}✗ Failed to create Kind cluster after multiple attempts${RESET}"
    echo ""

    # Check for specific issues
    echo "${CYAN}Diagnostics:${RESET}"
    echo ""

    # Check Docker resources
    check_docker_resources
    echo ""

    # Check for orphaned containers
    ORPHANED=$(docker ps -a --filter "name=${CLUSTER_NAME}" --format "{{.Names}}" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$ORPHANED" -gt 0 ]; then
        echo "  ${YELLOW}⚠ Found $ORPHANED orphaned container(s)${RESET}"
        echo "  ${CYAN}Attempting automatic cleanup...${RESET}"
        cleanup_partial_cluster
        echo ""
        read -p "  Would you like to try one more time? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if create_cluster_with_retry; then
                echo "  ${GREEN}✓${RESET} Cluster created after cleanup!"
            else
                echo "  ${RED}✗ Still failing after cleanup${RESET}"
            fi
        fi
    fi

    echo ""
    echo "${YELLOW}Troubleshooting steps:${RESET}"
    echo "  1. Ensure Docker Desktop is running and has enough resources:"
    echo "     • Memory: At least 4GB allocated (8GB recommended)"
    echo "     • CPU: At least 2 cores allocated"
    echo "     • Check: Docker Desktop → Settings → Resources"
    echo ""
    echo "  2. Free up Docker resources:"
    echo "     ${CYAN}docker system prune -a${RESET}  # Remove unused images/containers"
    echo "     ${CYAN}docker system df${RESET}  # Check disk usage"
    echo ""
    echo "  3. Check for port conflicts:"
    echo "     ${CYAN}lsof -i :6443${RESET}"
    echo ""
    echo "  4. Manually clean up and retry:"
    echo "     ${CYAN}kind delete cluster --name ${CLUSTER_NAME}${RESET}"
    echo "     ${CYAN}docker system prune -f${RESET}"
    echo "     ${CYAN}make setup-k8s${RESET}"
    echo ""
    echo "  5. If issues persist, restart Docker Desktop completely"
    echo ""

    # Ask for permission to clean up Docker
    read -p "  Would you like to run 'docker system prune' to free up resources? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "  ${CYAN}Running docker system prune...${RESET}"
        docker system prune -f
        echo "  ${GREEN}✓${RESET} Cleanup complete"
        echo ""
        read -p "  Try creating cluster again? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cleanup_partial_cluster
            if create_cluster_with_retry; then
                echo "  ${GREEN}✓${RESET} Cluster created successfully!"
            else
                exit 1
            fi
        else
            exit 1
        fi
    else
        exit 1
    fi
fi

echo "  ${GREEN}✓${RESET} Cluster created"
echo ""

# Wait for cluster to be ready
echo "${CYAN}Step 3/5: Waiting for cluster to be ready...${RESET}"
echo "  ${CYAN}This may take 1-2 minutes...${RESET}"
if ! kubectl wait --for=condition=Ready nodes --all --timeout=180s 2>/dev/null; then
    echo ""
    echo "${YELLOW}⚠ Cluster nodes not ready within timeout${RESET}"
    echo "  Checking cluster status..."
    kubectl get nodes 2>/dev/null || true
    echo ""
    echo "  ${CYAN}You can check logs with:${RESET}"
    echo "    ${CYAN}docker logs ${CLUSTER_NAME}-control-plane${RESET}"
    echo ""
    echo "  ${YELLOW}The cluster may still be initializing. Continuing...${RESET}"
fi
echo "  ${GREEN}✓${RESET} Cluster ready"
echo ""

# Install ArgoCD
echo "${CYAN}Step 4/5: Installing ArgoCD...${RESET}"
kubectl create namespace "${ARGOCD_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${ARGOCD_NAMESPACE}" -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

echo "  ${CYAN}Waiting for ArgoCD pods to be ready...${RESET}"
kubectl wait --for=condition=Ready pods --all -n "${ARGOCD_NAMESPACE}" --timeout=300s || true

# Check if pods are ready
READY_PODS=$(kubectl get pods -n "${ARGOCD_NAMESPACE}" --field-selector=status.phase=Running --no-headers | wc -l | tr -d ' ')
TOTAL_PODS=$(kubectl get pods -n "${ARGOCD_NAMESPACE}" --no-headers | wc -l | tr -d ' ')

if [ "${READY_PODS}" -lt "${TOTAL_PODS}" ]; then
    echo "  ${YELLOW}⚠ Some ArgoCD pods are still starting...${RESET}"
    echo "  ${CYAN}You can check status with: kubectl get pods -n ${ARGOCD_NAMESPACE}${RESET}"
else
    echo "  ${GREEN}✓${RESET} All ArgoCD pods ready"
fi
echo ""

# Patch ArgoCD service
echo "${CYAN}Step 5/5: Patching ArgoCD service to LoadBalancer...${RESET}"
kubectl patch svc argocd-server -n "${ARGOCD_NAMESPACE}" -p '{"spec":{"type":"LoadBalancer"}}' || \
kubectl patch svc argocd-server -n "${ARGOCD_NAMESPACE}" -p '{"spec":{"type":"NodePort"}}' || true
echo "  ${GREEN}✓${RESET} ArgoCD service patched"
echo ""

echo "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
echo "${GREEN}${BOLD}✓ Setup complete!${RESET}"
echo "${GREEN}${BOLD}════════════════════════════════════════${RESET}"
echo ""
echo "${YELLOW}Cluster Information:${RESET}"
echo "  • Cluster name: ${CYAN}${CLUSTER_NAME}${RESET}"
echo "  • Context: ${CYAN}$(kubectl config current-context)${RESET}"
echo ""
echo "${YELLOW}ArgoCD Access:${RESET}"
echo "  • Get admin password: ${CYAN}kubectl -n ${ARGOCD_NAMESPACE} get secret argocd-initial-admin-secret -o jsonpath=\"{.data.password}\" | base64 -d${RESET}"
echo "  • Port forward: ${CYAN}kubectl port-forward svc/argocd-server -n ${ARGOCD_NAMESPACE} 8080:443${RESET}"
echo "  • Then access: ${CYAN}https://localhost:8080${RESET}"
echo ""
echo "${YELLOW}Next Steps:${RESET}"
echo "  1. Build and push images: ${CYAN}make build-push DOCKER_USER=your_username${RESET}"
echo "  2. Update image names in ${CYAN}k8s/apps/*.yaml${RESET} if needed"
echo "  3. Deploy to cluster: ${CYAN}make deploy-k8s${RESET}"
echo ""
