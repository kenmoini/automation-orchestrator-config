# kenmoini.automation_orchestrator_config.global_vars

## Description

An Ansible role that defines global variables available to every role in the
`kenmoini.automation_orchestrator_config` collection. A resource role consumes
these variables by declaring the role as a dependency in its `meta/main.yml`:

```console
# tail -4 meta/main.yml

dependencies:
  - role: global_vars
```

## Provided Variables

This role currently provides the following variables:

| Variable Name         | Default Value                                                     | Required | Description                                                     |
| :---                  | :---:                                                             | :---:    | :---                                                            |
| `operation_translate` | [See the default value below](#operation_translate-default-value) | Yes      | Provides translation from object states to human interpretation |

### operation_translate Default value

```yaml
---
operation_translate:
  present:
    verb: "Create/Update"
    action: "creation"
  absent:
    verb: "Remove"
    action: "deletion"
  exists:
    verb: "Already Exists"
    action: "exists"
  enabled:
    verb: "Enabled"
    action: "enabled"
  disabled:
    verb: "Disabled"
    action: "disabled"
  rotated:
    verb: "Rotate"
    action: "rotation"
  launched:
    verb: "Launch"
    action: "launch"
  approved:
    verb: "Approve"
    action: "approval"
  rejected:
    verb: "Reject"
    action: "rejection"
...
```

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
