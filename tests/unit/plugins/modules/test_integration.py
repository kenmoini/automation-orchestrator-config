# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import integration as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/integrations"
ITEM = LIST + "/i1"
PID_A = "11111111-1111-4111-8111-111111111111"
PID_B = "22222222-2222-4222-8222-222222222222"
CRED_ID = "33333333-3333-4333-8333-333333333333"


def _integ(**kw):
    obj = {
        "id": "i1",
        "name": "llm",
        "description": "old",
        "integration_type": "llm_provider",
        "enabled": True,
        "scope": "global",
        "configuration": {"integration_type": "llm_provider", "provider_hint": "openai", "base_url": "https://api.example.com", "allow_http": False},
        "management_credential_id": None,
        "labels": {"a": "1"},
    }
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _calls(api, method, path=None):
    return [c for c in api.calls if c["method"] == method and (path is None or c["path"] == path)]


def _writes(api):
    return [c for c in api.calls if c["method"] in ("POST", "PATCH", "PUT", "DELETE")]


def _model(row_id, model_id, name, enabled=False, is_default=False):
    return {"id": row_id, "integration_id": "i1", "model_id": model_id, "name": name, "enabled": enabled, "is_default": is_default}


def _tool(row_id, name, enabled=False):
    return {"id": row_id, "name": name, "namespaced_name": "llm__" + name, "integration_id": "i1", "enabled": enabled, "status": "active"}


BASE = {"name": "llm"}
CONF = {"provider_hint": "openai", "base_url": "https://api.example.com"}


# ------------------------------------------------------------------ pattern set


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _integ())
    params = dict(BASE, description="d", integration_type="llm_provider", configuration=dict(CONF), enabled=True, scope="global", labels={"a": "1"})
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert result["id"] == "i1"
    assert _calls(fake_api, "POST")[0]["body"] == {
        "name": "llm",
        "description": "d",
        "integration_type": "llm_provider",
        "configuration": {"integration_type": "llm_provider", "provider_hint": "openai", "base_url": "https://api.example.com"},
        "enabled": True,
        "scope": "global",
        "labels": {"a": "1"},
    }


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("PATCH", ITEM, 200, _integ(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new"), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"description": "new"}


def test_update_diff_mode(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("PATCH", ITEM, 200, _integ(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new", _ansible_diff=True), fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}


def test_labels_changed_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("PATCH", ITEM, 200, _integ(labels={"b": "2"}))
    run_module(module_under_test.main, dict(BASE, labels={"b": "2"}), fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"labels": {"b": "2"}}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    params = dict(BASE, description="old", integration_type="llm_provider", configuration=dict(CONF), enabled=True, scope="global", labels={"a": "1"})
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("DELETE", ITEM, 204)
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is True
    assert result["integration"] is None
    assert len(_calls(fake_api, "DELETE", ITEM)) == 1


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_exists_does_not_modify(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    result = run_module(module_under_test.main, dict(BASE, description="new", state="exists"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    params = dict(BASE, integration_type="llm_provider", configuration=dict(CONF), models=[{"name": "gpt", "enabled": True}], _ansible_check_mode=True)
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert _writes(fake_api) == []


def test_rename_uses_new_name(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ(name="llm2")))
    result = run_module(module_under_test.main, dict(BASE, new_name="llm2"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


# --------------------------------------------------------------- module specific


def test_create_requires_integration_type(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, configuration=dict(CONF)), fake_api)
    assert exc.value.kwargs["msg"] == "integration_type is required to create integration 'llm'"
    assert _writes(fake_api) == []


def test_integration_type_immutable_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, integration_type="mcp_server"), fake_api)
    assert exc.value.kwargs["msg"] == "integration_type cannot be changed on an existing integration"
    assert _writes(fake_api) == []


def test_configuration_gets_integration_type_and_full_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("PATCH", ITEM, 200, _integ())
    result = run_module(module_under_test.main, dict(BASE, configuration={"base_url": "https://new.example.com"}), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {
        "configuration": {"integration_type": "llm_provider", "provider_hint": "openai", "base_url": "https://new.example.com", "allow_http": False}
    }


def test_management_credential_resolved_in_project(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, _list({"id": PID_A, "name": "platform"}))
    fake_api.add("GET", "/api/v1/projects/" + PID_A + "/credentials", 200, _list({"id": CRED_ID, "name": "llm-key", "project_id": PID_A}))
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("PATCH", ITEM, 200, _integ(management_credential_id=CRED_ID))
    params = dict(BASE, management_credential="llm-key", management_credential_project="platform")
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"management_credential_id": CRED_ID}


def test_management_credential_uuid_needs_no_project(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ(management_credential_id=CRED_ID)))
    result = run_module(module_under_test.main, dict(BASE, management_credential=CRED_ID), fake_api)
    assert result["changed"] is False


def test_management_credential_name_requires_project(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, management_credential="llm-key"), fake_api)
    assert exc.value.kwargs["msg"] == "management_credential_project is required when management_credential is a name"
    assert fake_api.calls == []


def test_projects_reconcile_assign_and_unassign(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", "/api/v1/projects", 200, _list({"id": PID_A, "name": "alpha"}))
    fake_api.add("GET", ITEM + "/projects", 200, _list({"project_id": PID_B, "project_name": "beta"}))
    fake_api.add("POST", ITEM + "/projects/" + PID_A, 201, {})
    fake_api.add("DELETE", ITEM + "/projects/" + PID_B, 204)
    result = run_module(module_under_test.main, dict(BASE, projects=["alpha"]), fake_api)
    assert result["changed"] is True
    assert [c["path"] for c in _writes(fake_api)] == [ITEM + "/projects/" + PID_A, ITEM + "/projects/" + PID_B]
    assert [c["method"] for c in _writes(fake_api)] == ["POST", "DELETE"]
    assert result["projects"] == ["alpha"]


def test_projects_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/projects", 200, _list({"project_id": PID_A, "project_name": "alpha"}))
    result = run_module(module_under_test.main, dict(BASE, projects=[PID_A]), fake_api)
    assert result["changed"] is False
    assert result["projects"] == ["alpha"]
    assert _writes(fake_api) == []


def test_models_patch_only_differing_flags(fake_api):
    rows = [_model("m1", "gpt-4o", "GPT 4o", enabled=False, is_default=False), _model("m2", "gpt-mini", "GPT mini", enabled=True, is_default=True)]
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/models", 200, _list(*rows))
    fake_api.add("PATCH", ITEM + "/models/m1", 200, _model("m1", "gpt-4o", "GPT 4o", enabled=True))
    models = [{"model_id": "gpt-4o", "enabled": True, "is_default": False}, {"name": "GPT mini", "enabled": True, "is_default": True}]
    result = run_module(module_under_test.main, dict(BASE, models=models), fake_api)
    assert result["changed"] is True
    patches = _calls(fake_api, "PATCH")
    assert [(c["path"], c["body"]) for c in patches] == [(ITEM + "/models/m1", {"enabled": True})]
    assert [m["id"] for m in result["models"]] == ["m1", "m2"]
    assert result["models"][0]["enabled"] is True


def test_tools_patch_by_name_and_namespaced_name(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/tools", 200, _list(_tool("t1", "search", enabled=True), _tool("t2", "fetch")))
    fake_api.add("PATCH", ITEM + "/tools/t1", 200, _tool("t1", "search"))
    fake_api.add("PATCH", ITEM + "/tools/t2", 200, _tool("t2", "fetch", enabled=True))
    tools = [{"name": "search", "enabled": False}, {"name": "llm__fetch", "enabled": True}]
    result = run_module(module_under_test.main, dict(BASE, tools=tools), fake_api)
    assert result["changed"] is True
    assert [(c["path"], c["body"]) for c in _calls(fake_api, "PATCH")] == [(ITEM + "/tools/t1", {"enabled": False}), (ITEM + "/tools/t2", {"enabled": True})]


def test_models_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/models", 200, _list(_model("m1", "gpt-4o", "GPT 4o", enabled=True)))
    result = run_module(module_under_test.main, dict(BASE, models=[{"name": "gpt-4o", "enabled": True}]), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_missing_model_fails_with_hint(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/models", 200, _list(_model("m1", "gpt-4o", "GPT 4o")))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, models=[{"name": "claude", "enabled": True}]), fake_api)
    assert exc.value.kwargs["msg"] == "Model 'claude' not found on integration 'llm'; run with refresh: true"
    assert _writes(fake_api) == []


def test_missing_tool_fails_with_hint(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/tools", 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, tools=[{"name": "search", "enabled": True}]), fake_api)
    assert exc.value.kwargs["msg"] == "Tool 'search' not found on integration 'llm'; run with refresh: true"


def test_discover_on_create_feeds_discovered_models(fake_api):
    discovered = {
        "success": True,
        "discovered_models": [
            {"id": "gpt-4o", "name": "GPT 4o", "description": "big"},
            {"id": "gpt-mini", "name": "GPT mini", "description": "small"},
        ],
        "discovered_tools": None,
    }
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST + "/discover", 200, discovered)
    fake_api.add("POST", LIST, 201, _integ())
    fake_api.add("GET", ITEM + "/models", 200, _list(_model("m1", "gpt-4o", "GPT 4o", enabled=True, is_default=True), _model("m2", "gpt-mini", "GPT mini")))
    params = dict(
        BASE,
        integration_type="llm_provider",
        configuration=dict(CONF),
        management_credential=CRED_ID,
        models=[{"model_id": "gpt-4o", "enabled": True, "is_default": True}],
    )
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    discover_call = _calls(fake_api, "POST", LIST + "/discover")[0]
    assert discover_call["body"] == {
        "integration_type": "llm_provider",
        "configuration": {"integration_type": "llm_provider", "provider_hint": "openai", "base_url": "https://api.example.com"},
        "credential_id": CRED_ID,
    }
    create_body = _calls(fake_api, "POST", LIST)[0]["body"]
    assert create_body["management_credential_id"] == CRED_ID
    assert create_body["discovered_models"] == [
        {"model_id": "gpt-4o", "name": "GPT 4o", "description": "big", "enabled": True, "is_default": True},
        {"model_id": "gpt-mini", "name": "GPT mini", "description": "small"},
    ]
    assert "discovered_tools" not in create_body
    assert _calls(fake_api, "PATCH") == []


def test_discover_on_create_feeds_discovered_tools(fake_api):
    discovered = {"success": True, "discovered_tools": [{"name": "search", "description": "s", "parameters": {"type": "object"}}], "discovered_models": None}
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST + "/discover", 200, discovered)
    fake_api.add("POST", LIST, 201, _integ(integration_type="mcp_server"))
    fake_api.add("GET", ITEM + "/tools", 200, _list(_tool("t1", "search", enabled=True)))
    params = dict(BASE, integration_type="mcp_server", configuration={"base_url": "https://mcp.example.com"}, tools=[{"name": "search", "enabled": True}])
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    create_body = _calls(fake_api, "POST", LIST)[0]["body"]
    assert create_body["discovered_tools"] == [{"name": "search", "description": "s", "parameters": {"type": "object"}, "enabled": True}]
    assert result["tools"][0]["id"] == "t1"


def test_discover_missing_model_fails_before_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST + "/discover", 200, {"success": True, "discovered_models": [{"id": "gpt-4o", "name": "GPT 4o"}]})
    params = dict(BASE, integration_type="llm_provider", configuration=dict(CONF), models=[{"name": "claude", "enabled": True}])
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, params, fake_api)
    assert exc.value.kwargs["msg"] == "Model 'claude' not found on integration 'llm'; run with refresh: true"
    assert _calls(fake_api, "POST", LIST) == []


def test_discover_failure_reported(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST + "/discover", 200, {"success": False, "error": "connection refused"})
    params = dict(BASE, integration_type="llm_provider", configuration=dict(CONF), models=[{"name": "gpt-4o", "enabled": True}])
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, params, fake_api)
    assert exc.value.kwargs["msg"] == "Failed to discover models and tools for integration 'llm': connection refused"
    assert _calls(fake_api, "POST", LIST) == []


def test_discover_false_creates_then_reconciles(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _integ())
    fake_api.add("GET", ITEM + "/models", 200, _list(_model("m1", "gpt-4o", "GPT 4o")))
    fake_api.add("PATCH", ITEM + "/models/m1", 200, _model("m1", "gpt-4o", "GPT 4o", enabled=True))
    params = dict(BASE, integration_type="llm_provider", configuration=dict(CONF), discover=False, models=[{"name": "gpt-4o", "enabled": True}])
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "POST", LIST + "/discover") == []
    assert "discovered_models" not in _calls(fake_api, "POST", LIST)[0]["body"]
    assert _calls(fake_api, "PATCH")[0]["body"] == {"enabled": True}


@pytest.mark.parametrize("updated_count, expected", [(0, False), (2, True)])
def test_refresh_changed_only_when_updated_count(fake_api, updated_count, expected):
    refresh = {"synced_count": 0, "updated_count": updated_count, "missing_count": 0, "refreshed_at": "2026-10-18T00:00:00Z"}
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("POST", ITEM + "/refresh", 200, refresh)
    result = run_module(module_under_test.main, dict(BASE, refresh=True), fake_api)
    assert result["changed"] is expected
    assert result["refresh_result"] == refresh


def test_refresh_error_reported(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("POST", ITEM + "/refresh", 400, {"detail": "refresh is only supported for MCP servers"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, refresh=True), fake_api)
    assert exc.value.kwargs["msg"] == "Failed to refresh integration 'llm': refresh is only supported for MCP servers"
    assert exc.value.kwargs["status"] == 400


def test_validate_never_changed(fake_api):
    validation = {"success": False, "checked_at": "2026-10-18T00:00:00Z", "error": "unreachable", "error_type": "connection_error"}
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("POST", ITEM + "/validate", 200, validation)
    result = run_module(module_under_test.main, dict(BASE, validate=True), fake_api)
    assert result["changed"] is False
    assert result["validation"] == validation


def test_check_mode_skips_refresh_and_validate(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    result = run_module(module_under_test.main, dict(BASE, refresh=True, validate=True, _ansible_check_mode=True), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []
    assert "validation" not in result


def test_sub_resource_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/projects", 200, _list())
    fake_api.add("GET", "/api/v1/projects/" + PID_A, 200, {"id": PID_A, "name": "alpha"})
    fake_api.add("POST", ITEM + "/projects/" + PID_A, 403, {"detail": "forbidden"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, projects=[PID_A]), fake_api)
    assert exc.value.kwargs["msg"] == "Failed to update projects for integration 'llm': forbidden"
    assert exc.value.kwargs["status"] == 403


def test_model_patch_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/models", 200, _list(_model("m1", "gpt-4o", "GPT 4o")))
    fake_api.add("PATCH", ITEM + "/models/m1", 500, {"detail": "boom"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, models=[{"name": "gpt-4o", "enabled": True}]), fake_api)
    assert exc.value.kwargs["msg"] == "Failed to update models for integration 'llm': boom"


def test_check_mode_reconcile_reports_changed_without_writes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_integ()))
    fake_api.add("GET", ITEM + "/projects", 200, _list({"project_id": PID_B, "project_name": "beta"}))
    fake_api.add("GET", ITEM + "/models", 200, _list(_model("m1", "gpt-4o", "GPT 4o")))
    fake_api.add("GET", ITEM + "/tools", 200, _list(_tool("t1", "search")))
    params = dict(
        BASE,
        projects=[],
        models=[{"name": "gpt-4o", "enabled": True}],
        tools=[{"name": "search", "enabled": True}],
        _ansible_check_mode=True,
    )
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert _writes(fake_api) == []
    assert result["projects"] == []


def test_model_entry_requires_name_or_model_id(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, models=[{"enabled": True}]), fake_api)
    assert "name" in exc.value.kwargs["msg"] and "model_id" in exc.value.kwargs["msg"]
