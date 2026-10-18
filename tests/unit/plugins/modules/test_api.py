# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import api as api_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module


def test_api_get_passes_query_and_returns_json(fake_api):
    fake_api.add("GET", "/api/v1/projects", 200, {"resources": [{"id": "p1"}]}, query={"name": "demo"})
    result = run_module(api_module.main, {"endpoint": "/projects", "query_params": {"name": "demo"}}, fake_api)
    assert result["changed"] is False
    assert result["status"] == 200
    assert result["json"] == {"resources": [{"id": "p1"}]}
    assert fake_api.calls[0]["query"] == {"name": "demo"}


def test_api_post_changed_true_and_check_mode_skips(fake_api):
    fake_api.add("POST", "/api/v1/projects", 201, {"id": "p2"})
    result = run_module(api_module.main, {"endpoint": "/projects", "method": "POST", "data": {"name": "new"}}, fake_api)
    assert result["changed"] is True
    assert result["json"] == {"id": "p2"}
    assert fake_api.calls[0]["body"] == {"name": "new"}

    fake_api.calls[:] = []
    result = run_module(api_module.main, {"endpoint": "/projects", "method": "POST", "data": {"name": "new"}, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert result["json"] is None
    assert result["status"] is None
    assert fake_api.calls == []


def test_api_return_all_pages_collects_resources(fake_api):
    fake_api.add("GET", "/api/v1/users", 200, {"resources": [{"id": "u2"}], "next": None}, query={"cursor": "c2"})
    fake_api.add("GET", "/api/v1/users", 200, {"resources": [{"id": "u1"}], "next": "c2"})
    result = run_module(api_module.main, {"endpoint": "/api/v1/users", "return_all_pages": True}, fake_api)
    assert result["changed"] is False
    assert result["json"] == {"resources": [{"id": "u1"}, {"id": "u2"}]}


def test_api_returns_http_status(fake_api):
    fake_api.add("DELETE", "/api/v1/projects/p1", 204)
    result = run_module(api_module.main, {"endpoint": "/projects/p1", "method": "DELETE"}, fake_api)
    assert result["status"] == 204
    assert result["json"] is None
    assert result["changed"] is True


def test_api_expect_allows_other_status(fake_api):
    fake_api.add("GET", "/api/v1/things", 404, {"detail": "nope"})
    result = run_module(api_module.main, {"endpoint": "/things", "expect": [404]}, fake_api)
    assert result["status"] == 404


def test_api_unexpected_status_fails_via_fail_api(fake_api):
    fake_api.add("GET", "/api/v1/things", 404, {"title": "Not Found", "detail": "no such thing", "code": "not_found"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(api_module.main, {"endpoint": "/things"}, fake_api)
    kwargs = exc.value.args[0]
    assert kwargs["status"] == 404
    assert kwargs["msg"].startswith("API request failed")
