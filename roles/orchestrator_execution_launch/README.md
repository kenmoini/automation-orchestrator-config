# kenmoini.automation_orchestrator_config.orchestrator_execution_launch

## Description

An Ansible Role to launch workflow executions in Automation Orchestrator.
Note that `wait: true` blocks the play for each item until the execution reaches a final state.
An execution that ends up `paused` (for example waiting for an approval) ends the wait and returns normally.
Results are registered in `orchestrator_launched_executions`.

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
|`orchestrator_launch_executions`|`see below`|yes|Data structure describing the workflow executions to launch. Described below.||

### Secure Logging Variables

The following Variables complement each other.
If neither variable is set, secure logging defaults to `true` for this role because `input_data` may contain secrets.
Set `orchestrator_configuration_execution_launch_secure_logging: false` only to debug, and never with real secrets in the items.
`orchestrator_configuration_execution_launch_secure_logging` defaults to the value of `orchestrator_configuration_secure_logging` if it is not explicitly called. This allows for secure logging to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_execution_launch_secure_logging`|`true`|no|Whether or not to hide the sensitive tasks of this role from the log. Defaults to `true` for this role because items contain secrets.|
|`orchestrator_configuration_secure_logging`|unset|no|Shared across multiple roles, see above. When it is unset this role still defaults to `true`.|

## Data Structure

### Execution Launch Variables

|Variable Name|Default Value|Required|Type|Description|
|:---:|:---:|:---:|:---:|:---:|
|`workflow`|""|yes|str|Name or UUID of the workflow to run.|
|`project`|""|no|str|Name or UUID of the project that holds the workflow. Required when `workflow` is a name.|
|`trigger_node_id`|""|no|str|ID of the trigger node to start from. When omitted the workflow must have exactly one trigger, which is used.|
|`input_data`|""|no|dict|Input data passed to the execution.|
|`use_published`|`false`|no|bool|Run the published version of the workflow instead of the current one.|
|`wait`|`false`|no|bool|Poll the execution until it reaches a final state. The task blocks the play for each item and fails when the execution ends as `failed` or `cancelled`. A `paused` execution (for example waiting for an approval) ends the wait and returns normally.|
|`interval`|`2`|no|float|Seconds between polls when `wait` is true.|
|`timeout`|`0`|no|int|Seconds to wait for the execution when `wait` is true. `0` waits without limit.|

### Yaml Example

```yaml
---
orchestrator_launch_executions:
  - workflow: aoc-test-wait-workflow
    project: aoc-test-project-1
    input_data:
      environment: test
  - workflow: aoc-test-wait-workflow
    project: aoc-test-project-1
    wait: true
    timeout: 120
```

## Playbook Examples

### Standard Role Usage

```yaml
---
- name: Playbook to launch workflow executions in Automation Orchestrator
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
    - {role: kenmoini.automation_orchestrator_config.orchestrator_execution_launch, when: orchestrator_launch_executions is defined}
```

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
