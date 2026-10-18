# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: user_info
short_description: Gather information about users in the Automation Orchestrator
description:
  - Lists users, optionally filtered by username, name, authentication type or authentication source.
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
  username:
    description: Return only the user with exactly this username.
    type: str
  first_name:
    description: Filter users by first name, as supported by the API.
    type: str
  last_name:
    description: Filter users by last name, as supported by the API.
    type: str
  auth_type:
    description: Return only users with this authentication type.
    type: str
    choices: [local, federated]
  auth_source:
    description: Return only users that authenticate through this source, such as an identity provider.
    type: str
seealso:
  - module: kenmoini.automation_orchestrator_config.user
"""

EXAMPLES = r"""
- name: List all users
  kenmoini.automation_orchestrator_config.user_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: users

- name: Get one user
  kenmoini.automation_orchestrator_config.user_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    username: alice
  register: alice

- name: List federated users
  kenmoini.automation_orchestrator_config.user_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    auth_type: federated
...
"""

RETURN = r"""
resources:
  description: The matching users. At most one item when O(username) is given.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      username: alice
      email: alice@example.com
      first_name: Alice
      last_name: Admin
      is_enabled: true
      is_builtin: false
      auth_type: local
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(
        username=dict(type="str"),
        first_name=dict(type="str"),
        last_name=dict(type="str"),
        auth_type=dict(type="str", choices=["local", "federated"]),
        auth_source=dict(type="str"),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    query = module.build_desired({key: params[key] for key in ("username", "first_name", "last_name", "auth_type", "auth_source")})
    resources = module.get_all("/users", query)
    if params["username"] is not None:
        resources = [r for r in resources if r.get("username") == params["username"]]
    module.exit_info(resources)


if __name__ == "__main__":
    main()
