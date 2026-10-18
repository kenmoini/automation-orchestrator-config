# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: service_account
short_description: Manage service accounts in the Automation Orchestrator
description:
  - Creates, updates, enables, disables and deletes service accounts. A service account belongs to one project.
  - Use M(kenmoini.automation_orchestrator_config.service_account_credential) to manage the client credentials of a service account.
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
      - Name of the service account. Names are looked up within the project given by O(project).
    type: str
    required: true
  new_name:
    description:
      - New name for the service account.
      - When O(name) does not exist but O(new_name) does, that account is treated as the already renamed one, so reruns stay idempotent.
    type: str
  description:
    description:
      - Description of the service account.
    type: str
  project:
    description:
      - Name or UUID of the project the service account belongs to.
      - The project cannot be changed on an existing service account.
    type: str
    required: true
  state:
    description:
      - V(present) creates the service account when it is missing and updates its metadata.
      - V(exists) only creates the service account when it is missing and never updates it.
      - V(enabled) and V(disabled) ensure the service account exists, like V(present), and then enable or disable it when its status differs.
      - V(absent) deletes the service account. Deletion is permanent.
    type: str
    choices: [present, absent, exists, enabled, disabled]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.service_account_info
  - module: kenmoini.automation_orchestrator_config.service_account_credential
  - module: kenmoini.automation_orchestrator_config.project
"""

EXAMPLES = r"""
- name: Create a service account
  kenmoini.automation_orchestrator_config.service_account:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ci-pipeline
    description: Used by the CI pipeline
    project: platform

- name: Disable a service account
  kenmoini.automation_orchestrator_config.service_account:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ci-pipeline
    project: platform
    state: disabled

- name: Delete a service account
  kenmoini.automation_orchestrator_config.service_account:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ci-pipeline
    project: platform
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the service account, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 5f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
service_account:
  description: The service account as returned by the API, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the service account.
      type: str
    name:
      description: Name of the service account.
      type: str
    description:
      description: Description of the service account.
      type: str
    status:
      description: Either V(active) or V(disabled).
      type: str
    project_id:
      description: ID of the project.
      type: str
    project_name:
      description: Name of the project.
      type: str
    last_authenticated_at:
      description: Timestamp of the last authentication, or V(null).
      type: str
    labels:
      description: Read-only labels.
      type: dict
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Last update timestamp.
      type: str
  sample:
    id: 5f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: ci-pipeline
    description: Used by the CI pipeline
    status: active
    project_id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    project_name: platform
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        project=dict(type="str", required=True),
        state=dict(type="str", default="present", choices=["present", "absent", "exists", "enabled", "disabled"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "service_account"
    params = module.params
    state = params["state"]

    project_id = module.resolve_id("project", params["project"])
    if state in ("present", "enabled", "disabled"):
        existing = module.find_existing("/service_accounts", params["name"], params["new_name"], kind="service_account", project_id=project_id)
    else:
        existing = module.resolve_obj("service_account", params["name"], project_id=project_id)

    if state == "absent":
        changed = module.delete_if_needed(existing, "/service_accounts", item_label="service account")
        module.exit_result(changed, None)
    if state == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if state != "exists" and params["new_name"] else params["name"]
    desired = module.build_desired({"name": name, "description": params["description"], "project_id": project_id})
    changed, obj = module.create_or_update(existing, desired, "/service_accounts", immutable=("project_id",), item_label="service account")

    if state in ("enabled", "disabled"):
        action = "enable" if state == "enabled" else "disable"
        wanted_status = "active" if state == "enabled" else "disabled"
        if obj.get("status", "active") != wanted_status:
            changed = True
            before = dict(module._diff["before"]) if module._diff else {}
            after = dict(module._diff["after"]) if module._diff else {}
            before["status"] = obj.get("status", "active")
            after["status"] = wanted_status
            module._diff = {"before": before, "after": after}
            if module.check_mode:
                obj = dict(obj, status=wanted_status)
            else:
                try:
                    updated = module.request("POST", "/service_accounts/{0}/{1}".format(obj["id"], action))
                except OrchestratorAPIError as err:
                    module.fail_api(err, "Failed to {0} service account '{1}'".format(action, obj.get("name")))
                obj = updated if updated is not None else dict(obj, status=wanted_status)
    module.exit_result(changed, obj)


if __name__ == "__main__":
    main()
