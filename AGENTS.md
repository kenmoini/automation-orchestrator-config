# AGENTS.md — kenmoini.automation_orchestrator_config

## Project Overview

Ansible Collection for configuration-as-code of Red Hat Automation Orchestrator. It ships Python modules (one per API resource) and roles modeled on `redhat-cop/infra.aap_configuration`.

- **Collection FQCN:** `kenmoini.automation_orchestrator_config`
- **License:** GPL-3.0-or-later
- **Minimum Ansible version:** 2.16.0
- **No collection dependencies** in `galaxy.yml`

## Repository Structure

```text
├── galaxy.yml                  # Collection metadata
├── meta/runtime.yml            # requires_ansible, action_groups (orchestrator)
├── plugins/
│   ├── module_utils/           # orchestrator_api.py: OrchestratorModule base class
│   ├── modules/                # One short-named module per resource, *_info modules, api
│   └── doc_fragments/          # Shared documentation fragments
├── roles/                      # orchestrator_<resource> roles plus global_vars, collect_async_status, dispatch
├── tests/unit/                 # pytest unit tests (requirements.txt)
├── changelogs/                 # antsibull-changelog (fragments/)
└── docs/                       # STANDARDS.md, api/ snapshot, superpowers/ specs and plans
```

## Plugins

- All modules subclass the single `OrchestratorModule` base class in `plugins/module_utils/orchestrator_api.py`.
- Auth parameters: `orchestrator_host`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, plus `validate_certs` and `request_timeout`. Each has an `ORCHESTRATOR_*` environment fallback.
- Precedence: token, then client credentials, then username/password.
- Modules use short names (`project`, `group`, `workflow`), `_info` variants for reads, and an `api` module as an escape hatch. All are listed in the `orchestrator` action group in `meta/runtime.yml`; keep it in sync when adding a module.
- Module docs come from `DOCUMENTATION`/`EXAMPLES`/`RETURN` plus shared doc fragments.

## Roles

- Resource roles are named `orchestrator_<resource>` and take a list variable of the same name, `orchestrator_<resource>`.
- Global knobs use the `orchestrator_configuration_*` prefix; per-role overrides use `<role_name>_*`.
- Default state variable: `orchestrator_state` (items may override with `state`).
- Auth variables: `orchestrator_hostname`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, `orchestrator_validate_certs`, `orchestrator_request_timeout`.
- Helper roles: `global_vars` (shared vars such as `operation_translate`), `collect_async_status` (waits for and gathers async job results), `dispatch` (runs all resource roles in dependency order).
- Each role has `defaults/main.yml`, `tasks/main.yml`, `meta/main.yml`, `meta/argument_specs.yml`, `README.md`.
- Internal loop variables are double-underscore prefixed: `__orchestrator_<resource>_item`.

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

`make venv`, `make lint`, `make sanity`, `make unit`, `make build` (the Makefile arrives in a later task).
`make pytest` runs the unit tests with plain pytest on the synced copy (use it where ansible-test cannot run, e.g. sandboxes).

## Changelogs

`antsibull-changelog` with fragments in `changelogs/fragments/`. Every user-visible change needs a fragment.

## Notes

- Never commit credentials; `tests/auth.yml` is gitignored.
- Live lab spot-checks use `ORCHESTRATOR_*` env vars and objects named `aoc-test-*` only.
