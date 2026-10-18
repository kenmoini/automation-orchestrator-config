# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import role as role_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/roles"
POLICIES = "/api/v1/policies"
PID = "11111111-1111-4111-8111-111111111111"
POL_UUID = "22222222-2222-4222-8222-222222222222"


def _role(**kw):
    obj = {"id": "r1", "name": "ops", "description": "old", "policies": ["a", "b"], "labels": {"a": "1"}, "is_builtin": False, "project_id": None}
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _posts(api):
    return [c for c in api.calls if c["method"] == "POST"]


def _patches(api):
    return [c for c in api.calls if c["method"] == "PATCH"]


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _role())
    result = run_module(role_module.main, {"name": "ops", "description": "d", "policies": ["a", "b"], "labels": {"a": "1"}}, fake_api)
    assert result["changed"] is True
    assert result["id"] == "r1"
    assert result["role"]["name"] == "ops"
    assert _posts(fake_api)[0]["body"] == {"name": "ops", "description": "d", "policies": ["a", "b"], "labels": {"a": "1"}}


def test_create_with_project_sends_project_id(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _role(project_id=PID))
    run_module(role_module.main, {"name": "ops", "policies": ["a"], "project": PID}, fake_api)
    assert _posts(fake_api)[0]["body"] == {"name": "ops", "policies": ["a"], "project_id": PID}


def test_create_requires_policies(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(role_module.main, {"name": "ops"}, fake_api)
    assert exc.value.kwargs["msg"] == "policies is required to create role 'ops'"
    assert _posts(fake_api) == []


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role()))
    fake_api.add("PATCH", LIST + "/r1", 200, _role(description="new"))
    result = run_module(role_module.main, {"name": "ops", "description": "new"}, fake_api)
    assert result["changed"] is True
    assert _patches(fake_api)[0]["body"] == {"description": "new"}


def test_policies_changed_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role()))
    fake_api.add("PATCH", LIST + "/r1", 200, _role(policies=["a", "c"]))
    run_module(role_module.main, {"name": "ops", "policies": ["a", "c"]}, fake_api)
    assert _patches(fake_api)[0]["body"] == {"policies": ["a", "c"]}


def test_labels_changed_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role()))
    fake_api.add("PATCH", LIST + "/r1", 200, _role(labels={"b": "2"}))
    run_module(role_module.main, {"name": "ops", "labels": {"b": "2"}}, fake_api)
    assert _patches(fake_api)[0]["body"] == {"labels": {"b": "2"}}


def test_no_change_policies_order_insensitive(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role()))
    result = run_module(role_module.main, {"name": "ops", "description": "old", "policies": ["b", "a"]}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_role_policies_uuid_resolved_to_names(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("GET", POLICIES + "/" + POL_UUID, 200, {"id": POL_UUID, "name": "viewer", "project_id": None})
    fake_api.add("POST", LIST, 201, _role(policies=["viewer", "a"]))
    run_module(role_module.main, {"name": "ops", "policies": [POL_UUID, "a"]}, fake_api)
    assert _posts(fake_api)[0]["body"]["policies"] == ["viewer", "a"]


def test_role_policy_uuid_not_found_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("GET", POLICIES + "/" + POL_UUID, 404, {"status": 404, "title": "Not Found", "detail": "nope"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(role_module.main, {"name": "ops", "policies": [POL_UUID]}, fake_api)
    assert exc.value.kwargs["msg"] == "policy '{0}' not found".format(POL_UUID)


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role()))
    fake_api.add("DELETE", LIST + "/r1", 204)
    result = run_module(role_module.main, {"name": "ops", "state": "absent"}, fake_api)
    assert result["changed"] is True
    assert fake_api.calls[-1]["method"] == "DELETE"


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(role_module.main, {"name": "ops", "state": "absent"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_delete_builtin_fails_with_name(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role(name="admin", is_builtin=True)))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(role_module.main, {"name": "admin", "state": "absent"}, fake_api)
    assert "admin" in exc.value.kwargs["msg"]
    assert fake_api.calls[-1]["method"] == "GET"


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(role_module.main, {"name": "ops", "policies": ["a"], "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_project_scoped_lookup_sends_project_id(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role(id="sys"), _role(id="r2", project_id=PID)), query={"project_id": PID})
    fake_api.add("PATCH", LIST + "/r2", 200, _role(id="r2", description="new", project_id=PID))
    run_module(role_module.main, {"name": "ops", "description": "new", "project": PID}, fake_api)
    assert fake_api.calls[0]["query"]["project_id"] == PID
    assert _patches(fake_api)[0]["path"] == LIST + "/r2"


def test_unscoped_lookup_ignores_project_objects(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role(id="r2", project_id=PID)))
    fake_api.add("POST", LIST, 201, _role())
    result = run_module(role_module.main, {"name": "ops", "policies": ["a"]}, fake_api)
    assert "project_id" not in fake_api.calls[0]["query"]
    assert result["changed"] is True


def test_diff_mode_on_update(fake_api):
    fake_api.add("GET", LIST, 200, _list(_role()))
    fake_api.add("PATCH", LIST + "/r1", 200, _role(description="new"))
    result = run_module(role_module.main, {"name": "ops", "description": "new", "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}
