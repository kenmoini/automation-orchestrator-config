# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: credential_info
short_description: Gather information about credentials in the Automation Orchestrator
description:
  - Lists the credentials of a project, optionally filtered by name, credential type or enabled flag.
  - The API returns metadata only, and the V(inputs) of every credential are masked in the result.
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
  project:
    description: Name or ID of the project whose credentials are listed.
    type: str
    required: true
  name:
    description:
      - Return only the credential with exactly this name.
      - The API has no name filter, so the match is done after listing.
    type: str
  credential_type:
    description: Return only credentials of this credential type, given by name or ID.
    type: str
  enabled:
    description: Return only credentials whose enabled flag equals this value.
    type: bool
seealso:
  - module: kenmoini.automation_orchestrator_config.credential
  - module: kenmoini.automation_orchestrator_config.credential_type_info
"""

EXAMPLES = r"""
- name: List the credentials of a project
  kenmoini.automation_orchestrator_config.credential_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
  register: credentials

- name: Find enabled credentials of one type
  kenmoini.automation_orchestrator_config.credential_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
    credential_type: Machine
    enabled: true
...
"""

RETURN = r"""
resources:
  description: The matching credentials, with V(inputs) masked. At most one item when O(name) is given.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: ssh-prod
      credential_type_id: 5b0a7c1e-2f3d-4e6a-8b9c-0d1e2f3a4b5c
      project_id: 9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d
      enabled: true
      inputs: $encrypted$
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        project=dict(type="str", required=True),
        name=dict(type="str"),
        credential_type=dict(type="str"),
        enabled=dict(type="bool"),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    project_id = module.resolve_id("project", params["project"])
    type_id = module.resolve_id("credential_type", params["credential_type"]) if params["credential_type"] else None
    query = module.build_desired({"credential_type_id": type_id, "enabled": params["enabled"]})
    resources = module.get_all("/projects/{0}/credentials".format(project_id), query)
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]
    module.exit_info(resources)


if __name__ == "__main__":
    main()
