# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import project as project_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/projects"


def _project(**kw):
    obj = {"id": "p1", "name": "demo", "description": "old", "labels": {}, "is_default": False, "is_builtin": False}
    obj.update(kw)
    return obj


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None}, query={"name": "demo"})
    fake_api.add("POST", LIST, 201, _project(description="d", labels={"a": "b"}))
    result = run_module(project_module.main, {"name": "demo", "description": "d", "labels": {"a": "b"}}, fake_api)
    assert result["changed"] is True
    assert result["id"] == "p1"
    assert result["project"]["name"] == "demo"
    post = [c for c in fake_api.calls if c["method"] == "POST"][0]
    assert post["body"] == {"name": "demo", "description": "d", "labels": {"a": "b"}}


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_project()], "next": None}, query={"name": "demo"})
    fake_api.add("PATCH", LIST + "/p1", 200, _project(description="new"))
    result = run_module(project_module.main, {"name": "demo", "description": "new", "labels": {}}, fake_api)
    assert result["changed"] is True
    patch = [c for c in fake_api.calls if c["method"] == "PATCH"][0]
    assert patch["body"] == {"description": "new"}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_project()], "next": None}, query={"name": "demo"})
    result = run_module(project_module.main, {"name": "demo", "description": "old"}, fake_api)
    assert result["changed"] is False
    assert result["project"]["id"] == "p1"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_project()], "next": None}, query={"name": "demo"})
    fake_api.add("DELETE", LIST + "/p1", 204)
    result = run_module(project_module.main, {"name": "demo", "state": "absent"}, fake_api)
    assert result["changed"] is True
    assert fake_api.calls[-1]["method"] == "DELETE"


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None}, query={"name": "demo"})
    result = run_module(project_module.main, {"name": "demo", "state": "absent"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None}, query={"name": "demo"})
    result = run_module(project_module.main, {"name": "demo", "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_rename_with_new_name_patches_name(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_project()], "next": None}, query={"name": "demo"})
    fake_api.add("PATCH", LIST + "/p1", 200, _project(name="renamed"))
    result = run_module(project_module.main, {"name": "demo", "new_name": "renamed"}, fake_api)
    assert result["changed"] is True
    patch = [c for c in fake_api.calls if c["method"] == "PATCH"][0]
    assert patch["body"] == {"name": "renamed"}


def test_new_name_ignored_when_creating(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None}, query={"name": "demo"})
    fake_api.add("POST", LIST, 201, _project())
    run_module(project_module.main, {"name": "demo", "new_name": "renamed"}, fake_api)
    post = [c for c in fake_api.calls if c["method"] == "POST"][0]
    assert post["body"] == {"name": "demo"}


def test_exists_state_creates_but_never_updates(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None}, query={"name": "demo"})
    fake_api.add("POST", LIST, 201, _project())
    result = run_module(project_module.main, {"name": "demo", "state": "exists"}, fake_api)
    assert result["changed"] is True

    fake_api.calls[:] = []
    fake_api.routes[:] = []
    fake_api.add("GET", LIST, 200, {"resources": [_project()], "next": None}, query={"name": "demo"})
    result = run_module(project_module.main, {"name": "demo", "state": "exists", "description": "other", "new_name": "x"}, fake_api)
    assert result["changed"] is False
    assert result["project"]["description"] == "old"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_delete_builtin_project_fails_with_name(fake_api):
    fake_api.add(
        "GET", LIST, 200, {"resources": [_project(id="p0", name="Default", is_builtin=True, is_default=True)], "next": None}, query={"name": "Default"}
    )
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(project_module.main, {"name": "Default", "state": "absent"}, fake_api)
    assert "Default" in exc.value.args[0]["msg"]
    assert [c["method"] for c in fake_api.calls] == ["GET"]
