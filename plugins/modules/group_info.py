# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: group_info
short_description: Gather information about groups in the Automation Orchestrator
description:
  - Lists groups, optionally returning only the one with a given name.
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
    description: Return only the group with exactly this name.
    type: str
seealso:
  - module: kenmoini.automation_orchestrator_config.group
"""

EXAMPLES = r"""
- name: List all groups
  kenmoini.automation_orchestrator_config.group_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: groups

- name: Get one group by name
  kenmoini.automation_orchestrator_config.group_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: operators
  register: operators
...
"""

RETURN = r"""
resources:
  description: The matching groups. At most one item when O(name) is given.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: operators
      description: Platform operators
      is_builtin: false
      source: local
      member_count: 3
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str"),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    resources = module.get_all("/groups")
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]
    module.exit_info(resources)


if __name__ == "__main__":
    main()
