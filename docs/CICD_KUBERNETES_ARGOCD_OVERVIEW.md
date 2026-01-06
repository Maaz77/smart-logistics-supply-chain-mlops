# Comprehensive CI/CD, Kubernetes, and ArgoCD Overview Report

## Table of Contents
1. [Kubernetes Fundamentals](#kubernetes-fundamentals)
2. [Service Types and Networking](#service-types-and-networking)
3. [ArgoCD and GitOps](#argocd-and-gitops)
4. [CI/CD Workflows](#cicd-workflows)
5. [Model Deployment Strategies](#model-deployment-strategies)
6. [Project-Specific Implementation](#project-specific-implementation)
7. [Cross-Cluster Communication](#cross-cluster-communication-kubernetes-to-host-services)
8. [Best Practices and Recommendations](#best-practices-and-recommendations)

---

## Kubernetes Fundamentals

### Namespaces

**What is a Namespace?**
- A Kubernetes namespace is a virtual cluster that provides isolation and organization for resources
- Groups related resources (deployments, services, pods) together
- Separates resources from the `default` namespace or other namespaces

**Project Implementation:**
- `mlops-production` namespace: Contains application deployments (API, UI)
- `argocd` namespace: Contains ArgoCD components
- Defined in `k8s/apps/namespace.yaml` and `k8s/argocd/namespace.yaml`

**Key Points:**
- Namespaces are optional but recommended for organization
- Labels can be added for filtering and organization
- Resources are scoped to their namespace

### Deployments

**What is a Deployment?**
- A Kubernetes resource that manages pods and replicas
- Handles rolling updates, rollbacks, and scaling
- Ensures desired number of pods are running

**Relationship to Containers:**
- Typically, one deployment = one container image
- A deployment can have multiple containers (sidecar pattern)
- Each container in a pod can have a different image

**Project Implementation:**
- `serving-api` deployment: Manages API pods with `mlops-serving-api:latest` image
- `serving-ui` deployment: Manages UI pods with `mlops-serving-ui:latest` image
- Defined in `k8s/apps/api-deployment.yaml` and `k8s/apps/ui-deployment.yaml`

**Key Configuration:**
```yaml
spec:
  replicas: 2  # Number of pod instances
  template:
    spec:
      containers:
      - name: api
        image: maazamin98/mlops-serving-api:latest
```

### Pods and Nodes

**What is a Pod?**
- Smallest deployable unit in Kubernetes
- Contains one or more containers that share storage and network
- Ephemeral - can be created, destroyed, and recreated

**What is a Node?**
- A worker machine (physical or virtual) in the cluster
- Can run multiple pods
- In Kind clusters, nodes are Docker containers

**Service Exposure:**
- Services expose pods at the **cluster level**, not node level
- Services route to pods across all nodes in the cluster
- If a pod moves to another node, the service still routes to it
- Services provide stable IP and DNS name regardless of pod location

**Current Project Setup:**
- Single control-plane node in Kind cluster
- All pods run on this single node
- For production, multiple nodes recommended for high availability

### ConfigMaps

**What is a ConfigMap?**
- Kubernetes resource for storing configuration data
- Separates configuration from application code
- Can be mounted as files or used as environment variables

**Why Use ConfigMaps vs Direct Env Vars?**
- **Separation of concerns**: Config separate from deployment spec
- **Easy updates**: Change ConfigMap without touching deployment YAML
- **GitOps friendly**: ArgoCD can sync ConfigMap changes independently
- **Reusable**: Same ConfigMap can be used by multiple deployments
- **Better for experimentation**: Switch models without deployment changes

**Project Implementation:**
- `model-config` ConfigMap: Stores `MODEL_ALIAS` and `MODEL_NAME`
- Allows switching between different ML models without code changes
- Defined in `k8s/apps/model-config.yaml`

**ConfigMap Lifecycle:**
- When ConfigMap is updated, running pods **do not** automatically update
- New pods created after ConfigMap update will get the new values
- Pods must be restarted to pick up new ConfigMap values
- When a pod dies and is recreated, it gets the **current** ConfigMap values

---

## Service Types and Networking

### ClusterIP (Default)

**What it is:**
- Default service type
- Exposes pods within the cluster only
- Accessible from any node/pod in the cluster
- Not accessible from outside the cluster

**Use Cases:**
- Internal services
- Services that don't need external access
- Current project: API and UI services use ClusterIP

**Access:**
- From within cluster: `http://serving-api-service:8000`
- DNS: `serving-api-service.mlops-production.svc.cluster.local`

### NodePort

**What it is:**
- Exposes service on a high port (30000-32767) on every node
- Accessible via `NODE_IP:NODEPORT`
- Also accessible within cluster via ClusterIP

**Internet Exposure:**
- Only if nodes have public IPs and firewalls allow it
- Not automatically exposed to internet
- Requires proper network configuration

**Limitations:**
- High port numbers (not user-friendly)
- Security concerns in production
- On Kind, may not work directly due to container networking

### LoadBalancer

**What it is:**
- Creates an external load balancer (on cloud providers)
- Gets a public IP address
- Routes traffic to pods across nodes

**Internet Exposure:**
- Usually yes, but depends on:
  - Cloud provider configuration
  - Security groups/firewall rules
  - Whether it's public or internal load balancer

**On Kind (Local Development):**
- LoadBalancer stays in "Pending" state
- Doesn't create a real load balancer
- Often falls back to NodePort behavior

**Project Implementation:**
- ArgoCD service is patched to LoadBalancer in setup script
- On Kind, still requires `kubectl port-forward` for access

### Port Forwarding

**What it is:**
- `kubectl port-forward` creates a tunnel from local machine to cluster
- Bypasses service type entirely
- Works regardless of ClusterIP/NodePort/LoadBalancer

**Why Needed on Kind:**
- Kind runs in Docker containers
- LoadBalancer doesn't work (no cloud provider)
- NodePort may not be directly accessible
- Port-forwarding is the standard way to access services locally

**Usage:**
```bash
kubectl port-forward svc/serving-api-service -n mlops-production 8002:8000
# Access via http://localhost:8002
```

**For Production:**
- Use Ingress controller (recommended)
- Or LoadBalancer on cloud providers
- Port-forwarding is for local development only

### Ingress (Recommended for Production)

**What it is:**
- Single entry point for multiple services
- Provides SSL/TLS termination
- Domain-based routing (e.g., `api.yourdomain.com`)
- Path-based routing (e.g., `/api/*`, `/ui/*`)

**Benefits:**
- One LoadBalancer for Ingress controller (cost-effective)
- Better security and control
- Professional production setup

**Architecture:**
```
Internet → Ingress LoadBalancer → Ingress Controller → ClusterIP Services → Pods
```

---

## ArgoCD and GitOps

### What is ArgoCD?

**Definition:**
- ArgoCD is a GitOps continuous delivery tool for Kubernetes
- Automatically syncs Kubernetes resources from Git repositories
- Provides UI and CLI for managing deployments

**Key Concepts:**
- **Application**: ArgoCD custom resource that defines what to deploy
- **Sync**: Process of applying Git state to Kubernetes cluster
- **GitOps**: Infrastructure and application code stored in Git as source of truth

### ArgoCD Application vs Kubernetes Deployment

**Kubernetes Deployment:**
- Core Kubernetes resource (`kind: Deployment`)
- Manages pods and replicas
- Defines what containers to run

**ArgoCD Application:**
- ArgoCD custom resource (`kind: Application`, `apiVersion: argoproj.io/v1alpha1`)
- Not a core Kubernetes resource
- Tells ArgoCD what to deploy and how to sync it
- Manages the sync process from Git to Kubernetes

**Relationship:**
```
ArgoCD Application
    ↓ (manages/syncs)
Kubernetes Deployments (and other resources)
    ↓ (manages)
Pods
```

**Project Implementation:**
- `k8s/argocd/app.yaml`: ArgoCD Application definition
- Watches `k8s/apps/` directory in Git
- Syncs deployments, services, ConfigMaps to cluster

### ArgoCD Configuration

**Project Setup:**
```yaml
spec:
  source:
    repoURL: https://github.com/Maaz77/smart-logistics-supply-chain-mlops.git
    targetRevision: main
    path: k8s/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: mlops-production
  syncPolicy:
    automated:
      prune: true      # Remove resources deleted from Git
      selfHeal: true   # Fix manual changes automatically
```

**Key Features:**
- **Automated sync**: Automatically syncs when Git changes
- **Self-heal**: Reverts manual changes to match Git
- **Prune**: Removes resources deleted from Git
- **Retry**: Automatically retries failed syncs

### ArgoCD Access

**How to Access:**
- ArgoCD UI is accessible via `kubectl port-forward`
- Service is patched to LoadBalancer/NodePort (doesn't work on Kind)
- Standard access method:
  ```bash
  kubectl port-forward svc/argocd-server -n argocd 8080:443
  # Access: https://localhost:8080
  ```

**Why Port-Forward Needed:**
- Even with LoadBalancer/NodePort patch, Kind doesn't provide real load balancer
- Port-forwarding is the reliable method for local development
- Production deployments on cloud providers can use LoadBalancer directly

---

## CI/CD Workflows

### Continuous Integration (CI)

**What it is:**
- Automated testing and quality checks
- Runs on every code push or pull request
- Ensures code quality before merging

**Project Implementation:**
- GitHub Actions workflow (`.github/workflows/ci.yml`)
- Runs on `push` and `pull_request` to `main` branch
- Jobs:
  - **Quality Checks**: Linting, type checking, tests
  - **Infrastructure Tests**: Validates infrastructure setup

**Current CI Pipeline:**
1. Checkout code
2. Setup Python environment
3. Install dependencies
4. Run type checking
5. Run tests
6. Run integration tests
7. Validate infrastructure

### Continuous Deployment (CD) for Application Code

**Workflow for Adding New Feature:**

1. **Developer Makes Changes**
   ```bash
   git checkout -b feature/new-endpoint
   # ... make code changes ...
   git commit -m "Add new prediction endpoint"
   git push origin feature/new-endpoint
   ```

2. **CI Pipeline Runs**
   - Quality checks pass
   - Tests pass
   - Code is validated

3. **Build Docker Image**
   ```bash
   docker build -f serving/docker/Dockerfile.serving \
     -t maazamin98/mlops-serving-api:latest .
   docker push maazamin98/mlops-serving-api:latest
   ```

4. **Update Deployment YAML** (if using versioned tags)
   ```yaml
   # k8s/apps/api-deployment.yaml
   image: maazamin98/mlops-serving-api:v1.2.3
   ```

5. **Merge to Main**
   ```bash
   git checkout main
   git merge feature/new-endpoint
   git push origin main
   ```

6. **ArgoCD Automatically Syncs**
   - Detects changes in Git (polls every 3 minutes)
   - Syncs deployment to cluster
   - Kubernetes performs rolling update

7. **Rolling Update Process**
   - Creates new pods with new image
   - Waits for new pods to be ready
   - Terminates old pods
   - Zero-downtime deployment

### Continuous Deployment for ML Models

**Workflow for Switching Models:**

1. **Register New Model in MLflow**
   - Train new model version
   - Register with MLflow
   - Assign alias (e.g., `experiment`)

2. **Update ConfigMap in Git**
   ```yaml
   # k8s/apps/model-config.yaml
   data:
     MODEL_ALIAS: "experiment"  # Changed from "production"
   ```

3. **Commit and Push**
   ```bash
   git add k8s/apps/model-config.yaml
   git commit -m "Switch to experiment model"
   git push origin main
   ```

4. **ArgoCD Syncs ConfigMap**
   - Updates ConfigMap in cluster
   - Pods need restart to pick up new config

5. **Restart Pods**
   ```bash
   kubectl rollout restart deployment/serving-api -n mlops-production
   ```

6. **New Pods Load New Model**
   - Pods restart with new ConfigMap values
   - Load model from MLflow using new alias
   - New model is now serving requests

### Image Tagging Strategies

**Using `:latest` Tag:**
- **Pros**: Simple, no YAML changes needed
- **Cons**: Hard to track versions, can't rollback, not production-ready

**Using Versioned Tags:**
- **Pros**: Clear versioning, easy rollback, production-ready
- **Cons**: Need to update YAML with each deployment

**Recommended Approach:**
- Use commit SHA: `maazamin98/mlops-serving-api:abc1234`
- Or semantic versioning: `maazamin98/mlops-serving-api:v1.2.3`
- Update deployment YAML with new tag
- ArgoCD syncs automatically

---

## Model Deployment Strategies

### Strategy 1: MLflow Alias Switching (Implemented)

**How it Works:**
- Use ConfigMap to control which MLflow alias to use
- Switch alias to point to different model versions
- Restart pods to load new model

**Implementation:**
- ConfigMap stores `MODEL_ALIAS` environment variable
- API reads alias from environment
- Loads model: `models:/LogisticsDelayModel@{MODEL_ALIAS}`

**Workflow:**
1. Register models with different aliases in MLflow
2. Update ConfigMap to change alias
3. Restart pods
4. New model is loaded

**Pros:**
- Simple implementation
- Works with existing MLflow setup
- Easy to switch back
- No code changes needed

**Cons:**
- Requires pod restart
- All traffic goes to one model (no A/B testing)

### Strategy 2: Multiple Deployments with Traffic Splitting

**How it Works:**
- Create separate deployments for each model
- Use Ingress or Service Mesh to split traffic
- Route percentage of traffic to each model

**Use Cases:**
- A/B testing
- Canary deployments
- Gradual rollouts

**Implementation:**
- `serving-api-v6` deployment (Model Version 6)
- `serving-api-v7` deployment (Model Version 7)
- Ingress routes 90% to v6, 10% to v7

### Strategy 3: Canary Deployment

**How it Works:**
- Gradually shift traffic from old to new model
- Start with small percentage on new model
- Monitor performance
- Gradually increase percentage

**Example:**
- Day 1: 10% new model, 90% old model
- Day 2: 25% new model, 75% old model
- Day 3: 50% new model, 50% old model
- Day 4: 100% new model

### Strategy 4: Request Header-Based Routing

**How it Works:**
- Route requests to different models based on headers
- Useful for internal testing
- Allows specific clients to test new models

**Implementation:**
- Check header in API code
- Load appropriate model based on header
- Route to experiment or production model

---

## Project-Specific Implementation

### Kubernetes Cluster Setup

**Kind Cluster Configuration:**
- Single control-plane node
- All pods run on this node
- Configured in `k8s/kind-cluster.yaml`
- Created via `k8s/setup_k8s_mac.sh`

**Simplified Setup Script:**
- Removed over-cautious checks and retry logic
- Moved cluster config to separate YAML file
- Streamlined from 352 lines to 93 lines

### Application Deployment

**API Deployment:**
- Image: `maazamin98/mlops-serving-api:latest`
- Replicas: 2
- Reads model config from ConfigMap
- Connects to MLflow and LocalStack via `host.docker.internal`

**UI Deployment:**
- Image: `maazamin98/mlops-serving-ui:latest`
- Replicas: 1
- Connects to API via internal service DNS

**Services:**
- Both use `ClusterIP` (internal only)
- Accessible via port-forwarding locally
- For production, use Ingress or LoadBalancer

### Cross-Cluster Communication: Kubernetes to Host Services

**Architecture Overview:**
The API pods running in the Kubernetes cluster need to communicate with services running outside the cluster:
- **MLflow**: Running on Docker Compose (host machine, port 5001)
- **LocalStack (S3)**: Running on Docker Compose (host machine, port 4566)
- **PostgreSQL**: Running on Docker Compose (host machine, port 5432)

**The Challenge:**
- Kubernetes pods run inside Kind cluster (Docker container)
- MLflow and LocalStack run on the host machine via Docker Compose
- They are on different networks and cannot directly communicate

**Solution: `host.docker.internal`**

**What is `host.docker.internal`?**
- Special DNS name provided by Docker
- Resolves to the host machine's IP address from within containers
- Allows containers to access services running on the host
- Works on Docker Desktop for Mac/Windows and newer Linux setups

**How It Works:**

```
┌─────────────────────────────────────┐
│  Host Machine (Mac)                  │
│                                      │
│  ┌──────────────────────────────┐   │
│  │ Docker Compose Services       │   │
│  │  - MLflow: localhost:5001     │   │
│  │  - LocalStack: localhost:4566 │   │
│  │  - PostgreSQL: localhost:5432│   │
│  └──────────────────────────────┘   │
│                                      │
│  ┌──────────────────────────────┐   │
│  │ Kind Cluster Container       │   │
│  │  ┌────────────────────────┐  │   │
│  │  │ Kubernetes Pods         │  │   │
│  │  │  - API Pod             │  │   │
│  │  │    Uses:                │  │   │
│  │  │    host.docker.internal │  │   │
│  │  │    → Resolves to host  │  │   │
│  │  └────────────────────────┘  │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

**Project Configuration:**

**API Deployment Environment Variables:**
```yaml
env:
  # MLflow - reaches host machine's MLflow service
  - name: MLFLOW_TRACKING_URI
    value: "http://host.docker.internal:5001"

  # LocalStack S3 - reaches host machine's LocalStack
  - name: MLFLOW_S3_ENDPOINT_URL
    value: "http://host.docker.internal:4566"

  # PostgreSQL - reaches host machine's PostgreSQL
  - name: POSTGRES_HOST
    value: "host.docker.internal"
  - name: POSTGRES_PORT
    value: "5432"
```

**Communication Flow:**

1. **API Pod → MLflow:**
   ```
   API Pod (in Kind cluster)
     ↓ HTTP request to host.docker.internal:5001
   Docker network routing
     ↓ Resolves to host machine
   MLflow (Docker Compose, port 5001)
   ```

2. **API Pod → LocalStack (S3):**
   ```
   API Pod (in Kind cluster)
     ↓ HTTP request to host.docker.internal:4566
   Docker network routing
     ↓ Resolves to host machine
   LocalStack (Docker Compose, port 4566)
   ```

3. **API Pod → PostgreSQL:**
   ```
   API Pod (in Kind cluster)
     ↓ Connection to host.docker.internal:5432
   Docker network routing
     ↓ Resolves to host machine
   PostgreSQL (Docker Compose, port 5432)
   ```

**Why This Setup?**

**Development Benefits:**
- MLflow and LocalStack run independently via Docker Compose
- Can be started/stopped separately from Kubernetes
- Shared data persists across Kubernetes cluster recreations
- Easier to debug and manage services

**Production Considerations:**
- In production, these services would typically run inside Kubernetes
- MLflow would be a Kubernetes deployment
- S3 would be a real AWS S3 or compatible service
- PostgreSQL would be a managed database or Kubernetes StatefulSet
- No need for `host.docker.internal` in production

**Alternative Approaches:**

1. **Run Everything in Kubernetes:**
   - Deploy MLflow, LocalStack, PostgreSQL as Kubernetes resources
   - Use Kubernetes Services for internal communication
   - More complex but production-ready

2. **Use External Services:**
   - Connect to cloud-hosted MLflow, S3, and databases
   - Use proper network policies and security
   - Production standard approach

3. **Network Policies:**
   - Configure Kubernetes network policies
   - Control pod-to-pod and pod-to-external communication
   - Enhanced security

**Key Points:**
- `host.docker.internal` is a development convenience
- Works seamlessly on Docker Desktop
- Allows hybrid setup (K8s apps + Docker Compose services)
- Not needed in production where everything runs in Kubernetes
- Kind cluster is configured to support this networking pattern

### Model Configuration

**ConfigMap Structure:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: model-config
  namespace: mlops-production
data:
  MODEL_ALIAS: "production"
  MODEL_NAME: "LogisticsDelayModel"
```

**API Code:**
- Reads `MODEL_ALIAS` and `MODEL_NAME` from environment
- Falls back to defaults if not set
- Loads model from MLflow using alias

**Switching Models:**
1. Update ConfigMap in Git or via kubectl
2. ArgoCD syncs (if updated in Git)
3. Restart pods to pick up new config
4. New model is loaded

### ArgoCD Application

**Configuration:**
- Watches `k8s/apps/` directory
- Monitors `main` branch
- Auto-syncs with self-heal enabled
- Syncs to `mlops-production` namespace

**Managed Resources:**
- Deployments (API, UI)
- Services
- ConfigMaps (model-config)
- Namespace

### MLflow Integration

**Model Loading:**
- Uses MLflow model registry aliases
- Format: `models:/LogisticsDelayModel@{alias}`
- Resolves alias to specific model version
- Loads artifacts from S3 (LocalStack)

**Model Switching:**
- Change alias in ConfigMap
- API loads model with new alias
- No need to rebuild Docker images

---

## Best Practices and Recommendations

### Kubernetes

1. **Use Namespaces**: Organize resources by environment/application
2. **Resource Limits**: Always set CPU and memory limits
3. **Health Checks**: Use liveness and readiness probes
4. **Multiple Nodes**: Use multiple nodes for production (high availability)
5. **ConfigMaps**: Separate configuration from code

### Service Types

1. **Development**: Use ClusterIP + port-forwarding
2. **Production**: Use Ingress controller (recommended)
3. **Avoid NodePort**: Not ideal for production
4. **LoadBalancer**: Use on cloud providers, not on Kind

### ArgoCD

1. **Automated Sync**: Enable for faster deployments
2. **Self-Heal**: Prevents configuration drift
3. **Versioned Tags**: Don't rely on `:latest` in production
4. **Git as Source of Truth**: All changes go through Git
5. **Monitor Sync Status**: Use ArgoCD UI to monitor deployments

### CI/CD

1. **Versioned Images**: Use commit SHA or semantic versioning
2. **Automated Testing**: Run tests before deployment
3. **Separate CI and CD**: CI validates, CD deploys
4. **Rollback Strategy**: Keep previous image versions
5. **Environment Separation**: Different configs for dev/staging/prod

### Model Deployment

1. **Use Aliases**: MLflow aliases for easy switching
2. **Monitor Performance**: Track metrics for each model
3. **Gradual Rollouts**: Use canary deployments for new models
4. **A/B Testing**: Split traffic to compare models
5. **Version Tracking**: Keep track of which model version is deployed

### Security

1. **Secrets Management**: Use Kubernetes Secrets, not ConfigMaps
2. **Network Policies**: Restrict pod-to-pod communication
3. **RBAC**: Limit access to Kubernetes resources
4. **Image Scanning**: Scan Docker images for vulnerabilities
5. **TLS/SSL**: Use HTTPS in production

---

## Common Workflows

### Deploying New Application Feature

1. Make code changes
2. Run CI pipeline (tests pass)
3. Build and push Docker image
4. Update deployment YAML with new image tag
5. Merge to main branch
6. ArgoCD syncs automatically
7. Kubernetes rolling update
8. Feature is live

### Switching ML Models

1. Register new model in MLflow with alias
2. Update ConfigMap (in Git or via kubectl)
3. ArgoCD syncs ConfigMap (if in Git)
4. Restart pods
5. New model is loaded and serving

### Rolling Back Deployment

1. Identify previous working image tag
2. Update deployment YAML with previous tag
3. Commit and push (or update directly)
4. ArgoCD syncs
5. Kubernetes rolls back to previous version

### Troubleshooting

1. **Check Pod Logs**: `kubectl logs -n mlops-production <pod-name>`
2. **Check ArgoCD Sync Status**: ArgoCD UI or `kubectl get app`
3. **Verify ConfigMap**: `kubectl get configmap model-config -n mlops-production -o yaml`
4. **Check Service**: `kubectl get svc -n mlops-production`
5. **Describe Pod**: `kubectl describe pod -n mlops-production <pod-name>`

---

## Key Takeaways

1. **Kubernetes Services** expose pods at cluster level, not node level
2. **ConfigMaps** separate configuration from code, enabling easy updates
3. **ArgoCD** automates Git-to-Kubernetes sync for true GitOps
4. **CI/CD** separates validation (CI) from deployment (CD)
5. **Model Switching** can be done via ConfigMap without code changes
6. **Port-Forwarding** is standard for local development with Kind
7. **Production** should use Ingress, not direct LoadBalancer per service
8. **Versioned Tags** are essential for production deployments
9. **Automated Sync** in ArgoCD enables fast, reliable deployments
10. **Git as Source of Truth** ensures reproducible, auditable deployments

---

## Conclusion

This project implements a modern MLOps pipeline with:
- **Kubernetes** for container orchestration
- **ArgoCD** for GitOps continuous deployment
- **MLflow** for model management
- **ConfigMaps** for flexible model switching
- **GitHub Actions** for CI/CD automation

The architecture supports both application code changes and ML model updates through automated GitOps workflows, providing a robust foundation for production ML serving.
