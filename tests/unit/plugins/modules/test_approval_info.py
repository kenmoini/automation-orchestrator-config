# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import approval_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

AID = "55555555-5555-4555-8555-555555555555"
EID = "44444444-4444-4444-8444-444444444444"
PID = "11111111-1111-4111-8111-111111111111"


def test_info_filters(fake_api):
    fake_api.add("GET", "/api/v1/approvals", 200, {"resources": [{"id": AID, "status": "pending"}]})
    result = run_module(module_under_test.main, {"status": "pending", "execution": EID}, fake_api)
    assert result["changed"] is False
    assert [r["id"] for r in result["resources"]] == [AID]
    query = fake_api.calls[0]["query"]
    assert query["status"] == "pending"
    assert query["execution_id"] == EID


def test_info_by_project_uses_project_path(fake_api):
    fake_api.add("GET", "/api/v1/projects/{0}/approvals".format(PID), 200, {"resources": [{"id": AID}]})
    result = run_module(module_under_test.main, {"project": PID, "status": "approved"}, fake_api)
    assert [r["id"] for r in result["resources"]] == [AID]
    assert fake_api.calls[0]["query"]["status"] == "approved"


def test_info_by_id(fake_api):
    fake_api.add("GET", "/api/v1/approvals/" + AID, 200, {"id": AID})
    result = run_module(module_under_test.main, {"id": AID}, fake_api)
    assert [r["id"] for r in result["resources"]] == [AID]


def test_info_by_id_404_empty(fake_api):
    fake_api.add("GET", "/api/v1/approvals/" + AID, 404, {"detail": "nope"})
    result = run_module(module_under_test.main, {"id": AID}, fake_api)
    assert result["resources"] == []
