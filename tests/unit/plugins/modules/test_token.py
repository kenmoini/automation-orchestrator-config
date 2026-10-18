# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import token as token_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module


def test_token_returns_access_token_and_expires_in(fake_api):
    fake_api.add("POST", "/api/v1/auth/login", 200, {"access_token": "abc123", "token_type": "Bearer", "expires_in": 3600})
    result = run_module(
        token_module.main,
        {"orchestrator_username": "admin", "orchestrator_password": "pw"},
        fake_api,
    )
    assert result["changed"] is True
    assert result["access_token"] == "abc123"
    assert result["token_type"] == "Bearer"
    assert result["expires_in"] == 3600
    assert fake_api.calls[0]["body"] == {"username": "admin", "password": "pw"}


def test_token_with_client_credentials(fake_api):
    fake_api.add("POST", "/api/v1/auth/token", 200, {"access_token": "cc-tok", "expires_in": 900})
    result = run_module(
        token_module.main,
        {"orchestrator_client_id": "cid", "orchestrator_client_secret": "sec"},
        fake_api,
    )
    assert result["access_token"] == "cc-tok"
    assert result["expires_in"] == 900


def test_token_fails_when_only_token_given(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(token_module.main, {"orchestrator_token": "static"}, fake_api)
    assert exc.value.args[0]["msg"] == "token module needs orchestrator_username/orchestrator_password or orchestrator_client_id/orchestrator_client_secret"
    assert fake_api.calls == []


def test_token_check_mode_still_returns_token(fake_api):
    fake_api.add("POST", "/api/v1/auth/login", 200, {"access_token": "abc123", "expires_in": 60})
    result = run_module(
        token_module.main,
        {"orchestrator_username": "admin", "orchestrator_password": "pw", "_ansible_check_mode": True},
        fake_api,
    )
    assert result["access_token"] == "abc123"
    assert result["changed"] is True
