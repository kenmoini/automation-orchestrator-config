# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import role_assignment as ra_module
from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import role_assignment_info as info_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

LIST = "/api/v1/role_assignments"
UID = "11111111-1111-4111-8111-111111111111"
GID = "22222222-2222-4222-8222-222222222222"
PID = "33333333-3333-4333-8333-333333333333"
RID = "44444444-4444-4444-8444-444444444444"


def _ra(**kw):
    obj = {
        "id": "ra1",
        "principal_id": UID,
        "group_id": None,
        "principal_name": "alice",
        "principal_type": "user",
        "role_name": "ops",
        "project_id": PID,
        "is_builtin": False,
    }
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _calls(api, method):
    return [c for c in api.calls if c["method"] == method]


def test_create_user_assignment_body(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _ra())
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID}, fake_api)
    assert result["changed"] is True
    assert result["id"] == "ra1"
    assert result["role_assignment"]["role_name"] == "ops"
    assert _calls(fake_api, "POST")[0]["body"] == {"role_name": "ops", "principal_id": UID, "project_id": PID}


def test_create_global_assignment_omits_project(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _ra(project_id=None))
    run_module(ra_module.main, {"role": "ops", "user": UID}, fake_api)
    assert _calls(fake_api, "POST")[0]["body"] == {"role_name": "ops", "principal_id": UID}


def test_create_group_assignment_body(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _ra(principal_id=None, group_id=GID, principal_type="group"))
    run_module(ra_module.main, {"role": "ops", "group": GID, "project": PID}, fake_api)
    assert _calls(fake_api, "POST")[0]["body"] == {"role_name": "ops", "group_id": GID, "project_id": PID}
    assert _calls(fake_api, "GET")[0]["query"]["group_id"] == GID


def test_existing_assignment_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra()))
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID}, fake_api)
    assert result["changed"] is False
    assert result["id"] == "ra1"
    assert [c["method"] for c in fake_api.calls] == ["GET"]
    query = fake_api.calls[0]["query"]
    assert query["role_name"] == "ops" and query["principal_id"] == UID and query["project_id"] == PID


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra()))
    fake_api.add("DELETE", LIST + "/ra1", 204)
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID, "state": "absent"}, fake_api)
    assert result["changed"] is True
    assert len(_calls(fake_api, "DELETE")) == 1


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "state": "absent"}, fake_api)
    assert result["changed"] is False
    assert _calls(fake_api, "DELETE") == []


def test_user_and_group_mutually_exclusive(fake_api):
    with pytest.raises(AnsibleFailJson):
        run_module(ra_module.main, {"role": "ops", "user": UID, "group": GID}, fake_api)


def test_user_or_group_required(fake_api):
    with pytest.raises(AnsibleFailJson):
        run_module(ra_module.main, {"role": "ops"}, fake_api)


def test_global_vs_project_scope_distinguished(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra(project_id=PID)))
    fake_api.add("POST", LIST, 201, _ra(project_id=None))
    result = run_module(ra_module.main, {"role": "ops", "user": UID}, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "POST")[0]["body"] == {"role_name": "ops", "principal_id": UID}


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "POST") == []
    assert result["role_assignment"]["role_name"] == "ops"


def test_check_mode_absent_no_delete(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra()))
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID, "state": "absent", "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "DELETE") == []


def test_delete_builtin_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra(is_builtin=True)))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID, "state": "absent"}, fake_api)
    assert "ops" in exc.value.kwargs["msg"] and "built-in" in exc.value.kwargs["msg"]
    assert _calls(fake_api, "DELETE") == []


def test_role_uuid_resolved_to_name(fake_api):
    fake_api.add("GET", "/api/v1/projects/" + PID + "/roles/" + RID, 200, {"id": RID, "name": "ops"})
    fake_api.add("GET", "/api/v1/roles/" + RID, 200, {"id": RID, "name": "ops"})
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _ra())
    run_module(ra_module.main, {"role": RID, "user": UID, "project": PID}, fake_api)
    assert _calls(fake_api, "POST")[0]["body"]["role_name"] == "ops"


def test_role_uuid_not_found(fake_api):
    fake_api.add("GET", "/api/v1/projects/" + PID + "/roles/" + RID, 404, {"detail": "nope"})
    fake_api.add("GET", "/api/v1/roles/" + RID, 404, {"detail": "nope"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(ra_module.main, {"role": RID, "user": UID, "project": PID}, fake_api)
    assert exc.value.kwargs["msg"] == "role '{0}' not found".format(RID)


def test_api_error_on_create_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 422, {"detail": "bad role"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(ra_module.main, {"role": "ops", "user": UID}, fake_api)
    assert exc.value.kwargs["msg"].startswith("Failed to create role assignment 'ops' for user '{0}'".format(UID))
    assert exc.value.kwargs["status"] == 422


def test_multiple_matches_fail(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra(id="a"), _ra(id="b")))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID}, fake_api)
    assert exc.value.kwargs["msg"].startswith("Found 2 role assignments")


def test_diff_on_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", LIST, 201, _ra())
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID, "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {}, "after": {"role_name": "ops", "principal_id": UID, "project_id": PID}}


def test_info_filters_passed_as_query(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra()))
    result = run_module(
        info_module.main,
        {"role": "ops", "user": UID, "project": PID, "scope": "project", "principal_type": "user"},
        fake_api,
    )
    assert result["changed"] is False
    assert result["resources"][0]["id"] == "ra1"
    query = fake_api.calls[0]["query"]
    assert query["role_name"] == "ops"
    assert query["principal_id"] == UID
    assert query["project_id"] == PID
    assert query["scope"] == "project"
    assert query["principal_type"] == "user"


def test_info_group_filter(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    run_module(info_module.main, {"group": GID}, fake_api)
    assert fake_api.calls[0]["query"]["group_id"] == GID


def test_lookup_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 403, {"detail": "forbidden"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(ra_module.main, {"role": "ops", "user": UID}, fake_api)
    assert exc.value.kwargs["status"] == 403
    assert exc.value.kwargs["msg"].startswith("Failed to look up role assignments")


def test_info_lookup_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", LIST, 500, {"detail": "boom"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(info_module.main, {}, fake_api)
    assert exc.value.kwargs["status"] == 500


def test_absent_delete_404_is_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list(_ra()))
    fake_api.add("DELETE", LIST + "/ra1", 404, {"detail": "gone"})
    result = run_module(ra_module.main, {"role": "ops", "user": UID, "project": PID, "state": "absent", "_ansible_diff": True}, fake_api)
    assert result["changed"] is False
    assert result["diff"] == {"before": {}, "after": {}}
