# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import user as user_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/users"
GROUPS = "/api/v1/groups"
DIRECTORY = "/api/v1/groups/directory"
PW = "correct-horse-battery"
G_USERS = "11111111-1111-4111-8111-111111111111"
G_OPS = "22222222-2222-4222-8222-222222222222"
G_IDP = "33333333-3333-4333-8333-333333333333"


def _user(**kw):
    obj = {
        "id": "u1",
        "username": "alice",
        "email": "a@example.com",
        "first_name": "Alice",
        "last_name": "A",
        "is_enabled": True,
        "is_builtin": False,
        "auth_type": "local",
    }
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _member(gid, name, *types):
    return {"id": gid, "name": name, "membership_sources": [{"type": t} for t in (types or ("manual",))]}


def _by_method(fake_api, method):
    return [c for c in fake_api.calls if c["method"] == method]


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"username": "alice"})
    fake_api.add("POST", LIST, 201, _user())
    result = run_module(user_module.main, {"username": "alice", "password": PW, "email": "a@example.com", "is_enabled": True}, fake_api)
    assert result["changed"] is True
    assert result["id"] == "u1"
    assert result["user"]["username"] == "alice"
    assert "password" not in result["user"]
    assert _by_method(fake_api, "POST")[0]["body"] == {"username": "alice", "password": PW, "email": "a@example.com", "is_enabled": True}


def test_user_create_requires_password(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(user_module.main, {"username": "alice"}, fake_api)
    assert exc.value.args[0]["msg"] == "password is required to create a local user 'alice'"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_user_create_passes_group_names(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("GET", GROUPS + "/" + G_OPS, 200, {"id": G_OPS, "name": "ops"})
    fake_api.add("POST", LIST, 201, _user())
    result = run_module(user_module.main, {"username": "alice", "password": PW, "groups": ["devs", G_OPS]}, fake_api)
    assert _by_method(fake_api, "POST")[0]["body"]["group_names"] == ["devs", "ops"]
    assert result["groups"] == ["devs", "ops"]


def test_user_create_empty_groups_sends_empty_list(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _user())
    run_module(user_module.main, {"username": "alice", "password": PW, "groups": []}, fake_api)
    assert _by_method(fake_api, "POST")[0]["body"]["group_names"] == []


def test_create_without_groups_omits_group_names(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _user())
    run_module(user_module.main, {"username": "alice", "password": PW}, fake_api)
    assert "group_names" not in _by_method(fake_api, "POST")[0]["body"]


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("PATCH", LIST + "/u1", 200, _user(email="new@example.com"))
    result = run_module(user_module.main, {"username": "alice", "email": "new@example.com", "first_name": "Alice"}, fake_api)
    assert result["changed"] is True
    assert _by_method(fake_api, "PATCH")[0]["body"] == {"email": "new@example.com"}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    result = run_module(user_module.main, {"username": "alice", "email": "a@example.com", "password": PW}, fake_api)
    assert result["changed"] is False
    assert result["user"]["id"] == "u1"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("DELETE", LIST + "/u1", 204)
    result = run_module(user_module.main, {"username": "alice", "state": "absent"}, fake_api)
    assert result["changed"] is True
    assert fake_api.calls[-1]["method"] == "DELETE"


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"username": "alice"})
    result = run_module(user_module.main, {"username": "alice", "state": "absent"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"username": "alice"})
    result = run_module(user_module.main, {"username": "alice", "password": PW, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert [c["method"] for c in fake_api.calls] == ["GET"]
    assert "password" not in result["user"] or result["user"]["password"] != PW


def test_rename_with_new_username_patches_username(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("PATCH", LIST + "/u1", 200, _user(username="alicia"))
    result = run_module(user_module.main, {"username": "alice", "new_username": "alicia"}, fake_api)
    assert result["changed"] is True
    assert _by_method(fake_api, "PATCH")[0]["body"] == {"username": "alicia"}


def test_rename_rerun_is_idempotent(fake_api):
    fake_api.add("GET", LIST, 200, _list(), query={"username": "alice"})
    fake_api.add("GET", LIST, 200, _list(_user(username="alicia")), query={"username": "alicia"})
    result = run_module(user_module.main, {"username": "alice", "new_username": "alicia"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET", "GET"]


def test_create_uses_new_username_when_neither_exists(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _user(username="alicia"))
    run_module(user_module.main, {"username": "alice", "new_username": "alicia", "password": PW}, fake_api)
    assert _by_method(fake_api, "POST")[0]["body"]["username"] == "alicia"


def test_diff_mode_reports_patched_keys_only(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("PATCH", LIST + "/u1", 200, _user(first_name="Al"))
    result = run_module(user_module.main, {"username": "alice", "first_name": "Al", "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {"first_name": "Alice"}, "after": {"first_name": "Al"}}


def test_exists_state_creates_but_never_updates(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _user())
    result = run_module(user_module.main, {"username": "alice", "state": "exists", "password": PW}, fake_api)
    assert result["changed"] is True

    fake_api.calls[:] = []
    fake_api.routes[:] = []
    fake_api.add("GET", LIST, 200, _list(_user()))
    result = run_module(user_module.main, {"username": "alice", "state": "exists", "email": "other@example.com"}, fake_api)
    assert result["changed"] is False
    assert result["user"]["email"] == "a@example.com"
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_user_password_sent_only_on_create_by_default(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("PATCH", LIST + "/u1", 200, _user(first_name="Al"))
    run_module(user_module.main, {"username": "alice", "password": PW, "first_name": "Al"}, fake_api)
    assert _by_method(fake_api, "PATCH")[0]["body"] == {"first_name": "Al"}


def test_user_update_password_always_patches(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("PATCH", LIST + "/u1", 200, _user())
    result = run_module(user_module.main, {"username": "alice", "password": PW, "update_password": "always", "_ansible_diff": True}, fake_api)
    assert result["changed"] is True
    assert _by_method(fake_api, "PATCH")[0]["body"] == {"password": PW}
    assert PW not in str(result["diff"])
    assert PW not in str(result["user"])


def test_user_federated_never_sent_password(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user(auth_type="federated")), query={"username": "alice"})
    result = run_module(user_module.main, {"username": "alice", "password": PW, "update_password": "always"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_user_groups_put_only_when_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": [_member(G_USERS, "users"), _member(G_OPS, "ops")]})
    result = run_module(user_module.main, {"username": "alice", "groups": [G_OPS, G_USERS]}, fake_api)
    assert result["changed"] is False
    assert result["groups"] == ["ops", "users"]
    assert not _by_method(fake_api, "PUT")

    fake_api.calls[:] = []
    fake_api.add("PUT", LIST + "/u1/groups", 200, {})
    result = run_module(user_module.main, {"username": "alice", "groups": [G_OPS]}, fake_api)
    assert result["changed"] is True
    assert _by_method(fake_api, "PUT")[0]["body"] == {"group_ids": [G_OPS]}
    assert result["groups"] == ["ops"]


def test_user_groups_by_name_resolved(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", DIRECTORY, 200, _list({"id": G_OPS, "name": "ops"}), query={"name": "ops"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": []})
    fake_api.add("PUT", LIST + "/u1/groups", 200, {})
    result = run_module(user_module.main, {"username": "alice", "groups": ["ops"]}, fake_api)
    assert result["changed"] is True
    assert _by_method(fake_api, "PUT")[0]["body"] == {"group_ids": [G_OPS]}


def test_user_groups_preserve_idp_memberships(fake_api):
    fake_api.add("GET", GROUPS + "/" + G_OPS, 200, {"id": G_OPS, "name": "ops"})
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": [_member(G_IDP, "idp-admins", "idp"), _member(G_USERS, "users")]})
    fake_api.add("PUT", LIST + "/u1/groups", 200, {})
    result = run_module(user_module.main, {"username": "alice", "groups": [G_OPS]}, fake_api)
    assert _by_method(fake_api, "PUT")[0]["body"] == {"group_ids": sorted([G_OPS, G_IDP])}
    assert "idp-admins" in result["groups"]


def test_user_groups_check_mode_no_put(fake_api):
    fake_api.add("GET", GROUPS + "/" + G_OPS, 200, {"id": G_OPS, "name": "ops"})
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": [_member(G_USERS, "users")]})
    result = run_module(user_module.main, {"username": "alice", "groups": [G_OPS], "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert not _by_method(fake_api, "PUT")


def test_user_groups_none_leaves_memberships_untouched(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    result = run_module(user_module.main, {"username": "alice"}, fake_api)
    assert result["changed"] is False
    assert [c["method"] for c in fake_api.calls] == ["GET"]
    assert "groups" not in result


def test_user_groups_put_failure_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": []})
    fake_api.add("GET", GROUPS + "/" + G_OPS, 200, {"id": G_OPS, "name": "ops"})
    fake_api.add("PUT", LIST + "/u1/groups", 422, {"title": "Unprocessable", "status": 422, "detail": "unknown group"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(user_module.main, {"username": "alice", "groups": [G_OPS]}, fake_api)
    assert exc.value.args[0]["status"] == 422
    assert exc.value.args[0]["msg"].startswith("Failed to update groups of user")


def test_user_groups_unknown_uuid_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": []})
    fake_api.add("GET", GROUPS + "/" + G_OPS, 404, {"title": "Not Found", "status": 404, "detail": "nope"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(user_module.main, {"username": "alice", "groups": [G_OPS]}, fake_api)
    assert exc.value.args[0]["msg"] == "group '{0}' not found".format(G_OPS)
    assert not _by_method(fake_api, "PUT")


def test_user_federated_with_metadata_change_patches_without_password(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user(auth_type="federated")), query={"username": "alice"})
    fake_api.add("PATCH", LIST + "/u1", 200, _user(email="new@example.com"))
    run_module(user_module.main, {"username": "alice", "email": "new@example.com", "password": PW, "update_password": "always"}, fake_api)
    assert _by_method(fake_api, "PATCH")[0]["body"] == {"email": "new@example.com"}


def test_user_exists_missing_without_password_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(user_module.main, {"username": "alice", "state": "exists"}, fake_api)
    assert "password is required" in exc.value.args[0]["msg"]


def test_user_groups_follow_pagination(fake_api):
    fake_api.add("GET", LIST, 200, _list(_user()), query={"username": "alice"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": [_member(G_OPS, "ops")], "next": None}, query={"cursor": "c2"})
    fake_api.add("GET", LIST + "/u1/groups", 200, {"resources": [_member(G_USERS, "users")], "next": "c2"})
    result = run_module(user_module.main, {"username": "alice", "groups": [G_OPS, G_USERS]}, fake_api)
    assert result["changed"] is False
    assert result["groups"] == ["ops", "users"]
    assert not _by_method(fake_api, "PUT")
    pages = [c for c in fake_api.calls if c["path"] == LIST + "/u1/groups"]
    assert [c["query"].get("cursor") for c in pages] == [None, "c2"]
