# kenmoini.automation_orchestrator_config.orchestrator_settings

## Description

An Ansible Role to update Settings in Automation Orchestrator.
The `orchestrator_settings` variable can be a dictionary of `key: value` pairs, which is applied with a single module call, or a list of items. A value of `null` in the dictionary resets that setting to its default.

## Requirements

The `kenmoini.automation_orchestrator_config` collection must be installed.

## Variables

|Variable Name|Default Value|Required|Description|Example|
|:---|:---:|:---:|:---|:---|
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
|`orchestrator_settings`|`see below`|yes|Dictionary of `key: value` settings or list of items. Described below.||

### Enforcing defaults

The following Variables complement each other.
If both variables are not set, enforcing default values is not done.
Enabling these variables enforces default values on options that are optional in the Orchestrator API.
This should be enabled to enforce configuration and prevent configuration drift. It is recommended to be enabled, however it is not enforced by default.

Enabling this will enforce configuration without specifying every option in the configuration files.

`orchestrator_configuration_settings_enforce_defaults` defaults to the value of `orchestrator_configuration_enforce_defaults` if it is not explicitly called. This allows for enforced defaults to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_settings_enforce_defaults`|`false`|no|Whether or not to enforce default option values on only the settings role|
|`orchestrator_configuration_enforce_defaults`|`false`|no|This variable enables enforced default values as well, but is shared across multiple roles, see above.|

### Secure Logging Variables

The following Variables complement each other.
If both variables are not set, secure logging defaults to false.
The role defaults to false as normally the setting task does not include sensitive information.
`orchestrator_configuration_settings_secure_logging` defaults to the value of `orchestrator_configuration_secure_logging` if it is not explicitly called. This allows for secure logging to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_settings_secure_logging`|`false`|no|Whether or not to include the sensitive Setting role tasks in the log. Set this value to `true` if you will be providing your sensitive values from elsewhere.|
|`orchestrator_configuration_secure_logging`|`false`|no|This variable enables secure logging as well, but is shared across multiple roles, see above.|

### Asynchronous Retry Variables

The following Variables set asynchronous retries for the role.
If neither of the retries or delay or retries are set, they will default to their respective defaults.
This allows for all items to be created, then checked that the task finishes successfully.
This also speeds up the overall role.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_async_retries`|50|no|This variable sets the number of retries to attempt for the role globally.|
|`orchestrator_configuration_settings_async_retries`|`{{ orchestrator_configuration_async_retries }}`|no|This variable sets the number of retries to attempt for the role.|
|`orchestrator_configuration_async_delay`|1|no|This sets the delay between retries for the role globally.|
|`orchestrator_configuration_settings_async_delay`|`orchestrator_configuration_async_delay`|no|This sets the delay between retries for the role.|
|`orchestrator_configuration_loop_delay`|0|no|This sets the pause between each item in the loop for the roles globally. To help when API is getting overloaded.|
|`orchestrator_configuration_settings_loop_delay`|`orchestrator_configuration_loop_delay`|no|This sets the pause between each item in the loop for the role. To help when API is getting overloaded.|
|`orchestrator_configuration_async_dir`|`null`|no|Sets the directory to write the results file for async tasks. The default value is set to `null` which uses the Ansible Default of `~/.ansible_async/`.|

## Setting Data Structure

### Setting Variables

|Variable Name|Default Value|Required|Type|Description|
|:---:|:---:|:---:|:---:|:---:|
|`name`|""|yes|str|Key of the setting, for example `general.session_timeout`.|
|`value`|""|no|raw|New value of the setting, of any type matching the setting.|
|`expected_version`|""|no|int|Version of the setting the change is based on; the API answers with a conflict when it was changed meanwhile.|
|`register`|""|no|str|Variable to set based on the result of the object creation/modification.|

### Yaml Example (dictionary)

```yaml
---
orchestrator_settings:
  general.session_timeout: 3600
  general.example_flag: false
```

A value of `null` resets that setting to its default. The dictionary is applied with a single module call.

### Yaml Example (list)

```yaml
---
orchestrator_settings:
  - name: general.session_timeout
    value: 3600
  - name: general.example_flag
    value: false
    expected_version: 2
```

### Json Example

```json
{
  "orchestrator_settings": {
    "general.session_timeout": 3600,
    "general.example_flag": false
  }
}
```

In list form each item is applied by its own asynchronous module call and `register` is available; in dictionary form it is not.

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
    - {role: kenmoini.automation_orchestrator_config.orchestrator_settings, when: orchestrator_settings is defined}
```

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
