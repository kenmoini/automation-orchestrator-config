# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: approval_info
short_description: Gather information about approval requests on the Automation Orchestrator
description:
  - Reads one approval request by O(id), or lists approval requests filtered on the server by O(execution) and O(status).
  - With O(project) the project scoped endpoint is used.
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
  id:
    description: UUID of one approval request. Returns an empty list when it does not exist. Mutually exclusive with O(execution) and O(project).
    type: str
  execution:
    description: UUID of an execution. Return only approval requests raised by it.
    type: str
  status:
    description: Return only approval requests in this status.
    type: str
    choices: [pending, approved, rejected, expired, cancelled]
  project:
    description: Name or UUID of a project. Return only approval requests of this project.
    type: str
seealso:
  - module: kenmoini.automation_orchestrator_config.approval
"""

EXAMPLES = r"""
- name: List pending approvals of an execution
  kenmoini.automation_orchestrator_config.approval_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    execution: "{{ run.id }}"
    status: pending
  register: pending

- name: List approvals of a project
  kenmoini.automation_orchestrator_config.approval_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    project: platform
...
"""

RETURN = r"""
resources:
  description: The matching approval requests.
  returned: always
  type: list
  elements: dict
  sample:
    - id: 55555555-5555-4555-8555-555555555555
      name: release-gate
      execution_id: 44444444-4444-4444-8444-444444444444
      status: pending
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule


def main():
    argument_spec = dict(
        id=dict(type="str"),
        execution=dict(type="str"),
        status=dict(type="str", choices=["pending", "approved", "rejected", "expired", "cancelled"]),
        project=dict(type="str"),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True, mutually_exclusive=[["id", "execution"], ["id", "project"]])
    params = module.params

    if params["id"]:
        try:
            approval = module.request("GET", "/approvals/{0}".format(params["id"]))
        except OrchestratorAPIError as err:
            if err.status != 404:
                module.fail_api(err, "Failed to read approval '{0}'".format(params["id"]))
            approval = None
        resources = [approval] if approval else []
    else:
        query = {}
        if params["execution"]:
            query["execution_id"] = params["execution"]
        if params["status"]:
            query["status"] = params["status"]
        path = "/approvals"
        if params["project"]:
            path = "/projects/{0}/approvals".format(module.resolve_id("project", params["project"]))
        try:
            resources = module.get_all(path, query)
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to list approvals")
    module.exit_info(resources)


if __name__ == "__main__":
    main()
