# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import execution_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

WID = "33333333-3333-4333-8333-333333333333"
OTHER = "55555555-5555-4555-8555-555555555555"
EID = "44444444-4444-4444-8444-444444444444"
EXE = "/api/v1/executions"


def test_info_bounded_list_sorted(fake_api):
    fake_api.add(
        "GET",
        EXE,
        200,
        {
            "resources": [
                {"id": "a", "workflow_id": WID, "status": "failed"},
                {"id": "b", "workflow_id": WID, "status": "completed"},
                {"id": "c", "workflow_id": OTHER, "status": "failed"},
            ],
            "next": "more",
        },
    )
    result = run_module(module_under_test.main, {"workflow": WID, "status": "failed"}, fake_api)
    assert [r["id"] for r in result["resources"]] == ["a"]
    assert len(fake_api.calls) == 1
    assert fake_api.calls[0]["query"]["sort"] == "-created_at"
    assert fake_api.calls[0]["query"]["limit"] == "20"
    assert result["changed"] is False


def test_info_by_id_404_empty(fake_api):
    fake_api.add("GET", EXE + "/" + EID, 404, {"detail": "not found"})
    result = run_module(module_under_test.main, {"id": EID}, fake_api)
    assert result["resources"] == []


def test_info_by_id(fake_api):
    fake_api.add("GET", EXE + "/" + EID, 200, {"id": EID, "status": "completed"})
    result = run_module(module_under_test.main, {"id": EID}, fake_api)
    assert [r["id"] for r in result["resources"]] == [EID]


def test_info_include_activities(fake_api):
    fake_api.add("GET", EXE + "/" + EID, 200, {"id": EID, "status": "completed"})
    fake_api.add("GET", EXE + "/" + EID + "/activities", 200, {"resources": [{"id": "act1", "activity_name": "step"}]})
    result = run_module(module_under_test.main, {"id": EID, "include_activities": True}, fake_api)
    assert result["resources"][0]["activities"] == [{"id": "act1", "activity_name": "step"}]
