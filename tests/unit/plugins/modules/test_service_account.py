# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import service_account as sa_module
from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import service_account_info as info_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/service_accounts"
ITEM = LIST + "/sa1"
PID = "33333333-3333-4333-8333-333333333333"
OTHER_PID = "44444444-4444-4444-8444-444444444444"
BASE = {"name": "ci", "project": PID}


def _sa(**kw):
    obj = {"id": "sa1", "name": "ci", "description": "old", "status": "active", "project_id": PID, "project_name": "demo"}
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _calls(api, method):
    return [c for c in api.calls if c["method"] == method]


def _writes(api):
    return [c for c in api.calls if c["method"] != "GET"]


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"name": "ci"})
    fake_api.add("POST", LIST, 201, _sa(description="d"))
    result = run_module(sa_module.main, dict(BASE, description="d"), fake_api)
    assert result["changed"] is True
    assert result["id"] == "sa1"
    assert result["service_account"]["name"] == "ci"
    assert _calls(fake_api, "POST")[0]["body"] == {"name": "ci", "description": "d", "project_id": PID}


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    fake_api.add("PATCH", ITEM, 200, _sa(description="new"))
    result = run_module(sa_module.main, dict(BASE, description="new"), fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"description": "new"}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    result = run_module(sa_module.main, dict(BASE, description="old"), fake_api)
    assert result["changed"] is False
    assert result["service_account"]["id"] == "sa1"
    assert _writes(fake_api) == []


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    fake_api.add("DELETE", ITEM, 204)
    result = run_module(sa_module.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is True
    assert len(_calls(fake_api, "DELETE")) == 1


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"name": "ci"})
    result = run_module(sa_module.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"name": "ci"})
    result = run_module(sa_module.main, dict(BASE, _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert _writes(fake_api) == []


def test_rename_idempotent(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"name": "ci"})
    fake_api.add("GET", LIST, 200, _list(_sa(name="ci2")), query={"name": "ci2"})
    result = run_module(sa_module.main, dict(BASE, new_name="ci2", description="old"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_rename_patches_name(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    fake_api.add("PATCH", ITEM, 200, _sa(name="ci2"))
    run_module(sa_module.main, dict(BASE, new_name="ci2"), fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"name": "ci2"}


def test_diff_mode_on_update(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    fake_api.add("PATCH", ITEM, 200, _sa(description="new"))
    result = run_module(sa_module.main, dict(BASE, description="new", _ansible_diff=True), fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}


def test_project_name_resolved_and_client_side_match(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, _list({"id": PID, "name": "demo"}), query={"name": "demo"})
    fake_api.add("GET", LIST, 200, _list(_sa(id="other", project_id=OTHER_PID)), query={"name": "ci"})
    fake_api.add("POST", LIST, 201, _sa())
    run_module(sa_module.main, {"name": "ci", "project": "demo"}, fake_api)
    assert _calls(fake_api, "POST")[0]["body"] == {"name": "ci", "project_id": PID}


def test_enabled_state_calls_enable_when_disabled(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa(status="disabled")), query={"name": "ci"})
    fake_api.add("POST", ITEM + "/enable", 200, _sa(status="active"))
    result = run_module(sa_module.main, dict(BASE, state="enabled"), fake_api)
    assert result["changed"] is True
    assert result["service_account"]["status"] == "active"
    assert [c["path"] for c in _writes(fake_api)] == [ITEM + "/enable"]


def test_enabled_state_noop_when_active(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    result = run_module(sa_module.main, dict(BASE, state="enabled"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_disabled_state_calls_disable(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    fake_api.add("POST", ITEM + "/disable", 200, _sa(status="disabled"))
    result = run_module(sa_module.main, dict(BASE, state="disabled"), fake_api)
    assert result["changed"] is True
    assert [c["path"] for c in _writes(fake_api)] == [ITEM + "/disable"]


def test_disabled_state_check_mode_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()), query={"name": "ci"})
    result = run_module(sa_module.main, dict(BASE, state="disabled", _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert result["service_account"]["status"] == "disabled"
    assert _writes(fake_api) == []


def test_disabled_state_creates_then_disables(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"name": "ci"})
    fake_api.add("POST", LIST, 201, _sa())
    fake_api.add("POST", ITEM + "/disable", 200, _sa(status="disabled"))
    result = run_module(sa_module.main, dict(BASE, state="disabled"), fake_api)
    assert result["changed"] is True
    assert [c["path"] for c in _writes(fake_api)] == [LIST, ITEM + "/disable"]


def test_enable_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa(status="disabled")), query={"name": "ci"})
    fake_api.add("POST", ITEM + "/enable", 409, {"detail": "nope"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(sa_module.main, dict(BASE, state="enabled"), fake_api)
    assert exc.value.kwargs["msg"].startswith("Failed to enable service account 'ci'")
    assert exc.value.kwargs["status"] == 409


def test_project_immutable_fails(fake_api):
    # Name lookups are project scoped, so a project mismatch can only be seen when the account is addressed by UUID.
    sa_id = "66666666-6666-4666-8666-666666666666"
    fake_api.add("GET", LIST + "/" + sa_id, 200, _sa(id=sa_id))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(sa_module.main, {"name": sa_id, "project": OTHER_PID}, fake_api)
    assert exc.value.kwargs["msg"] == "project_id cannot be changed on an existing service account"
    assert _writes(fake_api) == []


def test_same_name_in_other_project_is_a_new_account(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa(id="other", project_id=OTHER_PID)), query={"name": "ci"})
    fake_api.add("POST", LIST, 201, _sa())
    result = run_module(sa_module.main, BASE, fake_api)
    assert result["changed"] is True


def test_create_requires_project(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(sa_module.main, {"name": "ci"}, fake_api)
    assert "project" in exc.value.kwargs["msg"]


def test_info_filters_and_include_credentials(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa(), _sa(id="sa2", project_id=OTHER_PID)), query={"name": "ci", "status": "active"})
    fake_api.add("GET", ITEM + "/credentials", 200, {"resources": [{"id": "c1", "identifier": "cid", "status": "active"}], "max_credentials": 2})
    result = run_module(info_module.main, {"name": "ci", "project": PID, "status": "active", "include_credentials": True}, fake_api)
    assert result["changed"] is False
    assert [r["id"] for r in result["resources"]] == ["sa1"]
    assert result["resources"][0]["credentials"] == [{"id": "c1", "identifier": "cid", "status": "active"}]


def test_info_without_credentials(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()))
    result = run_module(info_module.main, {}, fake_api)
    assert "credentials" not in result["resources"][0]
    assert len(fake_api.calls) == 1


def test_info_credentials_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_sa()))
    fake_api.add("GET", ITEM + "/credentials", 500, {"detail": "boom"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(info_module.main, {"include_credentials": True}, fake_api)
    assert exc.value.kwargs["status"] == 500
