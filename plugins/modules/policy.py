# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: policy
short_description: Manage policies in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes policies.
  - Policies are looked up by O(name) within the scope given by O(project). Without O(project) only system-scoped policies are considered.
  - Only the options you set are compared and changed. Statements are compared regardless of their order.
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
      - Name of the policy, used to look it up.
      - Must start and end with a letter or digit and may contain letters, digits, C(:), C(_) and C(-). The API validates the name.
    type: str
    required: true
  new_name:
    description:
      - Rename the policy called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no policy is called O(name) but one is called O(new_name), that policy is used as is, so a rerun makes no change.
      - When neither policy exists, the policy is created with O(new_name).
    type: str
  description:
    description: Description of the policy.
    type: str
  statements:
    description:
      - Statements of the policy. Required when the policy is created.
      - Each statement is a dictionary with the keys C(effect) (V(allow) or V(deny)), C(actions) (list of action strings),
        C(scope) (V(any), V(self) or V(project)) and optionally C(conditions) (dictionary).
      - The order of the statements and of the actions inside a statement does not matter when comparing.
    type: list
    elements: dict
  labels:
    description: Labels of the policy as a dictionary.
    type: dict
  project:
    description:
      - Name or UUID of the project the policy belongs to. Omit it for a system-scoped policy.
      - The project cannot be changed on an existing policy.
    type: str
  state:
    description:
      - V(present) creates the policy or updates it to match the options.
      - V(exists) creates the policy when it is missing and never modifies an existing one.
      - V(absent) deletes the policy. Deletion is permanent. Built-in policies cannot be deleted.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.policy_info
  - module: kenmoini.automation_orchestrator_config.role
"""

EXAMPLES = r"""
- name: Create a system policy
  kenmoini.automation_orchestrator_config.policy:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: workflow-reader
    description: Read access to workflows
    statements:
      - effect: allow
        actions: [workflow:read, workflow:list]
        scope: any

- name: Create a policy in a project
  kenmoini.automation_orchestrator_config.policy:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: project-editor
    project: platform
    statements:
      - effect: allow
        actions: [workflow:update]
        scope: project

- name: Delete a policy
  kenmoini.automation_orchestrator_config.policy:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: workflow-reader
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the policy, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
policy:
  description: The policy as returned by the API, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the policy.
      type: str
    name:
      description: Name of the policy.
      type: str
    description:
      description: Description of the policy.
      type: str
    statements:
      description: Statements of the policy.
      type: list
      elements: dict
    is_builtin:
      description: Whether this is a built-in policy.
      type: bool
    project_id:
      description: ID of the project the policy belongs to, or V(null) for a system policy.
      type: str
    scope:
      description: Scope of the policy.
      type: str
    labels:
      description: Labels of the policy.
      type: dict
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Last update timestamp.
      type: str
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: workflow-reader
    is_builtin: false
    project_id: null
    statements:
      - effect: allow
        actions: [workflow:read]
        scope: any
        conditions: null
"""

import json

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def _normalize_statements(statements):
    """Return ``statements`` in an order-insensitive comparison form (None values dropped, actions and statements sorted)."""
    result = []
    for stmt in statements or []:
        item = dict((k, v) for k, v in stmt.items() if v is not None)
        if isinstance(item.get("actions"), list):
            item["actions"] = sorted(item["actions"])
        result.append(item)
    return sorted(result, key=lambda item: json.dumps(item, sort_keys=True))


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        statements=dict(type="list", elements="dict"),
        labels=dict(type="dict"),
        project=dict(type="str"),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "policy"
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None

    if params["state"] == "present":
        existing = module.find_existing("/policies", params["name"], params["new_name"], kind="policy", project_id=project_id)
    else:
        existing = module.resolve_obj("policy", params["name"], project_id)

    if params["state"] == "absent":
        changed = module.delete_if_needed(existing, "/policies", item_label="policy")
        module.exit_result(changed, None)

    if params["state"] == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if params["state"] == "present" and params["new_name"] else params["name"]
    if existing is None and not params["statements"]:
        module.fail_json(msg="statements is required to create policy '{0}'".format(name))

    desired = module.build_desired(
        {
            "name": name,
            "description": params["description"],
            "statements": params["statements"],
            "labels": params["labels"],
            "project_id": project_id,
        }
    )
    if existing is not None and "statements" in desired and _normalize_statements(existing.get("statements")) == _normalize_statements(desired["statements"]):
        del desired["statements"]
    changed, obj = module.create_or_update(existing, desired, "/policies", immutable=("project_id",), item_label="policy")
    module.exit_result(changed, obj)


if __name__ == "__main__":
    main()
