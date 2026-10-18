# kenmoini.automation_orchestrator_config.dispatch

## Description

An Ansible Role to run all roles in the kenmoini.automation_orchestrator_config collection.

## Variables

This is a meta role, its purpose is to run the other roles in the collection, and it can be used to call roles in a custom order.

The control variable is `orchestrator_configuration_dispatcher_roles` which sets the roles to run, in order.

If you wish to run just a subset of roles either use `orchestrator_configuration_dispatcher_exclude_roles` to exclude entries from the default list or define `orchestrator_configuration_dispatcher_roles` with wanted roles locally.

### Option: `dispatch_include_wildcard_vars`

This option provides a powerful way to organize your configuration. When you set `dispatch_include_wildcard_vars: true`, the role will automatically find and combine settings that you have defined across multiple different variables. This lets you keep your configuration neat and tidy (e.g., defining projects for each environment in separate, organized files) instead of managing one giant list.

#### Example Setup and Workflow

This example shows how to structure your files and playbook to use this feature, combining a set of "common" projects with environment-specific ones.

#### 1. Organize Your Configuration Files

First, create folders to hold your common and environment-specific configurations. This approach allows you to separate different types of configurations into their own files and reduce duplication.

```bash
.
├── playbook.yml
└── config/
    ├── all/
    │   └── projects.yml
    ├── dev/
    │   └── projects.yml
    └── prod/
        └── projects.yml
```

NOTE: This is just an example and you can organize it however you want. You can also use group_vars as well the only thing that matters is the naming the vars and getting them ingested in some way.

#### 2. Define Variables in Your Files

Next, define the variables inside the corresponding files. Notice the variable names end with a suffix (`_all`, `_prod`, etc.) that identifies their purpose.

**`config/all/projects.yml`:**

```yaml
orchestrator_projects_all:
  - name: common-intranet
    description: Project shared by every environment
```

**`config/prod/projects.yml`:**

```yaml
orchestrator_projects_prod:
  - name: prod-app
    description: Production application project
```

#### 3. Load the Variables in Your Playbook

In your main playbook, you must load all the relevant configuration files. A common pattern is to load the `all` directory first, then layer the environment-specific configuration on top.

**`playbook.yml`:**

```yaml
- name: Configure Automation Orchestrator
  hosts: localhost
  gather_facts: false

  tasks:
    - name: Load all common configuration
      ansible.builtin.include_vars:
        dir: "config/all"
        extensions:
          - 'yml'

    - name: Load environment-specific configuration
      ansible.builtin.include_vars:
        dir: "config/{{ env }}"
        extensions:
          - 'yml'
      # Example: Run with `ansible-playbook playbook.yml -e "env=prod"`

    - name: Run the main configuration role
      ansible.builtin.include_role:
        name: kenmoini.automation_orchestrator_config.dispatch
      vars:
        dispatch_include_wildcard_vars: true
```

#### 4. See the Result

When you run the playbook (e.g., with `-e "env=prod"`), it loads variables from both `config/all` and `config/prod`. The `dispatch` role will then detect both the `orchestrator_projects_all` and `orchestrator_projects_prod` variables. Because `dispatch_include_wildcard_vars` is **`true`**, it automatically merges their contents into the base `orchestrator_projects` variable.

#### Resulting Master List

```yaml
orchestrator_projects:
  - name: common-intranet
    description: Project shared by every environment
  - name: prod-app
    description: Production application project
```

By default, this option is **`false`**.

To exclude roles to avoid unwanted updates, use `orchestrator_configuration_dispatcher_exclude_roles`:

```yaml
orchestrator_configuration_dispatcher_exclude_roles:
  - orchestrator_execution_launch
  - orchestrator_approval_decisions
```

The exclusion is applied each time the roles are run, so it still works when `orchestrator_configuration_dispatcher_roles` is overridden.

### Roles

The roles run in this order. A role only runs when its variable is defined. Each role also has its own tags, so a playbook can be limited to a subset with `--tags`.

| # | Role | Variable | Tags |
| --- | ---- | -------- | ---- |
| 1 | `orchestrator_settings` | `orchestrator_settings` | `settings`, `orchestrator_settings` |
| 2 | `orchestrator_identity_providers` | `orchestrator_identity_providers` | `identity_providers`, `orchestrator_identity_providers` |
| 3 | `orchestrator_groups` | `orchestrator_groups` | `groups`, `orchestrator_groups` |
| 4 | `orchestrator_users` | `orchestrator_users` | `users`, `orchestrator_users` |
| 5 | `orchestrator_projects` | `orchestrator_projects` | `projects`, `orchestrator_projects` |
| 6 | `orchestrator_policies` | `orchestrator_policies` | `policies`, `orchestrator_policies` |
| 7 | `orchestrator_roles` | `orchestrator_roles` | `roles`, `orchestrator_roles` |
| 8 | `orchestrator_role_assignments` | `orchestrator_role_assignments` | `role_assignments`, `orchestrator_role_assignments` |
| 9 | `orchestrator_credentials` | `orchestrator_credentials` | `credentials`, `orchestrator_credentials` |
| 10 | `orchestrator_integrations` | `orchestrator_integrations` | `integrations`, `orchestrator_integrations` |
| 11 | `orchestrator_service_accounts` | `orchestrator_service_accounts` | `service_accounts`, `orchestrator_service_accounts` |
| 12 | `orchestrator_service_account_credentials` | `orchestrator_service_account_credentials` | `service_account_credentials`, `orchestrator_service_account_credentials` |
| 13 | `orchestrator_workflows` | `orchestrator_workflows` | `workflows`, `orchestrator_workflows` |
| 14 | `orchestrator_execution_launch` | `orchestrator_launch_executions` | `execution_launch`, `orchestrator_execution_launch` |
| 15 | `orchestrator_approval_decisions` | `orchestrator_approval_decisions` | `approval_decisions`, `orchestrator_approval_decisions` |

#### Dispatch role var list keys

Each role has its own variables, for information on those please see each role which this role will call. Each item of the list has three elements:

- `role` which is the name of the role within kenmoini.automation_orchestrator_config
- `var` which is the variable which is used in that role. We use this to prevent the role being called if the variable is not set
- `tags` the tags which are applied to the role so it is possible to apply tags to a playbook using the dispatcher with these tags.

It is possible to redefine this variable with a subset of roles or with different tags. In general we suggest keeping the same structure and perhaps just using a subset.

For more information about variables, see [top-level README](../../README.md).
For more information about roles, see each roles' README (also linked in the top-level README)

#### Using list of wildcard variables in external playbooks

In case an external playbook needs to read and process the wildcard variables like the `dispatch` role does,
the following task shows how to make the `orchestrator_configuration_all_vars` list variable available in the playbook:

```yaml
    - name: Read list of known Automation Orchestrator wildcard variables
      ansible.builtin.include_role:
        name: kenmoini.automation_orchestrator_config.dispatch
        tasks_from: vars_only
        public: true
```

## License

GPL-3.0-or-later

## Author

Ken Moini
