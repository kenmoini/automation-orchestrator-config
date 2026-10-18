# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: execution_info
short_description: Gather information about workflow executions on the Automation Orchestrator
description:
  - Reads one execution by O(id), or scans the most recent executions.
  - The executions list endpoint has no server-side filters, so without O(id) the module reads one page of the O(limit) most recently created executions
    and filters it by O(workflow) and O(status) on the client. This is a bounded, most-recent-first scan, not a full history search.
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
    description: UUID of one execution. Returns an empty list when it does not exist. Mutually exclusive with O(workflow).
    type: str
  workflow:
    description: Name or UUID of a workflow. Return only executions of this workflow.
    type: str
  project:
    description: Name or UUID of the project that holds the workflow. Required when O(workflow) is a name.
    type: str
  status:
    description: Return only executions in this status.
    type: str
    choices: [pending, running, paused, completed, completed_with_errors, failed, cancelled]
  limit:
    description: Number of most recent executions to scan when O(id) is not set.
    type: int
    default: 20
  include_activities:
    description: Add the activities of each execution under the C(activities) key.
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.execution
  - module: kenmoini.automation_orchestrator_config.execution_cancel
"""

EXAMPLES = r"""
- name: Read one execution with its activities
  kenmoini.automation_orchestrator_config.execution_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    id: "{{ run.id }}"
    include_activities: true

- name: Find failed runs of a workflow among the last 50 executions
  kenmoini.automation_orchestrator_config.execution_info:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    workflow: deploy-app
    project: platform
    status: failed
    limit: 50
  register: failures
...
"""

RETURN = r"""
resources:
  description: The matching executions, newest first, each with C(activities) when O(include_activities=true).
  returned: always
  type: list
  elements: dict
  sample:
    - id: 4f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      workflow_id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
      workflow_name: deploy-app
      status: failed
      created_at: "2026-10-18T12:00:00Z"
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule, is_uuid


def main():
    argument_spec = dict(
        id=dict(type="str"),
        workflow=dict(type="str"),
        project=dict(type="str"),
        status=dict(type="str", choices=["pending", "running", "paused", "completed", "completed_with_errors", "failed", "cancelled"]),
        limit=dict(type="int", default=20),
        include_activities=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True, mutually_exclusive=[["id", "workflow"]])
    params = module.params

    if params["id"]:
        try:
            execution = module.request("GET", "/executions/{0}".format(params["id"]))
        except OrchestratorAPIError as err:
            if err.status != 404:
                module.fail_api(err, "Failed to read execution {0}".format(params["id"]))
            execution = None
        resources = [execution] if execution else []
    else:
        workflow_id = None
        if params["workflow"]:
            if not is_uuid(params["workflow"]) and not params["project"]:
                module.fail_json(msg="project is required when workflow is a name")
            project_id = module.resolve_id("project", params["project"]) if params["project"] else None
            workflow_id = module.resolve_id("workflow", params["workflow"], project_id=project_id)
        try:
            body = module.request("GET", "/executions", query={"sort": "-created_at", "limit": params["limit"]})
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to list executions")
        resources = [
            e
            for e in (body or {}).get("resources") or []
            if (workflow_id is None or e.get("workflow_id") == workflow_id) and (params["status"] is None or e.get("status") == params["status"])
        ]

    if params["include_activities"]:
        for execution in resources:
            try:
                execution["activities"] = module.get_all("/executions/{0}/activities".format(execution["id"]))
            except OrchestratorAPIError as err:
                module.fail_api(err, "Failed to read activities of execution {0}".format(execution["id"]))
    module.exit_info(resources)


if __name__ == "__main__":
    main()
