# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: role
short_description: Manage roles in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes roles.
  - Roles are looked up by O(name) within the scope given by O(project). Without O(project) only system-scoped roles are considered.
  - Only the options you set are compared and changed. Policies are compared regardless of their order.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
  diff_mode:
    support: full
options:
  name:
    description:
      - Name of the role, used to look it up.
      - Must start and end with a letter or digit and may contain letters, digits, C(:), C(_) and C(-). The API validates the name.
    type: str
    required: true
  new_name:
    description:
      - Rename the role called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no role is called O(name) but one is called O(new_name), that role is used as is, so a rerun makes no change.
      - When neither role exists, the role is created with O(new_name).
    type: str
  description:
    description: Description of the role.
    type: str
  policies:
    description:
      - Policies granted by the role, as names or UUIDs. Required when the role is created.
      - UUIDs are converted to policy names because the API works with names.
      - Policies are looked up in the scope given by O(project).
      - The order does not matter when comparing.
    type: list
    elements: str
  labels:
    description: Labels of the role as a dictionary.
    type: dict
  project:
    description:
      - Name or UUID of the project the role belongs to. Omit it for a system-scoped role.
      - The project cannot be changed on an existing role.
    type: str
  state:
    description:
      - V(present) creates the role or updates it to match the options.
      - V(exists) creates the role when it is missing and never modifies an existing one.
      - V(absent) deletes the role. Deletion is permanent. Built-in roles cannot be deleted.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.role_info
  - module: kenmoini.automation_orchestrator_config.policy
"""

EXAMPLES = r"""
- name: Create a system role
  kenmoini.automation_orchestrator_config.role:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: operators
    description: Platform operators
    policies:
      - workflow-reader
      - workflow-runner

- name: Create a role in a project
  kenmoini.automation_orchestrator_config.role:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: project-editor
    project: platform
    policies:
      - project-editor

- name: Delete a role
  kenmoini.automation_orchestrator_config.role:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: operators
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the role, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
role:
  description: The role as returned by the API, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the role.
      type: str
    name:
      description: Name of the role.
      type: str
    description:
      description: Description of the role.
      type: str
    policies:
      description: Names of the policies of the role.
      type: list
      elements: str
    is_builtin:
      description: Whether this is a built-in role.
      type: bool
    project_id:
      description: ID of the project the role belongs to, or V(null) for a system role.
      type: str
    scope:
      description: Scope of the role.
      type: str
    labels:
      description: Labels of the role.
      type: dict
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Last update timestamp.
      type: str
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: operators
    policies: [workflow-reader, workflow-runner]
    is_builtin: false
    project_id: null
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule, is_uuid


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        policies=dict(type="list", elements="str"),
        labels=dict(type="dict"),
        project=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "role"
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None

    if params["state"] == "present":
        existing = module.find_existing("/roles", params["name"], params["new_name"], kind="role", project_id=project_id)
    else:
        existing = module.resolve_obj("role", params["name"], project_id)

    if params["state"] == "absent":
        changed = module.delete_if_needed(existing, "/roles", item_label="role")
        module.exit_result(changed, None)

    if params["state"] == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if params["state"] == "present" and params["new_name"] else params["name"]
    if existing is None and not params["policies"]:
        module.fail_json(msg="policies is required to create role '{0}'".format(name))

    policies = None
    if params["policies"] is not None:
        policies = []
        for value in params["policies"]:
            if is_uuid(value):
                policy = module.resolve_obj("policy", value, project_id=project_id)
                if policy is None:
                    module.fail_json(msg="policy '{0}' not found".format(value))
                value = policy["name"]
            policies.append(value)

    desired = module.build_desired(
        {
            "name": name,
            "description": params["description"],
            "policies": policies,
            "labels": params["labels"],
            "project_id": project_id,
        }
    )
    changed, obj = module.create_or_update(existing, desired, "/roles", immutable=("project_id",), item_label="role")
    module.exit_result(changed, obj)


if __name__ == "__main__":
    main()
