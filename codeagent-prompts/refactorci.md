### CODING_AGENT_PROMPT: Centralizing Automation via Makefile (Single Source of Truth)

**Context:** We are refactoring our project's automation suite to eliminate logic duplication. The `Makefile` must become the **Single Source of Truth** for all code quality, testing, and infrastructure commands. Currently, the `ci.yml` and pre-commit hooks contain hardcoded commands that drift from the `Makefile`.

**Task:**
Refactor the `Makefile`, `.github/workflows/ci.yml`, and `.pre-commit-config.yaml` to ensure all automation flows through the `Makefile`.

**1. Makefile Refactor (Separating Check vs. Fix):**

*
**Explicit Separation:** Create distinct targets for "checking" (validation) and "fixing" (auto-formatting).


*
`check-style`: Run `ruff check .` and `ruff format --check .`.


*
`fix-style`: Run `ruff check --fix .` and `ruff format .`.




*
**Update `quality` Target:** This target should now act as the CI entry point, calling `check-style`, `type-check`, and `test` in sequence.


*
**Clean Environment:** Ensure `make install` handles `poetry install` and `make setup` handles the full environment initialization.



**2. GitHub Actions Refactor (`ci.yml`):**

*
**Eliminate Raw Commands:** Replace all `poetry run ruff ...` and `poetry run pytest ...` calls with their corresponding `make` targets.


* **Job 1 (Quality):** Use `make install`, `make check-style`, `make type-check`, and `make test`.
*
**Job 2 (Infra):** Use `make infra-init` and `make infra-status` to validate the terraform/LocalStack setup.



**3. Pre-commit Refactor (`.pre-commit-config.yaml`):**

* **Local Hooks:** Instead of calling `ruff` directly, configure local hooks to execute `make check-style`.
*
**Constraint:** Ensure the hooks are configured to run efficiently or on all files as per the project's "fail-fast" philosophy.



**4. Constraints & Standards:**

*
**Environment Parity:** The commands executed by a developer locally via `make` must be identical to the commands executed in the GitHub Action.


*
**Colorized Output:** Maintain the `CYAN`, `GREEN`, and `RED` status messages in the `Makefile` for better developer experience.


* **No Orphaned Logic:** No file other than the `Makefile` should contain the specific CLI flags for `ruff`, `mypy`, or `pytest`.

**Definition of Done:**

1. Running `make quality` locally executes the exact same sequence as the `quality` job in `ci.yml`.
2. All auto-formatting logic is contained solely within `make fix-style`.
3. The `.pre-commit-config.yaml` no longer contains tool-specific CLI arguments, delegating that responsibility to the `Makefile`.
4. A PR push triggers the CI, which successfully passes using the new `make` targets.
