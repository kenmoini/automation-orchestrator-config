# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: policy_info
short_description: Gather information about policies in the Automation Orchestrator
description:
  - Lists policies, optionally filtered by name, project, built-in flag or scope.
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
  name:
    description: Return only the policy with exactly this name.
    type: str
  project:
    description: Name or UUID of a project. Return only the policies of this project.
    type: str
  is_builtin:
    description: Return only policies whose built-in flag equals this value.
    type: bool
  scope:
    description: Return only policies with this scope, as filtered by the API.
    type: str
    choices: [system, project]
seealso:
  - module: kenmoini.automation_orchestrator_config.policy
"""

EXAMPLES = r"""
- name: List all policies
  kenmoini.automation_orchestrator_config.policy_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: policies

- name: Get one policy by name
  kenmoini.automation_orchestrator_config.policy_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: workflow-reader

- name: List the policies of a project
  kenmoini.automation_orchestrator_config.policy_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
...
"""

RETURN = r"""
resources:
  description: The matching policies. At most one item when O(name) is given.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: workflow-reader
      description: Read access to workflows
      is_builtin: false
      project_id: null
      scope: system
      labels: {}
      statements:
        - effect: allow
          actions: [workflow:read]
          scope: any
          conditions: null
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str"),
        project=dict(type="str"),
        is_builtin=dict(type="bool"),
        scope=dict(type="str", choices=["system", "project"]),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None
    query = module.build_desired({"name": params["name"], "project_id": project_id, "is_builtin": params["is_builtin"], "scope": params["scope"]})
    resources = module.get_all("/policies", query)
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]
    module.exit_info(resources)


if __name__ == "__main__":
    main()
