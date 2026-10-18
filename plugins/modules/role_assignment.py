# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: role_assignment
short_description: Manage role assignments in the Automation Orchestrator
description:
  - Grants a role to a user or a group, globally or within a project, and revokes it again.
  - Role assignments are immutable, so the module only creates or deletes them. An assignment is identified by its role, its principal and its project.
  - Without O(project) the assignment is global. A project assignment is never mistaken for a global one.
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
  role:
    description:
      - Name or UUID of the role to assign.
      - A UUID is converted to the role name because the API works with names.
      - Roles are looked up in the scope given by O(project).
    type: str
    required: true
  user:
    description:
      - Username or UUID of the user receiving the role.
      - Mutually exclusive with O(group). One of O(user) or O(group) is required.
    type: str
  group:
    description:
      - Name or UUID of the group receiving the role.
      - Mutually exclusive with O(user). One of O(user) or O(group) is required.
    type: str
  project:
    description:
      - Name or UUID of the project the assignment is scoped to. Omit it for a global assignment.
    type: str
  state:
    description:
      - V(present) creates the assignment when it is missing.
      - V(absent) deletes the assignment. Deletion is permanent. Built-in assignments cannot be deleted.
    type: str
    choices: [present, absent]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.role_assignment_info
  - module: kenmoini.automation_orchestrator_config.role
"""

EXAMPLES = r"""
- name: Grant a role to a user in a project
  kenmoini.automation_orchestrator_config.role_assignment:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    role: project-editor
    user: alice
    project: platform

- name: Grant a role to a group globally
  kenmoini.automation_orchestrator_config.role_assignment:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    role: operators
    group: platform-team

- name: Revoke a role
  kenmoini.automation_orchestrator_config.role_assignment:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    role: operators
    group: platform-team
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the role assignment, or V(null) when it was deleted or does not exist. In check mode a new assignment has no ID.
  returned: always
  type: str
  sample: 8a5d6c1e-6d0a-4a38-9a43-0a6f2f4f3c11
role_assignment:
  description: The role assignment as returned by the API, or V(null) when deleted or missing. In check mode a new assignment is the requested body.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the assignment.
      type: str
    principal_id:
      description: ID of the user, or V(null) for a group.
      type: str
    group_id:
      description: ID of the group, or V(null) for a user.
      type: str
    principal_name:
      description: Name of the user or group.
      type: str
    principal_type:
      description: Either V(user) or V(group).
      type: str
    role_name:
      description: Name of the role.
      type: str
    project_id:
      description: ID of the project, or V(null) for a global assignment.
      type: str
    project_name:
      description: Name of the project, or V(null) for a global assignment.
      type: str
    is_builtin:
      description: Whether this is a built-in assignment.
      type: bool
    created_at:
      description: Creation timestamp.
      type: str
  sample:
    id: 8a5d6c1e-6d0a-4a38-9a43-0a6f2f4f3c11
    principal_type: user
    principal_name: alice
    role_name: project-editor
    project_id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    is_builtin: false
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule, is_uuid


def main():
    argument_spec = dict(
        role=dict(type="str", required=True),
        user=dict(type="str"),
        group=dict(type="str"),
        project=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )
    module = OrchestratorModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[["user", "group"]],
        required_one_of=[["user", "group"]],
    )
    module.result_key = "role_assignment"
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None

    role_name = params["role"]
    if is_uuid(role_name):
        role = module.resolve_obj("role", role_name, project_id=project_id)
        if role is None:
            module.fail_json(msg="role '{0}' not found".format(role_name))
        role_name = role["name"]

    if params["user"]:
        principal_kind, principal_label, principal_key, principal_type = "user", params["user"], "principal_id", "user"
    else:
        principal_kind, principal_label, principal_key, principal_type = "group", params["group"], "group_id", "group"
    principal_id = module.resolve_id(principal_kind, principal_label)

    query = module.build_desired({"role_name": role_name, "project_id": project_id, principal_key: principal_id})
    try:
        found = module.get_all("/role_assignments", query)
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to look up role assignments")
    matches = []
    for item in found:
        if item.get("principal_type") != principal_type or item.get("role_name") != role_name:
            continue
        if item.get(principal_key) != principal_id or (item.get("project_id") or None) != project_id:
            continue
        matches.append(item)
    if len(matches) > 1:
        module.fail_json(
            msg="Found {0} role assignments for role '{1}' and {2} '{3}'{4}".format(
                len(matches), role_name, principal_kind, principal_label, " in project '{0}'".format(params["project"]) if project_id else ""
            )
        )
    existing = matches[0] if matches else None
    desired = module.build_desired({"role_name": role_name, principal_key: principal_id, "project_id": project_id})
    context = "role assignment '{0}' for {1} '{2}'".format(role_name, principal_kind, principal_label)

    if params["state"] == "absent":
        if existing is None:
            module.exit_result(False, None)
        if existing.get("is_builtin"):
            module.fail_json(msg="Cannot delete built-in {0}".format(context))
        module._diff = {"before": existing, "after": {}}
        if not module.check_mode:
            try:
                module.request("DELETE", "/role_assignments/{0}".format(existing["id"]), expect=(200, 202, 204))
            except OrchestratorAPIError as err:
                if err.status != 404:
                    module.fail_api(err, "Failed to delete {0}".format(context))
                module._diff = {"before": {}, "after": {}}
                module.exit_result(False, None)
        module.exit_result(True, None)

    if existing is not None:
        module.exit_result(False, existing)

    module._diff = {"before": {}, "after": desired}
    if module.check_mode:
        module.exit_result(True, desired)
    try:
        obj = module.request("POST", "/role_assignments", data=desired)
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to create {0}".format(context))
    module.exit_result(True, obj if obj is not None else desired)


if __name__ == "__main__":
    main()
