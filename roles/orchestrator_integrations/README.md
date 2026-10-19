# kenmoini.automation_orchestrator_config.orchestrator_integrations

## Description

An Ansible Role to create, update and delete Integrations in Automation Orchestrator.
Note that `state: absent` permanently deletes the integration; it cannot be recovered.

## Requirements

The `kenmoini.automation_orchestrator_config` collection must be installed.

## Variables

|Variable Name|Default Value|Required|Description|Example|
|:---|:---:|:---:|:---|:---|
|`orchestrator_state`|"present"|no|The state all objects will take unless overridden by object default|'absent'|
|`orchestrator_hostname`|""|yes|Hostname or URL of the Automation Orchestrator server.|orchestrator.example.com|
|`orchestrator_validate_certs`|`true`|no|Whether or not to validate the Automation Orchestrator server's SSL certificate.||
|`orchestrator_username`|""|no|User on the Automation Orchestrator server. Either username / password, a token, or client ID / secret needs to be specified.||
|`orchestrator_password`|""|no|Password of the user on the server. This should be stored in an Ansible Vault or elsewhere and called from a parent playbook.||
|`orchestrator_token`|""|no|Token for the Automation Orchestrator server. This should be stored in an Ansible Vault or elsewhere and called from a parent playbook.||
|`orchestrator_client_id`|""|no|OAuth client ID for the Automation Orchestrator server, used with the client secret.||
|`orchestrator_client_secret`|""|no|OAuth client secret for the Automation Orchestrator server. This should be stored in an Ansible Vault or elsewhere.||
|`orchestrator_request_timeout`|`10`|no|Timeout in seconds for requests to the Automation Orchestrator server.||
|`orchestrator_configuration_collect_logs`|`false`|no|Specify whether to collect async results and continue for all failed async tasks instead of failing on the first error. Collected results are available in the `orchestrator_configuration_role_errors` variable.||
|`orchestrator_configuration_register`|""|no|Specify a variable to register the values of all orchestrator configuration tasks. This will create an object with each object type as an element containing a list of each item created.||
|`orchestrator_integrations`|`see below`|yes|Data structure describing your integration items. Described below.||

### Enforcing defaults

The following Variables complement each other.
If both variables are not set, enforcing default values is not done.
Enabling these variables enforces default values on options that are optional in the Orchestrator API.
This should be enabled to enforce configuration and prevent configuration drift. It is recommended to be enabled, however it is not enforced by default.

Enabling this will enforce configuration without specifying every option in the configuration files.

`orchestrator_configuration_integrations_enforce_defaults` defaults to the value of `orchestrator_configuration_enforce_defaults` if it is not explicitly called. This allows for enforced defaults to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_integrations_enforce_defaults`|`false`|no|Whether or not to enforce default option values on only the integrations role|
|`orchestrator_configuration_enforce_defaults`|`false`|no|This variable enables enforced default values as well, but is shared across multiple roles, see above.|

### Secure Logging Variables

The following Variables complement each other.
If both variables are not set, secure logging defaults to false.
The role defaults to false as normally the integration task does not include sensitive information.
`orchestrator_configuration_integrations_secure_logging` defaults to the value of `orchestrator_configuration_secure_logging` if it is not explicitly called. This allows for secure logging to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_integrations_secure_logging`|`false`|no|Whether or not to include the sensitive Integration role tasks in the log. Set this value to `true` if you will be providing your sensitive values from elsewhere.|
|`orchestrator_configuration_secure_logging`|`false`|no|This variable enables secure logging as well, but is shared across multiple roles, see above.|

### Asynchronous Retry Variables

The following Variables set asynchronous retries for the role.
If neither of the retries or delay or retries are set, they will default to their respective defaults.
This allows for all items to be created, then checked that the task finishes successfully.
This also speeds up the overall role.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_async_retries`|50|no|This variable sets the number of retries to attempt for the role globally.|
|`orchestrator_configuration_integrations_async_retries`|`{{ orchestrator_configuration_async_retries }}`|no|This variable sets the number of retries to attempt for the role.|
|`orchestrator_configuration_async_delay`|1|no|This sets the delay between retries for the role globally.|
|`orchestrator_configuration_integrations_async_delay`|`orchestrator_configuration_async_delay`|no|This sets the delay between retries for the role.|
|`orchestrator_configuration_loop_delay`|0|no|This sets the pause between each item in the loop for the roles globally. To help when API is getting overloaded.|
|`orchestrator_configuration_integrations_loop_delay`|`orchestrator_configuration_loop_delay`|no|This sets the pause between each item in the loop for the role. To help when API is getting overloaded.|
|`orchestrator_configuration_async_dir`|`null`|no|Sets the directory to write the results file for async tasks. The default value is set to `null` which uses the Ansible Default of `~/.ansible_async/`.|

## Integration Data Structure

### Integration Variables

|Variable Name|Default Value|Required|Type|Description|
|:---:|:---:|:---:|:---:|:---:|
|`name`|""|yes|str|Name of the integration.|
|`new_name`|""|no|str|New name for the integration, used to rename it.|
|`description`|""|no|str|Description of the integration.|
|`integration_type`|""|no|str|Type of the integration: `mcp_server`, `llm_provider` or `ansible_automation_platform`. Required to create an integration.|
|`configuration`|`{}`|no|dict|Connection settings of the integration, such as `base_url`, `allow_http`, `insecure_skip_tls_verify`, `ca_certificate` and, for LLM providers, `provider_hint`.|
|`management_credential`|""|no|str|Name or ID of the credential used to connect to the integration.|
|`management_credential_project`|""|no|str|Name or ID of the project that owns `management_credential`. Required when it is a name.|
|`enabled`|""|no|bool|Whether the integration is enabled.|
|`scope`|""|no|str|`global` (available to all projects) or `project` (only the assigned projects).|
|`labels`|`{}`|no|dict|Labels (key/value pairs) to set on the integration.|
|`projects`|`[]`|no|list|Names or IDs of the projects the integration is assigned to. When set the assignments are made to match; an empty list removes all.|
|`models`|`[]`|no|list|Models of an LLM provider integration to enable, disable or make the default (dicts with `name` or `model_id`, `enabled`, `is_default`).|
|`tools`|`[]`|no|list|Tools of an MCP server integration to enable or disable (dicts with `name` and `enabled`).|
|`discover`|""|no|bool|Discover models or tools on the provider before creating the integration (module default `true`).|
|`refresh`|""|no|bool|Fetch the current models or tools from the provider after the integration is created or updated.|
|`validate`|""|no|bool|Test the connection to the integration at the end of the task.|
|`state`|`present`|no|str|Desired state of the resource: `present`, `absent`, `exists` (`absent` is permanent).|
|`register`|""|no|str|Variable to set based on the result of the object creation/modification.|

### Yaml Example

```yaml
---
orchestrator_integrations:
  - name: openai
    integration_type: llm_provider
    configuration:
      provider_hint: openai
      base_url: https://api.openai.com/v1
    management_credential: openai-key
    management_credential_project: Platform Team
    scope: project
    projects:
      - Platform Team
    models:
      - name: gpt-4o
        enabled: true
        is_default: true
    validate: true

  - name: old-integration
    state: absent

  - name: OpenShell Test AAP
    description: OpenShell Test Ansible Automation Platform (AAP) integration
    management_credential: OS-T-HubAAP
    management_credential_project: openshell-test
    integration_type: ansible_automation_platform
    configuration:
      integration_type: ansible_automation_platform
      base_url: https://example.com
      insecure_skip_tls_verify: true
      allow_http: false
      # ca_certificate: |
      #   -----BEGIN CERTIFICATE-----
      #   MII...
      #   -----END CERTIFICATE-----
    scope: global # or project
    # projects:
    #   - openshell-test
    validate: false
    discover: false
```

### Json Example

```json
{
  "orchestrator_integrations": [
    {
      "name": "openai",
      "integration_type": "llm_provider",
      "configuration": {
        "provider_hint": "openai",
        "base_url": "https://api.openai.com/v1"
      },
      "management_credential": "openai-key",
      "management_credential_project": "Platform Team",
      "scope": "project",
      "projects": [
        "Platform Team"
      ],
      "models": [
        {
          "name": "gpt-4o",
          "enabled": true,
          "is_default": true
        }
      ],
      "validate": true
    },
    {
      "name": "old-integration",
      "state": "absent"
    }
  ]
}
```

## Playbook Examples

### Standard Role Usage

```yaml
---
- name: Playbook to configure Automation Orchestrator
  hosts: localhost
  connection: local
  # Define following vars here, or in a vars file
  # orchestrator_hostname: orchestrator.example.com
  # orchestrator_username: admin
  # orchestrator_password: changeme
  pre_tasks:
    - name: Include vars from orchestrator_configs directory
      ansible.builtin.include_vars:
        dir: ./orchestrator_configs
        extensions: ["yml"]
  roles:
    - {role: kenmoini.automation_orchestrator_config.orchestrator_integrations, when: orchestrator_integrations is defined}
```

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
