### CODING_AGENT_PROMPT: Universal Script Runner via Docker

**Context:** You are enhancing the `Makefile` to allow developers to run Python scripts inside the specialized `dev` container. This ensures that feature engineering, data ingestion, and training scripts run in a controlled, production-parallel environment.

**Task:**
1. **Update the `Makefile`:**
   - Add a new target called `run`.
   - It should accept a variable `script`.
   - The command should be: `docker compose run --rm dev-service python $(script)`
   - Add a safety check: if `$(script)` is empty, print a helpful message: "Usage: make run script=path/to/script.py".
   - Use `.PHONY: run`.

2. **Refine `docker-compose.dev.yaml`:**
   - Ensure the `dev-service` uses the `target: dev` from the multi-stage `Dockerfile`.
   - Ensure the `volumes` section mounts `./src:/app/src` and `./data:/app/data` to allow for live code changes and data persistence.
   - Map the `.env` file using `env_file: .env`.

3. **Verify `src/utils/common.py`:**
   - Ensure there is a helper function that correctly detects if it is running inside Docker (e.g., checking for the existence of `/.dockerenv`) to switch between `localhost` and `localstack` hostnames.

**Constraints:**
- The `make run` command must correctly use the `mlops-network` to communicate with the `postgres` and `localstack` containers.
- Do not hardcode the script path; it must be dynamic.

**Definition of Done:**
1. Running `make run script=src/utils/common.py` (or any simple script) prints the output from the container.
2. The user sees a clear error message if they forget the `script=` argument.
3. The container exits and removes itself immediately after the script finishes.
