.DEFAULT_GOAL := help

# =============================================================================
# 00 Environment / constants START
# =============================================================================

MODULE_ID := logistics_service
MODULE_NAME := ForPrint Logistics Service

PYTHON ?= .venv_logistics_service/bin/python
export PYTHONDONTWRITEBYTECODE := 1

BLUEPRINT_ROOT ?= /srv/software_development/forprint-project/forprint_system_blueprint
BLUEPRINT_PYTHON ?= $(BLUEPRINT_ROOT)/.venv_blueprint/bin/python

MODULE_GUIDE := $(BLUEPRINT_ROOT)/module_guides/$(MODULE_ID).md
MANIFEST_SCHEMA := $(BLUEPRINT_ROOT)/machine/module_manifest_schema.yaml
PROMPT_INDEX := $(BLUEPRINT_ROOT)/coordination/outgoing_prompts/$(MODULE_ID)/index.yaml
ACTIVE_PROMPT_DIR := $(BLUEPRINT_ROOT)/coordination/outgoing_prompts/$(MODULE_ID)/approved
LOCAL_PROMPT_DIR := coordination/prompts/received

LOCAL_ACTIVE_PROMPT_DIR := coordination/prompts/active
LOCAL_ARCHIVED_PROMPT_DIR := coordination/prompts/archived
LOCAL_PROMPT_INDEX := coordination/prompts/index.yaml
BLUEPRINT_PROMPT_INDEX := $(BLUEPRINT_ROOT)/coordination/outgoing_prompts/$(MODULE_ID)/index.yaml
PROMPT_STATE_SYNC := scripts/coordination/sync_prompt_state.py

MODULE_POLICY := $(BLUEPRINT_ROOT)/coordination/module_policy/$(MODULE_ID)/module_policy.md
MODULE_DIRECTIVE_INDEX := $(BLUEPRINT_ROOT)/coordination/directives/modules/$(MODULE_ID)/index.yaml

COORDINATION_CHECKER := $(BLUEPRINT_ROOT)/scripts/check_coordination_metadata.py
COORDINATION_FIXER := $(BLUEPRINT_ROOT)/scripts/fix_coordination_metadata.py

PACKET ?=

COMPLETION_PACKET_VALIDATOR := scripts/coordination/validate_completion_packet.py
COMPLETION_PACKET_APPLIER := scripts/coordination/apply_completion_packet.py
CHECK_REPORT_RUNNER := scripts/diagnostics/run_logistics_checks.py
PROJECT_POLICY_CHECKER := scripts/validation/check_project_policies.py

COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_RED := \033[31m

ifeq ($(NO_COLOR),1)
COLOR_RESET :=
COLOR_BOLD :=
COLOR_GREEN :=
COLOR_YELLOW :=
COLOR_RED :=
endif

# =============================================================================
# 00 Environment / constants FINISH
# =============================================================================


# =============================================================================
# 01 Help / navigation START
# =============================================================================

.PHONY: help
help:
	@echo "$(COLOR_BOLD)$(MODULE_NAME) Make targets$(COLOR_RESET)"
	@echo ""
	@echo "Operator workflow:"
	@echo "  make module-start"
	@echo "  make module-sync"
	@echo "  make module-validate"
	@echo ""
	@echo "Bootstrap and development:"
	@echo "  make install"
	@echo "  make env-check"
	@echo "  make tooling-check"
	@echo "  make config-check"
	@echo "  make secrets-check"
	@echo ""
	@echo "Blueprint and coordination:"
	@echo "  make blueprint-pull"
	@echo "  make blueprint-check"
	@echo "  make blueprint-prompts-list"
	@echo "  make blueprint-prompts-sync"
	@echo "  make blueprint-prompt"
	@echo "  make blueprint-prompt-status"
	@echo "  make blueprint-standards-list"
	@echo "  make blueprint-standards-check"
	@echo "  make module-policy-check"
	@echo "  make coordination-check"
	@echo "  make coordination-fix"
	@echo "  make governance-check"
	@echo ""
	@echo "Validation:"
	@echo "  make cache-clean"
	@echo "  make compile"
	@echo "  make lint"
	@echo "  make format"
	@echo "  make format-check"
	@echo "  make test"
	@echo "  make check"
	@echo "  make logistics-check"
	@echo "  make check-report"
	@echo "  make local-model-examples-check"
	@echo "  make local-model-boundary-check"
	@echo "  make test-address-book-check"
	@echo "  make test-address-book-preview"
	@echo "  make logistics-model-preview"
	@echo "  make status-report"
	@echo "  make report-status"
	@echo ""
	@echo "  make project-policy-check"
	@echo "  make completion-packet-validate PACKET=<path>"
	@echo "  make completion-packet-apply PACKET=<path>"
	@echo "  make completion-packet-check PACKET=<path>"
	@echo "  make report-clean"

# =============================================================================
# 01 Help / navigation FINISH
# =============================================================================



# =============================================================================
# 02 Operator entrypoints / Blueprint-first workflow START
# =============================================================================

# Purpose: prepare Logistics Service for approved Blueprint prompt execution.
# Result: current Blueprint sources are checked, approved prompts are
# synchronized locally, coordination is validated and the active prompt
# is displayed. The Blueprint repository remains read-only.
.PHONY: module-start
module-start:
	$(MAKE) blueprint-check
	$(MAKE) blueprint-standards-check
	$(MAKE) blueprint-sync-directives
	$(MAKE) blueprint-prompts-sync
	$(MAKE) coordination-check
	$(MAKE) status-report
	$(MAKE) blueprint-prompt

# Purpose: synchronize module-visible Blueprint state without reading the
# active prompt as an execution instruction.
# Result: Blueprint paths, standards and prompt queue are checked and
# synchronized into module-owned coordination records.
.PHONY: module-sync
module-sync:
	$(MAKE) blueprint-check
	$(MAKE) blueprint-standards-check
	$(MAKE) blueprint-sync-directives
	$(MAKE) blueprint-prompts-sync
	$(MAKE) coordination-check
	$(MAKE) status-report

# Purpose: run the canonical module-level validation and cleanup flow.
# Result: full checks and governance pass, generated reports are removed,
# and current module status is displayed without external writes.
.PHONY: module-validate
module-validate:
	$(MAKE) check-report-full
	$(MAKE) governance-check
	$(MAKE) report-clean
	$(MAKE) status-report

# =============================================================================
# 02 Operator entrypoints / Blueprint-first workflow FINISH
# =============================================================================


# =============================================================================
# 02 Blueprint synchronization START
# =============================================================================

.PHONY: blueprint-pull
blueprint-pull:
	git -C "$(BLUEPRINT_ROOT)" pull --ff-only

.PHONY: blueprint-check
blueprint-check:
	@test -d "$(BLUEPRINT_ROOT)"
	@test -f "$(MODULE_GUIDE)"
	@test -f "$(MANIFEST_SCHEMA)"
	@test -f "$(PROMPT_INDEX)"
	@test -d "$(BLUEPRINT_ROOT)/coordination/standards"
	@echo "$(COLOR_GREEN)Blueprint paths are readable for $(MODULE_ID).$(COLOR_RESET)"

.PHONY: blueprint-sync-directives
blueprint-sync-directives:
	@if [ -f "$(MODULE_DIRECTIVE_INDEX)" ]; then \
		echo "$(COLOR_GREEN)Blueprint module directive index is readable.$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_YELLOW)DEFERRED: no module directive index is available yet.$(COLOR_RESET)"; \
	fi

.PHONY: blueprint-prompts-list
blueprint-prompts-list:
	@test -d "$(ACTIVE_PROMPT_DIR)"
	@find "$(ACTIVE_PROMPT_DIR)" -maxdepth 1 -type f -name '*.md' | sort

.PHONY: blueprint-prompts-check
blueprint-prompts-check:
	@test -f "$(PROMPT_INDEX)"
	@test -n "$$(find "$(ACTIVE_PROMPT_DIR)" -maxdepth 1 -type f -name '*.md' -print -quit)"
	@echo "$(COLOR_GREEN)Blueprint prompt queue is readable for $(MODULE_ID).$(COLOR_RESET)"


.PHONY: blueprint-prompts-sync
blueprint-prompts-sync:
	@test -f "$(BLUEPRINT_PROMPT_INDEX)" || \
		(echo "$(COLOR_RED)Missing Blueprint prompt index: $(BLUEPRINT_PROMPT_INDEX)$(COLOR_RESET)"; exit 1)
	$(PYTHON) $(PROMPT_STATE_SYNC) \
		--module-id "$(MODULE_ID)" \
		--blueprint-index "$(BLUEPRINT_PROMPT_INDEX)" \
		--blueprint-module-dir "$(BLUEPRINT_ROOT)/coordination/outgoing_prompts/$(MODULE_ID)" \
		--received-dir "$(LOCAL_PROMPT_DIR)" \
		--active-dir "$(LOCAL_ACTIVE_PROMPT_DIR)" \
		--archived-dir "$(LOCAL_ARCHIVED_PROMPT_DIR)" \
		--local-index "$(LOCAL_PROMPT_INDEX)" \
		--status-yaml coordination/status/current_status.yaml \
		--status-md coordination/status/current_status.md \
		--questions-md coordination/status/next_questions_for_blueprint.md


.PHONY: blueprint-prompt
blueprint-prompt:
	@count="$$(find "$(LOCAL_ACTIVE_PROMPT_DIR)" -maxdepth 1 -type f -name '*.md' | wc -l)"; \
		test "$$count" -eq 1 || \
		(echo "$(COLOR_RED)Expected exactly one active local prompt, found $$count.$(COLOR_RESET)"; exit 1)
	@cat "$$(find "$(LOCAL_ACTIVE_PROMPT_DIR)" -maxdepth 1 -type f -name '*.md' | sort | head -n 1)"


.PHONY: blueprint-prompt-check
blueprint-prompt-check:
	$(PYTHON) $(PROMPT_STATE_SYNC) \
		--local-index "$(LOCAL_PROMPT_INDEX)" \
		--status-yaml coordination/status/current_status.yaml \
		--received-dir "$(LOCAL_PROMPT_DIR)" \
		--active-dir "$(LOCAL_ACTIVE_PROMPT_DIR)" \
		--check-only


.PHONY: blueprint-prompt-status
blueprint-prompt-status:
	$(PYTHON) $(PROMPT_STATE_SYNC) \
		--local-index "$(LOCAL_PROMPT_INDEX)" \
		--status-only

.PHONY: blueprint-standards-list
blueprint-standards-list:
	@find "$(BLUEPRINT_ROOT)/coordination/standards" -maxdepth 2 -type f | sort

.PHONY: blueprint-standards-check
blueprint-standards-check:
	@test -f "$(BLUEPRINT_ROOT)/coordination/standards/index.yaml"
	@test -d "$(BLUEPRINT_ROOT)/coordination/standards/modular_topology_and_resilience"
	@test -d "$(BLUEPRINT_ROOT)/coordination/standards/third_party_reuse"
	@echo "$(COLOR_GREEN)Blueprint standards are readable.$(COLOR_RESET)"

.PHONY: blueprint-standards-sync
blueprint-standards-sync:
	@echo "$(COLOR_YELLOW)DEFERRED: local standards snapshot sync is not implemented yet.$(COLOR_RESET)"

# =============================================================================
# 02 Blueprint synchronization FINISH
# =============================================================================


# =============================================================================
# 03 Coordination and governance START
# =============================================================================

.PHONY: module-policy-check
module-policy-check:
	@if [ -f "$(MODULE_POLICY)" ]; then \
		echo "$(COLOR_GREEN)Module policy is readable for $(MODULE_ID).$(COLOR_RESET)"; \
	else \
		echo "$(COLOR_YELLOW)MISSING_NEEDS_ALIGNMENT: module policy file is not available yet.$(COLOR_RESET)"; \
	fi

.PHONY: coordination-check
coordination-check:
	@test -f forprint_module_manifest.yaml
	@test -f coordination/status/current_status.yaml
	@test -f coordination/status/current_status.md
	@test -f coordination/status/next_questions_for_blueprint.md
	@test -f coordination/prompts/index.yaml
	@test -f coordination/reports/index.yaml
	@if [ -x "$(BLUEPRINT_PYTHON)" ] && [ -f "$(COORDINATION_CHECKER)" ]; then \
		"$(BLUEPRINT_PYTHON)" "$(COORDINATION_CHECKER)" --module-root "$(CURDIR)"; \
	else \
		"$(PYTHON)" -c "from pathlib import Path; import yaml; files = [Path('forprint_module_manifest.yaml'), Path('coordination/status/current_status.yaml'), Path('coordination/prompts/index.yaml'), Path('coordination/reports/index.yaml')]; [yaml.safe_load(path.read_text(encoding='utf-8')) for path in files]; print('Local YAML coordination fallback: OK')"; \
	fi

.PHONY: coordination-fix
coordination-fix:
	@if [ -x "$(BLUEPRINT_PYTHON)" ] && [ -f "$(COORDINATION_FIXER)" ]; then \
		"$(BLUEPRINT_PYTHON)" "$(COORDINATION_FIXER)" --module-root "$(CURDIR)"; \
	else \
		echo "$(COLOR_YELLOW)DEFERRED: central coordination fixer is unavailable.$(COLOR_RESET)"; \
	fi

.PHONY: coordination-records-check
coordination-records-check:
	$(MAKE) coordination-check

.PHONY: coordination-records-refresh
coordination-records-refresh:
	@echo "$(COLOR_YELLOW)DEFERRED: automated coordination refresh is not implemented for bootstrap v0.1.$(COLOR_RESET)"

.PHONY: status-report
status-report:
	@echo "$(COLOR_BOLD)== $(MODULE_NAME) status ==$(COLOR_RESET)"
	@sed -n '1,240p' coordination/status/current_status.yaml

.PHONY: report-status
report-status:
	$(MAKE) status-report

.PHONY: governance-check
governance-check:
	$(MAKE) blueprint-check
	$(MAKE) blueprint-sync-directives
	$(MAKE) blueprint-prompts-check
	$(MAKE) blueprint-prompt-check
	$(MAKE) blueprint-standards-check
	$(MAKE) module-policy-check
	$(MAKE) coordination-check
	$(MAKE) status-report

# =============================================================================
# 03 Coordination and governance FINISH
# =============================================================================


# =============================================================================
# 04 Environment / configuration START
# =============================================================================

.PHONY: install
install:
	$(PYTHON) -m pip install -e ".[dev]"

.PHONY: env-check
env-check:
	@test -x "$(PYTHON)"
	@echo "MODULE_ID=$(MODULE_ID)"
	@echo "PYTHON=$(PYTHON)"
	@$(PYTHON) --version
	@test -d config
	@test -d reports
	@test -d runtime
	@echo "$(COLOR_GREEN)Environment check passed.$(COLOR_RESET)"

.PHONY: tooling-check
tooling-check:
	@$(PYTHON) -m ruff --version
	@$(PYTHON) -m pytest --version
	@$(PYTHON) -c "import yaml; print('PyYAML:', yaml.__version__)"

.PHONY: config-check
config-check:
	@test -f config/module.yaml
	@test -f config/providers.example.yaml
	@test -f config/README.md
	@test -f .env.example
	@$(PYTHON) -c "from pathlib import Path; import yaml; [yaml.safe_load(Path(path).read_text(encoding='utf-8')) for path in ['config/module.yaml', 'config/providers.example.yaml']]; print('Configuration YAML: OK')"

.PHONY: secrets-check
secrets-check:
	@if git ls-files --error-unmatch .env >/dev/null 2>&1; then \
		echo "$(COLOR_RED)FAILED: .env is tracked by Git.$(COLOR_RESET)"; \
		exit 1; \
	fi
	@if git ls-files | grep -E '(^|/)(\.env|\.env\.local|\.env\.production|secrets/.*\.(env|key|pem))$$' >/dev/null; then \
		echo "$(COLOR_RED)FAILED: tracked secret-like file detected.$(COLOR_RESET)"; \
		exit 1; \
	fi
	@test -f .env.example
	@grep -q '^FORPRINT_LOGISTICS_LIVE_PROVIDER_WRITES_ENABLED=false$$' .env.example
	@echo "$(COLOR_GREEN)Secrets policy check passed.$(COLOR_RESET)"

# =============================================================================
# 04 Environment / configuration FINISH
# =============================================================================


# =============================================================================
# 05 Syntax / formatting / tests START
# =============================================================================

.PHONY: cache-clean
cache-clean:
	@find app scripts tests \
		-type d \
		-name '__pycache__' \
		-prune \
		-exec rm -rf {} +
	@find app scripts tests \
		-type f \
		\( -name '*.pyc' -o -name '*.pyo' \) \
		-delete
	@echo "$(COLOR_GREEN)Python bytecode caches removed.$(COLOR_RESET)"

.PHONY: compile
compile:
	@rm -rf tmp/py_compile
	@mkdir -p tmp/py_compile
	@status=0; \
	PYTHONPYCACHEPREFIX="$(CURDIR)/tmp/py_compile" \
		$(PYTHON) -m py_compile \
		$$(find app scripts tests -name '*.py' -type f | sort) \
		|| status=$$?; \
	rm -rf tmp/py_compile; \
	exit $$status

.PHONY: lint
lint:
	$(PYTHON) -m ruff check app scripts tests

.PHONY: lint-fix
lint-fix:
	$(PYTHON) -m ruff check app scripts tests --fix

.PHONY: format
format:
	$(PYTHON) -m ruff format app scripts tests

.PHONY: format-check
format-check:
	$(PYTHON) -m ruff format app scripts tests --check

.PHONY: test
test:
	@status=0; \
	$(PYTHON) -m pytest -q || status=$$?; \
	$(MAKE) --no-print-directory cache-clean; \
	exit $$status

.PHONY: check
check:
	$(MAKE) env-check
	$(MAKE) tooling-check
	$(MAKE) config-check
	$(MAKE) secrets-check
	$(MAKE) compile
	$(MAKE) lint
	$(MAKE) format-check
	$(MAKE) project-policy-check
	$(MAKE) local-model-examples-check
	$(MAKE) local-model-boundary-check
	$(MAKE) test-address-book-check
	$(MAKE) provider-contract-check
	$(MAKE) test
	$(MAKE) coordination-check


.PHONY: local-model-examples-check
local-model-examples-check:
	$(PYTHON) -m scripts.validation.check_local_model_examples


.PHONY: local-model-boundary-check
local-model-boundary-check:
	$(PYTHON) -m scripts.validation.check_local_model_boundaries

.PHONY: test-address-book-check
test-address-book-check:
	$(PYTHON) -m scripts.validation.check_test_address_book

.PHONY: test-address-book-preview
test-address-book-preview:
	$(PYTHON) -m scripts.previews.preview_test_address_book

.PHONY: logistics-model-preview
logistics-model-preview:
	$(PYTHON) -m scripts.previews.preview_local_logistics_model

.PHONY: provider-contract-check
provider-contract-check:
	$(PYTHON) -m scripts.validation.check_provider_adapter_contract

.PHONY: provider-contract-preview
provider-contract-preview:
	$(PYTHON) -m scripts.previews.preview_provider_adapter_contract

.PHONY: logistics-check
logistics-check:
	$(MAKE) check

.PHONY: check-report
check-report:
	$(PYTHON) $(CHECK_REPORT_RUNNER)

.PHONY: check-report-full
check-report-full:
	$(PYTHON) $(CHECK_REPORT_RUNNER) --full

# =============================================================================
# 05 Syntax / formatting / tests FINISH
# =============================================================================


# =============================================================================
# 06 Completion packet / diagnostics START
# =============================================================================

.PHONY: project-policy-check
project-policy-check:
	$(PYTHON) $(PROJECT_POLICY_CHECKER)

.PHONY: completion-packet-validate
completion-packet-validate:
	@test -n "$(PACKET)" || \
		(echo "$(COLOR_RED)PACKET is required.$(COLOR_RESET)"; exit 2)
	$(PYTHON) $(COMPLETION_PACKET_VALIDATOR) "$(PACKET)"

.PHONY: completion-packet-apply
completion-packet-apply:
	@test -n "$(PACKET)" || \
		(echo "$(COLOR_RED)PACKET is required.$(COLOR_RESET)"; exit 2)
	$(PYTHON) $(COMPLETION_PACKET_APPLIER) "$(PACKET)"

.PHONY: completion-packet-check
completion-packet-check:
	@test -n "$(PACKET)" || \
		(echo "$(COLOR_RED)PACKET is required.$(COLOR_RESET)"; exit 2)
	$(MAKE) completion-packet-validate PACKET="$(PACKET)"
	$(MAKE) completion-packet-apply PACKET="$(PACKET)"
	$(MAKE) completion-packet-apply PACKET="$(PACKET)"

.PHONY: report-clean
report-clean:
	@rm -f \
		reports/logistics_service_check_report.json \
		reports/logistics_service_check_report.md
	@rm -rf reports/diagnostics
	@echo "$(COLOR_GREEN)Generated check reports removed.$(COLOR_RESET)"

# =============================================================================
# 06 Completion packet / diagnostics FINISH
# =============================================================================

# =============================================================================
# 07 Git helpers START
# =============================================================================

.PHONY: git-status
git-status:
	git status --short --branch
	git log -5 --oneline 2>/dev/null || true

.PHONY: pre-commit
pre-commit:
	$(MAKE) governance-check
	$(MAKE) check
	$(MAKE) check-report
	git diff --check
	git status --short

# =============================================================================
# 07 Git helpers FINISH
# =============================================================================
