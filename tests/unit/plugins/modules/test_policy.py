# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import policy as policy_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/policies"
PID = "11111111-1111-4111-8111-111111111111"
STMTS = [
    {"effect": "allow", "actions": ["workflow:read", "workflow:list"], "scope": "any", "conditions": None},
    {"effect": "deny", "actions": ["user:delete"], "scope": "self", "conditions": None},
]


def _policy(**kw):
    obj = {"id": "p1", "name": "reader", "description": "old", "statements": STMTS, "labels": {"a": "1"}, "is_builtin": False, "project_id": None}
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
    fake_api.add("POST", LIST, 201, _policy())
    result = run_module(policy_module.main, {"name": "reader", "description": "d", "statements": STMTS, "labels": {"a": "1"}}, fake_api)
    assert result["changed"] is True
    assert result["id"] == "p1"
    assert result["policy"]["name"] == "reader"
    assert _posts(fake_api)[0]["body"] == {"name": "reader", "description": "d", "statements": STMTS, "labels": {"a": "1"}}


def test_create_with_project_sends_project_id(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _policy(project_id=PID))
    run_module(policy_module.main, {"name": "reader", "statements": STMTS, "project": PID}, fake_api)
    assert _posts(fake_api)[0]["body"] == {"name": "reader", "statements": STMTS, "project_id": PID}


def test_create_requires_statements(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(policy_module.main, {"name": "reader"}, fake_api)
    assert exc.value.kwargs["msg"] == "statements is required to create policy 'reader'"
    assert _posts(fake_api) == []


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy()))
    fake_api.add("PATCH", LIST + "/p1", 200, _policy(description="new"))
    result = run_module(policy_module.main, {"name": "reader", "description": "new"}, fake_api)
    assert result["changed"] is True
    assert _patches(fake_api)[0]["body"] == {"description": "new"}


def test_labels_changed_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy()))
    fake_api.add("PATCH", LIST + "/p1", 200, _policy(labels={"b": "2"}))
    run_module(policy_module.main, {"name": "reader", "labels": {"b": "2"}}, fake_api)
    assert _patches(fake_api)[0]["body"] == {"labels": {"b": "2"}}


def test_statements_changed_patch(fake_api):
    new = [{"effect": "allow", "actions": ["workflow:read"], "scope": "any", "conditions": None}]
    fake_api.add("GET", LIST, 200, _list(_policy()))
    fake_api.add("PATCH", LIST + "/p1", 200, _policy(statements=new))
    run_module(policy_module.main, {"name": "reader", "statements": new}, fake_api)
    assert _patches(fake_api)[0]["body"] == {"statements": new}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy()))
    result = run_module(policy_module.main, {"name": "reader", "description": "old", "labels": {"a": "1"}}, fake_api)
    assert result["changed"] is False
    assert result["policy"]["id"] == "p1"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_policy_statements_order_insensitive(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy()))
    reordered = [
        {"effect": "deny", "actions": ["user:delete"], "scope": "self"},
        {"effect": "allow", "actions": ["workflow:list", "workflow:read"], "scope": "any", "conditions": None},
    ]
    result = run_module(policy_module.main, {"name": "reader", "statements": reordered}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy()))
    fake_api.add("DELETE", LIST + "/p1", 204)
    result = run_module(policy_module.main, {"name": "reader", "state": "absent"}, fake_api)
    assert result["changed"] is True
    assert fake_api.calls[-1]["method"] == "DELETE"


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(policy_module.main, {"name": "reader", "state": "absent"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(policy_module.main, {"name": "reader", "statements": STMTS, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_project_scoped_lookup_sends_project_id(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy(id="sys", project_id=None), _policy(id="p2", project_id=PID)), query={"project_id": PID})
    fake_api.add("PATCH", LIST + "/p2", 200, _policy(id="p2", description="new", project_id=PID))
    run_module(policy_module.main, {"name": "reader", "description": "new", "project": PID}, fake_api)
    assert fake_api.calls[0]["query"]["project_id"] == PID
    assert _patches(fake_api)[0]["path"] == LIST + "/p2"


def test_unscoped_lookup_ignores_project_objects(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy(id="p2", project_id=PID)))
    fake_api.add("POST", LIST, 201, _policy())
    result = run_module(policy_module.main, {"name": "reader", "statements": STMTS}, fake_api)
    assert "project_id" not in fake_api.calls[0]["query"]
    assert result["changed"] is True
    assert len(_posts(fake_api)) == 1


def test_diff_mode_on_update(fake_api):
    fake_api.add("GET", LIST, 200, _list(_policy()))
    fake_api.add("PATCH", LIST + "/p1", 200, _policy(description="new"))
    result = run_module(policy_module.main, {"name": "reader", "description": "new", "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}
