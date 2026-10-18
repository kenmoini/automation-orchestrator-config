# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import execution as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

PID = "11111111-1111-4111-8111-111111111111"
WID = "33333333-3333-4333-8333-333333333333"
EID = "44444444-4444-4444-8444-444444444444"
EXE = "/api/v1/executions"
WF = "/api/v1/workflows/" + WID
WF_LIST = "/api/v1/projects/" + PID + "/workflows"
SLEEP = "ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules.execution.time.sleep"
TIME = "ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules.execution.time.time"


def _exe(status="running", **kw):
    obj = {"id": EID, "workflow_id": WID, "workflow_name": "deploy", "status": status, "error_details": None}
    obj.update(kw)
    return obj


def _wf(triggers):
    return {"id": WID, "name": "deploy", "project_id": PID, "version": {"workflow_definition": {"triggers": triggers}}}


def _launch(fake_api, status="running"):
    fake_api.add("POST", EXE, 201, _exe(status))


def test_launch_body_and_single_trigger_autopick(fake_api):
    fake_api.add("GET", WF_LIST, 200, {"resources": [{"id": WID, "name": "deploy", "project_id": PID}]})
    fake_api.add("GET", WF, 200, _wf([{"id": "t1"}]))
    _launch(fake_api)
    result = run_module(module_under_test.main, {"workflow": "deploy", "project": PID, "input_data": {"a": 1}}, fake_api)
    assert result["changed"] is True
    assert result["id"] == EID
    assert result["status"] == "running"
    assert result["paused"] is False
    assert result["workflow_id"] == WID
    assert result["execution"]["id"] == EID
    post = [c for c in fake_api.calls if c["method"] == "POST"][0]
    assert post["body"] == {"workflow_id": WID, "trigger_node_id": "t1", "input_data": {"a": 1}, "use_published": False}


def test_multiple_triggers_require_trigger_node_id(fake_api):
    fake_api.add("GET", WF, 200, _wf([{"id": "t1"}, {"id": "t2"}]))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"workflow": WID}, fake_api)
    assert exc.value.args[0]["msg"] == "workflow '{0}' has 2 triggers; set trigger_node_id".format(WID)
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_explicit_trigger_skips_definition_fetch(fake_api):
    _launch(fake_api)
    result = run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t9", "use_published": True}, fake_api)
    assert result["changed"] is True
    assert [(c["method"], c["path"]) for c in fake_api.calls] == [("POST", EXE)]
    assert fake_api.calls[0]["body"] == {"workflow_id": WID, "trigger_node_id": "t9", "use_published": True}


def test_wait_polls_until_terminal(fake_api, mocker):
    sleep = mocker.patch(SLEEP)
    _launch(fake_api, "running")
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("running"), times=1)
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("completed"))
    result = run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1", "wait": True, "interval": 1}, fake_api)
    assert result["status"] == "completed"
    assert result["changed"] is True
    assert sleep.call_count == 2


def test_wait_paused_exits_not_failed(fake_api, mocker):
    mocker.patch(SLEEP)
    _launch(fake_api)
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("paused"))
    result = run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1", "wait": True}, fake_api)
    assert result["paused"] is True
    assert result["changed"] is True
    assert result["status"] == "paused"


def test_wait_failed_status_fails(fake_api, mocker):
    mocker.patch(SLEEP)
    _launch(fake_api)
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("failed", error_details={"message": "boom"}))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1", "wait": True}, fake_api)
    res = exc.value.args[0]
    assert res["status"] == "failed"
    assert EID in res["msg"] and "failed" in res["msg"] and "boom" in res["msg"]
    assert res["execution"]["id"] == EID


def test_wait_cancelled_fails(fake_api, mocker):
    mocker.patch(SLEEP)
    _launch(fake_api)
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("cancelled"))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1", "wait": True}, fake_api)
    assert "was cancelled" in exc.value.args[0]["msg"]


def test_wait_completed_with_errors_warns(fake_api, mocker):
    mocker.patch(SLEEP)
    warn = mocker.patch("ansible.module_utils.basic.AnsibleModule.warn")
    _launch(fake_api)
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("completed_with_errors"))
    result = run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1", "wait": True}, fake_api)
    assert result["changed"] is True
    assert result["status"] == "completed_with_errors"
    assert warn.called


def test_wait_timeout_fails_with_id(fake_api, mocker):
    mocker.patch(SLEEP)
    mocker.patch(TIME, side_effect=[100, 100, 200, 300, 400])
    _launch(fake_api)
    fake_api.add("GET", EXE + "/" + EID, 200, _exe("running"), times=5)
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1", "wait": True, "timeout": 30}, fake_api)
    res = exc.value.args[0]
    assert EID in res["msg"]
    assert res["msg"] == "Timed out after 30 seconds waiting for execution {0} (status: running)".format(EID)
    assert res["status"] == "running"


def test_check_mode_no_post(fake_api):
    fake_api.add("GET", WF, 200, _wf([{"id": "t1"}]))
    result = run_module(module_under_test.main, {"workflow": WID, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert result["execution"] is None
    assert result["status"] is None
    assert all(c["method"] == "GET" for c in fake_api.calls)


def test_workflow_name_requires_project(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"workflow": "deploy"}, fake_api)
    assert exc.value.args[0]["msg"] == "project is required when workflow is a name"


def test_launch_api_error_reports_fail_api(fake_api):
    fake_api.add("POST", EXE, 422, {"detail": "bad trigger"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"workflow": WID, "trigger_node_id": "t1"}, fake_api)
    res = exc.value.args[0]
    assert res["msg"].startswith("Failed to launch execution for workflow '{0}'".format(WID))
    assert res["status"] == 422
