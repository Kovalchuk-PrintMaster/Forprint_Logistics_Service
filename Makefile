.DEFAULT_GOAL := help

# =============================================================================
# 00 Environment / constants START
# =============================================================================

MODULE_ID := logistics_service
MODULE_NAME := ForPrint Logistics Service

PYTHON ?= .venv_logistics_service/bin/python
export PYTHONDONTWRITEBYTECODE := 1

BLUEPRINT_ROOT ?= /srv/software_development/forprint-project/forprint_system_blueprint

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
MODULE_COORDINATION_SYNC_CHECK_SCRIPT := scripts/coordination_sync_check.py
H9_RUNTIME := scripts/coordination/h9_runtime.py
MODULE_MEMORY_BUILDER := scripts/knowledge/build_module_memory_index.py
MODULE_MEMORY_VALIDATOR := scripts/validation/validate_module_memory.py
DOCUMENT_AUTHORITY_VALIDATOR := scripts/validation/validate_document_authority.py
FRESH_CONTEXT_VALIDATOR := scripts/validation/validate_fresh_context.py

MODULE_POLICY := $(BLUEPRINT_ROOT)/coordination/module_policy/$(MODULE_ID)/module_policy.md
MODULE_DIRECTIVE_INDEX := $(BLUEPRINT_ROOT)/coordination/directives/modules/$(MODULE_ID)/index.yaml


PACKET ?=

COMPLETION_PACKET_VALIDATOR := scripts/coordination/validate_completion_packet.py
COMPLETION_PACKET_APPLIER := scripts/coordination/apply_completion_packet.py
COMPLETION_REPORT_VALIDATOR := scripts/coordination/validate_completion_report.py
COMPLETION_SAFETY_CHECKER := scripts/validation/check_completion_safety_boundaries.py
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
	@echo "  make module-status"
	@echo "  make module-validate"
	@echo "  make self-knowledge-status"
	@echo "  make module-memory-build"
	@echo "  make module-memory-check"
	@echo "  make document-authority-check"
	@echo "  make fresh-context-check"
	@echo ""
	@echo "Bootstrap and development:"
	@echo "  make install"
	@echo "  make env-check"
	@echo "  make tooling-check"
	@echo "  make config-check"
	@echo "  make secrets-check"
	@echo ""
	@echo "Blueprint and coordination:"
	@echo "  make coordination-sync-check"
	@echo "  make blueprint-check"
	@echo "  make blueprint-prompts-list"
	@echo "  make prompt-notify"
	@echo "  make prompt-next"
	@echo "  make prompt-read-next"
	@echo "  make blueprint-prompts-sync"
	@echo "  make blueprint-prompt"
	@echo "  make blueprint-prompt-status"
	@echo "  make blueprint-standards-list"
	@echo "  make blueprint-standards-check"
	@echo "  make module-policy-check"
	@echo "  make coordination-check"
	@echo "  make coordination-fix"
	@echo "  make governance-check"
	@echo "  make git-status"
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
	@echo "  make tracking-events-check"
	@echo "  make tracking-events-preview"
	@echo "  make tracking-events-preview-generate"
	@echo "  make tracking-events-v0-4-evidence-check"
	@echo "  make tracking-events-v0-4-subject-status"
	@echo "  make tracking-events-v0-4-subject-preflight"
	@echo "  make tracking-events-v0-4-subject-prepare"
	@echo "  make tracking-events-v0-4-subject-check"
	@echo "  make tracking-events-v0-4-finalization-idempotency-check"
	@echo "  make tracking-events-v0-4-finalize-status"
	@echo "  make tracking-events-v0-4-finalize-preflight"
	@echo "  make tracking-events-v0-4-finalize-prepare"
	@echo "  make tracking-events-v0-4-finalization-check"
	@echo "  make tracking-events-v0-4-postpublication-idempotency-check"
	@echo "  make status-report"
	@echo "  make report-status"
	@echo ""
	@echo "  make project-policy-check"
	@echo "  make completion-packet-validate PACKET=<path>"
	@echo "  make completion-packet-apply PACKET=<path>"
	@echo "  make completion-packet-check PACKET=<path>"
	@echo "  make tracking-events-v0-3-reference-completion-check PACKET=<path>"
	@echo "  make completion-safety-check"
	@echo "  make completion-report-validate PACKET=<path>"
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
	$(MAKE) coordination-sync-check
	$(MAKE) module-sync
	$(MAKE) module-status
	$(MAKE) prompt-notify
	$(MAKE) prompt-read-next

# Purpose: synchronize module-visible Blueprint state without reading the
# active prompt as an execution instruction.
# Result: Blueprint paths, standards and prompt queue are checked and
# synchronized into module-owned coordination records.
.PHONY: module-sync
module-sync:
	$(MAKE) module-sync-apply
	$(MAKE) document-awareness
	$(MAKE) coordination-check
	$(MAKE) module-status

.PHONY: module-sync-apply
module-sync-apply:
	$(PYTHON) $(H9_RUNTIME) sync --module-root . --blueprint-root "$(BLUEPRINT_ROOT)" --module "$(MODULE_ID)"

.PHONY: document-awareness
document-awareness:
	$(PYTHON) $(H9_RUNTIME) awareness --module-root . --module "$(MODULE_ID)"

.PHONY: module-status
module-status:
	$(PYTHON) $(H9_RUNTIME) status --module-root . --module "$(MODULE_ID)"

# Purpose: run the canonical read-only module-level validation flow.
# Result: full checks, governance and coordination validation pass without
# generated-report cleanup, status mutation, external writes, commit or push.
.PHONY: module-validate
module-validate:
	$(MAKE) check-report-full
	$(MAKE) module-memory-check
	$(MAKE) document-authority-check
	$(MAKE) fresh-context-check
	$(MAKE) governance-check
	$(MAKE) coordination-check

# =============================================================================
# 02 Operator entrypoints / Blueprint-first workflow FINISH
# =============================================================================


# =============================================================================
# 02 Blueprint synchronization START
# =============================================================================

.PHONY: blueprint-pull
blueprint-pull:
	@echo "$(COLOR_RED)FAILED: blueprint-pull is deprecated and forbidden; use coordination-sync-check and update Blueprint only from the Blueprint repository.$(COLOR_RESET)"; exit 2

.PHONY: coordination-sync-check
coordination-sync-check:
	$(PYTHON) $(MODULE_COORDINATION_SYNC_CHECK_SCRIPT) --blueprint-root "$(BLUEPRINT_ROOT)" --module "$(MODULE_ID)"

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

.PHONY: prompt-notify
prompt-notify:
	$(PYTHON) $(MODULE_COORDINATION_SYNC_CHECK_SCRIPT) --blueprint-root "$(BLUEPRINT_ROOT)" --module "$(MODULE_ID)" --local-only

.PHONY: prompt-next
prompt-next:
	$(PYTHON) $(H9_RUNTIME) prompt-next --module-root . --module "$(MODULE_ID)"

.PHONY: prompt-read-next
prompt-read-next:
	$(PYTHON) $(H9_RUNTIME) prompt-read-next --module-root . --module "$(MODULE_ID)"

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
	$(PYTHON) $(H9_RUNTIME) coordination-validate --module-root . --module "$(MODULE_ID)"

.PHONY: coordination-fix
coordination-fix:
	@echo "$(COLOR_YELLOW)DEFERRED: H9 current runtime has no automatic coordination fixer; repair module-owned records explicitly.$(COLOR_RESET)"

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
# 03A Module self-knowledge START
# =============================================================================

.PHONY: module-memory-build
module-memory-build:
	$(PYTHON) $(MODULE_MEMORY_BUILDER) build --module-root .

.PHONY: module-memory-check
module-memory-check:
	$(PYTHON) $(MODULE_MEMORY_VALIDATOR)

.PHONY: document-authority-check
document-authority-check:
	$(PYTHON) $(DOCUMENT_AUTHORITY_VALIDATOR)

.PHONY: fresh-context-check
fresh-context-check:
	$(PYTHON) $(FRESH_CONTEXT_VALIDATOR)

.PHONY: self-knowledge-status
self-knowledge-status:
	$(PYTHON) $(MODULE_MEMORY_BUILDER) status --module-root .

# =============================================================================
# 03A Module self-knowledge FINISH
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
	$(MAKE) module-memory-check
	$(MAKE) document-authority-check
	$(MAKE) fresh-context-check
	$(MAKE) local-model-examples-check
	$(MAKE) local-model-boundary-check
	$(MAKE) test-address-book-check
	$(MAKE) provider-contract-check
	$(MAKE) tracking-events-check
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

# Purpose: validate the provider-neutral tracking event contract.
# Result: taxonomy, transitions, idempotency and safety checks pass.
.PHONY: tracking-events-check
tracking-events-check:
	$(PYTHON) -m scripts.validation.check_tracking_events_contract

# Purpose: show the synthetic tracking and notification handoff preview.
# Result: deterministic preview is printed without filesystem mutation.
.PHONY: tracking-events-preview
tracking-events-preview:
	$(PYTHON) -m scripts.previews.preview_tracking_events_contract --no-write

# Purpose: explicitly generate the tracking-events preview artifact.
# Result: writes reports/previews/tracking_events_contract_preview.json.
.PHONY: tracking-events-preview-generate
tracking-events-preview-generate:
	$(PYTHON) -m scripts.previews.preview_tracking_events_contract

.PHONY: logistics-check
logistics-check:
	$(MAKE) check

.PHONY: check-report
check-report:
	$(PYTHON) scripts/diagnostics/run_logistics_checks_read_only.py

.PHONY: check-report-full
check-report-full:
	$(PYTHON) scripts/diagnostics/run_logistics_checks_read_only.py --full

.PHONY: check-report-generate
check-report-generate:
	$(PYTHON) $(CHECK_REPORT_RUNNER)

.PHONY: check-report-full-generate
check-report-full-generate:
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
	@test -n "$(PACKET)" || (echo "$(COLOR_RED)PACKET=<path> is required.$(COLOR_RESET)"; exit 1)
	$(MAKE) completion-safety-check
	$(MAKE) completion-packet-validate PACKET="$(PACKET)"
	$(MAKE) completion-report-validate PACKET="$(PACKET)"

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

.PHONY: completion-safety-check
completion-safety-check:
	$(PYTHON) $(COMPLETION_SAFETY_CHECKER)

.PHONY: completion-report-validate
completion-report-validate:
	@test -n "$(PACKET)" || (echo "$(COLOR_RED)PACKET=<path> is required.$(COLOR_RESET)"; exit 1)
	$(PYTHON) $(COMPLETION_REPORT_VALIDATOR) "$(PACKET)"

.PHONY: tracking-events-v0-3-reference-completion-check
tracking-events-v0-3-reference-completion-check:
	@test -n "$(PACKET)" || (echo "PACKET=<path> is required" && exit 2)
	$(PYTHON) scripts/coordination/validate_tracking_events_v0_3_reference_completion.py "$(PACKET)"


# Tracking Events / Completion Exchange v0.4 validation surface.
BLUEPRINT_COORDINATION_REGISTRY ?= $(BLUEPRINT_ROOT)/coordination/registry/coordination_source_registry_v0_1.yaml

.PHONY: completion-packet-v0-4-validate
completion-packet-v0-4-validate:
	@test -n "$(PACKET)" || (echo "PACKET=<path> is required" && exit 2)
	$(PYTHON) scripts/coordination/validate_completion_packet_v0_4.py --root . --packet "$(PACKET)"

.PHONY: completion-outbox-v0-4-validate
completion-outbox-v0-4-validate:
	@test -n "$(EVENT)" || (echo "EVENT=<path> is required" && exit 2)
	$(PYTHON) scripts/coordination/validate_completion_outbox_v0_4.py "$(EVENT)" --root . --registry "$(BLUEPRINT_COORDINATION_REGISTRY)"

.PHONY: tracking-events-v0-4-evidence-check
tracking-events-v0-4-evidence-check:
	$(PYTHON) scripts/coordination/validate_tracking_events_v0_4_evidence.py


# Tracking Events v0.4 two-phase completion publication.
# Subject preparation is mutation-capable but does not mutate terminal
# coordination records and does not create Packet/Outbox.
.PHONY: tracking-events-v0-4-subject-status
tracking-events-v0-4-subject-status:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_completion_subject.py status

.PHONY: tracking-events-v0-4-subject-preflight
tracking-events-v0-4-subject-preflight:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_completion_subject.py preflight

.PHONY: tracking-events-v0-4-subject-prepare
tracking-events-v0-4-subject-prepare:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_completion_subject.py prepare

.PHONY: tracking-events-v0-4-subject-check
tracking-events-v0-4-subject-check:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_completion_subject.py check

.PHONY: tracking-events-v0-4-finalization-idempotency-check
tracking-events-v0-4-finalization-idempotency-check:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_completion_subject.py idempotency-check


# Tracking Events v0.4 post-publication finalization.
# finalize-prepare is module-owned and mutation-capable; it never commits/pushes.
.PHONY: tracking-events-v0-4-finalize-status
tracking-events-v0-4-finalize-status:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_finalization.py status

.PHONY: tracking-events-v0-4-finalize-preflight
tracking-events-v0-4-finalize-preflight:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_finalization.py preflight

.PHONY: tracking-events-v0-4-finalize-prepare
tracking-events-v0-4-finalize-prepare:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_finalization.py prepare

.PHONY: tracking-events-v0-4-finalization-check
tracking-events-v0-4-finalization-check:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_finalization.py check

.PHONY: tracking-events-v0-4-postpublication-idempotency-check
tracking-events-v0-4-postpublication-idempotency-check:
	$(PYTHON) scripts/coordination/tracking_events_v0_4_finalization.py idempotency-check
