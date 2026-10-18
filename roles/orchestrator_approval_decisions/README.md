# kenmoini.automation_orchestrator_config.orchestrator_approval_decisions

## Description

An Ansible Role to approve or reject pending approval requests in Automation Orchestrator.
Each item identifies the approval request either by `id`, or by `execution` together with `name`.
Results are registered in `orchestrator_decided_approvals`.

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
|`orchestrator_approval_decisions`|`see below`|yes|Data structure describing the approval decisions to record. Described below.||

### Secure Logging Variables

The following Variables complement each other.
If both variables are not set, secure logging defaults to false.
The role defaults to false as normally the approval decision task does not include sensitive information.
`orchestrator_configuration_approval_decisions_secure_logging` defaults to the value of `orchestrator_configuration_secure_logging` if it is not explicitly called. This allows for secure logging to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

|Variable Name|Default Value|Required|Description|
|:---:|:---:|:---:|:---:|
|`orchestrator_configuration_approval_decisions_secure_logging`|`false`|no|Whether or not to include the sensitive approval decisions role tasks in the log. Set this value to `true` if you will be providing your sensitive values from elsewhere.|
|`orchestrator_configuration_secure_logging`|`false`|no|This variable enables secure logging as well, but is shared across multiple roles, see above.|

## Data Structure

### Approval Decision Variables

|Variable Name|Default Value|Required|Type|Description|
|:---:|:---:|:---:|:---:|:---:|
|`id`|""|no|str|UUID of the approval request. Mutually exclusive with `execution`.|
|`execution`|""|no|str|UUID of the execution that raised the approval request. Requires `name`.|
|`name`|""|no|str|Name of the approval request within the execution, matched exactly. Requires `execution`.|
|`decision`|""|yes|str|Decision to record: `approved` or `rejected`.|
|`notes`|""|no|str|Free-text notes stored with the decision.|

### Yaml Example

```yaml
---
orchestrator_approval_decisions:
  - id: 00000000-0000-4000-8000-000000000001
    decision: approved
    notes: Approved by test run
  - execution: 00000000-0000-4000-8000-000000000002
    name: Manager approval
    decision: rejected
```

## Playbook Examples

### Standard Role Usage

```yaml
---
- name: Playbook to record approval decisions in Automation Orchestrator
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
    - {role: kenmoini.automation_orchestrator_config.orchestrator_approval_decisions, when: orchestrator_approval_decisions is defined}
```

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
