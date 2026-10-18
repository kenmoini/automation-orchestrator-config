# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import integration_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/integrations"
PID = "11111111-1111-4111-8111-111111111111"


def _integ(iid, name, **kw):
    obj = {
        "id": iid,
        "name": name,
        "integration_type": "llm_provider",
        "enabled": True,
        "scope": "global",
        "configuration": {"integration_type": "llm_provider"},
    }
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def test_info_lists_all(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ("i1", "a"), _integ("i2", "b")))
    result = run_module(module_under_test.main, {}, fake_api)
    assert result["changed"] is False
    assert [r["name"] for r in result["resources"]] == ["a", "b"]
    assert "models" not in result["resources"][0]


def test_info_filters_and_include_models(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, _list({"id": PID, "name": "platform"}))
    fake_api.add("GET", LIST, 200, _list(_integ("i1", "a"), _integ("i2", "ab")))
    fake_api.add("GET", LIST + "/i1/models", 200, _list({"id": "m1", "model_id": "gpt-4o", "name": "GPT 4o", "enabled": True}))
    fake_api.add("GET", LIST + "/i1/tools", 200, _list({"id": "t1", "name": "search", "enabled": False}))
    params = {
        "name": "a",
        "integration_type": "llm_provider",
        "enabled": True,
        "scope": "global",
        "project": "platform",
        "include_models": True,
        "include_tools": True,
    }
    result = run_module(module_under_test.main, params, fake_api)
    assert [r["name"] for r in result["resources"]] == ["a"]
    assert result["resources"][0]["models"][0]["id"] == "m1"
    assert result["resources"][0]["tools"][0]["id"] == "t1"
    call = [c for c in fake_api.calls if c["path"] == LIST][0]
    assert call["query"]["integration_type"] == "llm_provider"
    assert call["query"]["enabled"] == "true"
    assert call["query"]["scope"] == "global"
    assert call["query"]["project_id"] == PID
    assert [c for c in fake_api.calls if c["path"] == LIST + "/i2/models"] == []


def test_info_sub_list_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ("i1", "a")))
    fake_api.add("GET", LIST + "/i1/tools", 403, {"detail": "forbidden"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, {"include_tools": True}, fake_api)
    assert exc.value.kwargs["msg"] == "Failed to list tools for integration 'a': forbidden"
