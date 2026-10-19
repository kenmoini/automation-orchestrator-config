# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: credential_type_info
short_description: Gather information about credential types in the Automation Orchestrator
description:
  - Lists credential types, optionally only the one called O(name).
  - The V(inputs) and V(injectors) of a credential type are schemas, not secrets, and are returned as they are.
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
    description: The module does not produce a diff.
options:
  name:
    description:
      - Return only the credential type with exactly this name.
      - The API has no name filter, so the match is done after listing all credential types.
    type: str
seealso:
  - module: kenmoini.automation_orchestrator_config.credential
  - module: kenmoini.automation_orchestrator_config.credential_info
"""

EXAMPLES = r"""
- name: List all credential types
  kenmoini.automation_orchestrator_config.credential_type_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: credential_types

- name: Get the input schema of one credential type
  kenmoini.automation_orchestrator_config.credential_type_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: Machine
  register: machine_type
...
"""

RETURN = r"""
resources:
  description: The matching credential types. At most one item when O(name) is given.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: ID of the credential type.
      type: str
    name:
      description: Name of the credential type.
      type: str
    description:
      description: Description of the credential type.
      type: str
    inputs:
      description: Schema of the inputs a credential of this type takes.
      type: dict
    injectors:
      description: Injectors that expose the credential inputs to jobs.
      type: dict
    managed:
      description: Whether the credential type is built in.
      type: bool
    credential_count:
      description: Number of credentials of this type.
      type: int
    labels:
      description: Labels of the credential type.
      type: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: Machine
      inputs:
        fields:
          - id: password
            label: Password
            secret: true
      injectors: {}
      managed: true
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str"),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    resources = module.get_all("/credential_types")
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]
    module.exit_info(resources, strip_defaults=False)


if __name__ == "__main__":
    main()
