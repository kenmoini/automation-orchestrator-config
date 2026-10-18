# Resource role template

`roles/orchestrator_projects` is the reference implementation of the resource-role pattern. Every other
resource role is generated from it by substitution. Do not improvise: keep names, ordering and
blocks identical so the roles stay uniform.

## Terms

- `<res>`: plural resource name used in the role and variables (`projects`).
- `<module>`: the module wrapped, `kenmoini.automation_orchestrator_config.<module>` (`project`).
- `<Res>` / `<Module>`: Title-case forms used in task names and README prose (`Projects` / `Project`).
- `<item fields>`: the module params other than `name`/auth that an item may carry.

## Files

```text
roles/orchestrator_<res>/
  defaults/main.yml
  tasks/main.yml
  meta/main.yml
  meta/argument_specs.yml
  README.md
  tests/test.yml
  tests/configs/<res>.yml
```

All YAML: `.yml`, 2-space indent, starts `---`, ends `...`.

## defaults/main.yml (exact)

```yaml
---
orchestrator_<res>: []
orchestrator_configuration_<res>_secure_logging: "{{ orchestrator_configuration_secure_logging | default('false') }}"
orchestrator_configuration_<res>_async_retries: "{{ orchestrator_configuration_async_retries | default(50) }}"
orchestrator_configuration_<res>_async_delay: "{{ orchestrator_configuration_async_delay | default(1) }}"
orchestrator_configuration_<res>_loop_delay: "{{ orchestrator_configuration_loop_delay | default(0) }}"
orchestrator_configuration_<res>_enforce_defaults: "{{ orchestrator_configuration_enforce_defaults | default(false) }}"
orchestrator_configuration_async_dir:
...
```

## tasks/main.yml

Structure: `Manage Orchestrator <Res> Block` (vars `ansible_async_dir`, `no_log` from `_secure_logging`) with
`block:` [module task, check-mode `error_flag` task, `collect_async_status` include loop] and `always:`
[async cleanup]. See `roles/orchestrator_projects/tasks/main.yml` and copy it.

Substitution points:

- Module task name: `Managing <Res>`; module `kenmoini.automation_orchestrator_config.<module>`.
- Loop var `__orchestrator_<res>_item`; async register `__orchestrator_<res>_job_async`;
  results loop var `__orchestrator_<res>_job_async_results_item`.
- Loop label: `"{{ __operation.verb }} <module> {{ __orchestrator_<res>_item.name }}"`.
- `__operation` comes from `operation_translate[<item>.state | default(orchestrator_state) | default('present')]`
  (provided by `global_vars`; keys present, absent, exists, enabled, disabled, rotated, launched, approved, rejected).
- Item fields map 1:1 to module params:
  - `name: "{{ item.name | mandatory }}"` (use the module's identifying key(s) instead if it is not `name`).
  - strings/dicts/lists: `"{{ item.<f> | default(omit, true) }}"`.
  - booleans: `"{{ item.<f> | default(omit) }}"`.
  - When enforce-defaults is meaningful for a field, use
    `default(('' if orchestrator_configuration_<res>_enforce_defaults else omit), true)` (use `{}`, `[]`, `false`, `0` as the typed default).
  - `register` is consumed by `collect_async_status` and is never passed to the module.
- State line (exact): `state: "{{ __orchestrator_<res>_item.state | default(orchestrator_state | default('present')) }}"`.
- Auth block (exact, on every module call):

```yaml
        orchestrator_host: "{{ orchestrator_hostname | default(omit, true) }}"
        orchestrator_username: "{{ orchestrator_username | default(omit, true) }}"
        orchestrator_password: "{{ orchestrator_password | default(omit, true) }}"
        orchestrator_token: "{{ orchestrator_token | default(omit, true) }}"
        orchestrator_client_id: "{{ orchestrator_client_id | default(omit, true) }}"
        orchestrator_client_secret: "{{ orchestrator_client_secret | default(omit, true) }}"
        validate_certs: "{{ orchestrator_validate_certs | default(omit) }}"
        request_timeout: "{{ orchestrator_request_timeout | default(10, true) }}"
```

- Async settings on the module task (exact):
  `async: "{{ ansible_check_mode | ternary(0, 1000) }}"`, `poll: 0`, `register: __orchestrator_<res>_job_async`,
  `changed_when: (__orchestrator_<res>_job_async.changed if ansible_check_mode else false)`.
- Wait include: `ansible.builtin.include_role` of `kenmoini.automation_orchestrator_config.collect_async_status`, with vars
  `cas_secure_logging`, `cas_async_delay`, `cas_async_retries` (from the role's `_secure_logging`/`_async_delay`/`_async_retries`),
  `cas_job_async_results_item: "{{ __orchestrator_<res>_job_async_results_item }}"`,
  `cas_register_subvar: orchestrator_<res>`, `cas_error_list_var_name: "orchestrator_<res>_errors"`,
  `__operation`, and `cas_object_label` (`<verb> Orchestrator <Module> <name> | Wait for finish the <module> <action>`).
  The item's identifying keys must be among those `collect_async_status/tasks/handle_error.yml` captures
  (`name`, `username`, `project`, `workflow`, `role`, `user`, `group`, `service_account`, `key`).
- Task names in `tasks/main.yml` are not subject to the `name[prefix]` lint rule (it only checks included task files); the reference naming is kept.
- Lines over 160 characters (yamllint) are folded with `>-`; do the same for any long expression or description.
- `always:` cleanup block is copied unchanged apart from the renamed variables.

## meta/main.yml

`galaxy_info`: `role_name: <res>`, `author: Ken Moini`, `description: An Ansible Role to create, update and delete <Res> in Automation Orchestrator.`
(adapt verbs to what the module supports), `license: GPL-3.0-or-later`, `min_ansible_version: 2.16.0`,
`platforms: [{name: EL, versions: [all]}]`, `galaxy_tags: [orchestrator, configuration, <res>]`.
`dependencies: [{role: global_vars}]` only. No `collections:` key and no `meta_dependency_check`.

## meta/argument_specs.yml

`argument_specs.main.options`, in order: `orchestrator_<res>` (list of dict; per-item options left as a
commented `#        options:` block, each with `required`, `type`, `description`, including `state` and `register`),
async vars (`orchestrator_configuration_<res>_async_retries`, `orchestrator_configuration_async_retries`, `_async_delay`,
`orchestrator_configuration_async_delay`, `_loop_delay`, `orchestrator_configuration_loop_delay`, `_enforce_defaults`,
`orchestrator_configuration_enforce_defaults`, `orchestrator_configuration_async_dir`), no_log vars
(`orchestrator_configuration_<res>_secure_logging`, `orchestrator_configuration_secure_logging`), and the generic auth
vars (`orchestrator_state`, `orchestrator_hostname`, `orchestrator_validate_certs`, `orchestrator_username`,
`orchestrator_password`, `orchestrator_token`, `orchestrator_client_id`, `orchestrator_client_secret`,
`orchestrator_request_timeout`). Copy these blocks verbatim from the projects role. ansible-lint `role-argument-spec` and `args` must pass.

## README.md

Sections in order: Description (mention permanence of `state: absent` where it applies), Requirements,
Variables (incl. auth vars and `orchestrator_<res>`), Enforcing defaults, Secure Logging Variables, Asynchronous
Retry Variables, `<Module>` Data Structure with a per-item variable table listing every item field plus `state`
and `register`, YAML and JSON examples, Playbook Examples using
`kenmoini.automation_orchestrator_config.orchestrator_<res>`, License
(`https://github.com/kenmoini/automation_orchestrator_configuration/blob/main/LICENSE`), Author (Ken Moini).

## tests

`tests/test.yml`: play on localhost with vars `orchestrator_validate_certs: false`, `orchestrator_hostname: orchestrator.example.com`,
`orchestrator_username: admin`, `orchestrator_password: changeme`; `pre_tasks` include_vars `dir: ./configs`;
`roles: [{role: ../.., when: orchestrator_<res> is defined}]`. `tests/configs/<res>.yml` holds two items named
`aoc-test-<module>-1` / `-2`. Verify with `--syntax-check` only; the module would otherwise connect.

## Substitution list (projects -> new resource)

Apply to a copy of `roles/orchestrator_projects` (order matters: longest first):

```sh
sed -e 's/__orchestrator_projects_item/__orchestrator_<res>_item/g' \
    -e 's/__orchestrator_projects_job_async/__orchestrator_<res>_job_async/g' \
    -e 's/orchestrator_configuration_projects_/orchestrator_configuration_<res>_/g' \
    -e 's/orchestrator_projects/orchestrator_<res>/g' \
    -e 's/automation_orchestrator_config\.project:/automation_orchestrator_config.<module>:/' \
    -e 's/Projects/<Res>/g' -e 's/Project/<Module>/g' \
    -e 's/projects/<res>/g' -e 's/project/<module>/g'
```

Then hand-edit: the item field lines in `tasks/main.yml`, the commented per-item options in
`argument_specs.yml`, the README data-structure table and examples, the description/tags in `meta/main.yml`,
and `tests/configs/<res>.yml`. The sed does not touch the module-specific fields; check every `description`/`labels`
line is replaced. Rename `tests/configs/projects.yml` to `tests/configs/<res>.yml`.

## Action-role variant

Roles wrapping `execution` / `approval` (actions, not resources) use a plain loop without async and without the
`collect_async_status` include (see Task 24). Keep the same defaults naming (minus async vars), auth block,
`operation_translate` labels and meta/README/tests layout.
