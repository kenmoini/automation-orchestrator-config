# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import copy

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    SECRET_PLACEHOLDER,
    strip_secrets,
)
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import (
    AnsibleExitJson,
    AnsibleFailJson,
    make_module,
)

PID = "11111111-1111-4111-8111-111111111111"
PID2 = "44444444-4444-4444-8444-444444444444"
OID = "22222222-2222-4222-8222-222222222222"
WID = "33333333-3333-4333-8333-333333333333"


def check_module(fake_api, diff=False):
    return make_module(fake_api, supports_check_mode=True, _ansible_check_mode=True, _ansible_diff=diff)


def methods(fake_api):
    return [(c["method"], c["path"]) for c in fake_api.calls]


# ------------------------------------------------------------ build_desired


def test_build_desired_drops_none(fake_api):
    module = make_module(fake_api)

    desired = module.build_desired({"name": "p", "description": None, "labels": {}, "enabled": False, "tags": []})

    assert desired == {"name": "p", "labels": {}, "enabled": False, "tags": []}


# ------------------------------------------------------------ compute_patch


def test_compute_patch_only_changed_keys(fake_api):
    module = make_module(fake_api)
    existing = {"id": OID, "name": "p", "description": "old", "labels": {"a": "1", "b": "2"}, "enabled": True}
    desired = {"name": "p", "description": "new", "labels": {"b": "2", "a": "1"}, "enabled": True}

    assert module.compute_patch(existing, desired) == {"description": "new"}
    assert module.compute_patch(existing, {"labels": {"a": "1"}}) == {"labels": {"a": "1"}}
    # explicit None means "set to null" and is only sent when the existing value is not null
    assert module.compute_patch(existing, {"description": None}) == {"description": None}
    assert module.compute_patch({"description": None}, {"description": None}) == {}
    assert module.compute_patch(existing, {"new_key": "x"}) == {"new_key": "x"}


def test_compute_patch_list_order_insensitive_for_scalars(fake_api):
    module = make_module(fake_api)
    existing = {"actions": ["read", "write"], "rules": [{"a": 1}, {"b": 2}], "nested": {"x": ["b", "a"], "y": {"z": 1}}}
    existing_copy = copy.deepcopy(existing)

    assert module.compute_patch(existing, {"actions": ["write", "read"]}) == {}
    assert module.compute_patch(existing, {"actions": ["write"]}) == {"actions": ["write"]}
    assert module.compute_patch(existing, {"nested": {"y": {"z": 1}, "x": ["a", "b"]}}) == {}
    # lists of dicts are order-sensitive
    assert module.compute_patch(existing, {"rules": [{"b": 2}, {"a": 1}]}) == {"rules": [{"b": 2}, {"a": 1}]}
    assert module.compute_patch(existing, {"rules": [{"a": 1}, {"b": 2}]}) == {}
    # inputs are never mutated
    assert existing == existing_copy


def test_compute_patch_full_fields_sends_merged_dict(fake_api):
    module = make_module(fake_api)
    existing = {"configuration": {"issuer": "https://idp", "client_id": "abc", "client_secret": SECRET_PLACEHOLDER, "scopes": ["openid"]}}

    unchanged = module.compute_patch(existing, {"configuration": {"client_id": "abc"}}, full_fields=("configuration",))
    changed = module.compute_patch(existing, {"configuration": {"client_id": "xyz"}}, full_fields=("configuration",))

    assert unchanged == {}
    assert changed == {"configuration": {"issuer": "https://idp", "client_id": "xyz", "client_secret": SECRET_PLACEHOLDER, "scopes": ["openid"]}}
    # missing existing dict -> the desired dict is sent as-is
    assert module.compute_patch({}, {"configuration": {"client_id": "abc"}}, full_fields=("configuration",)) == {"configuration": {"client_id": "abc"}}


def test_compute_patch_secrets_included_only_when_update_secrets(fake_api):
    module = make_module(fake_api)
    existing = {"name": "c", "inputs": SECRET_PLACEHOLDER, "configuration": {"client_id": "abc", "client_secret": SECRET_PLACEHOLDER}}
    desired = {"name": "c", "inputs": {"password": "s3cret"}}
    nested = {"configuration": {"client_id": "abc", "client_secret": "s3cret"}}
    kwargs = dict(full_fields=("configuration",), secret_fields=("inputs", "client_secret"))

    assert module.compute_patch(existing, desired, update_secrets=True, **kwargs) == {"inputs": {"password": "s3cret"}}
    assert module.compute_patch(existing, desired, update_secrets=False, **kwargs) == {}
    assert module.compute_patch(existing, nested, update_secrets=True, **kwargs) == {"configuration": {"client_id": "abc", "client_secret": "s3cret"}}
    assert module.compute_patch(existing, nested, update_secrets=False, **kwargs) == {}


def _idp_patch(fake_api, update_secrets):
    existing = {"id": OID, "name": "idp", "configuration": {"issuer_url": "https://old", "client_id": "abc", "client_secret": SECRET_PLACEHOLDER}}
    desired = {"configuration": {"issuer_url": "https://new", "client_secret": "new"}}
    fake_api.add("PATCH", "/api/v1/identity_providers/{0}".format(OID), 200, existing)
    module = make_module(fake_api)
    changed, dummy = module.create_or_update(
        existing, desired, "/identity_providers", full_fields=("configuration",), secret_fields=("client_secret",), update_secrets=update_secrets
    )
    return changed, fake_api.calls[-1]["body"]


def test_full_field_drops_server_secret_when_update_secrets_false(fake_api):
    changed, body = _idp_patch(fake_api, update_secrets=False)

    assert changed is True
    assert body == {"configuration": {"issuer_url": "https://new", "client_id": "abc"}}
    assert "client_secret" not in body["configuration"]


def test_full_field_sends_secret_when_update_secrets_true(fake_api):
    changed, body = _idp_patch(fake_api, update_secrets=True)

    assert changed is True
    assert body == {"configuration": {"issuer_url": "https://new", "client_id": "abc", "client_secret": "new"}}


def test_full_field_missing_existing_drops_secret_when_update_secrets_false(fake_api):
    module = make_module(fake_api)
    desired = {"configuration": {"client_id": "a", "client_secret": "s"}}
    kwargs = dict(full_fields=("configuration",), secret_fields=("client_secret",))

    for existing in ({"id": OID}, {"id": OID, "configuration": None}, {"id": OID, "configuration": "junk"}):
        assert module.compute_patch(existing, desired, update_secrets=False, **kwargs) == {"configuration": {"client_id": "a"}}
        assert module.compute_patch(existing, desired, update_secrets=True, **kwargs) == {"configuration": {"client_id": "a", "client_secret": "s"}}
    # only a secret supplied and not updating secrets -> nothing to send
    assert module.compute_patch({"id": OID}, {"configuration": {"client_secret": "s"}}, update_secrets=False, **kwargs) == {}


# ------------------------------------------------------------ create_or_update


def test_create_posts_when_missing_and_check_mode_does_not(fake_api):
    created = {"id": OID, "name": "p", "labels": {}}
    fake_api.add("POST", "/api/v1/projects", 201, created)
    desired = {"name": "p", "labels": {}}

    module = make_module(fake_api)
    assert module.create_or_update(None, desired, "/projects") == (True, created)
    assert methods(fake_api) == [("POST", "/api/v1/projects")]
    assert fake_api.calls[-1]["body"] == desired

    fake_api.calls[:] = []
    module = check_module(fake_api, diff=True)
    assert module.create_or_update(None, desired, "/projects") == (True, desired)
    assert fake_api.calls == []
    assert module._diff == {"before": {}, "after": desired}

    # create_path overrides the POST target
    fake_api.add("POST", "/api/v1/projects/{0}/workflows".format(PID), 201, {"id": WID, "name": "w"})
    module = make_module(fake_api)
    changed, obj = module.create_or_update(None, {"name": "w"}, "/workflows", create_path="/projects/{0}/workflows".format(PID))
    assert changed and obj["id"] == WID


def test_update_patches_only_when_changed(fake_api):
    existing = {"id": OID, "name": "p", "description": "old", "labels": {"a": "1"}}
    patched = dict(existing, description="new")
    fake_api.add("PATCH", "/api/v1/projects/{0}".format(OID), 200, patched)

    module = make_module(fake_api, _ansible_diff=True)
    assert module.create_or_update(existing, {"name": "p", "labels": {"a": "1"}}, "/projects") == (False, existing)
    assert fake_api.calls == []

    assert module.create_or_update(existing, {"name": "p", "description": "new"}, "/projects") == (True, patched)
    assert methods(fake_api) == [("PATCH", "/api/v1/projects/{0}".format(OID))]
    assert fake_api.calls[-1]["body"] == {"description": "new"}
    assert module._diff == {"before": {"description": "old"}, "after": {"description": "new"}}

    fake_api.calls[:] = []
    module = check_module(fake_api)
    assert module.create_or_update(existing, {"description": "new"}, "/projects") == (True, patched)
    assert fake_api.calls == []


def test_immutable_change_fails(fake_api):
    existing = {"id": WID, "name": "w", "project_id": PID}
    path = "/projects/{0}/workflows".format(PID)
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.create_or_update(existing, {"name": "w", "project_id": PID2}, path, immutable=("project_id",))
    assert exc.value.kwargs["msg"] == "project_id cannot be changed on an existing workflow"
    assert fake_api.calls == []

    # unchanged immutable key is fine
    assert module.create_or_update(existing, {"name": "w", "project_id": PID}, path, immutable=("project_id",)) == (False, existing)


def test_create_or_update_api_error_fails(fake_api):
    fake_api.add("POST", "/api/v1/projects", 409, {"title": "Conflict", "detail": "name taken", "code": "conflict"})
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.create_or_update(None, {"name": "p"}, "/projects")
    assert exc.value.kwargs["msg"] == "Failed to create project: name taken"
    assert exc.value.kwargs["status"] == 409


# ------------------------------------------------------------ delete_if_needed


def test_delete_builtin_fails_with_name(fake_api):
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.delete_if_needed({"id": OID, "name": "Admin", "is_builtin": True}, "/roles")
    assert exc.value.kwargs["msg"] == "Cannot delete built-in role 'Admin'"

    with pytest.raises(AnsibleFailJson) as exc:
        check_module(fake_api).delete_if_needed({"id": OID, "name": "Viewer", "is_builtin": True}, "/policies", item_label="policy")
    assert exc.value.kwargs["msg"] == "Cannot delete built-in policy 'Viewer'"
    assert fake_api.calls == []


def test_delete_skipped_in_check_mode_but_reports_changed(fake_api):
    existing = {"id": OID, "name": "p"}
    fake_api.add("DELETE", "/api/v1/projects/{0}".format(OID), 204)

    module = check_module(fake_api, diff=True)
    assert module.delete_if_needed(None, "/projects") is False
    assert module.delete_if_needed(existing, "/projects") is True
    assert fake_api.calls == []
    assert module._diff == {"before": existing, "after": {}}

    module = make_module(fake_api)
    assert module.delete_if_needed(existing, "/projects") is True
    assert methods(fake_api) == [("DELETE", "/api/v1/projects/{0}".format(OID))]


def test_update_and_delete_api_errors(fake_api):
    existing = {"id": OID, "name": "p", "description": "old"}
    fake_api.add("PATCH", "/api/v1/projects/{0}".format(OID), 422, {"detail": "bad description"})
    fake_api.add("DELETE", "/api/v1/projects/{0}".format(OID), 404, {"detail": "gone"}, times=1)
    fake_api.add("DELETE", "/api/v1/projects/{0}".format(OID), 409, {"detail": "in use"})
    module = make_module(fake_api)

    with pytest.raises(AnsibleFailJson) as exc:
        module.create_or_update(existing, {"description": "new"}, "/projects")
    assert exc.value.kwargs["msg"] == "Failed to update project 'p': bad description"

    # already gone -> nothing changed, and no deletion recorded in the diff
    assert module.delete_if_needed(existing, "/projects") is False
    assert module._diff == {"before": {}, "after": {}}
    with pytest.raises(AnsibleFailJson) as exc:
        module.delete_if_needed(existing, "/projects")
    assert exc.value.kwargs["msg"] == "Failed to delete project 'p': in use"


# ------------------------------------------------------------ exit_result / strip_secrets


def test_exit_result_strips_secrets_and_sets_id(fake_api):
    obj = {"id": OID, "name": "c", "inputs": {"password": "s3cret"}, "configuration": {"client_secret": "s3cret", "client_id": "abc"}}
    original = copy.deepcopy(obj)

    module = make_module(fake_api)
    module.result_key = "credential"
    with pytest.raises(AnsibleExitJson) as exc:
        module.exit_result(True, obj, client_secret="one-time")
    result = exc.value.kwargs
    assert result["changed"] is True
    assert result["id"] == OID
    masked_configuration = {"client_secret": SECRET_PLACEHOLDER, "client_id": "abc"}
    assert result["credential"] == {"id": OID, "name": "c", "inputs": SECRET_PLACEHOLDER, "configuration": masked_configuration}
    assert result["client_secret"] == "one-time"
    assert "diff" not in result
    assert obj == original
    assert "s3cret" not in repr(result)

    module = make_module(fake_api)
    with pytest.raises(AnsibleExitJson) as exc:
        module.exit_result(False)
    assert exc.value.kwargs["id"] is None
    assert exc.value.kwargs["object"] is None


def test_exit_result_includes_diff_only_in_diff_mode(fake_api):
    existing = {"id": OID, "name": "c", "password": "old"}
    fake_api.add("PATCH", "/api/v1/users/{0}".format(OID), 200, existing)
    module = make_module(fake_api, _ansible_diff=True)

    changed, obj = module.create_or_update(existing, {"password": "s3cret"}, "/users", secret_fields=("password",))
    with pytest.raises(AnsibleExitJson) as exc:
        module.exit_result(changed, obj)
    assert exc.value.kwargs["diff"] == {"before": {"password": SECRET_PLACEHOLDER}, "after": {"password": SECRET_PLACEHOLDER}}
    assert "s3cret" not in repr(exc.value.kwargs)


def test_strip_secrets_returns_copy():
    obj = {"password": "x", "nested": {"password": "kept"}, "configuration": {"password": "y"}}
    assert strip_secrets(obj) == {"password": SECRET_PLACEHOLDER, "nested": {"password": "kept"}, "configuration": {"password": SECRET_PLACEHOLDER}}
    assert obj["password"] == "x"
    assert strip_secrets(None) is None
    assert strip_secrets({"token": "t"}, secret_fields=("token",)) == {"token": SECRET_PLACEHOLDER}
