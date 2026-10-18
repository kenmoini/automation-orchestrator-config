# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import credential as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

PID = "11111111-1111-4111-8111-111111111111"
TID = "22222222-2222-4222-8222-222222222222"
TID2 = "33333333-3333-4333-8333-333333333333"
LIST = "/api/v1/projects/" + PID + "/credentials"
CREDS = "/api/v1/credentials"


def _cred(**kw):
    obj = {
        "id": "c1",
        "name": "ssh-prod",
        "description": "old",
        "credential_type_id": TID,
        "inputs": {"password": "$encrypted$"},
        "enabled": True,
        "project_id": PID,
        "labels": {"a": "1"},
    }
    obj.update(kw)
    return obj


def _list(*objs):
    return {"resources": list(objs), "next": None}


def _posts(api):
    return [c for c in api.calls if c["method"] == "POST"]


def _patches(api):
    return [c for c in api.calls if c["method"] == "PATCH"]


def _deletes(api):
    return [c for c in api.calls if c["method"] == "DELETE"]


BASE = {"name": "ssh-prod", "project": PID}


def test_create(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", CREDS, 201, _cred())
    params = dict(BASE, description="d", credential_type=TID, inputs={"password": "s3"}, enabled=True, labels={"a": "1"})
    result = run_module(module_under_test.main, params, fake_api)
    assert result["changed"] is True
    assert result["id"] == "c1"
    assert _posts(fake_api)[0]["body"] == {
        "name": "ssh-prod",
        "description": "d",
        "credential_type_id": TID,
        "project_id": PID,
        "inputs": {"password": "s3"},
        "enabled": True,
        "labels": {"a": "1"},
    }


def test_create_resolves_names(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, _list({"id": PID, "name": "p"}))
    fake_api.add("GET", "/api/v1/credential_types", 200, _list({"id": TID, "name": "ssh"}))
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", CREDS, 201, _cred())
    run_module(module_under_test.main, {"name": "ssh-prod", "project": "p", "credential_type": "ssh"}, fake_api)
    assert _posts(fake_api)[0]["body"] == {"name": "ssh-prod", "credential_type_id": TID, "project_id": PID}


def test_inputs_sent_on_create_and_not_logged(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    fake_api.add("POST", CREDS, 201, _cred())
    result = run_module(module_under_test.main, dict(BASE, credential_type=TID, inputs={"password": "s3cret"}, _ansible_diff=True), fake_api)
    assert _posts(fake_api)[0]["body"]["inputs"] == {"password": "s3cret"}
    assert result["credential"]["inputs"] == "$encrypted$"
    assert "s3cret" not in repr(result)
    assert result["diff"]["after"]["inputs"] == "$encrypted$"


def test_create_requires_credential_type(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE), fake_api)
    assert exc.value.kwargs["msg"] == "credential_type is required to create credential 'ssh-prod'"
    assert _posts(fake_api) == []


def test_update_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    fake_api.add("PATCH", CREDS + "/c1", 200, _cred(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new"), fake_api)
    assert result["changed"] is True
    assert _patches(fake_api)[0]["body"] == {"description": "new"}


def test_update_diff_mode(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    fake_api.add("PATCH", CREDS + "/c1", 200, _cred(description="new"))
    result = run_module(module_under_test.main, dict(BASE, description="new", _ansible_diff=True), fake_api)
    assert result["diff"] == {"before": {"description": "old"}, "after": {"description": "new"}}


def test_labels_changed_patch(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    fake_api.add("PATCH", CREDS + "/c1", 200, _cred(labels={"b": "2"}))
    run_module(module_under_test.main, dict(BASE, labels={"b": "2"}), fake_api)
    assert _patches(fake_api)[0]["body"] == {"labels": {"b": "2"}}


def test_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    result = run_module(module_under_test.main, dict(BASE, description="old", credential_type=TID, enabled=True, labels={"a": "1"}), fake_api)
    assert result["changed"] is False
    assert _patches(fake_api) == []


def test_update_secrets_false_skips_inputs_and_no_change(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred(inputs={"password": "$encrypted$"})))
    result = run_module(module_under_test.main, dict(BASE, inputs={"password": "new"}, update_secrets=False, description="old"), fake_api)
    assert result["changed"] is False
    assert _patches(fake_api) == []


def test_update_secrets_true_patches_inputs_changed(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    fake_api.add("PATCH", CREDS + "/c1", 200, _cred())
    result = run_module(module_under_test.main, dict(BASE, inputs={"password": "new"}), fake_api)
    assert result["changed"] is True
    assert _patches(fake_api)[0]["body"] == {"inputs": {"password": "new"}}
    assert result["credential"]["inputs"] == "$encrypted$"


def test_credential_type_immutable_fails(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(module_under_test.main, dict(BASE, credential_type=TID2), fake_api)
    assert "credential_type_id cannot be changed" in exc.value.kwargs["msg"]
    assert _patches(fake_api) == []


def test_rename_rerun_is_idempotent(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred(name="ssh-new")))
    result = run_module(module_under_test.main, dict(BASE, new_name="ssh-new"), fake_api)
    assert result["changed"] is False
    assert _patches(fake_api) == []


def test_absent_deletes(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    fake_api.add("DELETE", CREDS + "/c1", 204)
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is True
    assert result["credential"] is None
    assert len(_deletes(fake_api)) == 1


def test_absent_missing_noop(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, state="absent"), fake_api)
    assert result["changed"] is False
    assert _deletes(fake_api) == []


def test_check_mode_create_no_post(fake_api):
    fake_api.add("GET", LIST, 200, _list())
    result = run_module(module_under_test.main, dict(BASE, credential_type=TID, inputs={"password": "x"}, _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert _posts(fake_api) == []
    assert result["credential"]["inputs"] == "$encrypted$"


def test_exists_does_not_modify(fake_api):
    fake_api.add("GET", LIST, 200, _list(_cred()))
    result = run_module(module_under_test.main, dict(BASE, state="exists", description="zzz"), fake_api)
    assert result["changed"] is False
    assert _patches(fake_api) == []
