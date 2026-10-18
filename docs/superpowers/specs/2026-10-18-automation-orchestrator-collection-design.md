# Plan: `kenmoini.automation_orchestrator_config` — Ansible Collection for Automation Orchestrator

## Context

Red Hat's Automation Orchestrator (tech preview in AAP 2.7) exposes a REST API at `/api/v1`
(spec title "Syntara API", v1.3.1, OpenAPI 3.1, 126 endpoints, 259 schemas). The user wants a
configuration-as-code Ansible Collection for it, modeled on `redhat-cop/infra.aap_configuration`
(devel). The repo `/Users/kenmoini/Development/automation_orchestrator_configuration` is empty.

The reference collection is **roles only**: each role wraps an idempotent module from Red Hat's
`ansible.controller` / `ansible.platform` / `ansible.hub` / `ansible.eda` collections. **No such module
collection exists for Orchestrator**, so this collection must ship both the modules and the roles.

Research artifacts (session-local, not committed):
- OpenAPI spec: `/tmp/claude-501/ao-spec/openapi.json`
- Reference clone: `/tmp/claude-501/aap_config_ref`

## Decisions (user-confirmed)

| Topic | Decision |
|---|---|
| Architecture | Modules + roles in **one** collection |
| FQCN | `kenmoini.automation_orchestrator_config` |
| Role / var prefix | `orchestrator_` (roles `orchestrator_projects`, vars `orchestrator_projects`, auth `orchestrator_hostname` …) |
| Module names | Short: `.project`, `.workflow`, `.credential`, … (FQCN disambiguates) |
| Scope v0.1.0 | All config resources + action roles (executions, approvals) + dispatch/helpers |
| Workflows | Item takes `definition_file` (JSON/YAML path) **or** `workflow_definition` (inline dict); optional `publish: true`; `is_import` passthrough; export playbook |
| License | GPL-3.0-or-later |
| Testing | Unit (pytest, mocked HTTP) + `ansible-test sanity` in CI; live tests are a documented **manual** playbook against the lab |
| Delete guard | None. `state: absent` deletes (workflows cascade versions+executions; projects hard-delete). Match the reference; warn in docs |
| Secrets | `update_secrets: true` by default (credential inputs, IdP client_secret) and `update_password: on_create` for users. Items supplying secrets report changed each run; `tests/configs` set `update_secrets: false` so the idempotency run is `changed=0` |
| Lab spot-checks | Allowed during implementation with creds from `ORCHESTRATOR_HOST/USERNAME/PASSWORD` env vars: read calls plus create/delete of objects named `aoc-test-*`. Never committed |

## Key API facts that shape the design

- Auth: Bearer JWT. `POST /auth/login` (username/password) → `{access_token, expires_in}`; or
  `POST /auth/token` form `grant_type=client_credentials` (service accounts). Every endpoint,
  including `/version`, needs auth.
- Pagination: cursor-based (`limit` ≤ 100, `cursor`; response `{next, prev, total?, resources}`).
- IDs are UUIDs. Updates are PATCH. Deletes return 204. Errors are RFC 9457 problem-details.
- `name=` server filter exists for projects, roles, policies, service_accounts, users
  (`username=`); **not** for workflows, credentials, groups, integrations, identity_providers →
  client-side match after paginating. Workflows are listed per project at
  `/projects/{id}/workflows`; credentials at `/projects/{id}/credentials`.
- Secrets are write-only: credential `inputs`, OIDC `client_secret`, SA `client_secret` (one-time).
- Workflow `PATCH` with `workflow_definition` does server-side change detection and bumps
  `current_version`; publishing is `POST /workflows/{id}/versions/{v}/publish`.
- `PUT /users/{id}/groups` declaratively sets memberships. `UserCreate.group_names` on create.
- Role assignment = `role_name` + exactly one of `principal_id` | `group_id`, optional `project_id`;
  list filters `principal_name`, `role_name`, `project_id` make it idempotent.
- `is_builtin` objects cannot be deleted; `expected_version` optimistic locking on settings/workflows.

## Deviations from the reference (my calls)

- `meta_dependency_check` role is dropped: modules live in this collection; nothing external to verify.
- Group membership is managed from the **user** side (`groups:` list → `PUT /users/{id}/groups`),
  not from the group side, so there is one source of truth. The `group` module manages name/description only.
- Default-state var is `orchestrator_state` (reference: `platform_state`).
- Modules re-authenticate per invocation when given username/password. For large runs the README
  recommends obtaining a token once with the `token` module and setting `orchestrator_token`.
- `meta/runtime.yml` defines an action group `orchestrator` so users can set
  `module_defaults: group/kenmoini.automation_orchestrator_config.orchestrator` for auth.

## Builder-check resolutions (settled by me after an independent review of this plan against the spec)

- **Service account credentials are not nameable** (`identifier` is server-generated). `state: present`
  without `identifier` means "ensure at least one *active* credential exists" (idempotent; secret returned
  only on the creating run). `identifier` targets an existing one; `state: rotated` always issues a new
  secret. Role stays in the dispatch chain; README says to `register` and store the secret externally.
- **One-shot actions on declarative modules** (`integration.refresh`/`validate`, `identity_provider.test`):
  run whenever `true`, skipped in check mode. `validate`/`test` never report changed (result returned in
  `validation`/`test_result`); `refresh` reports changed only if the server reports `updated_count > 0`.
- **LLM model / MCP tool rows**: spec is contradictory on whether `/refresh` covers `llm_provider`.
  Plan: when `models:` or `tools:` is given and the integration has no rows yet, call
  `POST /integrations/discover` (on create, feeding `discovered_models`/`discovered_tools` into the create
  body) or `/refresh` (mcp_server). This contacts the external provider during apply; documented.
  Confirm against the lab in phase 4.
- **User groups**: on create, omitting `groups` lets the server apply its default (`users` group); on update,
  omitting leaves memberships untouched. The declarative set only replaces `manual` memberships and
  preserves `idp`-sourced ones (`membership_sources`).
- **IdP `group_mapping_entries`**: module accepts `mapped_group` (name) or `mapped_group_id` (UUID) and
  resolves names; diff compares the resolved form. `redirect_uri` stays a plain required field.
- **Full-object PATCH for nested configs**: `OIDCConfigurationUpdate` requires `issuer_url`, `client_id`,
  `redirect_uri` on every PATCH, and integration `configuration` needs the `integration_type`
  discriminator. `create_or_update` gets a `full_fields=()` hook; those modules send the merged
  `configuration` whole whenever any key in it changed.
- **`definition_file` is read controller-side** in the role via `lookup('ansible.builtin.file') | from_yaml`
  (JSON is valid YAML), so paths resolve against the playbook/config dir and templating is possible with
  `lookup('template')`. The module also accepts `definition_file` for direct use (module-side path).
  Export playbook writes under `orchestrator_export_dir` (default `./orchestrator_exports/<project>/<name>.json`).
- **Workflow export**: `GET /workflows/{id}/versions/{v}/export` has no response schema. `workflow_info`
  uses `GET /workflows/{id}` (`WorkflowReadWithVersion.version.workflow_definition`) and
  `GET /workflows/{id}/versions/{v}` instead; `/export` is not relied upon.
- **Cheaper name lookups**: use `GET /groups/directory?name=` and `GET /users/directory?username=`
  (exact client-side match on the result) before falling back to full pagination.
- **Executions list has no filters**: `execution_info` is by `id`, or by `workflow` with a bounded
  `limit` and `sort=-created_at`; no full-table scans by default.
- **Role-name shadowing**: `role_assignment` takes `role_name`; a UUID is resolved back to a name. System-
  and project-scoped roles may share a name; module docs note the server decides precedence.
- **Soft deletes** (users, groups, service accounts, IdPs): whether a deleted name can be re-created is
  unknown; checked against the lab in phase 3 and recorded in `docs/API_COMPATIBILITY.md`.
- **Schema facts to honor**: `GroupCreate`/`UserCreate` have no `labels`; `ServiceAccountRead.labels` is
  read-only; `WorkflowRead.is_enabled` is not settable; `PublishVersionRequest` accepts an inline
  `workflow_definition` (save+publish in one call when `publish: true` and the definition changed);
  `UserUpdate` has no `group_names`.

## Repository layout

```
galaxy.yml                      # namespace kenmoini, name automation_orchestrator_config, 0.1.0, GPL-3.0-or-later
meta/runtime.yml                # requires_ansible ">=2.16.0", action_groups.orchestrator
LICENSE  README.md  CLAUDE.md  AGENTS.md  CONTRIBUTING.md  CHANGELOG.rst
Makefile                        # venv (uv), lint, sanity, unit, build, install, live
.gitignore .pre-commit-config.yaml .ansible-lint .yamllint .black.cfg .flake8 .markdownlint-cli2.yaml
.github/workflows/pre-commit.yml  .github/workflows/release.yml  .github/ISSUE_TEMPLATE/ PULL_REQUEST_TEMPLATE.md
changelogs/config.yaml  changelogs/fragments/
docs/GETTING_STARTED.md  docs/STANDARDS.md  docs/API_COMPATIBILITY.md (tested against API 1.3.1)
plugins/
  doc_fragments/auth.py
  module_utils/orchestrator_api.py      # OrchestratorModule base class + HTTP client
  modules/*.py                          # see module table
playbooks/configure_orchestrator.yml  playbooks/export_workflows.yml  playbooks/get_token.yml
roles/<role>/{defaults,tasks,meta,tests}/… + README.md
tests/unit/plugins/module_utils/  tests/unit/plugins/modules/  tests/unit/requirements.txt
tests/sanity/ignore-2.16.txt … ignore-2.20.txt (only if needed)
tests/configure_orchestrator.yml  tests/configs/*.yml  tests/auth.yml.example  (live, manual)
```

## Plugins

### `plugins/module_utils/orchestrator_api.py`

`class OrchestratorModule(AnsibleModule)` — stdlib + `ansible.module_utils.urls` only.

- **Auth params** (shared via `doc_fragments/auth.py`), each with env fallback:
  `orchestrator_host` (`ORCHESTRATOR_HOST`), `orchestrator_username` (`ORCHESTRATOR_USERNAME`),
  `orchestrator_password` (`ORCHESTRATOR_PASSWORD`, no_log), `orchestrator_token`
  (`ORCHESTRATOR_TOKEN`, no_log), `orchestrator_client_id` / `orchestrator_client_secret`
  (`ORCHESTRATOR_CLIENT_ID/SECRET`, for service accounts), `validate_certs`
  (`ORCHESTRATOR_VERIFY_SSL`, default true), `request_timeout` (default 10).
  No mutual exclusion; `authenticate()` applies precedence token > client credentials > username/password; `required_together` for each pair.
- `authenticate()`: login or client-credentials; stores bearer header. On 401 mid-run, re-login once.
- `request(method, path, query=None, data=None, expect=(200,201,204))` → parsed JSON; parses
  RFC 9457 body into `fail_json(msg=detail, code=..., status=...)`; honors `Retry-After` on 429 (bounded).
- `get_all(path, query=None)` → follows `next` cursor with `limit=100`.
- `get_one_by_name(path, name, *, name_field="name", query=None, scope_label=None)` → uses server
  filter when the endpoint supports it (table in module_utils), else client-side exact match;
  fails on >1 match with a clear message.
- `resolve_id(kind, value, **scope)` → accepts a UUID or a name; kinds: project, credential_type,
  credential(project), user, group, role(project), policy(project), integration, identity_provider,
  service_account(project), workflow(project).
- `create_or_update(existing, desired, path, *, immutable=(), secret_fields=(), update_secrets=True)`
  → computes a shallow diff over keys the caller provided (omit-unset semantics), supports
  `check_mode` and `--diff`, PATCHes only when changed; returns `(changed, obj)`.
- `delete_if_needed(existing, path)`; refuses `is_builtin` with a clear error.
- `full_fields=()` option on `create_or_update`: nested dicts that the API requires whole (IdP/integration `configuration`) are sent merged in full when any sub-key differs.
- `exit_json` always includes `id` and the final object (secrets stripped).

### Modules (`plugins/modules/`)

Pattern for every resource module: `name` (+ `new_name` where the API allows rename), `description`,
`labels`, resource fields, scoping (`project`), `state: present|absent` (+ `exists` where useful).
All accept names or UUIDs for references. `_info` modules take optional `name`/filters and return `resources`.

| Module | Endpoints | Notable params / behavior |
|---|---|---|
| `token` | `POST /auth/login`, `/auth/token` | returns `access_token`, `expires_in`; `no_log`; never changed=false (mirrors `ansible.platform.token`) |
| `project` / `project_info` | `/projects` | `name`, `new_name`, `description`, `labels` |
| `group` / `group_info` | `/groups` | name/description only (see deviation) |
| `user` / `user_info` | `/users`, `PUT /users/{id}/groups` | `username`, `password` (min 14), `update_password: on_create|always`, `email`, `first_name`, `last_name`, `is_enabled`, `groups: [names]` (declarative set; omit = untouched). Federated users: metadata/groups only |
| `policy` / `policy_info` | `/policies` | `statements[]{effect,actions,scope,conditions}`, optional `project` |
| `role` / `role_info` | `/roles` | `policies: [names]`, optional `project` |
| `role_assignment` / `role_assignment_info` | `/role_assignments` | `user` xor `group`, `role`, optional `project`; idempotent via list filters |
| `credential_type_info` | `/credential_types` | read-only; resolve by name |
| `credential` / `credential_info` | `/credentials`, `/projects/{id}/credentials` | `credential_type` (name), `project` (required), `inputs` (no_log), `enabled`, `update_secrets` (default true → sending inputs reports changed) |
| `integration` / `integration_info` | `/integrations` + `/projects/{pid}`, `/models`, `/tools`, `/refresh`, `/validate` | `integration_type` (mcp_server/llm_provider/ansible_automation_platform), `configuration` (dict, `integration_type` injected), `management_credential` (+`management_credential_project`), `enabled`, `scope`, `projects: [names]` (reconcile assign/unassign), `models: [{name|model_id, enabled, is_default}]`, `tools: [{name, enabled}]`, `refresh: bool`, `validate: bool` |
| `identity_provider` / `identity_provider_info` | `/identity_providers`, `/test` | `configuration` (OIDC dict), `enabled`, `update_secrets`, `test: bool` |
| `service_account` / `service_account_info` | `/service_accounts`, `/enable`, `/disable` | `project`, `state: present|absent|enabled|disabled` |
| `service_account_credential` | `/service_accounts/{id}/credentials` (+rotate/enable/disable) | `service_account`, `project`, `identifier` (targets existing), `grace_period_seconds`, `expires_at`, `state: present|absent|rotated|enabled|disabled`; returns one-time `client_secret` (no_log) — documented as register-and-store |
| `setting` / `setting_info` | `/settings`, `/settings/{key}` | `name`+`value` or `settings: dict`; diff against current `value`; bulk PATCH when dict |
| `workflow` / `workflow_info` | `/workflows`, `/projects/{id}/workflows`, `/versions`, `/publish`, `/unpublish`, `/export` | `project` (required), `workflow_definition` xor `definition_file` (JSON or YAML), `is_import`, `change_description`, `publish: bool`, `unpublish: bool`, `state`. Create requires a definition; update without one is metadata-only. Local diff of normalized definition vs `GET /versions/{current_version}` for accurate `changed`/check mode; server bumps version on change; publish if `published_version_number != current_version`. `workflow_info` has `include_definition`/`version` for export |
| `execution` / `execution_info` / `execution_cancel` | `/executions`, `/cancel`, `/retry`, `/activities` | `workflow`, `project`, `trigger_node_id` (auto-picked when the definition has exactly one trigger), `input_data`, `use_published`, `wait`, `interval`, `timeout`; terminal states from `ExecutionStatus` enum |
| `approval` / `approval_info` | `/approvals`, `PATCH /approvals/{id}` | `approval_id` or (`execution` + `name`), `decision: approved|rejected`, `notes` |
| `api` | any | `endpoint`, `method`, `data`, `query_params`; escape hatch like `ansible.controller.api` |

## Roles

Each resource role follows the reference contract exactly (see `roles/controller_organizations` in the
clone for the template): `defaults/main.yml` (list var `[]`; `orchestrator_configuration_<res>_secure_logging`,
`_async_retries`, `_async_delay`, `_loop_delay`, `_enforce_defaults`; `orchestrator_configuration_async_dir`),
`tasks/main.yml` (block → module with `loop`, `async`/`poll: 0`, check-mode `error_flag`,
`include_role: collect_async_status`, `always` async cleanup), `meta/main.yml` (dep `global_vars`),
`meta/argument_specs.yml`, `README.md` (variable tables, data-structure table, JSON + YAML examples,
playbook example), `tests/test.yml` + `tests/configs/<res>.yml`.

Shared auth passed to every module: `orchestrator_host: "{{ orchestrator_hostname | default(omit, true) }}"`,
`orchestrator_username/password/token/client_id/client_secret`, `validate_certs: "{{ orchestrator_validate_certs | default(omit) }}"`,
`request_timeout: "{{ orchestrator_request_timeout | default(10, true) }}"`.
Item `state` defaults to `orchestrator_state | default('present')`.

| Role | List var | Dispatch order / tag |
|---|---|---|
| `orchestrator_settings` | `orchestrator_settings` (dict or list) | 1 `settings` |
| `orchestrator_groups` | `orchestrator_groups` | 2 `groups` |
| `orchestrator_identity_providers` | `orchestrator_identity_providers` | 3 `identity_providers` |
| `orchestrator_users` | `orchestrator_users` | 4 `users` |
| `orchestrator_projects` | `orchestrator_projects` | 5 `projects` |
| `orchestrator_policies` | `orchestrator_policies` | 6 `policies` |
| `orchestrator_roles` | `orchestrator_roles` | 7 `roles` |
| `orchestrator_service_accounts` | `orchestrator_service_accounts` | 8 `service_accounts` |
| `orchestrator_role_assignments` | `orchestrator_role_assignments` | 9 `role_assignments` |
| `orchestrator_credentials` | `orchestrator_credentials` | 10 `credentials` |
| `orchestrator_integrations` | `orchestrator_integrations` | 11 `integrations` |
| `orchestrator_service_account_credentials` | `orchestrator_service_account_credentials` | 12 `service_account_credentials` |
| `orchestrator_workflows` | `orchestrator_workflows` | 13 `workflows` |
| `orchestrator_execution_launch` | `orchestrator_launch_executions` | 14 `execution_launch` |
| `orchestrator_approval_decisions` | `orchestrator_approval_decisions` | 15 `approval_decisions` |

Helper roles:
- `global_vars` — `operation_translate` (copied, add `enabled`/`disabled`/`rotated`).
- `collect_async_status` — ported from the reference; `cas_*` interface unchanged; error list var
  `orchestrator_configuration_role_errors`; register support via `orchestrator_configuration_register`;
  `handle_error.yml` captures `name`, `username`, `project`, `workflow`, `role`, `user`, `group`.
- `dispatch` — `orchestrator_configuration_dispatcher_roles` (ordered table above),
  `orchestrator_configuration_dispatcher_exclude_roles`, `dispatch_include_wildcard_vars` +
  `include_wildcard_vars.yml` + `vars/main.yml` list `orchestrator_configuration_all_vars`,
  final "Display errors and fail" task — all ported from `roles/dispatch` in the clone.

Global knobs (mirror `aap_configuration_*`): `orchestrator_configuration_secure_logging`,
`_async_retries` (50), `_async_delay` (1), `_loop_delay` (0), `_async_dir`, `_enforce_defaults`,
`_collect_logs`, `_register`, `orchestrator_state`.

## Playbooks

- `playbooks/configure_orchestrator.yml` — include_vars from `orchestrator_configs/` dir then `dispatch` (mirrors `configure_aap.yml`).
- `playbooks/export_workflows.yml` — `workflow_info` with `include_definition` → writes `<project>/<name>.json` files consumable by `definition_file`.
- `playbooks/get_token.yml` — `token` module → prints/sets `orchestrator_token`.

## Tooling & CI

- `Makefile`: `venv` (`uv venv .venv --python 3.12`; installs ansible-core, ansible-lint, antsibull-changelog,
  pytest, pytest-mock, black, flake8, pre-commit, yamllint), `lint` (pre-commit all), `sanity`
  (`ansible-test sanity --venv` from a `build/ansible_collections/kenmoini/automation_orchestrator_config`
  symlink, gitignored), `unit` (`ansible-test units --venv` or pytest), `build`, `install`, `live`
  (runs `tests/configure_orchestrator.yml` reading creds from `ORCHESTRATOR_*` env or gitignored `tests/auth.yml`).
- `.ansible-lint`: `profile: production`, `offline: true`, `loop_var_prefix: "^(__|{role}_)"`,
  `var_naming_pattern`, `task_name_prefix: "{stem} | "`, enable `args`, `role-argument-spec`, `name[prefix]`.
- `.pre-commit-config.yaml`: pre-commit-hooks, markdownlint-cli2, black (len 160), flake8 (len 160), ansible-lint, antsibull-changelog lint.
- `.github/workflows/pre-commit.yml`: lint + `ansible-test sanity` + `ansible-test units` on py 3.11–3.13 against ansible-core 2.16–2.20 matrix (subset to keep it fast).
- `changelogs/config.yaml` copied from reference (title changed); every feature commit adds a fragment.
- `CLAUDE.md`/`AGENTS.md`: adapted from the reference, documenting the module+role contract above.

## Implementation phases (each ends green: lint + sanity + unit)

1. **Scaffold** — galaxy.yml, runtime.yml, LICENSE, README skeleton, tooling configs, Makefile, CI, changelog config, `global_vars`, CLAUDE.md/AGENTS.md. Verify `make venv lint sanity` on an empty collection.
2. **module_utils + `token` + `api`** (TDD) — unit tests for auth precedence/env fallback, login & client-credentials flows, 401 retry, cursor pagination, RFC 9457 error mapping, `get_one_by_name` server vs client filtering, `create_or_update` diff/check/diff-mode, secret handling.
3. **Identity & RBAC modules** — `project`, `group`, `user`, `policy`, `role`, `role_assignment` (+ `_info`). Unit tests per module (mock `request`).
4. **Content modules** — `credential_type_info`, `credential`, `integration`, `identity_provider`, `service_account`, `service_account_credential`, `setting` (+ `_info`).
5. **Workflow & action modules** — `workflow`, `workflow_info`, `execution`, `execution_info`, `execution_cancel`, `approval`, `approval_info`.
6. **Roles** — `collect_async_status`, 15 resource/action roles, `dispatch`; each with README, argument_specs, `tests/test.yml`, `tests/configs/`.
7. **Playbooks, docs, live runbook** — `configure_orchestrator.yml`, `export_workflows.yml`, `get_token.yml`, `tests/configs/*.yml` covering every role, `docs/GETTING_STARTED.md`, `docs/API_COMPATIBILITY.md`, README content tables, changelog fragment, `0.1.0` tag prep.

## Verification

- `make lint` → pre-commit clean (ansible-lint production profile, black, flake8, markdownlint).
- `make sanity` → `ansible-test sanity --venv` passes with no new ignore entries.
- `make unit` → pytest green; module_utils ≥ 90% line coverage.
- `ansible-galaxy collection build && ansible-galaxy collection install *.tar.gz` succeeds; `ansible-doc kenmoini.automation_orchestrator_config.workflow` renders.
- Each role's `tests/test.yml` passes `ansible-playbook --syntax-check`; dispatch role syntax-checks with all vars defined.
- **Manual live run** (user-executed, creds via `ORCHESTRATOR_*` env): `make live` applies `tests/configs/` to the lab instance; a second run reports `changed=0` (test configs set `update_secrets: false`; `refresh`/`validate`/`test` flags left unset); `--check` run reports no changes; `export_workflows.yml` round-trips a workflow created from `definition_file`; `make live-cleanup` removes all `aoc-test-*` objects.
- **Builder spot-checks during implementation** (allowed by user): confirm export shape, model/tool row population, and soft-delete name reuse; findings recorded in `docs/API_COMPATIBILITY.md`.

## Out of scope for 0.1.0

Files API, admin session revocation, authz introspection (`can_i`/`who_can`), AAP proxy lookups
(available through the `api` module), websocket tickets, OIDC browser flows, `setup_aap_oidc` convenience endpoint.
