# kenmoini.automation_orchestrator_config.orchestrator_credentials

## Description

An Ansible Role to create, update and delete Credentials in Automation Orchestrator.
Note that `state: absent` permanently deletes the credential; it cannot be recovered.

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
|`orchestrator_credentials`|`see below`|yes|Data structure describing your credential items. Described below.||

### Enforcing defaults

The following Variables complement each other.
If both variables are not set, enforcing default values is not done.
Enabling these variables enforces default values on options that are optional in the Orchestrator API.
This should be enabled to enforce configuration and prevent configuration drift. It is recommended to be enabled, however it is not enforced by default.

Enabling this will enforce configuration without specifying every option in the configuration files.

`orchestrator_configuration_credentials_enforce_defaults` defaults to the value of `orchestrator_configuration_enforce_defaults` if it is not explicitly called. This allows for enforced defaults to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_credentials_enforce_defaults`|`false`|no|Whether or not to enforce default option values on only the credentials role|
|`orchestrator_configuration_enforce_defaults`|`false`|no|This variable enables enforced default values as well, but is shared across multiple roles, see above.|

### Secure Logging Variables

The following Variables complement each other.
If neither variable is set, secure logging defaults to `true` for this role because items contain secrets (`inputs`).
Set `orchestrator_configuration_credentials_secure_logging: false` only to debug, and never with real secrets in the items.
`orchestrator_configuration_credentials_secure_logging` defaults to the value of `orchestrator_configuration_secure_logging` if it is not explicitly called. This allows for secure logging to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_credentials_secure_logging`|`true`|no|Whether or not to hide the sensitive tasks of this role from the log. Defaults to `true` for this role because items contain secrets.|
|`orchestrator_configuration_secure_logging`|unset|no|Shared across multiple roles, see above. When it is unset this role still defaults to `true`.|

### Asynchronous Retry Variables

The following Variables set asynchronous retries for the role.
If neither of the retries or delay or retries are set, they will default to their respective defaults.
This allows for all items to be created, then checked that the task finishes successfully.
This also speeds up the overall role.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_async_retries`|50|no|This variable sets the number of retries to attempt for the role globally.|
|`orchestrator_configuration_credentials_async_retries`|`{{ orchestrator_configuration_async_retries }}`|no|This variable sets the number of retries to attempt for the role.|
|`orchestrator_configuration_async_delay`|1|no|This sets the delay between retries for the role globally.|
|`orchestrator_configuration_credentials_async_delay`|`orchestrator_configuration_async_delay`|no|This sets the delay between retries for the role.|
|`orchestrator_configuration_loop_delay`|0|no|This sets the pause between each item in the loop for the roles globally. To help when API is getting overloaded.|
|`orchestrator_configuration_credentials_loop_delay`|`orchestrator_configuration_loop_delay`|no|This sets the pause between each item in the loop for the role. To help when API is getting overloaded.|
|`orchestrator_configuration_async_dir`|`null`|no|Sets the directory to write the results file for async tasks. The default value is set to `null` which uses the Ansible Default of `~/.ansible_async/`.|

## Credential Data Structure

### Credential Variables

|Variable Name|Default Value|Required|Type|Description|
|:---:|:---:|:---:|:---:|:---:|
|`name`|""|yes|str|Name of the credential.|
|`new_name`|""|no|str|New name for the credential, used to rename it.|
|`description`|""|no|str|Description of the credential.|
|`credential_type`|""|no|str|Name or ID of the credential type. Required to create a credential.|
|`project`|""|yes|str|Name or ID of the project that owns the credential. Cannot be changed on an existing credential.|
|`inputs`|`{}`|no|dict|Secret and non-secret values of the credential, following the input schema of its credential type. Keep secrets in an Ansible Vault.|
|`enabled`|""|no|bool|Whether the credential is enabled.|
|`labels`|`{}`|no|dict|Labels (key/value pairs) to set on the credential.|
|`update_secrets`|""|no|bool|When `true` (the module default) `inputs` are sent on every update and the task always reports a change; when `false` they are only used to create the credential.|
|`state`|`present`|no|str|Desired state of the resource: `present`, `absent`, `exists` (`absent` is permanent).|
|`register`|""|no|str|Variable to set based on the result of the object creation/modification.|

### Yaml Example

```yaml
---
orchestrator_credentials:
  - name: openai-key
    credential_type: LLM Provider
    project: Platform Team
    inputs:
      api_key: '{{ vault_openai_key }}'
    update_secrets: false
  - name: old-credential
    project: Platform Team
    state: absent

  - name: OS-T-HubAAP
    description: Ansible Automation Platform (AAP) credentials for OpenShell Test
    credential_type: Ansible Automation Platform
    project: openshell-test
    inputs:
      username: admin
      password: notpassword
      # Or
      # token: ey...
    update_secrets: false
    labels:
      env: test
```

### Json Example

```json
{
  "orchestrator_credentials": [
    {
      "name": "openai-key",
      "credential_type": "LLM Provider",
      "project": "Platform Team",
      "inputs": {
        "api_key": "{{ vault_openai_key }}"
      },
      "update_secrets": false
    },
    {
      "name": "old-credential",
      "project": "Platform Team",
      "state": "absent"
    }
  ]
}
```

### Idempotence and secrets

With the module default `update_secrets: true` the secret `inputs` are sent on every run, so the task reports a change every time. Set `update_secrets: false` on items whose `inputs` should only be used to create the credential; this is recommended for idempotent runs. Secure logging defaults to `true` for this role so the secret values are kept out of the log; do not set `orchestrator_configuration_secure_logging` or `orchestrator_configuration_credentials_secure_logging` to `false` with real secrets.

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
    - {role: kenmoini.automation_orchestrator_config.orchestrator_credentials, when: orchestrator_credentials is defined}
```

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
