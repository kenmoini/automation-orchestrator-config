# AGENTS.md — kenmoini.automation_orchestrator_config

## Context

This repository is an Ansible Collection (`kenmoini.automation_orchestrator_config`) that provides modules and roles for managing Red Hat Automation Orchestrator (tech preview, API 1.3.1) resources as code. See `CLAUDE.md` for the layout and `docs/ROLE_TEMPLATE.md` for the role contract.

## Code Review Guidelines

When reviewing pull requests to this collection, verify the following:

### Module Compliance

- Modules subclass `OrchestratorModule` and use the shared auth doc fragment; a new module is listed in the `orchestrator` action group in `meta/runtime.yml`.
- Resource modules use `find_existing`, then `delete_if_needed` or `create_or_update`, and end with `exit_result`; `_info` modules end with `exit_info`.
- Write-only values are declared in `secret_fields`, honor `update_secrets`, and never appear in return values or logs. Nested configs the API needs whole use `full_fields`.
- Check mode must not change anything; one-shot actions are skipped in check mode.
- `DOCUMENTATION`, `EXAMPLES` and `RETURN` are complete, with `version_added` set; the Python header and `black`/`flake8` (line length 160) rules are followed.
- New modules have unit tests in `tests/unit/plugins/modules/` with mocked HTTP covering create, update, no-change, delete and check mode.

### Role Structure Compliance

- New roles follow `docs/ROLE_TEMPLATE.md`: `defaults/main.yml`, `tasks/main.yml`, `meta/main.yml`, `meta/argument_specs.yml`, `README.md`, `tests/test.yml` and `tests/configs/`.
- `meta/main.yml` declares the dependency on `global_vars`.
- `defaults/main.yml` initializes the resource list to `[]` and includes the standard variables for secure logging, async retries, async delay, loop delay, enforce defaults and `orchestrator_configuration_async_dir`.
- Role names use the `orchestrator_` prefix.
- The identifying key (not always `name`) is used in the module task, loop label and README, and is captured by `collect_async_status/tasks/handle_error.yml` (`name`, `username`, `project`, `workflow`, `role`, `user`, `group`, `service_account`, `identifier`, `key`); a new key must be added there
- Roles whose items may carry secrets (users, credentials, identity providers, service account credentials, execution launch) default secure logging to `true`; flag any such role defaulting to `false`

### Async Task Pattern

All resource roles must follow the async block pattern:

1. A block with `ansible_async_dir` and `no_log` set
2. The module task loops over the resource list with `async` and `poll: 0`
3. A "Flag for errors (check mode only)" task using `ansible.builtin.set_fact` to set `error_flag`
4. An `include_role` of `kenmoini.automation_orchestrator_config.collect_async_status` to wait for results, passing `cas_async_delay`, `cas_async_retries`, `cas_secure_logging`, `cas_job_async_results_item`, `cas_register_subvar`, `cas_error_list_var_name`, and `cas_object_label`
5. An `always` block that cleans up async result files via `ansible.builtin.async_status` with `mode: cleanup`

### Variable Naming

- Internal loop variables use double-underscore prefix: `__orchestrator_<res>_item`
- Async result variables follow: `__orchestrator_<res>_job_async` and `__orchestrator_<res>_job_async_results_item`
- Variable names must match pattern `^[a-z_][a-z0-9_]*$`
- Loop variable prefix must match `^(__|{role}_)`

### Task Naming

- Task names must follow the `"{stem} | "` prefix pattern enforced by ansible-lint
- Example: `"Managing Projects"` for the projects role task

### Authentication Parameters

- Modules take `orchestrator_host`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, `validate_certs`, `request_timeout`
- Roles pass `orchestrator_hostname`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, `orchestrator_validate_certs`, `orchestrator_request_timeout` with `default(omit, true)` fallbacks
- No mutual exclusion between auth methods; `authenticate()` applies the precedence token > client credentials > username/password (`required_together` for each pair)

### Dispatch Integration

- New roles must be added to the dispatcher list in `roles/dispatch/defaults/main.yml`, in dependency order
- Current order: settings, groups, identity_providers, users, projects, policies, roles, service_accounts, role_assignments, credentials, integrations, service_account_credentials, workflows, execution_launch, approval_decisions (keep `vars/main.yml`, `meta/argument_specs.yml` and the dispatch README table in sync)
- The entry must specify `role`, `var`, and `tags` at minimum, and the dispatch README table must be updated

### Documentation

- Role `README.md` must include: description, variable table (with defaults, required flag, description, example), data structure documentation with YAML examples, and a license link
- `meta/argument_specs.yml` must fully describe all role options with types and defaults
- New roles and modules appear in the tables of the top-level `README.md`
- Behavior that depends on an unconfirmed API assumption is recorded in `docs/API_COMPATIBILITY.md`

### Changelog

- Every feature or bugfix PR must include a changelog fragment in `changelogs/fragments/`
- Fragment file must be valid YAML with `...` document end marker
- Use appropriate category: `minor_changes`, `major_changes`, `bugfixes`, `breaking_changes`, etc.

### Testing

- Unit tests cover new module behavior; `make pytest` and `make lint` pass, and CI runs `ansible-test sanity` and `units`
- New roles include test data in `roles/<role>/tests/configs/` and a `test.yml` playbook, plus an entry in `tests/configs/` and the live harness when applicable
- Live test objects are named `aoc-test-*`; `tests/auth.yml` and any credentials are never committed

### Linting Standards

- YAML files must use `.yml` extension
- YAML files must end with `...` (document-end marker)
- 2-space indentation, no trailing whitespace
- Jinja2 variables must have spaces: `{{ var }}` not `{{var}}`
- ansible-lint profile: `production`
- Python code: `black` formatting (line length 160), `flake8` compliance

## PR Submission

When submitting PRs:

1. Run `make lint` (pre-commit) and `make pytest` before pushing
2. Include a changelog fragment
