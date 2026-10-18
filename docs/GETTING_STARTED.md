# Getting started with kenmoini.automation_orchestrator_config

This guide takes you from an empty directory to a working configuration-as-code setup for Red Hat Automation Orchestrator (tech preview).

## What is this collection?

`kenmoini.automation_orchestrator_config` manages Automation Orchestrator resources from YAML: projects, workflows, credentials, users, groups, roles, policies, identity providers, integrations, service accounts and settings. It ships the modules that call the API and the roles that loop over variable lists, plus playbooks that tie it together.

## Prerequisites

1. ansible-core 2.16 or higher.
2. Access to an Automation Orchestrator instance.
3. API credentials: a token, a service account (client ID and secret), or a username and password.

## Installation

```yaml
---
collections:
  - name: kenmoini.automation_orchestrator_config
...
```

```bash
ansible-galaxy collection install -r requirements.yml
ansible-galaxy collection list | grep kenmoini
```

## Quick start

### 1. Create the directory layout

One file per resource type, each defining the `orchestrator_<resource>` list for that role:

```text
orchestrator_configs/
├── auth.yml           # connection details (encrypt with ansible-vault)
├── projects.yml       # orchestrator_projects
├── groups.yml         # orchestrator_groups
├── users.yml          # orchestrator_users
├── credentials.yml    # orchestrator_credentials
├── workflows.yml      # orchestrator_workflows
└── files/
    └── demo-workflow.json  # workflow definition referenced by workflows.yml
```

Every `.yml`/`.yaml` file under the directory (subdirectories included) is loaded as variables, so keep workflow definition files as `.json`.

### 2. Add authentication

`orchestrator_configs/auth.yml`:

```yaml
---
orchestrator_hostname: orchestrator.example.com
orchestrator_validate_certs: true

# Pick one of the following.
orchestrator_token: your-access-token
# orchestrator_client_id: your-service-account-id
# orchestrator_client_secret: your-service-account-secret
# orchestrator_username: admin
# orchestrator_password: your-password
...
```

If several methods are set, the first available is used: token, then client credentials, then username and password (they are not mutually exclusive). Never commit credentials; encrypt the file:

```bash
ansible-vault encrypt orchestrator_configs/auth.yml
```

### 3. Run the configuration

```bash
ansible-playbook kenmoini.automation_orchestrator_config.configure_orchestrator \
  -e orchestrator_configs_dir=./orchestrator_configs --ask-vault-pass
```

`orchestrator_configs_dir` defaults to `orchestrator_configs` in the current directory. The playbook loads every `.yml` file in it and runs the `dispatch` role. Add `--check --diff` first to preview changes.

## A minimal end-to-end example

Project, group, user, credential, then a workflow imported from a file and published.

`projects.yml`:

```yaml
---
orchestrator_projects:
  - name: demo-project
    description: Demo project
    labels:
      env: demo
...
```

`groups.yml`:

```yaml
---
orchestrator_groups:
  - name: demo-team
    description: Demo team
...
```

`users.yml`:

```yaml
---
orchestrator_users:
  - username: demo-user
    password: "{{ vault_demo_user_password }}"
    update_password: on_create
    email: demo-user@example.com
    first_name: Demo
    last_name: User
    groups:
      - demo-team
...
```

`credentials.yml`:

```yaml
---
orchestrator_credentials:
  - name: demo-credential
    credential_type: Generic
    project: demo-project
    inputs:
      token: "{{ vault_demo_token }}"
    update_secrets: false
...
```

`workflows.yml`:

```yaml
---
orchestrator_workflows:
  - name: demo-workflow
    description: Demo workflow
    project: demo-project
    definition_file: files/demo-workflow.json
    publish: true
...
```

The `definition_file` is JSON or YAML, read on the controller. A relative path resolves against the configs directory (`orchestrator_configs_dir`), so this example reads `orchestrator_configs/files/demo-workflow.json`; an absolute path is used as-is. (`{{ playbook_dir }}` would point inside the installed collection, so do not use it here.) Alternatively set `workflow_definition` to an inline dictionary. The dispatch role applies the roles in dependency order (groups before identity providers and users, projects before credentials and workflows, service accounts before role assignments), so the file names do not matter.

## Understanding the dispatch role

The dispatch role runs only the roles whose list variable is defined, in this order: settings, groups, identity providers, users, projects, policies, roles, service accounts, role assignments, credentials, integrations, service account credentials, workflows, execution launch, approval decisions. See the [dispatch README](../roles/dispatch/README.md) for the exact table.

### Using tags

```bash
# Only projects and workflows
ansible-playbook kenmoini.automation_orchestrator_config.configure_orchestrator --tags projects,workflows

# Everything except credentials
ansible-playbook kenmoini.automation_orchestrator_config.configure_orchestrator --skip-tags credentials
```

Each role has two tags: the short name (`projects`, `role_assignments`) and the role name (`orchestrator_projects`).

### Excluding roles

```yaml
orchestrator_configuration_dispatcher_exclude_roles:
  - orchestrator_execution_launch
  - orchestrator_approval_decisions
```

### Wildcard variables

To share configuration across environments, suffix the variable name (`_all`, `_dev`, `_prod`) and enable merging:

```yaml
# config/all/projects.yml
orchestrator_projects_all:
  - name: common-intranet

# config/prod/projects.yml
orchestrator_projects_prod:
  - name: prod-app
```

```yaml
- name: Apply configuration
  ansible.builtin.include_role:
    name: kenmoini.automation_orchestrator_config.dispatch
  vars:
    dispatch_include_wildcard_vars: true
```

The dispatch role merges `orchestrator_projects_all` and `orchestrator_projects_prod` into `orchestrator_projects`. If you call the playbook instead, pass `-e dispatch_include_wildcard_vars=true`.

## Exporting workflows

Export existing workflow definitions to files you can commit and feed back through `definition_file`:

```bash
ansible-playbook kenmoini.automation_orchestrator_config.export_workflows \
  -e orchestrator_export_dir=./exports \
  -e '{"orchestrator_export_projects": ["demo-project"]}'
```

Files are written to `<dir>/<project>/<workflow>.json`. Leave `orchestrator_export_projects` out to export every project.

## Tokens for large runs

With username and password every module call logs in again. Get a token once and reuse it:

```bash
ansible-playbook kenmoini.automation_orchestrator_config.get_token \
  -e orchestrator_hostname=orchestrator.example.com \
  -e orchestrator_client_id=... -e orchestrator_client_secret=...
```

Then supply `orchestrator_token` to the later runs.

## Error handling

```yaml
orchestrator_configuration_collect_logs: true
```

With this set, a failing item no longer stops the run; failures are collected in `orchestrator_configuration_role_errors`. Set `orchestrator_configuration_register` to a variable name to collect what was created or changed.

## Best practices

1. Keep the configuration in version control; encrypt secrets with Ansible Vault.
2. Start small and preview with `--check --diff`.
3. Set `update_secrets: false` on credentials once created so runs are idempotent.
4. Keep secure logging on when handling secrets. The secret-bearing roles (users, credentials, identity providers, service account credentials, execution launch) default to `true`; do not set `orchestrator_configuration_secure_logging: false` with real secrets.
5. `state: absent` deletes permanently; test in a lab first.

## Troubleshooting

- "couldn't resolve module/action": the collection is not installed; run `ansible-galaxy collection list`.
- Authentication failures: check `orchestrator_hostname` and which of token, client credentials or username and password is set. Every endpoint needs authentication.
- Timeouts: raise `orchestrator_request_timeout` (default 10 seconds).
- Unexpected differences on workflows or integrations: see [API_COMPATIBILITY.md](API_COMPATIBILITY.md).

## Next steps

- [Main README](../README.md) for the full role and module tables.
- [playbooks/README.md](../playbooks/README.md) for the shipped playbooks.
- [tests/configs](../tests/configs) for more example configuration.
