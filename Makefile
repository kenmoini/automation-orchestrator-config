# Tooling for kenmoini.automation_orchestrator_config
export PATH := $(CURDIR)/.venv/bin:$(PATH)
export ANSIBLE_LOCAL_TEMP ?= $(CURDIR)/.ansible/tmp
export ANSIBLE_HOME ?= $(CURDIR)/.ansible
export ANSIBLE_COLLECTIONS_PATH := $(CURDIR)/build

PY ?= 3.12
COLL_DIR := build/ansible_collections/kenmoini/automation_orchestrator_config
COVERAGE ?=
# Must be outside this repo's work tree: under the git-ignored build/ dir ansible-test walks up
# to this repo's .git, lists no files at all and silently tests nothing.
SYNC_ROOT ?= $(patsubst %/,%,$(or $(TMPDIR),/tmp))/kenmoini-aoc-sync
SYNC_DIR := $(SYNC_ROOT)/ansible_collections/kenmoini/automation_orchestrator_config

.PHONY: venv link sync lint sanity unit pytest build install changelog live live-check live-cleanup

venv:
	uv venv .venv --python $(PY)
	uv pip install --python .venv/bin/python ansible-core ansible-lint antsibull-changelog pytest pytest-mock black flake8 pre-commit pre-commit-uv yamllint

link:
	mkdir -p build/ansible_collections/kenmoini .ansible/tmp
	ln -sfn $(CURDIR) $(COLL_DIR)

# ansible-test resolves symlinks and refuses to run outside an ansible_collections tree,
# so test targets run against a synced copy instead of the symlink.
sync:
	mkdir -p $(SYNC_DIR) .ansible/tmp
	rsync -a --delete --exclude .git --exclude .venv --exclude build --exclude .ansible --exclude .superpowers --exclude tests/output ./ $(SYNC_DIR)/

lint:
	mkdir -p .ansible/tmp
	.venv/bin/pre-commit run --all-files

sanity: sync
	cd $(SYNC_DIR) && $(CURDIR)/.venv/bin/ansible-test sanity --venv --python $(PY)

unit: sync
	@if [ -z "$$(find tests/unit/plugins -name 'test_*.py' 2>/dev/null)" ]; then \
		echo "no unit tests yet"; \
	elif [ -n "$(COVERAGE)" ]; then \
		cd $(SYNC_DIR) && $(CURDIR)/.venv/bin/ansible-test units --venv --python $(PY) --coverage && $(CURDIR)/.venv/bin/ansible-test coverage report --venv --python $(PY); \
	else \
		cd $(SYNC_DIR) && $(CURDIR)/.venv/bin/ansible-test units --venv --python $(PY); \
	fi

# Unit tests via plain pytest on the synced copy (no ansible-test venv; works where ansible-test cannot).
pytest: sync
	cd $(SYNC_DIR) && PYTHONPATH=$(SYNC_ROOT) $(CURDIR)/.venv/bin/pytest tests/unit -q -p no:cacheprovider

build:
	mkdir -p build .ansible/tmp
	.venv/bin/ansible-galaxy collection build --force --output-path build/

install: build
	.venv/bin/ansible-galaxy collection install --force build/kenmoini-automation_orchestrator_config-*.tar.gz

changelog:
	.venv/bin/antsibull-changelog lint

live:
	@echo "defined in Task 27"

live-check:
	@echo "defined in Task 27"

live-cleanup:
	@echo "defined in Task 27"
