# kenmoini.automation_orchestrator_config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.1.0 of an Ansible Collection that manages Red Hat Automation Orchestrator as code: idempotent Python modules over its REST API, plus `infra.aap_configuration`-style roles and a `dispatch` role.

**Architecture:** One `module_utils` base class (`OrchestratorModule`) owns auth, HTTP, cursor pagination, name→UUID resolution, and diff/patch semantics. Each API resource gets a thin module (+ `_info`) built on it. Each module gets a role following the reference async/collect_async_status contract, and `dispatch` runs the roles in dependency order.

**Tech Stack:** ansible-core ≥ 2.16 (tested 2.16–2.20), Python stdlib + `ansible.module_utils.urls`, `ansible-test` (sanity, units), pytest, ansible-lint (production profile), antsibull-changelog, pre-commit, `uv` for the dev venv.

**Spec:** `docs/superpowers/specs/2026-10-18-automation-orchestrator-collection-design.md` (read it first; this plan argues from it). API snapshot: `docs/api/openapi-1.3.1.json`. Reference collection: clone `https://github.com/redhat-cop/infra.aap_configuration.git` (branch `devel`) to `$TMPDIR/aap_config_ref` if `/tmp/claude-501/aap_config_ref` is gone; use `GIT_CONFIG_GLOBAL=/dev/null` for all git commands on this machine (the user's global gitconfig is broken).

## Global Constraints

- FQCN `kenmoini.automation_orchestrator_config`; version `0.1.0`; license `GPL-3.0-or-later`; `requires_ansible: ">=2.16.0"`.
- Every Python file starts with: `# -*- coding: utf-8 -*-`, `# Copyright (c) 2026 Ken Moini`, `# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)`, `# SPDX-License-Identifier: GPL-3.0-or-later`, then `from __future__ import absolute_import, division, print_function` and `__metaclass__ = type`.
- Modules and module_utils must pass `ansible-test sanity` for ansible-core 2.16: no f-strings, no walrus, no type annotations in `plugins/`, stdlib + `ansible.module_utils` only, `DOCUMENTATION`/`EXAMPLES`/`RETURN` YAML in every module, `extends_documentation_fragment: kenmoini.automation_orchestrator_config.auth`.
- Black and flake8 line length 160. YAML: `.yml` only, 2-space indent, every file ends with `...`. ansible-lint `production` profile, `task_name_prefix: "{stem} | "`, `loop_var_prefix: "^(__|{role}_)"`, `var_naming_pattern: "^[a-z_][a-z0-9_]*$"`.
- Names/prefixes: roles `orchestrator_<resource>`, list vars `orchestrator_<resource>`, global knobs `orchestrator_configuration_*`, default state `orchestrator_state`, auth vars `orchestrator_hostname|username|password|token|client_id|client_secret|validate_certs|request_timeout`, loop vars `__orchestrator_<resource>_item`.
- Module auth params: `orchestrator_host`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, `validate_certs`, `request_timeout`; env fallbacks `ORCHESTRATOR_HOST|USERNAME|PASSWORD|TOKEN|CLIENT_ID|CLIENT_SECRET|VERIFY_SSL|REQUEST_TIMEOUT`.
- API base path `/api/v1`. Every endpoint needs a Bearer token. Secrets (`inputs`, `client_secret`, `password`, tokens) are `no_log` and stripped from returned objects.
- Secrets default `update_secrets: true`; users `update_password: on_create`. No delete guards. Lab test objects are named `aoc-test-*`; credentials come only from `ORCHESTRATOR_*` env vars and are never written to the repo.
- Commit after every task with a conventional-commit message and an antsibull changelog fragment when the task adds user-visible behavior (fragments live in `changelogs/fragments/`, end with `...`).

## Review Focus

1. `orchestrator_host` given as `orchestrator.example.com/` or `http://…` — must normalize to `https://host` without trailing slash and accept an explicit `http://`. Pinned in Task 4.
2. A `name` lookup that returns several matches (e.g. `/users/directory?username=bob` returning `bob` and `bobby`) must match exactly and fail clearly on true duplicates, never pick the first. Pinned in Task 5.
3. HTTP 429 with `Retry-After` must retry (bounded, ≤ 3) rather than fail; a 401 after a successful login must re-login once then fail. Pinned in Task 4.
4. A `definition_file` whose embedded `name` differs from the item `name` must be sent with the item name (the API requires `WorkflowDefinition.name`); a definition that is unchanged must report `changed: false` in both run and check mode. Pinned in Task 17.
5. `state: absent` on an `is_builtin` object (Default project, `users` group, builtin roles) must fail with a message naming the object, not a raw 4xx. Pinned in Task 6 and exercised in Task 9.

---

## Phase 1 — Scaffold and tooling

### Task 1: Collection skeleton

**Files:**
- Create: `galaxy.yml`, `meta/runtime.yml`, `LICENSE` (GPL-3.0 text), `README.md` (title, one-paragraph description, install, auth, "Content" placeholder), `CHANGELOG.rst` (empty header), `changelogs/config.yaml`, `changelogs/fragments/.keep`, `.gitignore`, `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/STANDARDS.md`, `plugins/modules/__init__.py` (empty), `plugins/module_utils/__init__.py`, `plugins/doc_fragments/__init__.py`, `tests/unit/requirements.txt`.

**Interfaces:**
- Produces: `galaxy.yml` with `namespace: kenmoini`, `name: automation_orchestrator_config`, `version: 0.1.0`, `license: [GPL-3.0-or-later]`, `authors: [Ken Moini]`, `repository: https://github.com/kenmoini/automation_orchestrator_configuration`, `tags: [automation_platform, orchestrator, configuration, infrastructure]`, no `dependencies`, `build_ignore: [.github, .venv, build, docs/api, docs/superpowers, tests/auth.yml, "*.tar.gz", .pre-commit-config.yaml, Makefile]`.
- Produces: `meta/runtime.yml` with `requires_ansible: ">=2.16.0"` and `action_groups: {orchestrator: [token, api, project, project_info, group, group_info, user, user_info, policy, policy_info, role, role_info, role_assignment, role_assignment_info, credential_type_info, credential, credential_info, integration, integration_info, identity_provider, identity_provider_info, service_account, service_account_info, service_account_credential, setting, setting_info, workflow, workflow_info, execution, execution_info, execution_cancel, approval, approval_info]}`.

- [ ] **Step 1: Write `galaxy.yml` and `meta/runtime.yml`** with the values above.
- [ ] **Step 2: Copy and adapt from the reference clone**: `changelogs/config.yaml` (set `title: kenmoini.automation_orchestrator_config`), `docs/STANDARDS.md` (verbatim), `LICENSE` (verbatim GPL-3.0), `CLAUDE.md`/`AGENTS.md` (rewrite for this collection: module+role contract from the spec's "Roles" and "Plugins" sections, naming constraints from Global Constraints, the `make` targets from Task 2), `CONTRIBUTING.md` (fragment + pre-commit requirements).
- [ ] **Step 3: Write `.gitignore`**: `.venv/`, `build/`, `*.tar.gz`, `tests/auth.yml`, `tests/output/`, `.ansible/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `orchestrator_exports/`.
- [ ] **Step 4: Write `tests/unit/requirements.txt`**: `pytest`, `pytest-mock`.
- [ ] **Step 5: Verify build**
  Run: `cd /Users/kenmoini/Development/automation_orchestrator_configuration && ansible-galaxy collection build --force --output-path "$TMPDIR"`
  Expected: `Created collection for kenmoini.automation_orchestrator_config at …/kenmoini-automation_orchestrator_config-0.1.0.tar.gz`
- [ ] **Step 6: Commit** — `chore: scaffold kenmoini.automation_orchestrator_config collection`

### Task 2: Lint, sanity, unit tooling and CI

**Files:**
- Create: `Makefile`, `.ansible-lint`, `.yamllint`, `.black.cfg`, `.flake8`, `.markdownlint-cli2.yaml`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`, `tests/unit/plugins/__init__.py`, `tests/unit/plugins/module_utils/__init__.py`, `tests/unit/plugins/modules/__init__.py`.

**Interfaces:**
- Produces `make` targets used by every later task: `venv` (`uv venv .venv --python 3.12` then `uv pip install --python .venv/bin/python ansible-core ansible-lint antsibull-changelog pytest pytest-mock black flake8 pre-commit yamllint`), `link` (creates gitignored `build/ansible_collections/kenmoini/automation_orchestrator_config` symlink to the repo root), `lint` (`.venv/bin/pre-commit run --all-files`), `sanity` (`cd build/ansible_collections/kenmoini/automation_orchestrator_config && ../../../../.venv/bin/ansible-test sanity --venv --python 3.12`), `unit` (same cwd, `ansible-test units --venv --python 3.12` plus `--coverage` option via `COVERAGE=1`), `build`, `install` (`ansible-galaxy collection install --force` the tarball), `changelog` (`antsibull-changelog lint`), `live`, `live-check`, `live-cleanup` (defined in Task 27; stub them with `@echo "defined in tests/"` for now).
- Produces `.ansible-lint`: `profile: production`, `offline: true`, `exclude_paths: [.cache/, .github/, changelogs/, build/, .venv/, docs/, tests/output/]`, `loop_var_prefix: "^(__|{role}_)"`, `var_naming_pattern: "^[a-z_][a-z0-9_]*$"`, `task_name_prefix: "{stem} | "`, `enable_list: [args, role-argument-spec, empty-string-compare, no-same-owner, name[prefix], galaxy-version-incorrect, yaml]`, `skip_list: [jinja[spacing], role-name[path], var-naming[no-role-prefix]]`, `warn_list: [experimental, no-log-password]`.

- [ ] **Step 1: Write `Makefile`** with the targets above; `ANSIBLE_LOCAL_TEMP ?= $(CURDIR)/.ansible/tmp` exported for all ansible commands (the sandbox denies `~/.ansible/tmp`).
- [ ] **Step 2: Write lint configs**: `.black.cfg` (`[tool.black] line-length = 160`), `.flake8` (`max-line-length = 160`, `exclude = .venv,build`), `.yamllint` (reference `.yamllint` if present, else `extends: default` with `line-length: {max: 160}`, `truthy: {allowed-values: ["true", "false"]}`, `document-end: {present: true}`), `.markdownlint-cli2.yaml` (`config: {MD013: false, MD033: false}`, `ignores: [build, .venv, docs/api, CHANGELOG.rst]`).
- [ ] **Step 3: Write `.pre-commit-config.yaml`**: pre-commit-hooks `end-of-file-fixer`, `trailing-whitespace`; `markdownlint-cli2`; `black` (`--config=.black.cfg --check --diff`); `flake8`; `ansible-lint` (local hook, `entry: .venv/bin/ansible-lint`, `language: system`, `pass_filenames: false`); `antsibull-changelog lint` (local hook). Pin versions that exist as of 2026-10 (check `pip index versions` if unsure).
- [ ] **Step 4: Write `.github/workflows/ci.yml`**: on push/PR; job `lint` (python 3.12, `pip install -r .github/requirements.txt`, `pre-commit run --all-files`); job `sanity-units` matrix `{ansible: "2.16", python: "3.11"}, {ansible: "2.18", python: "3.12"}, {ansible: "2.20", python: "3.13"}` checking out into `ansible_collections/kenmoini/automation_orchestrator_config`, `pip install "ansible-core~=X.0"`, `ansible-test sanity --venv --python $PY`, `ansible-test units --venv --python $PY`. Write `.github/requirements.txt` (`ansible-core`, `ansible-lint`, `antsibull-changelog`, `pre-commit`).
- [ ] **Step 5: Verify tooling on the empty collection**
  Run: `make venv link lint sanity`
  Expected: pre-commit "Passed" for every hook; `ansible-test sanity` ends with no failures (an empty `plugins/` is fine).
- [ ] **Step 6: Commit** — `chore: add lint, sanity, unit tooling and CI`

### Task 3: `global_vars` role

**Files:**
- Create: `roles/global_vars/defaults/main.yml`, `roles/global_vars/meta/main.yml`, `roles/global_vars/README.md`.

**Interfaces:**
- Produces: `operation_translate` dict with keys `present`, `absent`, `exists`, `enabled`, `disabled`, `rotated`, `launched`, `approved`, `rejected`; each `{verb: str, action: str}` (e.g. `rotated: {verb: Rotate, action: rotation}`, `launched: {verb: Launch, action: launch}`).

- [ ] **Step 1: Copy `roles/global_vars` from the reference**, replace author/links, extend `operation_translate` with the new keys.
- [ ] **Step 2: Verify** — Run: `make lint` → passes.
- [ ] **Step 3: Commit** — `feat(roles): add global_vars role`

---

## Phase 2 — module_utils, `token`, `api`

### Task 4: `OrchestratorModule` auth, HTTP, errors

**Files:**
- Create: `plugins/module_utils/orchestrator_api.py`
- Test: `tests/unit/plugins/module_utils/test_orchestrator_api_http.py`, `tests/unit/plugins/module_utils/conftest.py`

**Interfaces:**
- Produces (in `orchestrator_api.py`):
  - `API_PREFIX = "/api/v1"`
  - `AUTH_ARGUMENT_SPEC` dict (params listed in Global Constraints; `validate_certs` type bool default True; `request_timeout` type float default 10; `no_log` on password/token/client_secret; each with `fallback=(env_fallback, [...])`).
  - `class OrchestratorAPIError(Exception)` with attributes `status`, `code`, `title`, `detail`, `body`.
  - `class OrchestratorModule(AnsibleModule)`: `__init__(self, argument_spec=None, **kwargs)` merges `AUTH_ARGUMENT_SPEC`, adds `mutually_exclusive=[["orchestrator_token", "orchestrator_username"], ["orchestrator_token", "orchestrator_client_id"], ["orchestrator_username", "orchestrator_client_id"]]`, `required_together=[["orchestrator_username", "orchestrator_password"], ["orchestrator_client_id", "orchestrator_client_secret"]]`, `supports_check_mode` passthrough; sets `self.base_url` (normalized), `self.headers = {"Content-Type": "application/json", "Accept": "application/json"}`, `self._token = None`, `self._authenticated = False`.
  - `normalize_host(host) -> str`: adds `https://` when no scheme, strips trailing `/`, keeps `http://` when given, fails if empty.
  - `authenticate(self)`: token → set header; else client credentials → `POST /auth/token` form-encoded `grant_type=client_credentials&client_id&client_secret`; else `POST /auth/login` JSON `{username, password}`; stores `Authorization: Bearer <access_token>`; `fail_json` on 401 with the RFC 9457 `detail`.
  - `request(self, method, path, query=None, data=None, form=None, expect=None) -> object`: builds `base_url + API_PREFIX + path` (`path` may already start with `/api/v1`), urlencodes `query` (drops `None` values), JSON-encodes `data` or form-encodes `form`, calls `fetch_url(self, url, data=..., headers=..., method=..., timeout=self.params["request_timeout"])`; returns parsed JSON or `None` for 204; on 401 after auth, re-authenticates once and retries; on 429 sleeps `Retry-After` (default 1s, cap 30s) up to 3 times; otherwise raises `OrchestratorAPIError` built from the problem-details body (falls back to `info["msg"]`). `expect` defaults to `(200, 201, 202, 204)`.
  - `fail_api(self, err, context="")` → `fail_json(msg="<context>: <detail>", status=..., code=..., body=...)`.
- Test helpers (in `conftest.py`, importable by all unit tests): `module_args(dict)` context manager patching module args (use `ansible.module_utils.testing.patch_module_args` when importable, else set `ansible.module_utils.basic._ANSIBLE_ARGS`); `class FakeAPI` with `add(method, path, status, body=None, query=None, headers=None, times=None)` and `__call__(module, url, data=None, headers=None, method=None, timeout=None, **kw) -> (response, info)` matching on method + path + query subset, recording `calls: list[dict(method, path, query, body, headers)]`, returning a `response` with `.read()` → JSON bytes and `info={"status": status, "url": url, "body": bytes, "retry-after": ...}`; fixture `fake_api` that patches `…module_utils.orchestrator_api.fetch_url` with a `FakeAPI` instance; `make_module(fake_api, **params) -> OrchestratorModule` which applies `module_args` with `orchestrator_host="https://orch.example.com"` plus `orchestrator_token="t0k"` unless overridden.

- [ ] **Step 1: Write failing tests** in `test_orchestrator_api_http.py`:
  - `test_normalize_host_adds_https_and_strips_slash` (`"orch.example.com/"` → `"https://orch.example.com"`; `"http://orch:8080/"` → `"http://orch:8080"`).
  - `test_auth_precedence_token_over_password` (token given → no login call).
  - `test_login_with_username_password_sets_bearer` (`POST /api/v1/auth/login` body `{"username": "admin", "password": "pw"}`; next call carries `Authorization: Bearer abc`).
  - `test_client_credentials_uses_form_encoding` (`POST /api/v1/auth/token`, `Content-Type: application/x-www-form-urlencoded`, body contains `grant_type=client_credentials`).
  - `test_401_after_auth_relogins_once_then_fails` (sequence 401, login 200, 200 → success; sequence 401, login 200, 401 → `AnsibleFailJson` with `status == 401`).
  - `test_429_retries_with_retry_after` (429 `Retry-After: 0` then 200 → success; four 429s → fail with `status == 429`). Patch `time.sleep`.
  - `test_problem_details_error_mapping` (422 body `{"type":…,"title":"Validation Error","detail":"name invalid","code":"VALIDATION_ERROR","retryable":false}` → `OrchestratorAPIError.detail == "name invalid"`, `.code == "VALIDATION_ERROR"`).
  - `test_request_drops_none_query_and_returns_none_on_204`.
  - `test_env_fallback_for_host_and_token` (monkeypatch `ORCHESTRATOR_HOST`, `ORCHESTRATOR_TOKEN`).
- [ ] **Step 2: Run to verify they fail** — Run: `make unit` (or `.venv/bin/pytest tests/unit/plugins/module_utils -q` from the symlinked path). Expected: ImportError/AttributeError failures.
- [ ] **Step 3: Implement** `plugins/module_utils/orchestrator_api.py` (auth, request, errors only; leave pagination/lookup for Task 5) and `tests/unit/plugins/module_utils/conftest.py`.
- [ ] **Step 4: Run tests** — Expected: all PASS.
- [ ] **Step 5: Sanity** — Run: `make sanity`. Expected: pass (fix `no_log`, import, and compile findings rather than adding ignores).
- [ ] **Step 6: Commit** — `feat(module_utils): add OrchestratorModule auth and HTTP client`

### Task 5: Pagination and name resolution

**Files:**
- Modify: `plugins/module_utils/orchestrator_api.py`
- Test: `tests/unit/plugins/module_utils/test_orchestrator_api_lookup.py`

**Interfaces:**
- Produces:
  - `is_uuid(value) -> bool` (module-level; `uuid.UUID(str(value))` try/except).
  - `get_all(self, path, query=None) -> list`: sends `limit=100`, follows `next` cursor until `None`, concatenates `resources`.
  - `get_one_by_name(self, path, name, name_field="name", query=None, label=None) -> dict|None`: if `path` is in `SERVER_NAME_FILTERS` (dict mapping list path → filter param: `/projects`→`name`, `/roles`→`name`, `/policies`→`name`, `/service_accounts`→`name`, `/users`→`username`, `/users/directory`→`username`, `/groups/directory`→`name`) send it as a query param; always exact-match `name_field` client-side; 0 → `None`; >1 → `fail_json(msg="Found N <label> named '<name>'; expected 1")`.
  - `LOOKUPS = {kind: (path_template, name_field, scope)}` for kinds `project` (`/projects`, `name`, none), `user` (`/users`, `username`, none), `group` (`/groups`, `name`, none; tries `/groups/directory?name=` first and falls back to `/groups` when the directory call returns 403), `role` (`/roles`, `name`, optional `project_id` query), `policy` (`/policies`, `name`, optional `project_id`), `credential_type` (`/credential_types`, `name`), `credential` (`/projects/{project_id}/credentials`, `name`, requires `project_id`), `integration` (`/integrations`, `name`), `identity_provider` (`/identity_providers`, `name`), `service_account` (`/service_accounts`, `name`, optional `project_id` filter client-side), `workflow` (`/projects/{project_id}/workflows`, `name`, requires `project_id`).
  - `resolve_id(self, kind, value, project_id=None, required=True) -> str|None`: returns `value` unchanged when `is_uuid(value)`; else looks up and returns `obj["id"]`; when not found and `required`, `fail_json(msg="<kind> '<value>' not found")`; returns `None` when not required.
  - `resolve_obj(self, kind, value, project_id=None) -> dict|None` (same lookup but returns the object; a UUID does `GET <path>/<id>` and maps 404 → `None`).

- [ ] **Step 1: Write failing tests**: `test_get_all_follows_cursor` (two pages, second request has `cursor=abc`), `test_get_one_by_name_uses_server_filter_for_projects` (query `name=Default` sent), `test_get_one_by_name_exact_match_only` (directory returns `bob` and `bobby` → returns `bob`), `test_get_one_by_name_duplicates_fail`, `test_resolve_id_passes_uuid_through_without_http`, `test_resolve_id_not_found_fails_with_kind_and_value`, `test_resolve_workflow_requires_project_scope` (lists `/projects/<pid>/workflows`), `test_group_lookup_falls_back_when_directory_forbidden`.
- [ ] **Step 2: Run to verify fail.**
- [ ] **Step 3: Implement** the methods and tables above.
- [ ] **Step 4: Run tests → PASS; `make sanity` → pass.**
- [ ] **Step 5: Commit** — `feat(module_utils): add cursor pagination and name resolution`

### Task 6: Diff, create/update, delete semantics

**Files:**
- Modify: `plugins/module_utils/orchestrator_api.py`
- Test: `tests/unit/plugins/module_utils/test_orchestrator_api_crud.py`

**Interfaces:**
- Produces:
  - `SECRET_PLACEHOLDER = "$encrypted$"`
  - `build_desired(self, mapping) -> dict`: takes `{api_field: module_param_value}` and drops entries whose value is `None` (omit-unset semantics).
  - `compute_patch(self, existing, desired, full_fields=(), secret_fields=(), update_secrets=True) -> dict`: for each key in `desired`: if key in `secret_fields` → include iff `update_secrets`; elif key in `full_fields` (nested dict the API needs whole) → include the full merged dict (`existing[key]` updated with `desired[key]`) iff any sub-key differs or a secret sub-key is present and `update_secrets`; else include iff `existing.get(key) != desired[key]` (dicts/lists compared after JSON-normalizing: sort list of scalars, deep-compare dicts).
  - `create_or_update(self, existing, desired, path, create_path=None, full_fields=(), secret_fields=(), update_secrets=True, immutable=(), item_label=None) -> (changed: bool, obj: dict)`: when `existing is None` → `POST create_path or path` with `desired` (check mode: return `(True, desired)`); else compute patch; for keys in `immutable` that differ → `fail_json`; empty patch → `(False, existing)`; else `PATCH path/<id>` (check mode: merged preview); sets `self._diff = {"before": existing-subset, "after": merged}` used by `exit_result` when `self._diff_mode`.
  - `delete_if_needed(self, existing, path, item_label=None) -> bool`: `None` → `False`; `existing.get("is_builtin")` → `fail_json(msg="Cannot delete built-in <label> '<name>'")`; else `DELETE path/<id>` (skipped in check mode) → `True`.
  - `strip_secrets(obj, secret_fields=("inputs", "client_secret", "password"))` → copy with those keys replaced by `SECRET_PLACEHOLDER` (nested `configuration.client_secret` too).
  - `exit_result(self, changed, obj=None, **extra)`: `exit_json(changed=changed, id=obj.get("id") if obj else None, <resource-key>=strip_secrets(obj), diff=self._diff when diff mode, **extra)`; the resource key name is passed by the module via `self.result_key = "project"` etc. (default `"object"`).

- [ ] **Step 1: Write failing tests**: `test_build_desired_drops_none`, `test_compute_patch_only_changed_keys`, `test_compute_patch_list_order_insensitive_for_scalars`, `test_compute_patch_full_fields_sends_merged_dict`, `test_compute_patch_secrets_included_only_when_update_secrets`, `test_create_posts_when_missing_and_check_mode_does_not`, `test_update_patches_only_when_changed`, `test_immutable_change_fails` (project_id on workflow), `test_delete_builtin_fails_with_name` (Review Focus 5), `test_delete_skipped_in_check_mode_but_reports_changed`, `test_exit_result_strips_secrets_and_sets_id`.
- [ ] **Step 2: Run to verify fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run tests → PASS; `make sanity` → pass; coverage of `orchestrator_api.py` ≥ 90% (`make unit COVERAGE=1`).**
- [ ] **Step 5: Commit** — `feat(module_utils): add idempotent create/update/delete helpers`

### Task 7: Doc fragment, `token` module, `api` module, module test harness

**Files:**
- Create: `plugins/doc_fragments/auth.py`, `plugins/modules/token.py`, `plugins/modules/api.py`
- Test: `tests/unit/plugins/modules/conftest.py` (re-export `fake_api`, `module_args`, add `run_module(module_main, params, fake_api) -> dict` that executes a module's `main()` under `module_args` and returns the `exit_json`/`fail_json` kwargs, raising `AnsibleFailJson` for failures), `tests/unit/plugins/modules/test_token.py`, `tests/unit/plugins/modules/test_api.py`

**Interfaces:**
- `auth.py`: `class ModuleDocFragment: DOCUMENTATION = r"""options: orchestrator_host: … """` documenting all eight auth params with env fallbacks and the `module_defaults: group/kenmoini.automation_orchestrator_config.orchestrator` tip in `notes`.
- `token` module: params none beyond auth (`orchestrator_username/password` or `client_id/secret` required); `main()` calls `authenticate()` and `exit_json(changed=True, access_token=<token>, token_type="Bearer", expires_in=<int>)`; sets `no_log` on return via `ansible_facts`-free return and documents `access_token: returned: always, no_log: true`. Fails if only `orchestrator_token` is supplied (`msg="token module needs username/password or client credentials"`).
- `api` module: params `endpoint` (str, required; with or without `/api/v1`), `method` (choices GET/POST/PATCH/PUT/DELETE, default GET), `data` (raw dict), `query_params` (dict), `expect` (list of ints, optional), `return_all_pages` (bool, default false; when true and the response has `resources`+`next`, uses `get_all`). Returns `status`, `json`. `changed` = method != GET. `supports_check_mode=True` (non-GET skipped in check mode).

- [ ] **Step 1: Write failing tests**: `test_token_returns_access_token_and_expires_in`, `test_token_fails_when_only_token_given`, `test_api_get_passes_query_and_returns_json`, `test_api_post_changed_true_and_check_mode_skips`, `test_api_return_all_pages_collects_resources`.
- [ ] **Step 2: Run to verify fail.**
- [ ] **Step 3: Implement** the three plugin files and the `conftest.py` harness. Module skeleton for all later modules: `DOCUMENTATION`, `EXAMPLES`, `RETURN` YAML strings; `def main(): module = OrchestratorModule(argument_spec=dict(...), supports_check_mode=True); module.result_key = "<resource>"; …; if __name__ == "__main__": main()`.
- [ ] **Step 4: Run tests → PASS. Run `make sanity` (validate-modules now checks docs) → pass. Run `ansible-doc -t module kenmoini.automation_orchestrator_config.token` from the symlinked path → renders.**
- [ ] **Step 5: Changelog fragment** `changelogs/fragments/token-api-modules.yml` (`minor_changes`).
- [ ] **Step 6: Commit** — `feat(modules): add token and api modules with shared auth doc fragment`

---

## Phase 3 — Identity and RBAC modules

Every module task in Phases 3–5 follows the **module pattern**:

1. Tests first in `tests/unit/plugins/modules/test_<module>.py` using `run_module`/`fake_api`: `create` (POST body exact), `update_changed` (PATCH body contains only changed keys), `no_change` (`changed is False`, no PATCH call), `absent_deletes`, `absent_missing_noop`, `check_mode_create_no_post`, plus the module-specific cases listed in the task.
2. `plugins/modules/<module>.py` built on `OrchestratorModule`: resolve scope → `resolve_obj`/`get_one_by_name` existing → `build_desired` → `create_or_update` / `delete_if_needed` → `exit_result`.
3. `plugins/modules/<module>_info.py`: params `name` (optional) plus the filters listed; returns `resources: list` (secrets stripped). When `name` given, returns 0 or 1 items. Uses `get_all` with server filters where listed in Task 5.
4. `make unit`, `make sanity`, `ansible-doc` render, changelog fragment, commit.

### Task 8: `project`, `project_info` (establishes the pattern)

**Files:** `plugins/modules/project.py`, `plugins/modules/project_info.py`, tests.

**Interfaces:**
- `project` params: `name` (required), `new_name`, `description`, `labels` (dict), `state` (present/absent/exists, default present). Lookup `get_one_by_name("/projects", name)`; when `state=present` and `new_name` and the object exists, desired `name=new_name`. `result_key="project"`.
- `project_info` filters: `name`, `is_default` (bool), `is_builtin` (bool).

- [ ] **Step 1: Tests** (pattern set + `test_rename_with_new_name_patches_name`, `test_exists_state_creates_but_never_updates`, `test_info_filters_passed_as_query`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add project and project_info`

### Task 9: `group`, `group_info`, `user`, `user_info`

**Interfaces:**
- `group`: `name` (required), `new_name`, `description`, `state`. No labels. Builtin groups refuse delete (Review Focus 5 test: deleting `users` group fails with its name).
- `user`: `username` (required), `password` (no_log), `update_password` (choices `on_create`/`always`, default `on_create`), `email`, `first_name`, `last_name`, `is_enabled` (bool), `groups` (list of names/UUIDs; `None` = untouched), `state`. Create: `POST /users` with `group_names` = `groups` when provided (omit otherwise → server default). Update: `PATCH /users/{id}` for changed metadata (password included only when `update_password == "always"`); when `groups` provided, compute target set = resolved group ids ∪ existing memberships whose `membership_sources` contain a non-`manual` type (from `GET /users/{id}/groups`); `PUT /users/{id}/groups {"group_ids": [...]}` only when the set differs. Federated users (`auth_type == "federated"`): never send `password`; fail if `state=present` and the user does not exist (`msg="Federated users are created by their identity provider"`) — detected when `password` is absent and user missing → fail `password is required to create a local user`.
- `user_info` filters: `username`, `auth_type`, `auth_source`. `group_info` filter: `name`.

- [ ] **Step 1: Tests** (pattern set ×2 + `test_user_groups_put_only_when_changed`, `test_user_groups_preserve_idp_memberships`, `test_user_password_sent_only_on_create_by_default`, `test_user_update_password_always_patches`, `test_group_delete_builtin_fails`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add group and user modules`

### Task 10: `policy`, `policy_info`, `role`, `role_info`

**Interfaces:**
- `policy`: `name` (required; API pattern `^[a-zA-Z0-9]([a-zA-Z0-9:_-]*[a-zA-Z0-9])?$` — let the API validate), `new_name`, `description`, `statements` (list of dicts `{effect, actions, scope, conditions}`; required on create), `labels`, `project` (name/UUID → `project_id`), `state`. Lookup `/policies` with `name` and `project_id` filters. Statements compared order-insensitively by JSON-normalizing each dict.
- `role`: `name`, `new_name`, `description`, `policies` (list of policy names/UUIDs; required on create; API wants **names** — resolve UUIDs back to names via `GET /policies/{id}`), `labels`, `project`, `state`. Lookup `/roles` with `name` + `project_id`.
- `*_info` filters: `name`, `project`, `is_builtin`, `scope`.

- [ ] **Step 1: Tests** (pattern set ×2 + `test_policy_statements_order_insensitive`, `test_role_policies_uuid_resolved_to_names`, `test_project_scoped_lookup_sends_project_id`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add policy and role modules`

### Task 11: `role_assignment`, `role_assignment_info`

**Interfaces:**
- `role_assignment`: `role` (required; name or UUID → `role_name`), `user` xor `group` (required one of; name/UUID → `principal_id`/`group_id`), `project` (optional → `project_id`), `state` (present/absent). Lookup `GET /role_assignments` with `role_name`, `project_id`, and `principal_name` (username or group name) then client-side match on `principal_type` (`user`/`group`) and `project_id` (None for global). Create `POST /role_assignments`; absent `DELETE /role_assignments/{id}`. No update path (assignments are immutable).
- `role_assignment_info` filters: `role`, `user`, `group`, `project`, `scope`.

- [ ] **Step 1: Tests** (`test_create_user_assignment_body`, `test_create_group_assignment_body`, `test_existing_assignment_noop`, `test_absent_deletes`, `test_user_and_group_mutually_exclusive`, `test_global_vs_project_scope_distinguished`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add role_assignment module`

---

## Phase 4 — Content modules

### Task 12: `credential_type_info`, `credential`, `credential_info`

**Interfaces:**
- `credential_type_info`: filter `name`; returns `resources` with `inputs`/`injectors` schemas.
- `credential`: `name` (required), `new_name`, `description`, `credential_type` (name/UUID → `credential_type_id`; required on create; immutable), `project` (required → `project_id`), `inputs` (dict, no_log), `enabled` (bool), `labels`, `update_secrets` (bool, default true), `state`. Lookup `get_one_by_name("/projects/{pid}/credentials", name)`. Create `POST /credentials` with `project_id`. Update `PATCH /credentials/{id}`; `inputs` is a `secret_fields` entry so it is sent iff `update_secrets` (and then `changed=True`). Returned object has `inputs` replaced by `$encrypted$`.
- `credential_info` filters: `project` (required), `name`, `credential_type`, `enabled`.

- [ ] **Step 1: Tests** (pattern set + `test_inputs_sent_on_create_and_not_logged`, `test_update_secrets_false_skips_inputs_and_no_change`, `test_update_secrets_true_patches_inputs_changed`, `test_credential_type_immutable_fails`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add credential modules`

### Task 13: `integration`, `integration_info`

**Interfaces:**
- `integration`: `name` (required), `new_name`, `description`, `integration_type` (choices `mcp_server`, `llm_provider`, `ansible_automation_platform`; required on create; immutable), `configuration` (dict; module injects `integration_type` into it; `full_fields=("configuration",)`), `management_credential` (name/UUID) + `management_credential_project` (required when `management_credential` is a name) → `management_credential_id`, `enabled`, `scope` (choices `global`/`project`), `labels`, `projects` (list of names/UUIDs; when provided, reconcile via `GET /integrations/{id}/projects`, `POST`/`DELETE /integrations/{id}/projects/{pid}`), `models` (list of `{name|model_id, enabled, is_default}`), `tools` (list of `{name, enabled}`), `discover` (bool, default true: when creating with `models`/`tools` given, call `POST /integrations/discover` with `{integration_type, configuration, credential_id}` and pass `discovered_models`/`discovered_tools` with the requested `enabled` flags in the create body), `refresh` (bool: `POST /integrations/{id}/refresh` after create/update; changed iff `updated_count > 0`), `validate` (bool: `POST /integrations/{id}/validate`; never changed; result in `validation`), `state`. Models/tools reconcile: `GET /integrations/{id}/models` (`/tools`), match by `model_id`/`name`, `PATCH …/models/{id}` with only differing `enabled`/`is_default` (fail if a requested model/tool is absent after discover/refresh: `msg="Model 'x' not found on integration 'y'; run with refresh: true"`). Lookup `/integrations` filtered by `integration_type` then exact `name`.
- `integration_info` filters: `name`, `integration_type`, `enabled`, `scope`, `project`; option `include_models`, `include_tools` (bool) to attach sub-lists.

- [ ] **Step 1: Tests** (pattern set + `test_configuration_gets_integration_type_and_full_patch`, `test_projects_reconcile_assign_and_unassign`, `test_models_patch_only_differing_flags`, `test_discover_on_create_feeds_discovered_models`, `test_refresh_changed_only_when_updated_count`, `test_validate_never_changed`, `test_management_credential_resolved_in_project`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add integration modules`

### Task 14: `identity_provider`, `identity_provider_info`

**Interfaces:**
- `identity_provider`: `name` (required), `new_name`, `description`, `enabled`, `configuration` (dict; `provider_type` defaults to `oidc`; `full_fields=("configuration",)`; sub-key `client_secret` is secret → sent iff `update_secrets`; `group_mapping_entries[*].mapped_group` (name) is resolved to `mapped_group_id` before diffing), `update_secrets` (default true), `test` (bool: `POST /identity_providers/test` with `{name, description, configuration}` before create/update; never changed; result in `test_result`), `state`. Lookup `/identity_providers` exact name.
- `identity_provider_info` filter: `name`.

- [ ] **Step 1: Tests** (pattern set + `test_group_mapping_names_resolved`, `test_full_configuration_sent_on_subkey_change`, `test_client_secret_respects_update_secrets`, `test_test_flag_calls_endpoint_without_changed`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add identity_provider modules`

### Task 15: `service_account`, `service_account_info`, `service_account_credential`

**Interfaces:**
- `service_account`: `name` (required), `new_name`, `description`, `project` (required → `project_id`), `state` (present/absent/enabled/disabled). `enabled`/`disabled` imply present then `POST /service_accounts/{id}/enable|disable` when `status` differs. Lookup `/service_accounts?name=` then client-side `project_id` match.
- `service_account_credential`: `service_account` (name/UUID, required), `project` (required when name), `identifier` (optional; targets existing by `identifier`), `grace_period_seconds` (int), `expires_at` (str, ISO 8601), `state` (choices `present`, `absent`, `rotated`, `enabled`, `disabled`; default present). Semantics: `present` without `identifier` → ensure at least one credential with `status == "active"` exists, create (`credential_type: client_credentials`) if none → returns `client_id` (= `identifier`) and `client_secret` (no_log, only on the creating run); `present` with `identifier` → exists check only; `rotated` → `POST …/{id}/rotate` (requires `identifier`; always changed; returns new `client_secret`); `enabled`/`disabled` → toggle when status differs; `absent` → delete by `identifier` (required). `result_key="service_account_credential"`.
- `service_account_info` filters: `name`, `project`, `status`; option `include_credentials` (bool).

- [ ] **Step 1: Tests** (pattern set for `service_account` + `test_enabled_state_calls_enable_when_disabled`, `test_credential_present_creates_when_none_active`, `test_credential_present_noop_when_active_exists`, `test_credential_rotated_requires_identifier_and_returns_secret`, `test_credential_absent_requires_identifier`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add service account modules`

### Task 16: `setting`, `setting_info`

**Interfaces:**
- `setting`: either `name` + `value` (raw, any type) or `settings` (dict key→value); `expected_version` (int, only with `name`). Reads current via `GET /settings/{key}` (compare `value`; treat `null` value as "use default" and compare against `default_value` when desired equals default) ; single key → `PATCH /settings/{key} {"value": v}`; dict → one `PATCH /settings {"updates": [{"key","value"}]}` containing only changed keys. Returns `settings: {key: effective_value}` and `changed_keys: list`.
- `setting_info` filters: `name` (key), `category`, `group`; `categories: bool` returns `GET /settings/categories` instead.

- [ ] **Step 1: Tests** (`test_single_key_patch_when_differs`, `test_single_key_noop`, `test_bulk_patch_only_changed_keys`, `test_null_value_equal_to_default_is_noop`, `test_info_categories`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add setting modules`

---

## Phase 5 — Workflow and action modules

### Task 17: `workflow`, `workflow_info`

**Interfaces:**
- `workflow`: `name` (required), `new_name`, `description`, `labels`, `project` (required → `project_id`; immutable), `workflow_definition` (dict) xor `definition_file` (path; module reads it, `json.loads` then `yaml.safe_load` fallback), `is_import` (bool, default false), `change_description` (str), `publish` (bool, default false), `unpublish` (bool, default false), `state` (present/absent/exists). Behavior:
  1. Lookup via `resolve_obj("workflow", name, project_id)`; fetch current definition with `GET /workflows/{id}` (`WorkflowReadWithVersion.version.workflow_definition`).
  2. If a definition is given: set `definition["name"] = name` (Review Focus 4), set `schema_version` to `"2.0.0"` if absent; `normalize(d)` = JSON round-trip with sorted keys; `definition_changed = normalize(new) != normalize(current)`.
  3. Missing + present → `POST /workflows {name, description, labels, workflow_definition, project_id, is_import}` (fail with `msg="workflow_definition or definition_file is required to create workflow '<name>'"` when neither given).
  4. Existing → metadata patch via `compute_patch` on `name/description/labels`; if `definition_changed` add `workflow_definition` (+ `change_description`, `expected_version=current_version`) to the same `PATCH /workflows/{id}`.
  5. `publish` → if `definition_changed` and `publish`, send `POST /workflows/{id}/versions/{current_version}/publish` with `{change_description}` after the PATCH (re-read `current_version` from the PATCH response); if not changed and `published_version_number != current_version` → publish current. `unpublish` → `POST /workflows/{id}/unpublish` when `published_version_number` is not `None`.
  6. Returns `workflow` (metadata), `version` (int), `published_version` (int|None), `definition_changed` (bool). Check mode: compute everything, no writes.
- `workflow_info`: `project` (required unless `id` given), `name`, `id`, `include_definition` (bool, default false → attaches `workflow_definition` from `GET /workflows/{id}`), `version` (int → `GET /workflows/{id}/versions/{v}` definition instead), `include_versions` (bool → `GET /workflows/{id}/versions`).

- [ ] **Step 1: Tests** (pattern set + `test_create_requires_definition`, `test_definition_file_json_and_yaml_loaded`, `test_definition_name_overridden_to_item_name`, `test_unchanged_definition_no_patch_in_run_and_check_mode`, `test_changed_definition_patch_includes_expected_version`, `test_publish_after_change_targets_new_version`, `test_publish_noop_when_already_published`, `test_unpublish_when_published`, `test_project_immutable`, `test_info_include_definition_and_version`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add workflow modules`

### Task 18: `execution`, `execution_info`, `execution_cancel`

**Interfaces:**
- `execution`: `workflow` (name/UUID, required), `project` (required when name), `trigger_node_id` (optional; when absent, read the current definition's `triggers` and use the sole trigger's `id`, else fail `msg="workflow '<name>' has N triggers; set trigger_node_id"`), `input_data` (dict), `use_published` (bool, default false), `wait` (bool, default false), `interval` (float, default 2), `timeout` (int seconds, default 0 = forever). `POST /executions`; when `wait`, poll `GET /executions/{id}` every `interval` until `status in ("completed", "completed_with_errors", "failed", "cancelled")` or `paused` (approval pending → exit with `paused: true`, not failed); fail when `status in ("failed",)`, timeout → fail with `msg` containing the execution id. Always `changed=True`. Returns `execution` (full read), `id`, `status`.
- `execution_cancel`: `id` (required), `fail_if_not_running` (bool, default false). `POST /executions/{id}/cancel` when status is `pending|running|paused`; changed accordingly.
- `execution_info`: `id` or (`workflow` + `project` + `limit` default 20 + `status` client-side filter), sorted `-created_at`; option `include_activities` (bool → `GET /executions/{id}/activities`).

- [ ] **Step 1: Tests** (`test_launch_body_and_single_trigger_autopick`, `test_multiple_triggers_require_trigger_node_id`, `test_wait_polls_until_terminal`, `test_wait_paused_exits_not_failed`, `test_wait_failed_status_fails`, `test_wait_timeout_fails_with_id`, `test_cancel_running_changed`, `test_cancel_completed_noop`, `test_info_bounded_list_sorted`). Patch `time.sleep`.
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add execution modules`

### Task 19: `approval`, `approval_info`

**Interfaces:**
- `approval`: `id` or (`execution` UUID + `name`), `decision` (choices `approved`/`rejected`, required), `notes` (str). Lookup by id or `GET /approvals?execution_id=` + exact `name`; if `status == "pending"` → `PATCH /approvals/{id} {"status": decision, "notes": notes}` changed; if already decided with the same decision → noop; different decision → fail `msg="Approval '<name>' already <status>"`.
- `approval_info` filters: `id`, `execution`, `status`, `project`.

- [ ] **Step 1: Tests** (`test_decide_pending_patches`, `test_already_same_decision_noop`, `test_conflicting_decision_fails`, `test_lookup_by_execution_and_name`, `test_info_filters`).
- [ ] **Step 2: Fail → implement → pass → sanity → fragment → commit** `feat(modules): add approval modules`

### Task 20: Lab spot-checks and `docs/API_COMPATIBILITY.md`

**Files:** Create `docs/API_COMPATIBILITY.md`; create `tests/live/spot_checks.yml` (read-mostly playbook using the new modules; creates/deletes only `aoc-test-*` objects).

Requires `ORCHESTRATOR_HOST`, `ORCHESTRATOR_USERNAME`, `ORCHESTRATOR_PASSWORD` in the environment (ask the user if absent; do not proceed without them). Run with `ANSIBLE_LOCAL_TEMP` set and `validate_certs: false` for the lab.

- [ ] **Step 1: Write `tests/live/spot_checks.yml`** that: (a) `token` → fact; (b) `GET /version` via `api` → record API version; (c) create project `aoc-test-spot`, workflow `aoc-test-spot-wf` from a minimal valid definition (one trigger, one `wait` node — derive from `docs/api/openapi-1.3.1.json` `WorkflowDefinition`/`WaitNode`), then `api` GET `/workflows/{id}/versions/1/export` and `GET /workflows/{id}` → compare shapes; (d) create `llm_provider` integration with a bogus base_url and check whether `/models` has rows (expect none) and what `/refresh` returns (expect error or empty); (e) create user `aoc-test-spot-user`, delete, re-create same username → record 409 vs success; (f) delete everything created, including the project.
- [ ] **Step 2: Run** — `make live-spot` (add target: `ansible-playbook tests/live/spot_checks.yml`). Record results.
- [ ] **Step 3: Write `docs/API_COMPATIBILITY.md`**: tested API version string, export response shape (and whether `workflow_info` could use it), model/tool population behavior for `llm_provider` vs `mcp_server`, soft-delete name reuse per resource, any `validate_certs` notes. Adjust `workflow`/`integration`/`user` modules if a finding contradicts Tasks 9/13/17 (update their tests first).
- [ ] **Step 4: Commit** — `docs: record API compatibility findings from lab spot-checks`

---

## Phase 6 — Roles

### Task 21: `collect_async_status` role

**Files:** `roles/collect_async_status/{defaults/main.yml,meta/main.yml,tasks/main.yml,tasks/handle_error.yml,README.md}`

**Interfaces:**
- Consumes/produces the reference `cas_*` interface unchanged: `cas_async_retries`, `cas_async_delay`, `cas_secure_logging`, `cas_job_async_results_item`, `cas_register_subvar`, `cas_error_list_var_name`, `cas_object_label`.
- Global vars renamed: `aap_configuration_async_retries`→`orchestrator_configuration_async_retries`, `…_async_delay`, `…_secure_logging`, `aap_configuration_collect_logs`→`orchestrator_configuration_collect_logs`, `aap_configuration_register`→`orchestrator_configuration_register`, `aap_configuration_role_errors`→`orchestrator_configuration_role_errors`.
- `handle_error.yml` captures item keys `name`, `username`, `project`, `workflow`, `role`, `user`, `group`, `service_account`, `key` (replace the reference's controller-specific list).

- [ ] **Step 1: Copy the reference role**, apply the renames with `sed`, replace the captured-key tasks, rewrite README.
- [ ] **Step 2: Verify** — `make lint` passes; `ansible-playbook --syntax-check` on a throwaway play that includes the role with `cas_*` vars.
- [ ] **Step 3: Commit** — `feat(roles): add collect_async_status role`

### Task 22: Resource role template and `orchestrator_projects`

**Files:** `roles/orchestrator_projects/{defaults/main.yml,tasks/main.yml,meta/main.yml,meta/argument_specs.yml,README.md,tests/test.yml,tests/configs/projects.yml}`; `docs/ROLE_TEMPLATE.md` (the pattern below, for Task 23 implementers).

**Interfaces (the role pattern, used verbatim by Tasks 23–24 with `<res>` substituted):**
- `defaults/main.yml`: `orchestrator_<res>: []`, `orchestrator_configuration_<res>_secure_logging: "{{ orchestrator_configuration_secure_logging | default('false') }}"`, `…_async_retries: "{{ orchestrator_configuration_async_retries | default(50) }}"`, `…_async_delay: "{{ orchestrator_configuration_async_delay | default(1) }}"`, `…_loop_delay: "{{ orchestrator_configuration_loop_delay | default(0) }}"`, `…_enforce_defaults: "{{ orchestrator_configuration_enforce_defaults | default(false) }}"`, `orchestrator_configuration_async_dir:` (null).
- `tasks/main.yml`: copy `roles/controller_organizations/tasks/main.yml` from the reference; replace the module with `kenmoini.automation_orchestrator_config.<module>`; loop var `__orchestrator_<res>_item`; async register `__orchestrator_<res>_job_async`; `collect_async_status` include with `cas_register_subvar: orchestrator_<res>`, `cas_error_list_var_name: orchestrator_<res>_errors`; auth block on every module call:
  ```yaml
  orchestrator_host: "{{ orchestrator_hostname | default(omit, true) }}"
  orchestrator_username: "{{ orchestrator_username | default(omit, true) }}"
  orchestrator_password: "{{ orchestrator_password | default(omit, true) }}"
  orchestrator_token: "{{ orchestrator_token | default(omit, true) }}"
  orchestrator_client_id: "{{ orchestrator_client_id | default(omit, true) }}"
  orchestrator_client_secret: "{{ orchestrator_client_secret | default(omit, true) }}"
  validate_certs: "{{ orchestrator_validate_certs | default(omit) }}"
  request_timeout: "{{ orchestrator_request_timeout | default(10, true) }}"
  ```
  Item fields map 1:1 to module params with `| default(omit, true)` (bools use `| default(omit)`); `state: "{{ __item.state | default(orchestrator_state | default('present')) }}"`; label uses `operation_translate`.
- `meta/main.yml`: `galaxy_info` (role_name `<res>`, author Ken Moini, license GPL-3.0-or-later, min_ansible_version 2.16.0, platforms EL all, galaxy_tags), `dependencies: [{role: global_vars}]`.
- `meta/argument_specs.yml`: `orchestrator_<res>` (list of dict) with commented per-item options as in the reference, plus the async/no_log/generic auth options renamed.
- `README.md`: reference README structure with the renamed variables and a data-structure table listing every item field.
- `tests/test.yml`: reference `tests/test.yml` with `orchestrator_hostname: orchestrator.example.com`, `orchestrator_validate_certs: false`, `orchestrator_username: admin`, `orchestrator_password: changeme`; `tests/configs/<res>.yml` with two `aoc-test-*` items.

- [ ] **Step 1: Write `roles/orchestrator_projects`** per the pattern (module `project`; fields `name`, `new_name`, `description`, `labels`, `state`).
- [ ] **Step 2: Write `docs/ROLE_TEMPLATE.md`** capturing the pattern and the exact sed-able substitutions.
- [ ] **Step 3: Verify** — `make lint`; `ansible-playbook --syntax-check roles/orchestrator_projects/tests/test.yml` (run from `build/ansible_collections/kenmoini/automation_orchestrator_config` with `ANSIBLE_COLLECTIONS_PATH=$PWD/build`).
- [ ] **Step 4: Commit** — `feat(roles): add orchestrator_projects role and role template`

### Task 23: Remaining configuration roles

**Files:** one role dir each, per Task 22's pattern:

| Role | Module | Item fields → module params (beyond `name`, `description`, `labels`, `state`) |
|---|---|---|
| `orchestrator_settings` | `setting` | var may be a dict (`{key: value}`) → one module call with `settings`; or a list of `{name, value, expected_version}` → loop. Role detects with `is mapping`. |
| `orchestrator_identity_providers` | `identity_provider` | `enabled`, `configuration`, `update_secrets`, `test` |
| `orchestrator_groups` | `group` | `new_name` |
| `orchestrator_users` | `user` | `username` (replaces `name`), `password`, `update_password`, `email`, `first_name`, `last_name`, `is_enabled`, `groups` |
| `orchestrator_policies` | `policy` | `new_name`, `statements`, `project` |
| `orchestrator_roles` | `role` | `new_name`, `policies`, `project` |
| `orchestrator_role_assignments` | `role_assignment` | `role`, `user`, `group`, `project`; loop label `<role> -> <user or group>` |
| `orchestrator_credentials` | `credential` | `new_name`, `credential_type`, `project`, `inputs`, `enabled`, `update_secrets` |
| `orchestrator_integrations` | `integration` | `new_name`, `integration_type`, `configuration`, `management_credential`, `management_credential_project`, `enabled`, `scope`, `projects`, `models`, `tools`, `discover`, `refresh`, `validate` |
| `orchestrator_service_accounts` | `service_account` | `new_name`, `project`; state also `enabled`/`disabled` |
| `orchestrator_service_account_credentials` | `service_account_credential` | `service_account`, `project`, `identifier`, `grace_period_seconds`, `expires_at`; state `present/absent/rotated/enabled/disabled`; README warns the secret is returned once and shows `register` |
| `orchestrator_workflows` | `workflow` | `new_name`, `project`, `workflow_definition`, `definition_file`, `is_import`, `change_description`, `publish`, `unpublish`. Role passes `workflow_definition: "{{ item.workflow_definition | default((lookup('ansible.builtin.file', item.definition_file) | from_yaml) if item.definition_file is defined else omit) }}"` so files resolve controller-side; `definition_file` itself is **not** passed to the module. |

- [ ] **Step 1: Generate the 12 roles** from the template (a short throwaway script in `$TMPDIR` is fine; do not commit it), then hand-edit the field maps above, READMEs, argument_specs, and test configs (`aoc-test-*` names; `update_secrets: false` on items with secrets).
- [ ] **Step 2: Verify** — `make lint`; syntax-check every `roles/*/tests/test.yml`.
- [ ] **Step 3: Fragment + commit** — `feat(roles): add configuration roles for all Orchestrator resources`

### Task 24: Action roles

**Files:** `roles/orchestrator_execution_launch/…` (var `orchestrator_launch_executions`, module `execution`, fields `workflow`, `project`, `trigger_node_id`, `input_data`, `use_published`, `wait`, `interval`, `timeout`; **no async** — mirrors `controller_job_launch`: plain loop, `register: orchestrator_launched_executions`) and `roles/orchestrator_approval_decisions/…` (var `orchestrator_approval_decisions`, module `approval`, fields `id`, `execution`, `name`, `decision`, `notes`; plain loop).

- [ ] **Step 1: Write both roles** following `roles/controller_job_launch` from the reference (defaults: only `_secure_logging`).
- [ ] **Step 2: Verify** — lint + syntax-check.
- [ ] **Step 3: Fragment + commit** — `feat(roles): add execution launch and approval decision roles`

### Task 25: `dispatch` role

**Files:** `roles/dispatch/{defaults/main.yml,vars/main.yml,tasks/main.yml,tasks/include_wildcard_vars.yml,tasks/vars_only.yml,meta/main.yml,meta/argument_specs.yml,README.md,tests/test.yml,tests/configs/*.yml}`

**Interfaces:**
- `orchestrator_configuration_dispatcher_roles`: ordered list of `{role, var, tags}` exactly as the spec's Roles table (settings … approval_decisions, 15 entries; tags `[<short>, orchestrator_<res>]`).
- `orchestrator_configuration_dispatcher_exclude_roles: []`; `dispatch_include_wildcard_vars: false`; `vars/main.yml` `orchestrator_configuration_all_vars` = the 15 list-var names.
- `tasks/main.yml`: port of the reference (`include_wildcard_vars` → `include_role` loop with `apply: tags` and `when: vars[__role.var] is defined` → "Display errors and fail" on `orchestrator_configuration_role_errors` → check-mode `error_flag` fail). Drop the `_dispatch_assign_*` vars.

- [ ] **Step 1: Port the reference `dispatch` role** with the renames; `tests/configs/` gets one small file per resource (reuse Task 23 configs).
- [ ] **Step 2: Verify** — lint; `ansible-playbook --syntax-check roles/dispatch/tests/test.yml`; `ansible-playbook --list-tags roles/dispatch/tests/test.yml` shows all 15 tags.
- [ ] **Step 3: Fragment + commit** — `feat(roles): add dispatch role`

---

## Phase 7 — Playbooks, live test harness, docs, release prep

### Task 26: Collection playbooks

**Files:** `playbooks/configure_orchestrator.yml`, `playbooks/export_workflows.yml`, `playbooks/get_token.yml`, `playbooks/README.md`

- `configure_orchestrator.yml`: `hosts: localhost`, `connection: local`, `gather_facts: false`; `pre_tasks` include_vars `dir: "{{ orchestrator_configs_dir | default('orchestrator_configs') }}"` with `extensions: [yml]`, `ignore_files: [auth.yml.example]`; `roles: [kenmoini.automation_orchestrator_config.dispatch]`.
- `export_workflows.yml`: vars `orchestrator_export_dir` (default `./orchestrator_exports`), optional `orchestrator_export_projects` (list of names; default all via `project_info`); for each project → `workflow_info include_definition: true` → `ansible.builtin.copy` `content: "{{ item.workflow_definition | to_nice_json(indent=2) }}"` to `<dir>/<project.name>/<workflow.name>.json`; prints the summary of files written.
- `get_token.yml`: `token` module → `debug` of `expires_in` and `set_fact: orchestrator_token` (no_log on the module call).

- [ ] **Step 1: Write the three playbooks and README.**
- [ ] **Step 2: Verify** — `ansible-playbook --syntax-check` each; `make lint`.
- [ ] **Step 3: Commit** — `feat(playbooks): add configure, export_workflows and get_token playbooks`

### Task 27: Live test harness

**Files:** `tests/configure_orchestrator.yml`, `tests/cleanup_orchestrator.yml`, `tests/configs/*.yml` (one per role, every item named `aoc-test-*`, secrets with `update_secrets: false`, a workflow using `definition_file: "{{ playbook_dir }}/files/aoc-test-wait.json"`), `tests/files/aoc-test-wait.json`, `tests/auth.yml.example`, Makefile targets `live`, `live-check`, `live-cleanup`, `live-spot`.

- `tests/configure_orchestrator.yml`: like the collection playbook but `include_vars dir: configs` and vars from env: `orchestrator_hostname: "{{ lookup('env', 'ORCHESTRATOR_HOST') }}"`, username/password likewise, `orchestrator_validate_certs: "{{ lookup('env', 'ORCHESTRATOR_VERIFY_SSL') | default('false', true) | bool }}"`; `pre_tasks` fail fast when host is empty.
- `tests/cleanup_orchestrator.yml`: same configs with `orchestrator_state: absent` and `orchestrator_configuration_dispatcher_roles` reversed (Jinja `| reverse`), excluding action roles.
- Makefile: `live: ansible-playbook tests/configure_orchestrator.yml`, `live-check: … --check --diff`, `live-cleanup: ansible-playbook tests/cleanup_orchestrator.yml`.

- [ ] **Step 1: Write the files.**
- [ ] **Step 2: Verify locally** — `make lint`; syntax-check both playbooks.
- [ ] **Step 3: Run against the lab** (creds in env, user permitted): `make live` → completes; `make live` again → `changed=0`; `make live-check` → no changes; `ansible-playbook playbooks/export_workflows.yml -e orchestrator_export_projects='["aoc-test-project"]'` → file written and identical (normalized) to `tests/files/aoc-test-wait.json` except `name`; `make live-cleanup` → all `aoc-test-*` gone. Fix modules/roles for anything that fails (tests first).
- [ ] **Step 4: Commit** — `test: add live integration harness and configs`

### Task 28: Docs, changelog, release prep

**Files:** `README.md` (full: badges placeholder, requirements, install, auth incl. `module_defaults` group, token tip, error handling, register values, content tables of roles and modules with links), `docs/GETTING_STARTED.md` (adapted from the reference: directory layout, `orchestrator_configs/`, running `configure_orchestrator.yml`, tags, exclude roles, wildcard vars), `docs/API_COMPATIBILITY.md` (finalize), `CLAUDE.md`/`AGENTS.md` (sync with what was built), `changelogs/fragments/release-0.1.0.yml` (`release_summary`), `CHANGELOG.rst` generated.

- [ ] **Step 1: Write/finish the docs.**
- [ ] **Step 2: Generate changelog** — Run: `.venv/bin/antsibull-changelog release --version 0.1.0` → `CHANGELOG.rst` and `changelogs/changelog.yaml` updated, fragments consumed.
- [ ] **Step 3: Full verification** — `make lint sanity unit build install`; `ansible-doc -l kenmoini.automation_orchestrator_config` lists 33 modules; `ansible-galaxy collection verify` on the installed tarball; every `roles/*/tests/test.yml` syntax-checks.
- [ ] **Step 4: Commit and tag** — `chore(release): 0.1.0`; `git tag -a v0.1.0 -m "0.1.0"` (tag only; do not push unless asked).
