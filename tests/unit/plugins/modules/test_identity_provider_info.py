# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import identity_provider_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

LIST = "/api/v1/identity_providers"


def _page(*names):
    return {"resources": [{"id": "id-" + n, "name": n} for n in names], "next": None}


def test_info_lists_all(fake_api):
    fake_api.add("GET", LIST, 200, _page("a", "b"))
    result = run_module(module_under_test.main, {}, fake_api)
    assert result["changed"] is False
    assert [r["name"] for r in result["resources"]] == ["a", "b"]


def test_info_name_exact_match(fake_api):
    fake_api.add("GET", LIST, 200, _page("sso", "sso2", "SSO"))
    result = run_module(module_under_test.main, {"name": "sso"}, fake_api)
    assert [r["name"] for r in result["resources"]] == ["sso"]


def test_info_name_missing_empty(fake_api):
    fake_api.add("GET", LIST, 200, _page("a"))
    result = run_module(module_under_test.main, {"name": "zzz"}, fake_api)
    assert result["resources"] == []
