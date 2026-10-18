# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import execution_cancel as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

EID = "44444444-4444-4444-8444-444444444444"
ITEM = "/api/v1/executions/" + EID


def test_cancel_running_changed(fake_api):
    fake_api.add("GET", ITEM, 200, {"id": EID, "status": "running"})
    fake_api.add("POST", ITEM + "/cancel", 202)
    result = run_module(module_under_test.main, {"id": EID}, fake_api)
    assert result["changed"] is True
    assert result["id"] == EID
    assert result["status"] == "running"
    assert result["execution"]["id"] == EID
    assert [c["method"] for c in fake_api.calls] == ["GET", "POST"]


def test_cancel_completed_noop(fake_api):
    fake_api.add("GET", ITEM, 200, {"id": EID, "status": "completed"})
    result = run_module(module_under_test.main, {"id": EID}, fake_api)
    assert result["changed"] is False
    assert result["status"] == "completed"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_cancel_completed_fails_when_requested(fake_api):
    fake_api.add("GET", ITEM, 200, {"id": EID, "status": "completed"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"id": EID, "fail_if_not_running": True}, fake_api)
    assert exc.value.args[0]["msg"] == "Execution {0} is not running (status: completed)".format(EID)


def test_cancel_check_mode_no_post(fake_api):
    fake_api.add("GET", ITEM, 200, {"id": EID, "status": "paused"})
    result = run_module(module_under_test.main, {"id": EID, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert [c["method"] for c in fake_api.calls] == ["GET"]
