# Playbooks

Playbooks shipped with `kenmoini.automation_orchestrator_config`. Run them by FQCN:

```bash
ansible-playbook kenmoini.automation_orchestrator_config.<name>
```

## Authentication variables

All playbooks use the same variables as the roles: `orchestrator_hostname`, `orchestrator_username`, `orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`, `orchestrator_validate_certs` and `orchestrator_request_timeout`. Set them in the configs directory, the inventory, or with `-e`.

## configure_orchestrator

Loads every `.yml`/`.yaml` file from a configs directory as variables, then runs the `dispatch` role (all configuration roles, in dependency order).

```bash
ansible-playbook kenmoini.automation_orchestrator_config.configure_orchestrator \
  -e orchestrator_configs_dir=./my_configs
```

`orchestrator_configs_dir` defaults to `orchestrator_configs` (relative to the current directory). `auth.yml.example` is ignored.

Layout: one YAML file per resource, each defining an `orchestrator_<resource>` list.

```text
orchestrator_configs/
├── auth.yml                # orchestrator_hostname, orchestrator_token, ...
├── projects.yml            # orchestrator_projects: [...]
├── groups.yml              # orchestrator_groups: [...]
└── workflows.yml           # orchestrator_workflows: [...]
```

To split configuration per environment, use wildcard suffixes (`orchestrator_projects_all`, `orchestrator_projects_prod`, ...) and pass `-e dispatch_include_wildcard_vars=true`; the dispatch role merges them. See the `dispatch` role README.

## export_workflows

Exports workflow definitions to `<dir>/<project>/<workflow>.json` (names sanitized for the filesystem).

```bash
ansible-playbook kenmoini.automation_orchestrator_config.export_workflows \
  -e orchestrator_export_dir=./exports \
  -e '{"orchestrator_export_projects": ["my-project"]}'
```

- `orchestrator_export_dir` (default `./orchestrator_exports`)
- `orchestrator_export_projects` (optional list of project names; default all projects)

Authentication is applied through play-level `module_defaults` for the `group/kenmoini.automation_orchestrator_config.orchestrator` action group.

## get_token

Requests an access token and stores it in the `orchestrator_token` fact (output is `no_log`).

```bash
ansible-playbook kenmoini.automation_orchestrator_config.get_token \
  -e orchestrator_hostname=orchestrator.example.com \
  -e orchestrator_client_id=... -e orchestrator_client_secret=...
```

Reuse the token by passing `-e orchestrator_token=...` to later runs, or `import_playbook` this playbook ahead of plays that use the roles.
