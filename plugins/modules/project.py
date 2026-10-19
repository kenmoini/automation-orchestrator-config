# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: project
short_description: Manage projects in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes projects.
  - Projects are looked up by O(name). Only the options you set are compared and changed.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Changes are computed and reported but not made.
  diff_mode:
    support: full
    description: Shows the fields that change, before and after.
options:
  name:
    description:
      - Name of the project, used to look it up.
      - The API validates the name against C(^[a-zA-Z0-9]([a-zA-Z0-9:_-]*[a-zA-Z0-9])?$).
    type: str
    required: true
  new_name:
    description:
      - Rename the project called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no project is called O(name) but one is called O(new_name), that project is used as is, so a rerun makes no change.
      - When neither project exists, the project is created with O(new_name).
    type: str
  description:
    description: Description of the project.
    type: str
  labels:
    description: Labels of the project as key/value pairs.
    type: dict
  state:
    description:
      - V(present) creates the project or updates it to match the options.
      - V(exists) creates the project when it is missing and never modifies an existing one.
      - V(absent) deletes the project. Deletion is permanent. The built-in default project cannot be deleted.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.project_info
"""

EXAMPLES = r"""
- name: Create a project
  kenmoini.automation_orchestrator_config.project:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: platform
    description: Platform team automation
    labels:
      team: platform

- name: Rename a project
  kenmoini.automation_orchestrator_config.project:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: platform
    new_name: platform-engineering

- name: Delete a project
  kenmoini.automation_orchestrator_config.project:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: platform-engineering
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the project, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
project:
  description: The project as returned by the API, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the project.
      type: str
    name:
      description: Name of the project.
      type: str
    description:
      description: Description of the project.
      type: str
    labels:
      description: Labels of the project.
      type: dict
    is_default:
      description: Whether this is the default project.
      type: bool
    is_builtin:
      description: Whether this is a built-in project.
      type: bool
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Last update timestamp.
      type: str
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: platform
    description: Platform team automation
    labels:
      team: platform
    is_default: false
    is_builtin: false
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        labels=dict(type="dict"),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "project"
    params = module.params

    if params["state"] == "present":
        existing = module.find_existing("/projects", params["name"], params["new_name"])
    else:
        existing = module.get_one_by_name("/projects", params["name"])

    if params["state"] == "absent":
        changed = module.delete_if_needed(existing, "/projects")
        module.exit_result(changed, None)

    if params["state"] == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if params["state"] == "present" and params["new_name"] else params["name"]
    desired = module.build_desired({"name": name, "description": params["description"], "labels": params["labels"]})
    changed, obj = module.create_or_update(existing, desired, "/projects")
    module.exit_result(changed, obj)


if __name__ == "__main__":
    main()
