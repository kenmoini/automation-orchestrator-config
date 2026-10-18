# kenmoini.automation_orchestrator_config.collect_async_status

## Description

An Ansible role that checks the status of asynchronous tasks and optionally collects errors.

This is an internal role that is not meant to be called directly by users of this collection.
It depends on the `global_vars` role of this collection.

## Variables

| Variable Name                             | Default Value | Required | Description                                                                                                                                        |
| :---                                      | :---:         | :---:    | :---                                                                                                                                               |
| `cas_job_async_results_item`              |               | yes      | The asynchronous item to check the status of. This must be from the registered `async` task                                                        |
| `cas_error_list_var_name`                 |               | yes      | The name of the dictionary key to use when collecting errors                                                                                       |
| `cas_register_subvar`                     |               | yes      | The name of the dictionary key to use when registering values                                                                                      |
| `cas_object_label`                        |               | yes      | The task name used for the `async_status` check, typically describing the object being checked                                                     |
| `orchestrator_configuration_collect_logs` | `false`       | no       | When enabled collects error messages and continues execution. Messages are collected in a variable called `orchestrator_configuration_role_errors` |
| `orchestrator_configuration_register`     |               | no       | Name of a variable in which the results are collected, keyed by `cas_register_subvar`                                                              |

When errors are collected, each entry in `orchestrator_configuration_role_errors[cas_error_list_var_name]` holds the
`ERROR_MESSAGE` and, where present on the failed item, its `name`, `username`, `project`, `workflow`, `role`, `user`,
`group`, `service_account`, `identifier` and `key`.

### Secure Logging Variables

The following variables complement each other.
If both variables are not set, secure logging defaults to false.
`cas_secure_logging` defaults to the value of `orchestrator_configuration_secure_logging` if it is not explicitly set.
This allows secure logging to be toggled for the entire suite of configuration roles with a single variable, or for the user to selectively use it.

| Variable Name                               | Default Value | Required | Description                                                                                                                               |
| :---:                                       | :---:         | :---:    | :---:                                                                                                                                     |
| `orchestrator_configuration_secure_logging` | `false`       | no       | This variable enables secure logging as well, but is shared across multiple roles, see above.                                             |
| `cas_secure_logging`                        | `false`       | no       | Whether or not to hide the role tasks in the log. Set this value to `true` if you will be providing your sensitive values from elsewhere. |

### Asynchronous Retry Variables

The following variables set asynchronous retries for the role.
If neither the retries nor the delay are set, they will default to their respective defaults.
This allows for all items to be created, then checked that the task finishes successfully.
This also speeds up the overall role.

| Variable Name                              | Default Value                                    | Required | Description                                                                |
| :---:                                      | :---:                                            | :---:    | :---:                                                                      |
| `orchestrator_configuration_async_retries` | 50                                               | no       | This variable sets the number of retries to attempt for the role globally. |
| `cas_async_retries`                        | `{{ orchestrator_configuration_async_retries }}` | no       | This variable sets the number of retries to attempt for the role.          |
| `orchestrator_configuration_async_delay`   | 1                                                | no       | This sets the delay between retries for the role globally.                 |
| `cas_async_delay`                          | `{{ orchestrator_configuration_async_delay }}`   | no       | This sets the delay between retries for the role.                          |

## License

[GPLv3+](https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE)

## Author

[Ken Moini](https://github.com/kenmoini)
