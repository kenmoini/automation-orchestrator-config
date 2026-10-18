# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import group as group_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/groups"
DIRECTORY = "/api/v1/groups/directory"


def _group(**kw):
    obj = {"id": "g1", "name": "ops", "description": "old", "is_builtin": False, "source": "local", "member_count": 0}
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _group(description="d"))
    result = run_module(group_module.main, {"name": "ops", "description": "d"}, fake_api)
    assert result["changed"] is True
    assert result["id"] == "g1"
    assert result["group"]["name"] == "ops"
    post = [c for c in fake_api.calls if c["method"] == "POST"][0]
    assert post["body"] == {"name": "ops", "description": "d"}


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group()))
    fake_api.add("PATCH", LIST + "/g1", 200, _group(description="new"))
    result = run_module(group_module.main, {"name": "ops", "description": "new"}, fake_api)
    assert result["changed"] is True
    patch = [c for c in fake_api.calls if c["method"] == "PATCH"][0]
    assert patch["body"] == {"description": "new"}


def test_lookup_is_exact_match(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group(id="g2", name="ops2"), _group()))
    fake_api.add("PATCH", LIST + "/g1", 200, _group(description="new"))
    run_module(group_module.main, {"name": "ops", "description": "new"}, fake_api)
    assert [c["path"] for c in fake_api.calls if c["method"] == "PATCH"] == [LIST + "/g1"]


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group()))
    result = run_module(group_module.main, {"name": "ops", "description": "old"}, fake_api)
    assert result["changed"] is False
    assert result["group"]["id"] == "g1"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group()))
    fake_api.add("DELETE", LIST + "/g1", 204)
    result = run_module(group_module.main, {"name": "ops", "state": "absent"}, fake_api)
    assert result["changed"] is True
    assert fake_api.calls[-1]["method"] == "DELETE"


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(group_module.main, {"name": "ops", "state": "absent"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(group_module.main, {"name": "ops", "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_rename_with_new_name_patches_name(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group()))
    fake_api.add("PATCH", LIST + "/g1", 200, _group(name="renamed"))
    result = run_module(group_module.main, {"name": "ops", "new_name": "renamed"}, fake_api)
    assert result["changed"] is True
    patch = [c for c in fake_api.calls if c["method"] == "PATCH"][0]
    assert patch["body"] == {"name": "renamed"}


def test_rename_rerun_is_idempotent(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group(name="renamed")))
    result = run_module(group_module.main, {"name": "ops", "new_name": "renamed", "description": "old"}, fake_api)
    assert result["changed"] is False
    assert result["group"]["name"] == "renamed"
    assert [c["method"] for c in fake_api.calls] == ["GET", "GET"]


def test_create_uses_new_name_when_neither_exists(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _group(name="renamed"))
    run_module(group_module.main, {"name": "ops", "new_name": "renamed"}, fake_api)
    post = [c for c in fake_api.calls if c["method"] == "POST"][0]
    assert post["body"] == {"name": "renamed"}


def test_diff_mode_reports_patched_keys_only(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group()))
    fake_api.add("PATCH", LIST + "/g1", 200, _group(description="new"))
    result = run_module(group_module.main, {"name": "ops", "description": "new", "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}


def test_exists_state_creates_but_never_updates(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _group())
    result = run_module(group_module.main, {"name": "ops", "state": "exists"}, fake_api)
    assert result["changed"] is True

    fake_api.calls[:] = []
    fake_api.routes[:] = []
    fake_api.add("GET", LIST, 200, _list(_group()))
    result = run_module(group_module.main, {"name": "ops", "state": "exists", "description": "other", "new_name": "x"}, fake_api)
    assert result["changed"] is False
    assert result["group"]["description"] == "old"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_group_delete_builtin_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_group(id="g0", name="users", is_builtin=True)))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(group_module.main, {"name": "users", "state": "absent"}, fake_api)
    assert "users" in exc.value.args[0]["msg"]
    assert [c["method"] for c in fake_api.calls] == ["GET"]
