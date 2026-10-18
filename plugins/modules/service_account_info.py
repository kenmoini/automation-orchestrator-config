# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: service_account_info
short_description: Gather information about service accounts in the Automation Orchestrator
description:
  - Lists service accounts, optionally filtered by name, project or status, and optionally with the metadata of their credentials.
  - Credential secrets are never available after creation, so they are never returned.
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
    description: Return only the service account with exactly this name.
    type: str
  project:
    description: Name or UUID of a project. Return only the service accounts of this project.
    type: str
  status:
    description: Return only service accounts with this status.
    type: str
    choices: [active, disabled]
  include_credentials:
    description:
      - Add a C(credentials) list with the credential metadata (never secrets) to every returned service account.
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.service_account
  - module: kenmoini.automation_orchestrator_config.service_account_credential
"""

EXAMPLES = r"""
- name: List the service accounts of a project
  kenmoini.automation_orchestrator_config.service_account_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
  register: accounts

- name: Show a service account with its credentials
  kenmoini.automation_orchestrator_config.service_account_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    name: ci-pipeline
    project: platform
    include_credentials: true
...
"""

RETURN = r"""
resources:
  description: The matching service accounts. At most one item when O(name) and O(project) are given.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: ID of the service account.
      type: str
    name:
      description: Name of the service account.
      type: str
    status:
      description: Either V(active) or V(disabled).
      type: str
    project_id:
      description: ID of the project.
      type: str
    credentials:
      description: Credential metadata, only present with O(include_credentials).
      type: list
      elements: dict
  sample:
    - id: 5f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      name: ci-pipeline
      description: Used by the CI pipeline
      status: active
      project_id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      project_name: platform
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule


def main():
    argument_spec = dict(
        name=dict(type="str"),
        project=dict(type="str"),
        status=dict(type="str", choices=["active", "disabled"]),
        include_credentials=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params

    project_id = module.resolve_id("project", params["project"]) if params["project"] else None
    query = module.build_desired({"name": params["name"], "status": params["status"]})
    resources = module.get_all("/service_accounts", query, context="Failed to list service accounts")
    if params["name"] is not None:
        resources = [r for r in resources if r.get("name") == params["name"]]
    if project_id is not None:
        resources = [r for r in resources if r.get("project_id") == project_id]
    if params["include_credentials"]:
        resources = [dict(r) for r in resources]
        for item in resources:
            try:
                body = module.request("GET", "/service_accounts/{0}/credentials".format(item["id"]))
            except OrchestratorAPIError as err:
                module.fail_api(err, "Failed to list credentials for service account '{0}'".format(item.get("name")))
            item["credentials"] = list((body or {}).get("resources") or [])
    module.exit_info(resources)


if __name__ == "__main__":
    main()
