# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: group
short_description: Manage groups in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes groups.
  - Groups are looked up by O(name). Only the options you set are compared and changed.
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
      - Name of the group, used to look it up.
    type: str
    required: true
  new_name:
    description:
      - Rename the group called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no group is called O(name) but one is called O(new_name), that group is used as is, so a rerun makes no change.
      - When neither group exists, the group is created with O(new_name).
    type: str
  description:
    description: Description of the group.
    type: str
  state:
    description:
      - V(present) creates the group or updates it to match the options.
      - V(exists) creates the group when it is missing and never modifies an existing one.
      - V(absent) deletes the group. Deletion is permanent. Built-in groups such as C(users) cannot be deleted.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.group_info
  - module: kenmoini.automation_orchestrator_config.user
"""

EXAMPLES = r"""
- name: Create a group
  kenmoini.automation_orchestrator_config.group:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: operators
    description: Platform operators

- name: Rename a group
  kenmoini.automation_orchestrator_config.group:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: operators
    new_name: platform-operators

- name: Delete a group
  kenmoini.automation_orchestrator_config.group:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: platform-operators
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the group, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
group:
  description: The group as returned by the API, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the group.
      type: str
    name:
      description: Name of the group.
      type: str
    description:
      description: Description of the group.
      type: str
    is_builtin:
      description: Whether this is a built-in group.
      type: bool
    created_by:
      description: Who created the group.
      type: str
    source:
      description: Where the group comes from.
      type: str
    member_count:
      description: Number of members.
      type: int
    labels:
      description: Labels of the group.
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
    description: Platform operators
    is_builtin: false
    member_count: 0
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "group"
    params = module.params

    if params["state"] == "present":
        existing = module.find_existing("/groups", params["name"], params["new_name"])
    else:
        existing = module.get_one_by_name("/groups", params["name"])

    if params["state"] == "absent":
        changed = module.delete_if_needed(existing, "/groups")
        module.exit_result(changed, None)

    if params["state"] == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if params["state"] == "present" and params["new_name"] else params["name"]
    desired = module.build_desired({"name": name, "description": params["description"]})
    changed, obj = module.create_or_update(existing, desired, "/groups")
    module.exit_result(changed, obj)


if __name__ == "__main__":
    main()
