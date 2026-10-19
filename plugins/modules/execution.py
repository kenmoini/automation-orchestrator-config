# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: execution
short_description: Launch a workflow execution on the Automation Orchestrator
description:
  - Starts an execution of a workflow and optionally waits for it to finish.
  - Every launch creates a new execution, so the module always reports C(changed=true).
  - When O(trigger_node_id) is not set, the module reads the workflow's current definition and uses its only trigger.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Looks up the workflow and trigger but does not launch the execution; reports C(changed=true) with no execution.
  diff_mode:
    support: none
    description: The module does not produce a diff.
options:
  workflow:
    description: Name or UUID of the workflow to run.
    type: str
    required: true
  project:
    description: Name or UUID of the project that holds the workflow. Required when O(workflow) is a name.
    type: str
  trigger_node_id:
    description:
      - ID of the trigger node to start from.
      - When omitted the workflow must have exactly one trigger, which is used.
    type: str
  input_data:
    description: Input data passed to the execution.
    type: dict
  use_published:
    description: Run the published version of the workflow instead of the current one.
    type: bool
    default: false
  wait:
    description:
      - Poll the execution until it reaches a final state.
      - The task fails when the execution ends as C(failed) or C(cancelled), and warns on C(completed_with_errors).
      - An execution that is C(paused), for example waiting for an approval, ends the wait without failing; see RV(paused).
    type: bool
    default: false
  interval:
    description: Seconds between polls when O(wait=true).
    type: float
    default: 2
  timeout:
    description: Seconds to wait for the execution when O(wait=true). V(0) waits without limit.
    type: int
    default: 0
seealso:
  - module: kenmoini.automation_orchestrator_config.execution_info
  - module: kenmoini.automation_orchestrator_config.execution_cancel
"""

EXAMPLES = r"""
- name: Launch a workflow with its only trigger
  kenmoini.automation_orchestrator_config.execution:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    workflow: deploy-app
    project: platform
    input_data:
      version: "1.4.2"

- name: Launch the published version and wait up to ten minutes
  kenmoini.automation_orchestrator_config.execution:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    workflow: deploy-app
    project: platform
    trigger_node_id: manual-trigger
    use_published: true
    wait: true
    interval: 5
    timeout: 600
  register: run
...
"""

RETURN = r"""
id:
  description: UUID of the execution, or V(null) in check mode.
  returned: always
  type: str
  sample: 4f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
execution:
  description: The execution as last read from the API, or V(null) in check mode.
  returned: always
  type: dict
  sample:
    id: 4f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    workflow_id: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    workflow_name: deploy-app
    status: completed
    trigger_node_id: manual-trigger
    error_details: null
status:
  description: Status of the execution as last read, or V(null) in check mode.
  returned: always
  type: str
  sample: completed
paused:
  description: Whether the execution was paused, for example waiting for an approval, when the wait ended.
  returned: always
  type: bool
  sample: false
workflow_id:
  description: UUID of the workflow that was launched.
  returned: always
  type: str
  sample: 3f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
"""

import json
import time

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule, is_uuid

TERMINAL = ("completed", "completed_with_errors", "failed", "cancelled")


def _summary(details):
    """Return a short text for an execution's error_details."""
    if not details:
        return "no error details"
    if isinstance(details, dict):
        for key in ("message", "error", "detail"):
            if details.get(key):
                return str(details[key])
        return json.dumps(details, sort_keys=True)
    return str(details)


def _trigger_id(module, workflow_id, name):
    try:
        wf = module.request("GET", "/workflows/{0}".format(workflow_id))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to read workflow '{0}'".format(name))
    triggers = (((wf or {}).get("version") or {}).get("workflow_definition") or {}).get("triggers") or []
    if len(triggers) != 1:
        module.fail_json(msg="workflow '{0}' has {1} triggers; set trigger_node_id".format(name, len(triggers)))
    return triggers[0].get("id")


def _finish(module, execution, workflow_id, name, **extra):
    status = execution.get("status")
    result = dict(changed=True, id=execution.get("id"), execution=execution, status=status, paused=status == "paused", workflow_id=workflow_id)
    result.update(extra)
    module.exit_json(**result)


def main():
    argument_spec = dict(
        workflow=dict(type="str", required=True),
        project=dict(type="str"),
        trigger_node_id=dict(type="str"),
        input_data=dict(type="dict"),
        use_published=dict(type="bool", default=False),
        wait=dict(type="bool", default=False),
        interval=dict(type="float", default=2),
        timeout=dict(type="int", default=0),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params
    name = params["workflow"]

    if not is_uuid(name) and not params["project"]:
        module.fail_json(msg="project is required when workflow is a name")
    project_id = module.resolve_id("project", params["project"]) if params["project"] else None
    workflow_id = module.resolve_id("workflow", name, project_id=project_id)
    trigger = params["trigger_node_id"] or _trigger_id(module, workflow_id, name)

    if module.check_mode:
        module.exit_json(changed=True, id=None, execution=None, status=None, paused=False, workflow_id=workflow_id)

    body = module.build_desired(
        {
            "workflow_id": workflow_id,
            "trigger_node_id": trigger,
            "input_data": params["input_data"],
            "use_published": params["use_published"],
        }
    )
    try:
        execution = module.request("POST", "/executions", data=body, expect=[200, 201, 202])
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to launch execution for workflow '{0}'".format(name))

    if not params["wait"]:
        _finish(module, execution, workflow_id, name)

    exec_id = execution["id"]
    started = time.time()
    while True:
        status = execution.get("status")
        if status in TERMINAL or status == "paused":
            break
        if params["timeout"] and time.time() - started >= params["timeout"]:
            module.fail_json(
                msg="Timed out after {0} seconds waiting for execution {1} (status: {2})".format(params["timeout"], exec_id, status),
                execution=execution,
                status=status,
            )
        time.sleep(params["interval"])
        try:
            execution = module.request("GET", "/executions/{0}".format(exec_id))
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to poll execution {0}".format(exec_id))

    status = execution.get("status")
    if status == "failed":
        module.fail_json(
            msg="Execution {0} of workflow '{1}' failed: {2}".format(exec_id, name, _summary(execution.get("error_details"))),
            execution=execution,
            status=status,
        )
    if status == "cancelled":
        module.fail_json(msg="Execution {0} of workflow '{1}' was cancelled".format(exec_id, name), execution=execution, status=status)
    if status == "completed_with_errors":
        module.warn("Execution {0} of workflow '{1}' completed with errors: {2}".format(exec_id, name, _summary(execution.get("error_details"))))
    _finish(module, execution, workflow_id, name)


if __name__ == "__main__":
    main()
