# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: setting_info
short_description: Gather information about runtime settings of the Automation Orchestrator
description:
  - Lists runtime settings, optionally one by key or filtered by category and group, or lists the settings categories.
  - Sensitive setting values, such as passwords, are returned as the API provides them. Protect the registered result accordingly.
  - The C(value_type) of a setting is one of V(string), V(integer), V(float), V(boolean) or V(json).
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
    description:
      - Key of one setting to return. An unknown key returns an empty list.
      - Not combined with O(category) or O(group).
    type: str
  category:
    description: Return only settings of this category slug.
    type: str
  group:
    description: Return only settings of this group.
    type: str
  categories:
    description: When V(true), return the settings categories instead of settings.
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.setting
"""

EXAMPLES = r"""
- name: List all settings
  kenmoini.automation_orchestrator_config.setting_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: settings

- name: Get one setting
  kenmoini.automation_orchestrator_config.setting_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: general.session_timeout

- name: List the settings categories
  kenmoini.automation_orchestrator_config.setting_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    categories: true
...
"""

RETURN = r"""
resources:
  description: The matching settings, or the settings categories when O(categories=true).
  returned: always
  type: list
  elements: dict
  sample:
    - key: general.session_timeout
      category: general
      group: core
      value: null
      default_value: 3600
      effective_value: 3600
      value_type: integer
      requires_restart: false
      version: 1
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str"),
        category=dict(type="str"),
        group=dict(type="str"),
        categories=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    try:
        if params["categories"]:
            body = module.request("GET", "/settings/categories")
            resources = (body or {}).get("resources") or [] if isinstance(body, dict) else []
        elif params["name"]:
            try:
                row = module.request("GET", "/settings/{0}".format(params["name"]))
            except OrchestratorAPIError as err:
                if err.status != 404:
                    raise
                row = None
            resources = [row] if row else []
        else:
            resources = module.get_all("/settings", module.build_desired({"category": params["category"], "group": params["group"]}))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to look up settings")
    module.exit_info(resources)


if __name__ == "__main__":
    main()
