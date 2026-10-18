# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: identity_provider_info
short_description: Gather information about identity providers in the Automation Orchestrator
description:
  - Lists the OIDC identity providers, optionally only the one with a given name.
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
      - Return only the identity provider with exactly this name.
      - The API has no name filter, so the match is done after listing.
    type: str
seealso:
  - module: kenmoini.automation_orchestrator_config.identity_provider
"""

EXAMPLES = r"""
- name: List all identity providers
  kenmoini.automation_orchestrator_config.identity_provider_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: idps

- name: Get one identity provider
  kenmoini.automation_orchestrator_config.identity_provider_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: corporate-sso
  register: sso
...
"""

RETURN = r"""
resources:
  description: The matching identity providers. At most one item when O(name) is given.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: corporate-sso
      enabled: true
      configuration:
        provider_type: oidc
        issuer_url: https://sso.example.com/realms/corp
        client_id: automation-orchestrator
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def main():
    argument_spec = dict(name=dict(type="str"))
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    resources = module.get_all("/identity_providers", context="Failed to list identity providers")
    if module.params["name"] is not None:
        resources = [r for r in resources if r.get("name") == module.params["name"]]
    module.exit_info(resources)


if __name__ == "__main__":
    main()
