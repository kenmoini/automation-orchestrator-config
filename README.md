# kenmoini.automation_orchestrator_config

A configuration-as-code Ansible Collection for Red Hat Automation Orchestrator, modeled on `infra.aap_configuration`. It ships Python modules for each API resource and roles that manage those resources from variable lists.

## Requirements

- ansible-core >= 2.16

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

## Authentication

Modules and roles accept these parameters, each with an environment variable fallback:

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

## Content

Role and module tables are generated in a later task.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
