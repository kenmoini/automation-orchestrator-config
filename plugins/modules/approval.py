# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
module: approval
short_description: Approve or reject a pending approval request on the Automation Orchestrator
description:
  - Decides an approval request raised by a workflow execution.
  - Identify the request by O(id), or by O(execution) and O(name).
  - A request that is C(pending) is decided and the module reports C(changed=true).
  - A request that is already decided the same way is left alone. A request decided the other way, C(expired) or C(cancelled) fails the module.
version_added: "0.1.0"
author:
  - Ken Moini (@kenmoini)
extends_documentation_fragment:
  - kenmoini.automation_orchestrator_config.auth
attributes:
  check_mode:
    support: full
    description: Reads the approval and reports whether it would be decided, without deciding it.
  diff_mode:
    support: full
    description: Shows the status change from C(pending) to the decision.
options:
  id:
    description: UUID of the approval request. Mutually exclusive with O(execution).
    type: str
  execution:
    description: UUID of the execution that raised the approval request. Requires O(name).
    type: str
  name:
    description: Name of the approval request within the execution, matched exactly. Requires O(execution).
    type: str
  decision:
    description: Decision to record.
    type: str
    required: true
    choices: [approved, rejected]
  notes:
    description: Free-text notes stored with the decision.
    type: str
seealso:
  - module: kenmoini.automation_orchestrator_config.approval_info
  - module: kenmoini.automation_orchestrator_config.execution
"""

EXAMPLES = r"""
- name: Approve a pending request by name
  kenmoini.automation_orchestrator_config.approval:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    execution: "{{ run.id }}"
    name: release-gate
    decision: approved
    notes: Change window confirmed

- name: Reject a request by id
  kenmoini.automation_orchestrator_config.approval:
    orchestrator_host: orchestrator.example.com
    orchestrator_token: "{{ orchestrator_token }}"
    id: "{{ pending.resources[0].id }}"
    decision: rejected
...
"""

RETURN = r"""
id:
  description: UUID of the approval request.
  returned: always
  type: str
  sample: 55555555-5555-4555-8555-555555555555
status:
  description: Status of the approval request after the module ran.
  returned: always
  type: str
  sample: approved
approval:
  description: The approval request. After a decision it is the server response (or the pre-decision read in check mode, with the new status).
  returned: always
  type: dict
  sample:
    id: 55555555-5555-4555-8555-555555555555
    name: release-gate
    execution_id: 44444444-4444-4444-8444-444444444444
    status: approved
"""

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import OrchestratorAPIError, OrchestratorModule


def main():
    argument_spec = dict(
        id=dict(type="str"),
        execution=dict(type="str"),
        name=dict(type="str"),
        decision=dict(type="str", required=True, choices=["approved", "rejected"]),
        notes=dict(type="str"),
    )
    module = OrchestratorModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[["id", "execution"]],
        required_one_of=[["id", "execution"]],
        required_together=[["execution", "name"]],
    )
    module.result_key = "approval"
    params = module.params
    decision = params["decision"]

    if params["id"]:
        try:
            approval = module.request("GET", "/approvals/{0}".format(params["id"]))
        except OrchestratorAPIError as err:
            if err.status == 404:
                module.fail_json(msg="approval '{0}' not found".format(params["id"]))
            module.fail_api(err, "Failed to read approval '{0}'".format(params["id"]))
    else:
        found = module.get_all(
            "/approvals", {"execution_id": params["execution"]}, context="Failed to list approvals for execution {0}".format(params["execution"])
        )
        matches = [a for a in found if a.get("name") == params["name"]]
        if not matches:
            module.fail_json(msg="approval '{0}' not found for execution {1}".format(params["name"], params["execution"]))
        if len(matches) > 1:
            module.fail_json(msg="Found {0} approvals named '{1}' for execution {2}".format(len(matches), params["name"], params["execution"]))
        approval = matches[0]

    label = approval.get("name") or approval.get("id")
    status = approval.get("status")
    if status == decision:
        module.exit_result(False, approval, status=status)
    if status != "pending":
        module.fail_json(msg="Approval '{0}' already {1}".format(label, status), approval=approval, status=status)

    module._diff = {"before": {"status": status}, "after": {"status": decision}}
    result = dict(approval, status=decision)
    if not module.check_mode:
        body = {"status": decision}
        if params["notes"] is not None:
            body["notes"] = params["notes"]
        try:
            updated = module.request("PATCH", "/approvals/{0}".format(approval["id"]), data=body)
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to decide approval '{0}'".format(label))
        if isinstance(updated, dict) and updated:
            result = updated
    module.exit_result(True, result, status=result.get("status", decision))


if __name__ == "__main__":
    main()
