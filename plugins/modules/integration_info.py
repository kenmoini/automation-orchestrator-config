# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: integration_info
short_description: Gather information about integrations in the Automation Orchestrator
description:
  - Lists integrations, optionally filtered by name, type, enabled flag, scope or project.
  - Can attach the models and tools of every returned integration.
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
      - Return only the integration with exactly this name.
      - The API has no name filter, so the match is done after listing.
    type: str
  integration_type:
    description: Return only integrations of this type.
    type: str
    choices: [mcp_server, llm_provider, ansible_automation_platform]
  enabled:
    description: Return only integrations whose enabled flag equals this value.
    type: bool
  scope:
    description: Return only integrations with this scope.
    type: str
    choices: [global, project]
  project:
    description: Return only integrations available to this project, given by name or ID.
    type: str
  include_models:
    description: Add the models of every returned integration as RV(resources[].models).
    type: bool
    default: false
  include_tools:
    description: Add the tools of every returned integration as RV(resources[].tools).
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.integration
"""

EXAMPLES = r"""
- name: List all integrations
  kenmoini.automation_orchestrator_config.integration_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
  register: integrations

- name: Get one LLM provider with its models
  kenmoini.automation_orchestrator_config.integration_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: openai
    integration_type: llm_provider
    include_models: true
  register: openai
...
"""

RETURN = r"""
resources:
  description: The matching integrations. At most one item when O(name) is given.
  returned: always
  type: list
  elements: dict
  contains:
    models:
      description: The models of the integration.
      returned: when O(include_models=true)
      type: list
      elements: dict
    tools:
      description: The tools of the integration.
      returned: when O(include_tools=true)
      type: list
      elements: dict
  sample:
    - id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: openai
      integration_type: llm_provider
      enabled: true
      scope: global
      configuration:
        integration_type: llm_provider
        provider_hint: openai
      models:
        - id: 5b0a7c1e-2f3d-4e6a-8b9c-0d1e2f3a4b5c
          model_id: gpt-4o
          enabled: true
          is_default: true
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorModule


def _attach(module, integration, kind):
    """Set ``integration[kind]`` to the models or tools of ``integration``."""
    integration[kind] = module.get_all(
        "/integrations/{0}/{1}".format(integration["id"], kind), context="Failed to list {0} for integration '{1}'".format(kind, integration.get("name"))
    )


def main():
    argument_spec = dict(
        name=dict(type="str"),
        integration_type=dict(type="str", choices=["mcp_server", "llm_provider", "ansible_automation_platform"]),
        enabled=dict(type="bool"),
        scope=dict(type="str", choices=["global", "project"]),
        project=dict(type="str"),
        include_models=dict(type="bool", default=False),
        include_tools=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None
    query = module.build_desired(
        {"integration_type": params["integration_type"], "enabled": params["enabled"], "scope": params["scope"], "project_id": project_id}
    )
    resources = module.get_all("/integrations", query, context="Failed to list integrations")
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]
    for integration in resources:
        if params["include_models"]:
            _attach(module, integration, "models")
        if params["include_tools"]:
            _attach(module, integration, "tools")
    module.exit_info(resources)


if __name__ == "__main__":
    main()
