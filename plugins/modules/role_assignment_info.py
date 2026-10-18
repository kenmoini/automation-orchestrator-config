# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: role_assignment_info
short_description: Gather information about role assignments in the Automation Orchestrator
description:
  - Lists role assignments, optionally filtered by role, user, group, project, scope or principal type.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: The module only reads data.
  diff_mode:
    support: none
options:
  role:
    description: Name or UUID of a role. Return only assignments of this role. A UUID is converted to the role name.
    type: str
  user:
    description: Username or UUID of a user. Return only the assignments of this user.
    type: str
  group:
    description: Name or UUID of a group. Return only the assignments of this group.
    type: str
  project:
    description: Name or UUID of a project. Return only the assignments scoped to this project.
    type: str
  scope:
    description: Return only assignments with this scope.
    type: str
    choices: [system, project]
  principal_type:
    description: Return only assignments granted to this kind of principal.
    type: str
    choices: [user, group]
seealso:
  - module: kenmoini.automation_orchestrator_config.role_assignment
"""

EXAMPLES = r"""
- name: List all role assignments
  kenmoini.automation_orchestrator_config.role_assignment_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: assignments

- name: List the role assignments of a user
  kenmoini.automation_orchestrator_config.role_assignment_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    user: alice

- name: List the project-scoped assignments of a role
  kenmoini.automation_orchestrator_config.role_assignment_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    role: project-editor
    scope: project
...
"""

RETURN = r"""
resources:
  description: The matching role assignments.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 8a5d6c1e-6d0a-4a38-9a43-0a6f2f4f3c11
      principal_id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      group_id: null
      principal_name: alice
      principal_type: user
      role_name: project-editor
      project_id: null
      is_builtin: false
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule, is_uuid


def main():
    argument_spec = dict(
        role=dict(type="str"),
        user=dict(type="str"),
        group=dict(type="str"),
        project=dict(type="str"),
        scope=dict(type="str", choices=["system", "project"]),
        principal_type=dict(type="str", choices=["user", "group"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None
    role_name = params["role"]
    if role_name and is_uuid(role_name):
        role = module.resolve_obj("role", role_name, project_id=project_id)
        if role is None:
            module.fail_json(msg="role '{0}' not found".format(role_name))
        role_name = role["name"]

    query = module.build_desired(
        {
            "role_name": role_name or None,
            "principal_id": module.resolve_id("user", params["user"]) if params["user"] else None,
            "group_id": module.resolve_id("group", params["group"]) if params["group"] else None,
            "project_id": project_id,
            "scope": params["scope"],
            "principal_type": params["principal_type"],
        }
    )
    resources = module.get_all("/role_assignments", query, context="Failed to look up role assignments")
    module.exit_info(resources)


if __name__ == "__main__":
    main()
