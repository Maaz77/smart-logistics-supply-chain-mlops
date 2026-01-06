You are a Platform Engineer. Implement the **Kubernetes Hybrid Infrastructure** and **Tooling Setup** (Phase 3b).

**Context:**
- **Registry:** Docker Hub.
- **Architecture:** "Hybrid Local".
  - **Infrastructure:** (MLflow, Postgres, LocalStack) runs on Docker Compose (Host).
  - **Applications:** (Serving API, UI) run on Kind (Kubernetes).
- **Networking:** K8s pods must talk to Infrastructure via `host.docker.internal`.

**Requirements:**

1. **Setup Script (`/k8s/setup_k8s_mac.sh`):**
\   - **Cluster Creation:**
     - Create a Kind cluster named `modelserving-cluster`.
     - **Critical Config:** Ensure the cluster config allows `host.docker.internal` resolution (usually default on Docker Desktop for Mac, but verify).
   - **ArgoCD Installation:**
     - Install ArgoCD into the `argocd` namespace.
     - Wait for pods to be ready.
     - Patch the `argocd-server` service to type `LoadBalancer` (or NodePort) so the user can access the UI easily.

2. **Makefile Updates:**
   - Add variables: `DOCKER_USER=<your_dockerhub_username>` (User will provide this via env var).
   - `build-push`:
     - Build API & UI images.
     - Tag them: `$(DOCKER_USER)/mlops-serving-api:latest` and `$(DOCKER_USER)/mlops-serving-ui:latest`.
     - Push to Docker Hub.
   - `deploy-k8s`: Runs `kubectl apply -f k8s/apps`.

3. **Kubernetes Manifests (`k8s/apps/`):**
   - **`namespace.yaml`**: `mlops-production`.
   - **`api-deployment.yaml`**:
     - Image: `placeholder_user/mlops-serving-api:latest` (User will replace `placeholder_user` later).
     - **Env Vars (The Network Bridge):**
       - `MLFLOW_TRACKING_URI`: `http://host.docker.internal:5001` (Note: MLflow host port is 5001).
       - `MLFLOW_S3_ENDPOINT_URL`: `http://host.docker.internal:4566`.
       - `POSTGRES_HOST`: `host.docker.internal`.
       - `AWS_ACCESS_KEY_ID`: `test` (Plain text for local dev).
       - `AWS_SECRET_ACCESS_KEY`: `test`.
   - **`ui-deployment.yaml`**:
     - Image: `placeholder_user/mlops-serving-ui:latest`.
     - Env Var `API_URL`: `http://serving-api-service:8000` (Internal K8s DNS).

4. **ArgoCD App (`k8s/argocd/app.yaml`):**
   - Define the Application pointing to the local `k8s/apps` folder.
   - **Note:** Since ArgoCD runs in K8s, it cannot pull from a local folder easily without a Git repo.
   - **Correction:** Create the manifest, but instruct the user this requires the code to be pushed to GitHub. Use a placeholder repo URL `https://github.com/YOUR_USER/YOUR_REPO.git`.

**Definition of Done:**
- `sh /k8s/setup_k8s_mac.sh` installs tools and creates a running cluster.
- `make build-push DOCKER_USER=myuser` successfully pushes images.
- `kubectl get pods -n mlops-production` shows apps running (after applying manifests).
