# kenmoini.automation_orchestrator_config

<!-- Badges: add the CI status badge here once the GitHub Actions workflow is published. -->

Configuration as code for Red Hat Automation Orchestrator (tech preview, API 1.3.1). The collection is modeled on `infra.aap_configuration` and ships both the Python modules for every API resource and the roles that manage those resources from plain variable lists, so a whole instance can be described in YAML and applied idempotently.

## Requirements

- ansible-core >= 2.16
- Python 3.x on the controller (modules run on the controller; they only use the Ansible-bundled libraries)
- No collection dependencies

## Installation

```bash
ansible-galaxy collection install kenmoini.automation_orchestrator_config
```

Or in a `requirements.yml`:

```yaml
---
collections:
  - name: kenmoini.automation_orchestrator_config
...
```

```bash
ansible-galaxy collection install -r requirements.yml
```

New to the collection? Start with [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Authentication

Roles take the `orchestrator_*` variables below and pass them to the modules. Modules take the parameters directly and fall back to environment variables.

| Module parameter | Role variable | Environment variable |
| --- | --- | --- |
| `orchestrator_host` | `orchestrator_hostname` | `ORCHESTRATOR_HOST` |
| `orchestrator_username` | `orchestrator_username` | `ORCHESTRATOR_USERNAME` |
| `orchestrator_password` | `orchestrator_password` | `ORCHESTRATOR_PASSWORD` |
| `orchestrator_token` | `orchestrator_token` | `ORCHESTRATOR_TOKEN` |
| `orchestrator_client_id` | `orchestrator_client_id` | `ORCHESTRATOR_CLIENT_ID` |
| `orchestrator_client_secret` | `orchestrator_client_secret` | `ORCHESTRATOR_CLIENT_SECRET` |
| `validate_certs` | `orchestrator_validate_certs` | `ORCHESTRATOR_VERIFY_SSL` |
| `request_timeout` | `orchestrator_request_timeout` | (none; default 10) |

Precedence: token, then client credentials (client ID and secret), then username and password.

Instead of passing the parameters to every task, set them once with the action group:

```yaml
- name: Use the Orchestrator modules
  hosts: localhost
  gather_facts: false
  module_defaults:
    group/kenmoini.automation_orchestrator_config.orchestrator:
      orchestrator_host: orchestrator.example.com
      orchestrator_token: "{{ orchestrator_token }}"
  tasks:
    - name: Create a project
      kenmoini.automation_orchestrator_config.project:
        name: my-project
```

Tip for large runs: with username/password or client credentials every module call authenticates again. Request a token once with the `token` module (or the `get_token` playbook), then set `orchestrator_token` so every later call reuses it.

## Using the collection

The `configure_orchestrator` playbook loads every YAML file in a configuration directory as variables and runs the `dispatch` role, which applies all configuration roles in dependency order.

```bash
ansible-playbook kenmoini.automation_orchestrator_config.configure_orchestrator \
  -e orchestrator_configs_dir=./orchestrator_configs
```

- Each role runs only when its list variable is defined, for example `orchestrator_projects`.
- Run a subset with tags, for example `--tags projects,workflows`.
- Skip roles with `orchestrator_configuration_dispatcher_exclude_roles`.
- Split configuration per environment with wildcard variables (`orchestrator_projects_all`, `orchestrator_projects_prod`) and `dispatch_include_wildcard_vars: true`.
- `orchestrator_state` sets the default state (`present` or `absent`) for every item; an item can override it with its own `state`. `state: absent` deletes objects permanently (workflows cascade to their versions and executions), so use it with care.

See [playbooks/README.md](playbooks/README.md) and the [dispatch role](roles/dispatch/README.md).

## Secrets

- Secret values (credential `inputs`, identity provider `client_secret`) are write-only in the API. With `update_secrets: true` (the default) an item that supplies them is sent on every run and reports changed. Set `update_secrets: false` on an item once it is in place to make runs idempotent.
- User passwords use `update_password: on_create` by default, so an existing user is not touched. `update_password: always` resets the password on every run.
- A service account `client_secret` is shown once, by the run that creates (or rotates) it. `register` the result and store the secret outside Ansible.
- Set `orchestrator_configuration_secure_logging: true` (or a per-role `orchestrator_configuration_<role>_secure_logging`) to hide task output for roles that handle secrets. Keep passwords and secrets in Ansible Vault.

## Error handling

By default a role fails on the first error. Set `orchestrator_configuration_collect_logs: true` to continue and gather every failure in the `orchestrator_configuration_role_errors` variable, keyed by role, then inspect or print it after the run.

## Registering values

Set `orchestrator_configuration_register` to a variable name and the results of every role are collected there, as an object with one element per object type, each listing the items that were created or changed. To capture a single item's result, add the `register` key to the item with the name of the variable to set. This is how to keep a one-time service account secret.

## Roles

| Role | List variable | Purpose |
| --- | --- | --- |
| [`collect_async_status`](roles/collect_async_status/README.md) | - | Internal helper: waits for async tasks and collects results and errors |
| [`dispatch`](roles/dispatch/README.md) | `orchestrator_configuration_dispatcher_roles` | Runs all configuration roles in dependency order (with tags, exclusions and wildcard variable merging) |
| [`global_vars`](roles/global_vars/README.md) | - | Internal helper: shared variables for every role |
| [`orchestrator_approval_decisions`](roles/orchestrator_approval_decisions/README.md) | `orchestrator_approval_decisions` | Approve or reject pending approval requests in Automation Orchestrator |
| [`orchestrator_credentials`](roles/orchestrator_credentials/README.md) | `orchestrator_credentials` | Create, update and delete Credentials in Automation Orchestrator |
| [`orchestrator_execution_launch`](roles/orchestrator_execution_launch/README.md) | `orchestrator_launch_executions` | Launch workflow executions in Automation Orchestrator |
| [`orchestrator_groups`](roles/orchestrator_groups/README.md) | `orchestrator_groups` | Create, update and delete Groups in Automation Orchestrator |
| [`orchestrator_identity_providers`](roles/orchestrator_identity_providers/README.md) | `orchestrator_identity_providers` | Create, update and delete Identity Providers in Automation Orchestrator |
| [`orchestrator_integrations`](roles/orchestrator_integrations/README.md) | `orchestrator_integrations` | Create, update and delete Integrations in Automation Orchestrator |
| [`orchestrator_policies`](roles/orchestrator_policies/README.md) | `orchestrator_policies` | Create, update and delete Policies in Automation Orchestrator |
| [`orchestrator_projects`](roles/orchestrator_projects/README.md) | `orchestrator_projects` | Create, update and delete Projects in Automation Orchestrator |
| [`orchestrator_role_assignments`](roles/orchestrator_role_assignments/README.md) | `orchestrator_role_assignments` | Create, update and delete Role Assignments in Automation Orchestrator |
| [`orchestrator_roles`](roles/orchestrator_roles/README.md) | `orchestrator_roles` | Create, update and delete Roles in Automation Orchestrator |
| [`orchestrator_service_account_credentials`](roles/orchestrator_service_account_credentials/README.md) | `orchestrator_service_account_credentials` | Create, rotate, enable, disable and delete Service Account Credentials in Automation Orchestrator |
| [`orchestrator_service_accounts`](roles/orchestrator_service_accounts/README.md) | `orchestrator_service_accounts` | Create, update and delete Service Accounts in Automation Orchestrator |
| [`orchestrator_settings`](roles/orchestrator_settings/README.md) | `orchestrator_settings` | Update Settings in Automation Orchestrator |
| [`orchestrator_users`](roles/orchestrator_users/README.md) | `orchestrator_users` | Create, update and delete Users in Automation Orchestrator |
| [`orchestrator_workflows`](roles/orchestrator_workflows/README.md) | `orchestrator_workflows` | Create, update and delete Workflows in Automation Orchestrator |

## Modules

| Module | Purpose |
| --- | --- |
| `api` | Call any Automation Orchestrator API endpoint |
| `approval` | Approve or reject a pending approval request on the Automation Orchestrator |
| `approval_info` | Gather information about approval requests on the Automation Orchestrator |
| `credential` | Manage credentials in the Automation Orchestrator |
| `credential_info` | Gather information about credentials in the Automation Orchestrator |
| `credential_type_info` | Gather information about credential types in the Automation Orchestrator |
| `execution` | Launch a workflow execution on the Automation Orchestrator |
| `execution_cancel` | Cancel a running workflow execution on the Automation Orchestrator |
| `execution_info` | Gather information about workflow executions on the Automation Orchestrator |
| `group` | Manage groups in the Automation Orchestrator |
| `group_info` | Gather information about groups in the Automation Orchestrator |
| `identity_provider` | Manage OIDC identity providers in the Automation Orchestrator |
| `identity_provider_info` | Gather information about identity providers in the Automation Orchestrator |
| `integration` | Manage integrations in the Automation Orchestrator |
| `integration_info` | Gather information about integrations in the Automation Orchestrator |
| `policy` | Manage policies in the Automation Orchestrator |
| `policy_info` | Gather information about policies in the Automation Orchestrator |
| `project` | Manage projects in the Automation Orchestrator |
| `project_info` | Gather information about projects in the Automation Orchestrator |
| `role` | Manage roles in the Automation Orchestrator |
| `role_assignment` | Manage role assignments in the Automation Orchestrator |
| `role_assignment_info` | Gather information about role assignments in the Automation Orchestrator |
| `role_info` | Gather information about roles in the Automation Orchestrator |
| `service_account` | Manage service accounts in the Automation Orchestrator |
| `service_account_credential` | Manage the client credentials of a service account in the Automation Orchestrator |
| `service_account_info` | Gather information about service accounts in the Automation Orchestrator |
| `setting` | Manage runtime settings of the Automation Orchestrator |
| `setting_info` | Gather information about runtime settings of the Automation Orchestrator |
| `token` | Obtain an access token from the Automation Orchestrator |
| `user` | Manage local users in the Automation Orchestrator |
| `user_info` | Gather information about users in the Automation Orchestrator |
| `workflow` | Manage workflows in the Automation Orchestrator |
| `workflow_info` | Gather information about workflows in the Automation Orchestrator |

## Known limitations

- Automation Orchestrator is a tech preview and its API may change. Behaviors the collection assumes but has not yet confirmed against a live instance are tracked in [docs/API_COMPATIBILITY.md](docs/API_COMPATIBILITY.md).
- Some API list endpoints have no name filter, so lookups for workflows, credentials, groups, integrations and identity providers page through results client-side.

## Development

```bash
make venv          # create .venv with ansible-core, ansible-lint, pytest, pre-commit
make lint          # pre-commit hooks (yamllint, ansible-lint, black, flake8, markdownlint)
make pytest        # unit tests with plain pytest
make sanity        # ansible-test sanity
make unit          # ansible-test units
make build         # build the collection tarball into build/
make install       # build and install the tarball
make live          # apply tests/configs to a lab instance (needs tests/auth.yml, never committed)
make live-check    # the same in check mode with a diff
make live-cleanup  # remove the aoc-test-* objects
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/STANDARDS.md](docs/STANDARDS.md).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Author

Ken Moini
