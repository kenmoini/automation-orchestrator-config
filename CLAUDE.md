# CLAUDE.md — kenmoini.automation_orchestrator_config

## Project Overview

Ansible Collection for configuration-as-code of Red Hat Automation Orchestrator (tech preview, API 1.3.1). It ships Python modules (one per API resource) and roles modeled on `redhat-cop/infra.aap_configuration`.

- **Collection FQCN:** `kenmoini.automation_orchestrator_config`
- **Version:** 0.1.0
- **License:** GPL-3.0-or-later
- **Minimum Ansible version:** 2.16.0
- **No collection dependencies** in `galaxy.yml`

## Repository Structure

```text
├── galaxy.yml                  # Collection metadata
├── meta/runtime.yml            # requires_ansible, action_groups (orchestrator)
├── plugins/
│   ├── module_utils/           # orchestrator_api.py: OrchestratorModule base class
│   ├── modules/                # 33 modules
│   └── doc_fragments/          # Shared documentation fragments (orchestrator)
├── roles/                      # 18 roles
├── playbooks/                  # configure_orchestrator, export_workflows, get_token
├── tests/
│   ├── unit/                   # pytest unit tests with mocked HTTP
│   ├── configs/                # live-test configuration (objects named aoc-test-*)
│   ├── configure_orchestrator.yml, cleanup_orchestrator.yml   # live harness
│   └── auth.yml.example        # copy to tests/auth.yml (gitignored)
├── changelogs/                 # antsibull-changelog (fragments/)
└── docs/                       # STANDARDS.md, ROLE_TEMPLATE.md, GETTING_STARTED.md, API_COMPATIBILITY.md, api/ snapshot, superpowers/ specs and plans
```

## Plugins

- All modules subclass the single `OrchestratorModule` base class in `plugins/module_utils/orchestrator_api.py`.
- Auth parameters: `orchestrator_host`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, plus `validate_certs` and `request_timeout`. Each has an `ORCHESTRATOR_*` environment fallback.
- No mutual exclusion between auth methods: `authenticate()` applies the precedence token, then client credentials, then username/password; `required_together` holds for each pair. A token overrides `ORCHESTRATOR_USERNAME`/`ORCHESTRATOR_PASSWORD` from the environment.
- Modules (33): `api`, `approval`, `approval_info`, `credential`, `credential_info`, `credential_type_info`, `execution`, `execution_cancel`, `execution_info`, `group`, `group_info`, `identity_provider`, `identity_provider_info`, `integration`, `integration_info`, `policy`, `policy_info`, `project`, `project_info`, `role`, `role_assignment`, `role_assignment_info`, `role_info`, `service_account`, `service_account_credential`, `service_account_info`, `setting`, `setting_info`, `token`, `user`, `user_info`, `workflow`, `workflow_info`.
- Short names (`project`, `group`, `workflow`), `_info` variants for reads, `api` as an escape hatch. All are listed in the `orchestrator` action group in `meta/runtime.yml`; keep it in sync when adding a module.
- Module pattern: build the desired state, `find_existing(...)` the object, then either `delete_if_needed` for `state: absent` or `create_or_update(existing, desired, path, ...)`; finish with `exit_result(changed, obj)`. `_info` modules finish with `exit_info(resources)`.
  - `full_fields=(...)`: nested configs the API needs sent whole on any change (OIDC, integration `configuration`).
  - `secret_fields=(...)`: write-only values that are never diffed or returned, only sent when `update_secrets` is true.
  - `immutable=(...)`: fields that fail the task if changed.
- Module docs come from `DOCUMENTATION`/`EXAMPLES`/`RETURN` plus the shared doc fragment.

## Roles

Roles (18): `collect_async_status`, `dispatch`, `global_vars`, `orchestrator_approval_decisions`, `orchestrator_credentials`, `orchestrator_execution_launch`, `orchestrator_groups`, `orchestrator_identity_providers`, `orchestrator_integrations`, `orchestrator_policies`, `orchestrator_projects`, `orchestrator_role_assignments`, `orchestrator_roles`, `orchestrator_service_account_credentials`, `orchestrator_service_accounts`, `orchestrator_settings`, `orchestrator_users`, `orchestrator_workflows`.

- Resource roles are named `orchestrator_<resource>` and take a list variable `orchestrator_<resource>` (exceptions: `orchestrator_execution_launch` uses `orchestrator_launch_executions`).
- Global knobs use the `orchestrator_configuration_*` prefix; per-role overrides use `orchestrator_configuration_<res>_*`.
- Default state variable: `orchestrator_state` (items may override with `state`).
- Auth variables: `orchestrator_hostname`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, `orchestrator_validate_certs`, `orchestrator_request_timeout`.
- Helper roles: `global_vars` (shared vars such as `operation_translate`), `collect_async_status` (waits for and gathers async job results; handles `orchestrator_configuration_collect_logs`, `orchestrator_configuration_role_errors`, `orchestrator_configuration_register`), `dispatch` (runs all resource roles in dependency order).
- Each role has `defaults/main.yml`, `tasks/main.yml`, `meta/main.yml`, `meta/argument_specs.yml`, `README.md`, `tests/test.yml`. `docs/ROLE_TEMPLATE.md` is the contract; `roles/orchestrator_projects` is the reference implementation. Do not improvise.
- Internal loop variables are double-underscore prefixed: `__orchestrator_<resource>_item`.
- Identifying-key rule: the module task, loop label and README table use the resource's identifying key (`username` for users, `identifier` for service account credentials), not always `name`, and that key must be captured by `collect_async_status/tasks/handle_error.yml`.
- A new role must be added to the dispatcher list in `roles/dispatch/defaults/main.yml`.
- Dispatch order (`roles/dispatch/defaults/main.yml`, `vars/main.yml`, `meta/argument_specs.yml` and the dispatch README table must agree): settings, groups, identity_providers, users, projects, policies, roles, service_accounts, role_assignments, credentials, integrations, service_account_credentials, workflows, execution_launch, approval_decisions. Groups precede identity providers (group mappings) and service accounts precede role assignments (service-account principals). `tests/cleanup_orchestrator.yml` runs the list reversed.

### Async Task Pattern

1. Loop over the resource list with `async` and `poll: 0`.
2. Register the async job results.
3. Include `collect_async_status` to wait and gather results.
4. An `always` block cleans up async result files.
5. Check mode uses `ansible_check_mode | ternary(0, 1000)` for the async value.

## Coding Standards

See `docs/STANDARDS.md`.

- YAML files use `.yml`, 2-space indent, start with `---` and end with `...`.
- Spaces around Jinja variables: `{{ var }}`.
- Underscores in names; variable pattern `^[a-z_][a-z0-9_]*$`; task names prefixed `"{stem} | "`.
- `ansible-lint` profile `production`.
- Python: `black` and `flake8` (line length 160). Non-empty Python files start with the standard header (coding line, copyright, GPL line, SPDX line, then `from __future__ import absolute_import, division, print_function` and `__metaclass__ = type`). `__init__.py` files stay empty.
- Markdown: `markdownlint-cli2`, ATX headings, fenced code blocks.

## Dev Commands

- `make venv`: create `.venv` with the tooling.
- `make lint`: all pre-commit hooks.
- `make pytest`: unit tests with plain pytest on a synced copy; the in-sandbox runner.
- `make sanity` / `make unit`: `ansible-test` sanity and unit tests; need ansible-test to write to `/tmp`, so they run in CI in restricted sandboxes.
- `make build`, `make install`: build the tarball into `build/` and install it into `build/install` (never into the `make link` symlink path).
- `make live`, `make live-check`, `make live-cleanup`: apply, preview and remove `tests/configs` against a lab (see below).
- `make changelog`: lint changelog fragments.

## Changelogs

`antsibull-changelog` with fragments in `changelogs/fragments/`. Every user-visible change needs a fragment; releases run `antsibull-changelog release --version X.Y.Z`.

## Lab testing and credentials

- `tests/auth.yml` (copy `tests/auth.yml.example`) holds lab credentials. It is gitignored and must never be committed; `ORCHESTRATOR_HOST/USERNAME/PASSWORD` environment variables work too.
- Live runs touch only objects named `aoc-test-*`. `tests/configs` set `update_secrets: false` so the second run reports `changed=0`.
- Unverified API assumptions are tracked in `docs/API_COMPATIBILITY.md`; update it after live runs.

## Notes

- Never commit credentials or anything under `build/`.
- `state: absent` deletes permanently; there is no delete guard.
