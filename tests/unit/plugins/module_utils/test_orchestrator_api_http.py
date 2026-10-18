# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils import orchestrator_api
from ansible_collections.kenmoini.automation_orchestrator_config.plugins.module_utils.orchestrator_api import (
    OrchestratorAPIError,
    normalize_host,
)
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import (
    FETCH_URL_TARGET,
    AnsibleFailJson,
    make_module,
)

TOKEN_RESPONSE = {"access_token": "abc", "token_type": "Bearer", "expires_in": 3600}
VERSION = {"version": "1.3.1"}


@pytest.fixture
def no_sleep(mocker):
    return mocker.patch.object(orchestrator_api.time, "sleep")


def test_normalize_host_adds_https_and_strips_slash():
    assert normalize_host("orch.example.com/") == "https://orch.example.com"
    assert normalize_host("http://orch:8080/") == "http://orch:8080"
    assert normalize_host("https://orch.example.com") == "https://orch.example.com"
    with pytest.raises(ValueError):
        normalize_host("")


def test_auth_precedence_token_over_password(fake_api):
    fake_api.add("GET", "/api/v1/version", 200, VERSION)
    module = make_module(fake_api)
    assert module.request("GET", "/version") == VERSION
    assert [c["path"] for c in fake_api.calls] == ["/api/v1/version"]
    assert fake_api.calls[0]["headers"]["Authorization"] == "Bearer t0k"


def test_login_with_username_password_sets_bearer(fake_api):
    fake_api.add("POST", "/api/v1/auth/login", 200, TOKEN_RESPONSE)
    fake_api.add("GET", "/api/v1/version", 200, VERSION)
    module = make_module(fake_api, orchestrator_username="admin", orchestrator_password="pw")
    assert module.request("GET", "/version") == VERSION
    login, version = fake_api.calls
    assert login["method"] == "POST" and login["path"] == "/api/v1/auth/login"
    assert login["body"] == {"username": "admin", "password": "pw"}
    assert "Authorization" not in login["headers"]
    assert version["headers"]["Authorization"] == "Bearer abc"


def test_client_credentials_uses_form_encoding(fake_api):
    fake_api.add("POST", "/api/v1/auth/token", 200, TOKEN_RESPONSE)
    fake_api.add("GET", "/api/v1/version", 200, VERSION)
    module = make_module(fake_api, orchestrator_client_id="cid", orchestrator_client_secret="sec")
    module.request("GET", "/api/v1/version")
    token, version = fake_api.calls
    assert token["path"] == "/api/v1/auth/token"
    assert token["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert "grant_type=client_credentials" in token["raw"]
    assert "client_id=cid" in token["raw"] and "client_secret=sec" in token["raw"]
    assert version["headers"]["Content-Type"] == "application/json"
    assert version["headers"]["Authorization"] == "Bearer abc"


def test_401_after_auth_relogins_once_then_fails(fake_api):
    fake_api.add("GET", "/api/v1/version", 401, {"title": "Unauthorized", "detail": "token expired"}, times=1)
    fake_api.add("POST", "/api/v1/auth/login", 200, TOKEN_RESPONSE)
    fake_api.add("GET", "/api/v1/version", 200, VERSION, times=1)
    module = make_module(fake_api, orchestrator_username="admin", orchestrator_password="pw")
    module.authenticate()
    assert module.request("GET", "/version") == VERSION
    assert [c["path"] for c in fake_api.calls] == ["/api/v1/auth/login", "/api/v1/version", "/api/v1/auth/login", "/api/v1/version"]

    fake_api.routes, fake_api.calls = [], []
    fake_api.add("GET", "/api/v1/version", 401, {"title": "Unauthorized", "detail": "token expired"}, times=1)
    fake_api.add("POST", "/api/v1/auth/login", 200, TOKEN_RESPONSE)
    fake_api.add("GET", "/api/v1/version", 401, {"title": "Unauthorized", "detail": "still bad"}, times=1)
    with pytest.raises(AnsibleFailJson) as exc:
        try:
            module.request("GET", "/version")
        except OrchestratorAPIError as err:
            module.fail_api(err, "Failed to get version")
    assert exc.value.kwargs["status"] == 401
    assert exc.value.kwargs["msg"] == "Failed to get version: still bad"
    assert [c["path"] for c in fake_api.calls] == ["/api/v1/version", "/api/v1/auth/login", "/api/v1/version"]


def test_static_token_401_not_retried(fake_api):
    fake_api.add("GET", "/api/v1/version", 401, {"title": "Unauthorized", "detail": "token revoked", "code": "UNAUTHORIZED"})
    module = make_module(fake_api)
    with pytest.raises(OrchestratorAPIError) as exc:
        module.request("GET", "/version")
    assert exc.value.status == 401
    assert exc.value.detail == "token revoked"
    assert len(fake_api.calls) == 1
    assert not any(c["path"].startswith("/api/v1/auth/") for c in fake_api.calls)


def test_login_401_fails_with_problem_detail(fake_api):
    fake_api.add("POST", "/api/v1/auth/login", 401, {"title": "Unauthorized", "detail": "invalid credentials", "code": "UNAUTHORIZED"})
    module = make_module(fake_api, orchestrator_username="admin", orchestrator_password="bad")
    with pytest.raises(AnsibleFailJson) as exc:
        module.authenticate()
    assert "invalid credentials" in exc.value.kwargs["msg"]
    assert exc.value.kwargs["status"] == 401


def test_429_retries_with_retry_after(fake_api, no_sleep):
    fake_api.add("GET", "/api/v1/version", 429, {"detail": "slow down"}, headers={"Retry-After": "0"}, times=1)
    fake_api.add("GET", "/api/v1/version", 200, VERSION, times=1)
    module = make_module(fake_api)
    assert module.request("GET", "/version") == VERSION
    no_sleep.assert_called_once_with(0.0)

    no_sleep.reset_mock()
    fake_api.routes, fake_api.calls = [], []
    fake_api.add("GET", "/api/v1/version", 429, {"detail": "slow down", "code": "RATE_LIMITED"}, headers={"Retry-After": "120"})
    with pytest.raises(AnsibleFailJson) as exc:
        try:
            module.request("GET", "/version")
        except OrchestratorAPIError as err:
            module.fail_api(err)
    assert exc.value.kwargs["status"] == 429
    assert exc.value.kwargs["msg"] == "slow down"
    assert len(fake_api.calls) == 4
    assert no_sleep.call_count == 3
    assert all(call.args == (30.0,) for call in no_sleep.call_args_list)


def test_problem_details_error_mapping(fake_api):
    problem = {
        "type": "https://example.com/problems/validation",
        "title": "Validation Error",
        "detail": "name invalid",
        "code": "VALIDATION_ERROR",
        "retryable": False,
    }
    fake_api.add("POST", "/api/v1/workflows", 422, problem)
    module = make_module(fake_api)
    with pytest.raises(OrchestratorAPIError) as exc:
        module.request("POST", "/workflows", data={"name": "!"})
    err = exc.value
    assert err.status == 422
    assert err.detail == "name invalid"
    assert err.code == "VALIDATION_ERROR"
    assert err.title == "Validation Error"
    assert err.body == problem
    assert fake_api.calls[0]["body"] == {"name": "!"}

    with pytest.raises(AnsibleFailJson) as fail:
        module.fail_api(err, "Failed to create workflow")
    assert fail.value.kwargs["msg"] == "Failed to create workflow: name invalid"
    assert fail.value.kwargs["code"] == "VALIDATION_ERROR"
    assert fail.value.kwargs["body"] == problem


def test_error_without_problem_body_falls_back_to_msg(fake_api):
    fake_api.add("GET", "/api/v1/version", 500)
    module = make_module(fake_api)
    with pytest.raises(OrchestratorAPIError) as exc:
        module.request("GET", "/version")
    assert exc.value.status == 500
    assert exc.value.detail == "HTTP Error 500"
    assert exc.value.code is None


def test_connection_failure_without_response(mocker):
    mocker.patch(
        FETCH_URL_TARGET,
        return_value=(None, {"status": -1, "msg": "Request failed: <urlopen error [Errno 111] Connection refused>", "url": "x"}),
    )
    module = make_module()
    with pytest.raises(OrchestratorAPIError) as exc:
        module.request("GET", "/version")
    assert exc.value.status == -1
    assert "Connection refused" in exc.value.detail


def test_request_drops_none_query_and_returns_none_on_204(fake_api):
    fake_api.add("DELETE", "/api/v1/workflows/w1", 204, query={"force": "true"})
    module = make_module(fake_api)
    assert module.request("DELETE", "/workflows/w1", query={"force": "true", "cascade": None}) is None
    assert fake_api.calls[0]["query"] == {"force": "true"}
    assert fake_api.calls[0]["timeout"] == 10.0


def test_env_fallback_for_host_and_token(fake_api, monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_HOST", "env-orch.example.com/")
    monkeypatch.setenv("ORCHESTRATOR_TOKEN", "envtok")
    fake_api.add("GET", "/api/v1/version", 200, VERSION)
    module = make_module(fake_api, orchestrator_host=None, orchestrator_token=None)
    assert module.base_url == "https://env-orch.example.com"
    module.request("GET", "/version")
    assert fake_api.calls[0]["headers"]["Authorization"] == "Bearer envtok"
