# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import (
    AnsibleFailJson,
    make_module,
)

PID = "11111111-1111-4111-8111-111111111111"
UID = "22222222-2222-4222-8222-222222222222"
GID = "33333333-3333-4333-8333-333333333333"


def page(resources, next_cursor=None):
    return {"next": next_cursor, "prev": None, "total": None, "resources": resources}


def test_get_all_follows_cursor(fake_api):
    fake_api.add("GET", "/api/v1/integrations", 200, page([{"id": "c"}]), query={"cursor": "abc"})
    fake_api.add("GET", "/api/v1/integrations", 200, page([{"id": "a"}, {"id": "b"}], "abc"))
    module = make_module(fake_api)

    assert module.get_all("/integrations", query={"enabled": True}) == [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    assert [c["query"] for c in fake_api.calls] == [
        {"enabled": "true", "limit": "100"},
        {"enabled": "true", "limit": "100", "cursor": "abc"},
    ]


def test_get_all_stops_on_repeated_cursor(fake_api):
    fake_api.add("GET", "/api/v1/integrations", 200, page([{"id": "a"}], "abc"))
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.get_all("/integrations")
    assert "abc" in exc.value.kwargs["msg"]
    assert len(fake_api.calls) == 2


def test_get_one_by_name_uses_server_filter_for_projects(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, page([{"id": PID, "name": "Default"}]), query={"name": "Default"})
    module = make_module(fake_api)

    assert module.get_one_by_name("/projects", "Default") == {"id": PID, "name": "Default"}
    assert fake_api.calls[-1]["query"] == {"name": "Default", "limit": "100"}


def test_get_one_by_name_exact_match_only(fake_api):
    entries = [{"id": "b2", "username": "bobby"}, {"id": "b1", "username": "bob"}]
    fake_api.add("GET", "/api/v1/users/directory", 200, page(entries), query={"username": "bob"})
    module = make_module(fake_api)

    assert module.get_one_by_name("/users/directory", "bob", name_field="username") == {"id": "b1", "username": "bob"}


def test_get_one_by_name_duplicates_fail(fake_api):
    fake_api.add("GET", "/api/v1/integrations", 200, page([{"id": "1", "name": "dup"}, {"id": "2", "name": "dup"}]))
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.get_one_by_name("/integrations", "dup")
    assert exc.value.kwargs["msg"] == "Found 2 integrations named 'dup'; expected 1"


def test_resolve_id_passes_uuid_through_without_http(fake_api):
    module = make_module(fake_api)

    assert module.resolve_id("project", PID) == PID
    assert module.resolve_id("workflow", UID) == UID
    assert fake_api.calls == []


def test_resolve_id_not_found_fails_with_kind_and_value(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, page([]), query={"name": "nope"})
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.resolve_id("project", "nope")
    assert exc.value.kwargs["msg"] == "project 'nope' not found"
    assert module.resolve_id("project", "nope", required=False) is None


def test_resolve_workflow_requires_project_scope(fake_api):
    path = "/api/v1/projects/{0}/workflows".format(PID)
    fake_api.add("GET", path, 200, page([{"id": UID, "name": "deploy"}]))
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.resolve_id("workflow", "deploy")
    assert "project_id" in exc.value.kwargs["msg"]
    assert fake_api.calls == []

    assert module.resolve_id("workflow", "deploy", project_id=PID) == UID
    assert fake_api.calls[-1]["path"] == path

    with pytest.raises(AnsibleFailJson) as exc:
        module.resolve_id("workflow", "missing", project_id=PID)
    assert exc.value.kwargs["msg"] == "workflow 'missing' not found in project {0}".format(PID)


def test_group_lookup_falls_back_when_directory_forbidden(fake_api):
    fake_api.add("GET", "/api/v1/groups/directory", 403, {"status": 403, "title": "Forbidden", "detail": "nope"})
    fake_api.add("GET", "/api/v1/groups", 200, page([{"id": GID, "name": "admins"}]), query={"cursor": "c2"})
    fake_api.add("GET", "/api/v1/groups", 200, page([{"id": "other", "name": "admins-2"}], "c2"))
    fake_api.add("GET", "/api/v1/groups/{0}".format(GID), 200, {"id": GID, "name": "admins", "description": "full"})
    module = make_module(fake_api)

    assert module.resolve_id("group", "admins") == GID
    assert [c["path"] for c in fake_api.calls] == ["/api/v1/groups/directory", "/api/v1/groups", "/api/v1/groups"]
    assert fake_api.calls[0]["query"] == {"name": "admins", "limit": "100"}

    assert module.resolve_obj("group", "admins")["description"] == "full"


@pytest.mark.parametrize("kind, path", [("role", "/api/v1/roles"), ("policy", "/api/v1/policies")])
def test_unscoped_role_lookup_prefers_system_scope(fake_api, kind, path):
    entries = [{"id": UID, "name": "admin", "project_id": PID}, {"id": GID, "name": "admin", "project_id": None}]
    fake_api.add("GET", path, 200, page(entries), query={"name": "admin"})
    module = make_module(fake_api)

    assert module.resolve_id(kind, "admin") == GID
    assert "project_id" not in fake_api.calls[-1]["query"]
    assert module.resolve_id(kind, "admin", project_id=PID) == UID
    assert fake_api.calls[-1]["query"]["project_id"] == PID


def test_find_existing_prefers_name_then_new_name_then_none(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, page([{"id": "o", "name": "old"}]), query={"name": "old"})
    fake_api.add("GET", "/api/v1/projects", 200, page([]), query={"name": "gone"})
    fake_api.add("GET", "/api/v1/projects", 200, page([{"id": "n", "name": "new"}]), query={"name": "new"})
    fake_api.add("GET", "/api/v1/projects", 200, page([]), query={"name": "nothing"})
    module = make_module(fake_api)

    assert module.find_existing("/projects", "old", "new")["id"] == "o"
    assert module.find_existing("/projects", "gone", "new")["id"] == "n"
    assert module.find_existing("/projects", "gone", "nothing") is None
    assert module.find_existing("/projects", "gone") is None
