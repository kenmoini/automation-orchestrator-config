# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import identity_provider as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/identity_providers"
ITEM = LIST + "/p1"
TEST = LIST + "/test"
GROUPS = "/api/v1/groups/directory"
GID = "44444444-4444-4444-8444-444444444444"

OIDC = {
    "provider_type": "oidc",
    "issuer_url": "https://idp.example.com",
    "client_id": "orch",
    "redirect_uri": "https://orch.example.com/callback",
    "scopes": ["openid", "email"],
}


def _idp(**kw):
    obj = {"id": "p1", "name": "sso", "description": "old", "enabled": True, "configuration": dict(OIDC), "labels": {}}
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _calls(api, method, path=None):
    return [c for c in api.calls if c["method"] == method and (path is None or c["path"] == path)]


def _writes(api):
    return [c for c in api.calls if c["method"] in ("POST", "PATCH", "PUT", "DELETE")]


BASE = {"name": "sso"}
CONF = {
    "issuer_url": "https://idp.example.com",
    "client_id": "orch",
    "redirect_uri": "https://orch.example.com/callback",
    "scopes": ["openid", "email"],
}


# ------------------------------------------------------------------ pattern set


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _idp())
    result = run_module(module_under_test.main, dict(BASE, description="d", enabled=True, configuration=dict(CONF)), fake_api)
    assert _calls(fake_api, "PATCH") == []
    assert result["changed"] is True
    assert result["id"] == "p1"
    assert _calls(fake_api, "POST")[0]["body"] == {
        "name": "sso",
        "description": "d",
        "configuration": dict(OIDC),
    }


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("PATCH", ITEM, 200, _idp(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new"), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"description": "new"}


def test_update_diff_mode(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("PATCH", ITEM, 200, _idp(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new", _ansible_diff=True), fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}


def test_update_enabled_patches_enabled(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("PATCH", ITEM, 200, _idp(enabled=False))
    run_module(module_under_test.main, dict(BASE, enabled=False), fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"enabled": False}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    result = run_module(module_under_test.main, dict(BASE, description="old", enabled=True, configuration=dict(CONF)), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("DELETE", ITEM, 204)
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is True
    assert result["identity_provider"] is None
    assert len(_calls(fake_api, "DELETE", ITEM)) == 1


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_exists_does_not_modify(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    result = run_module(module_under_test.main, dict(BASE, description="new", state="exists"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, configuration=dict(CONF), test=True, _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert _writes(fake_api) == []


def test_rename_rerun_is_idempotent(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp(name="sso2")))
    result = run_module(module_under_test.main, dict(BASE, new_name="sso2"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


# --------------------------------------------------------------- module specific


def test_create_requires_configuration(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE), fake_api)
    assert exc.value.kwargs["msg"] == "configuration is required to create identity provider 'sso'"
    assert _writes(fake_api) == []


def test_group_mapping_names_resolved(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("GET", GROUPS, 200, _list({"id": GID, "name": "ops"}))
    fake_api.add("POST", LIST, 201, _idp())
    conf = dict(CONF, group_mapping_entries=[{"idp_group_value": "ops-team", "mapped_group": "ops"}])
    params = dict(BASE, configuration=conf)
    run_module(module_under_test.main, params, fake_api)
    entries = _calls(fake_api, "POST")[0]["body"]["configuration"]["group_mapping_entries"]
    assert entries == [{"idp_group_value": "ops-team", "mapped_group_id": GID}]
    assert "mapped_group" not in entries[0]


def test_group_mapping_resolved_form_is_idempotent(fake_api):
    existing = _idp(configuration=dict(OIDC, group_mapping_entries=[{"idp_group_value": "ops-team", "mapped_group_id": GID}]))
    fake_api.add("GET", LIST, 200, _list(existing))
    fake_api.add("GET", GROUPS, 200, _list({"id": GID, "name": "ops"}))
    conf = dict(CONF, group_mapping_entries=[{"idp_group_value": "ops-team", "mapped_group": "ops"}])
    result = run_module(module_under_test.main, dict(BASE, configuration=conf), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_full_configuration_sent_on_subkey_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("PATCH", ITEM, 200, _idp())
    run_module(module_under_test.main, dict(BASE, configuration={"scopes": ["openid", "profile"]}), fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"configuration": dict(OIDC, scopes=["openid", "profile"])}
    assert "client_secret" not in _calls(fake_api, "PATCH")[0]["body"]["configuration"]


def test_client_secret_respects_update_secrets(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    result = run_module(module_under_test.main, dict(BASE, configuration={"client_secret": "s3"}, update_secrets=False), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []

    fake_api.add("PATCH", ITEM, 200, _idp())
    result = run_module(module_under_test.main, dict(BASE, configuration={"client_secret": "s3"}), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"configuration": dict(OIDC, client_secret="s3")}
    assert "s3" not in str(result)


def test_test_flag_calls_endpoint_without_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("POST", TEST, 200, {"success": True, "message": "ok"})
    result = run_module(module_under_test.main, dict(BASE, configuration=dict(CONF, client_secret="s3"), update_secrets=False, test=True), fake_api)
    assert result["changed"] is False
    assert result["test_result"] == {"success": True, "message": "ok"}
    assert _calls(fake_api, "POST", TEST)[0]["body"] == {
        "name": "sso",
        "description": "old",
        "configuration": dict(OIDC, client_secret="s3"),
    }
    assert _calls(fake_api, "PATCH") == []


def test_test_runs_before_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", TEST, 200, {"success": True})
    fake_api.add("POST", LIST, 201, _idp())
    result = run_module(module_under_test.main, dict(BASE, configuration=dict(CONF), test=True), fake_api)
    assert result["changed"] is True
    assert [c["path"] for c in _calls(fake_api, "POST")] == [TEST, LIST]
    assert _calls(fake_api, "POST", TEST)[0]["body"] == {"name": "sso", "configuration": dict(OIDC)}


def test_test_failure_blocks_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", TEST, 200, {"success": False, "message": "discovery failed"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, configuration=dict(CONF), test=True), fake_api)
    assert exc.value.kwargs["msg"] == "Identity provider test failed: discovery failed"
    assert _calls(fake_api, "POST", LIST) == []


def test_test_api_error_is_wrapped(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", TEST, 500, {"detail": "boom"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, configuration=dict(CONF), test=True), fake_api)
    assert exc.value.kwargs["msg"].startswith("Failed to test identity provider 'sso'")


def test_create_disabled_patches_enabled_after_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _idp())
    fake_api.add("PATCH", ITEM, 200, _idp(enabled=False))
    result = run_module(module_under_test.main, dict(BASE, enabled=False, configuration=dict(CONF)), fake_api)
    assert result["changed"] is True
    assert "enabled" not in _calls(fake_api, "POST")[0]["body"]
    assert _calls(fake_api, "PATCH")[0]["body"] == {"enabled": False}
    assert result["identity_provider"]["enabled"] is False


def test_group_mapping_entries_reordered_no_patch(fake_api):
    entries = [{"idp_group_value": "a", "mapped_group_id": GID}, {"idp_group_value": "b", "mapped_group_id": GID}]
    fake_api.add("GET", LIST, 200, _list(_idp(configuration=dict(OIDC, group_mapping_entries=entries))))
    conf = dict(CONF, group_mapping_entries=list(reversed(entries)))
    result = run_module(module_under_test.main, dict(BASE, configuration=conf), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_empty_mapped_group_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    conf = dict(CONF, group_mapping_entries=[{"idp_group_value": "a", "mapped_group": ""}])
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, configuration=conf), fake_api)
    assert exc.value.kwargs["msg"] == "group '' not found"


def test_diff_masks_client_secret(fake_api):
    fake_api.add("GET", LIST, 200, _list(_idp()))
    fake_api.add("PATCH", ITEM, 200, _idp())
    result = run_module(module_under_test.main, dict(BASE, configuration={"client_secret": "s3"}, _ansible_diff=True), fake_api)
    assert "s3" not in str(result["diff"])
    assert result["diff"]["after"]["configuration"]["client_secret"] == "$encrypted$"
