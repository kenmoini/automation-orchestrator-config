# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import user_info as info_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

LIST = "/api/v1/users"


def test_info_lists_all(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [{"id": "u1", "username": "a"}, {"id": "u2", "username": "b"}], "next": None})
    result = run_module(info_module.main, {}, fake_api)
    assert result["changed"] is False
    assert [r["id"] for r in result["resources"]] == ["u1", "u2"]


def test_info_username_exact_match_only(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [{"id": "u1", "username": "al"}, {"id": "u2", "username": "alice"}], "next": None}, query={"username": "al"})
    result = run_module(info_module.main, {"username": "al"}, fake_api)
    assert [r["id"] for r in result["resources"]] == ["u1"]


def test_info_username_no_match_is_empty(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None}, query={"username": "nope"})
    assert run_module(info_module.main, {"username": "nope"}, fake_api)["resources"] == []


def test_info_filters_passed_as_query(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [], "next": None})
    run_module(info_module.main, {"first_name": "A", "last_name": "B", "auth_type": "federated", "auth_source": "okta"}, fake_api)
    query = fake_api.calls[0]["query"]
    assert (query["first_name"], query["last_name"], query["auth_type"], query["auth_source"]) == ("A", "B", "federated", "okta")


def test_info_strips_secrets(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [{"id": "u1", "username": "a", "password": "x"}], "next": None})
    assert run_module(info_module.main, {}, fake_api)["resources"][0]["password"] == "$encrypted$"
