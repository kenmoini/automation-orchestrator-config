# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import service_account_credential as cred_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

SAID = "55555555-5555-4555-8555-555555555555"
PID = "33333333-3333-4333-8333-333333333333"
CREDS = "/api/v1/service_accounts/" + SAID + "/credentials"
ITEM = CREDS + "/c1"
BASE = {"service_account": SAID}


def _cred(**kw):
    obj = {"id": "c1", "service_account_id": SAID, "credential_type": "client_credentials", "identifier": "cid-1", "status": "active"}
    obj.update(kw)
    return obj


def _creds(*objs):
    return {"resources": list(objs), "max_credentials": 2, "total_credentials": len(objs), "max_lifetime_days": 365}


def _calls(api, method):
    return [c for c in api.calls if c["method"] == method]


def _writes(api):
    return [c for c in api.calls if c["method"] != "GET"]


def test_credential_present_creates_when_none_active(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred(status="disabled")))
    fake_api.add("POST", CREDS, 201, dict(_cred(id="c2", identifier="cid-2"), client_secret="s3cret"))
    result = run_module(cred_module.main, BASE, fake_api)
    assert result["changed"] is True
    assert result["client_id"] == "cid-2"
    assert result["client_secret"] == "s3cret"
    assert result["id"] == "c2"
    assert "client_secret" not in str(result["service_account_credential"])
    assert _calls(fake_api, "POST")[0]["body"] == {"credential_type": "client_credentials"}


def test_credential_create_with_options(fake_api):
    fake_api.add("GET", CREDS, 200, _creds())
    fake_api.add("POST", CREDS, 201, dict(_cred(), client_secret="s"))
    run_module(cred_module.main, dict(BASE, grace_period_seconds=60, expires_at="2027-01-01T00:00:00+00:00"), fake_api)
    assert _calls(fake_api, "POST")[0]["body"] == {
        "credential_type": "client_credentials",
        "grace_period_seconds": 60,
        "expires_at": "2027-01-01T00:00:00+00:00",
    }


def test_credential_present_noop_when_active_exists(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    result = run_module(cred_module.main, BASE, fake_api)
    assert result["changed"] is False
    assert "client_secret" not in result
    assert result["service_account_credential"]["identifier"] == "cid-1"
    assert _writes(fake_api) == []


def test_credential_present_with_identifier_exists(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred(status="disabled")))
    result = run_module(cred_module.main, dict(BASE, identifier="cid-1"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_credential_present_with_identifier_missing_fails(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, dict(BASE, identifier="nope"), fake_api)
    assert exc.value.kwargs["msg"] == "service account credential 'nope' not found"


def test_credential_rotated_requires_identifier_and_returns_secret(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, dict(BASE, state="rotated"), fake_api)
    assert "identifier" in exc.value.kwargs["msg"]
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    fake_api.add("POST", ITEM + "/rotate", 200, dict(_cred(), client_secret="new-s"))
    result = run_module(cred_module.main, dict(BASE, state="rotated", identifier="cid-1", grace_period_seconds=30), fake_api)
    assert result["changed"] is True
    assert result["client_secret"] == "new-s"
    assert result["client_id"] == "cid-1"
    assert _calls(fake_api, "POST")[0]["body"] == {"grace_period_seconds": 30}


def test_credential_rotated_missing_fails(fake_api):
    fake_api.add("GET", CREDS, 200, _creds())
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, dict(BASE, state="rotated", identifier="cid-1"), fake_api)
    assert exc.value.kwargs["msg"] == "service account credential 'cid-1' not found"


def test_credential_rotated_check_mode_no_post(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    result = run_module(cred_module.main, dict(BASE, state="rotated", identifier="cid-1", _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert "client_secret" not in result
    assert _writes(fake_api) == []


def test_credential_enabled_toggles_only_when_disabled(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred(status="disabled")))
    fake_api.add("POST", ITEM + "/enable", 200, _cred())
    result = run_module(cred_module.main, dict(BASE, state="enabled", identifier="cid-1"), fake_api)
    assert result["changed"] is True
    assert [c["path"] for c in _writes(fake_api)] == [ITEM + "/enable"]


def test_credential_enabled_noop_when_active(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    result = run_module(cred_module.main, dict(BASE, state="enabled", identifier="cid-1"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_credential_disabled_toggles(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    fake_api.add("POST", ITEM + "/disable", 200, _cred(status="disabled"))
    result = run_module(cred_module.main, dict(BASE, state="disabled", identifier="cid-1"), fake_api)
    assert result["changed"] is True
    assert result["service_account_credential"]["status"] == "disabled"


def test_credential_enabled_requires_identifier(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, dict(BASE, state="enabled"), fake_api)
    assert "identifier" in exc.value.kwargs["msg"]


def test_credential_absent_requires_identifier(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, dict(BASE, state="absent"), fake_api)
    assert "identifier" in exc.value.kwargs["msg"]
    assert fake_api.calls == []


def test_credential_absent_deletes_and_404_noop(fake_api):
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    fake_api.add("DELETE", ITEM, 204)
    result = run_module(cred_module.main, dict(BASE, state="absent", identifier="cid-1"), fake_api)
    assert result["changed"] is True
    assert result["service_account_credential"] is None

    fake_api.calls[:] = []
    fake_api.routes[:] = []
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    fake_api.add("DELETE", ITEM, 404, {"detail": "gone"})
    result = run_module(cred_module.main, dict(BASE, state="absent", identifier="cid-1"), fake_api)
    assert result["changed"] is False


def test_credential_absent_missing_noop(fake_api):
    fake_api.add("GET", CREDS, 200, _creds())
    result = run_module(cred_module.main, dict(BASE, state="absent", identifier="cid-1"), fake_api)
    assert result["changed"] is False
    assert _writes(fake_api) == []


def test_credential_check_mode_create_no_post_no_secret(fake_api):
    fake_api.add("GET", CREDS, 200, _creds())
    result = run_module(cred_module.main, dict(BASE, _ansible_check_mode=True), fake_api)
    assert result["changed"] is True
    assert "client_secret" not in result
    assert _writes(fake_api) == []


def test_credential_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", CREDS, 200, _creds())
    fake_api.add("POST", CREDS, 422, {"detail": "limit reached"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, BASE, fake_api)
    assert exc.value.kwargs["msg"].startswith("Failed to create credential for service account '{0}'".format(SAID))
    assert exc.value.kwargs["status"] == 422


def test_credential_list_error_reports_fail_api(fake_api):
    fake_api.add("GET", CREDS, 403, {"detail": "forbidden"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, BASE, fake_api)
    assert exc.value.kwargs["status"] == 403
    assert exc.value.kwargs["msg"].startswith("Failed to list credential for service account")


def test_service_account_name_requires_project(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(cred_module.main, {"service_account": "ci"}, fake_api)
    assert exc.value.kwargs["msg"] == "project is required when service_account is a name"
    assert fake_api.calls == []


def test_service_account_name_resolved_with_project(fake_api):
    fake_api.add("GET", "/api/v1/service_accounts", 200, {"resources": [{"id": SAID, "name": "ci", "project_id": PID}], "next": None}, query={"name": "ci"})
    fake_api.add("GET", CREDS, 200, _creds(_cred()))
    result = run_module(cred_module.main, {"service_account": "ci", "project": PID}, fake_api)
    assert result["changed"] is False
