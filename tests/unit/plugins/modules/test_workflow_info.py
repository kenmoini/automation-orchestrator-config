# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import workflow_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

PID = "11111111-1111-4111-8111-111111111111"
WID = "33333333-3333-4333-8333-333333333333"
LIST = "/api/v1/projects/" + PID + "/workflows"
ITEM = "/api/v1/workflows/" + WID


def _wf(name="deploy", **kw):
    obj = {"id": WID, "name": name, "current_version": 2, "published_version_number": None, "project_id": PID}
    obj.update(kw)
    return obj


def _with_version(definition, **kw):
    obj = _wf(**kw)
    obj["version"] = {"version": 2, "workflow_definition": definition}
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def test_info_lists_and_filters_name_exactly(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf("deploy"), _wf("deploy-2", id="other")))
    result = run_module(module_under_test.main, {"project": PID, "name": "deploy"}, fake_api)
    assert result["changed"] is False
    assert [r["name"] for r in result["resources"]] == ["deploy"]
    assert "workflow_definition" not in result["resources"][0]


def test_info_by_id(fake_api):
    fake_api.add("GET", ITEM, 200, _with_version({"name": "deploy"}))
    result = run_module(module_under_test.main, {"id": WID}, fake_api)
    assert [r["id"] for r in result["resources"]] == [WID]
    assert "version" not in result["resources"][0]


def test_info_by_id_missing_returns_empty(fake_api):
    fake_api.add("GET", ITEM, 404, {"detail": "not found"})
    result = run_module(module_under_test.main, {"id": WID}, fake_api)
    assert result["resources"] == []


def test_info_requires_project_or_id(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"name": "deploy"}, fake_api)
    assert "project" in exc.value.kwargs["msg"]


def test_info_include_definition_and_version(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM, 200, _with_version({"name": "deploy", "nodes": ["current"]}))
    fake_api.add("GET", ITEM + "/versions/1", 200, {"version": 1, "workflow_definition": {"name": "deploy", "nodes": ["v1"]}})
    result = run_module(module_under_test.main, {"project": PID, "name": "deploy", "include_definition": True}, fake_api)
    assert result["resources"][0]["workflow_definition"] == {"name": "deploy", "nodes": ["current"]}
    result = run_module(module_under_test.main, {"project": PID, "name": "deploy", "version": 1}, fake_api)
    assert result["resources"][0]["workflow_definition"] == {"name": "deploy", "nodes": ["v1"]}


def test_info_include_versions(fake_api):
    versions = [{"version": 1, "status": "previously_published"}, {"version": 2, "status": "draft"}]
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM + "/versions", 200, {"resources": versions, "next": None})
    result = run_module(module_under_test.main, {"project": PID, "include_versions": True}, fake_api)
    assert result["resources"][0]["versions"] == versions


def test_info_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_wf()))
    fake_api.add("GET", ITEM + "/versions/9", 404, {"detail": "no such version"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"project": PID, "version": 9}, fake_api)
    assert exc.value.kwargs["msg"] == "Failed to read version 9 of workflow 'deploy': no such version"
