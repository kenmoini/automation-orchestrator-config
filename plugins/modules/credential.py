# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: credential
short_description: Manage credentials in the Automation Orchestrator
description:
  - Creates, updates, renames and deletes credentials of a project.
  - Credentials are looked up by O(name) within O(project). Only the options you set are compared and changed.
  - The API never returns secret values, so O(inputs) cannot be compared with the existing credential.
    With O(update_secrets=true) any task that supplies O(inputs) sends them and reports a change on every run.
    Set O(update_secrets=false) to make runs idempotent once the secrets are in place.
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
    description: Name of the credential, used to look it up within O(project).
    type: str
    required: true
  new_name:
    description:
      - Rename the credential called O(name) to this name. Only used when O(state=present).
      - The module is idempotent. When no credential is called O(name) but one is called O(new_name), that credential is used as is, so a rerun makes no change.
      - When neither credential exists, the credential is created with O(new_name).
    type: str
  description:
    description: Description of the credential.
    type: str
  credential_type:
    description:
      - Name or ID of the credential type, see M(kenmoini.automation_orchestrator_config.credential_type_info).
      - Required to create a credential.
      - It cannot be changed on an existing credential.
    type: str
  project:
    description:
      - Name or ID of the project that owns the credential.
      - It cannot be changed on an existing credential.
    type: str
    required: true
  inputs:
    description:
      - Secret and non-secret values of the credential, following the input schema of its credential type.
      - Sent whole when set and O(update_secrets=true), and never compared with the existing credential.
    type: dict
  enabled:
    description: Whether the credential is enabled.
    type: bool
  labels:
    description: Labels of the credential as key/value pairs.
    type: dict
  update_secrets:
    description:
      - When V(true), O(inputs) are sent on every update and the task reports a change.
      - When V(false), O(inputs) are only used to create the credential and are ignored on existing ones.
    type: bool
    default: true
  state:
    description:
      - V(present) creates the credential or updates it to match the options.
      - V(exists) creates the credential when it is missing and never modifies an existing one.
      - V(absent) deletes the credential. Deletion is permanent.
    type: str
    choices: [present, absent, exists]
    default: present
seealso:
  - module: kenmoini.automation_orchestrator_config.credential_info
  - module: kenmoini.automation_orchestrator_config.credential_type_info
"""

EXAMPLES = r"""
- name: Create a credential
  kenmoini.automation_orchestrator_config.credential:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ssh-prod
    project: platform
    credential_type: Machine
    inputs:
      username: automation
      password: "{{ vault_ssh_password }}"

- name: Update the description without touching the secrets
  kenmoini.automation_orchestrator_config.credential:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ssh-prod
    project: platform
    description: Production SSH access
    inputs:
      username: automation
      password: "{{ vault_ssh_password }}"
    update_secrets: false

- name: Delete a credential
  kenmoini.automation_orchestrator_config.credential:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ssh-prod
    project: platform
    state: absent
...
"""

RETURN = r"""
id:
  description: ID of the credential, or V(null) when it was deleted or does not exist.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
credential:
  description: The credential as returned by the API with V(inputs) masked, or V(null) when it was deleted or does not exist.
  returned: always
  type: dict
  contains:
    id:
      description: ID of the credential.
      type: str
    name:
      description: Name of the credential.
      type: str
    description:
      description: Description of the credential.
      type: str
    credential_type_id:
      description: ID of the credential type.
      type: str
    project_id:
      description: ID of the project.
      type: str
    inputs:
      description: Always masked as V($encrypted$).
      type: str
    enabled:
      description: Whether the credential is enabled.
      type: bool
    labels:
      description: Labels of the credential.
      type: dict
    created_at:
      description: Creation timestamp.
      type: str
    updated_at:
      description: Last update timestamp.
      type: str
  sample:
    id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    name: ssh-prod
    credential_type_id: 5b0a7c1e-2f3d-4e6a-8b9c-0d1e2f3a4b5c
    project_id: 9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d
    inputs: $encrypted$
    enabled: true
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str", required=True),
        new_name=dict(type="str"),
        description=dict(type="str"),
        credential_type=dict(type="str"),
        project=dict(type="str", required=True),
        inputs=dict(type="dict", no_log=True),
        enabled=dict(type="bool"),
        labels=dict(type="dict"),
        update_secrets=dict(type="bool", default=True),
        state=dict(type="str", default="present", choices=["present", "absent", "exists"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    module.result_key = "credential"
    params = module.params

    project_id = module.resolve_id("project", params["project"])

    if params["state"] == "present":
        existing = module.find_existing(None, params["name"], params["new_name"], kind="credential", project_id=project_id)
    else:
        existing = module.resolve_obj("credential", params["name"], project_id)

    if params["state"] == "absent":
        changed = module.delete_if_needed(existing, "/credentials", item_label="credential")
        module.exit_result(changed, None)

    if params["state"] == "exists" and existing is not None:
        module.exit_result(False, existing)

    name = params["new_name"] if params["state"] == "present" and params["new_name"] else params["name"]
    if existing is None and not params["credential_type"]:
        module.fail_json(msg="credential_type is required to create credential '{0}'".format(name))

    type_id = module.resolve_id("credential_type", params["credential_type"]) if params["credential_type"] else None
    desired = module.build_desired(
        {
            "name": name,
            "description": params["description"],
            "credential_type_id": type_id,
            "project_id": project_id,
            "inputs": params["inputs"],
            "enabled": params["enabled"],
            "labels": params["labels"],
        }
    )
    changed, obj = module.create_or_update(
        existing,
        desired,
        "/credentials",
        secret_fields=("inputs",),
        update_secrets=params["update_secrets"],
        immutable=("credential_type_id", "project_id"),
        item_label="credential",
    )
    module.exit_result(changed, obj)


if __name__ == "__main__":
    main()
