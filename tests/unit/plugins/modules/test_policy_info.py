# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import policy_info as info_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

LIST = "/api/v1/policies"
PID = "11111111-1111-4111-8111-111111111111"


def _page(*objs):
    return {"resources": list(objs), "next": None}


def test_info_lists_all(fake_api):
    fake_api.add("GET", LIST, 200, _page({"id": "p1", "name": "a"}, {"id": "p2", "name": "b"}))
    result = run_module(info_module.main, {}, fake_api)
    assert result["changed"] is False
    assert [r["id"] for r in result["resources"]] == ["p1", "p2"]


def test_info_name_exact_match_only(fake_api):
    fake_api.add("GET", LIST, 200, _page({"id": "p1", "name": "demo"}, {"id": "p2", "name": "demo2"}), query={"name": "demo"})
    result = run_module(info_module.main, {"name": "demo"}, fake_api)
    assert [r["id"] for r in result["resources"]] == ["p1"]


def test_info_filters_passed_as_query(fake_api):
    fake_api.add("GET", LIST, 200, _page())
    run_module(info_module.main, {"project": PID, "is_builtin": False, "scope": "project"}, fake_api)
    query = fake_api.calls[0]["query"]
    assert query["project_id"] == PID
    assert query["is_builtin"] == "false"
    assert query["scope"] == "project"


def test_info_scope_any_passed_through(fake_api):
    fake_api.add("GET", LIST, 200, _page())
    run_module(info_module.main, {"scope": "any"}, fake_api)
    assert fake_api.calls[0]["query"]["scope"] == "any"
