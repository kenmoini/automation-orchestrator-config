# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: execution_cancel
short_description: Cancel a running workflow execution on the Automation Orchestrator
description:
  - Cancels an execution that is C(pending), C(running) or C(paused).
  - An execution in any other state is left alone and the module reports C(changed=false), or fails when O(fail_if_not_running=true).
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Reads the execution and reports whether it would be cancelled, without cancelling it.
  diff_mode:
    support: none
options:
  id:
    description: UUID of the execution to cancel.
    type: str
    required: true
  fail_if_not_running:
    description: Fail instead of doing nothing when the execution is not C(pending), C(running) or C(paused).
    type: bool
    default: false
seealso:
  - module: kenmoini.automation_orchestrator_config.execution
  - module: kenmoini.automation_orchestrator_config.execution_info
"""

EXAMPLES = r"""
- name: Cancel an execution if it is still active
  kenmoini.automation_orchestrator_config.execution_cancel:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    id: "{{ run.id }}"

- name: Cancel an execution and fail when it already ended
  kenmoini.automation_orchestrator_config.execution_cancel:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    id: "{{ run.id }}"
    fail_if_not_running: true
...
"""

RETURN = r"""
id:
  description: UUID of the execution.
  returned: always
  type: str
  sample: 4f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
status:
  description: Status of the execution observed before the cancel request.
  returned: always
  type: str
  sample: running
execution:
  description: The execution as read before the cancel request.
  returned: always
  type: dict
  sample:
    id: 4f1c2b9e-6d0a-4a38-9a43-0a6f2f4f3c11
    workflow_name: deploy-app
    status: running
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule

ACTIVE = ("pending", "running", "paused")


def main():
    argument_spec = dict(
        id=dict(type="str", required=True),
        fail_if_not_running=dict(type="bool", default=False),
    )
    module = OrchestratorModule(argument_spec=argument_spec, supports_check_mode=True)
    params = module.params
    exec_id = params["id"]
    try:
        execution = module.request("GET", "/executions/{0}".format(exec_id))
    except OrchestratorAPIError as err:
        module.fail_api(err, "Failed to read execution {0}".format(exec_id))
    status = execution.get("status")

    if status not in ACTIVE:
        if params["fail_if_not_running"]:
            module.fail_json(msg="Execution {0} is not running (status: {1})".format(exec_id, status), execution=execution, status=status)
        module.exit_json(changed=False, id=exec_id, status=status, execution=execution)

    if not module.check_mode:
        try:
            module.request("POST", "/executions/{0}/cancel".format(exec_id), expect=[200, 202, 204])
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to cancel execution {0}".format(exec_id))
    module.exit_json(changed=True, id=exec_id, status=status, execution=execution)


if __name__ == "__main__":
    main()
