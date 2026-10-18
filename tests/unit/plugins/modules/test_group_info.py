# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import group_info as info_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

LIST = "/api/v1/groups"


def test_info_lists_all(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [{"id": "g1", "name": "a"}, {"id": "g2", "name": "b"}], "next": None})
    result = run_module(info_module.main, {}, fake_api)
    assert result["changed"] is False
    assert [r["id"] for r in result["resources"]] == ["g1", "g2"]


def test_info_name_exact_match_only(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [{"id": "g1", "name": "ops"}, {"id": "g2", "name": "ops2"}], "next": None})
    result = run_module(info_module.main, {"name": "ops"}, fake_api)
    assert [r["id"] for r in result["resources"]] == ["g1"]


def test_info_name_no_match_is_empty(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [{"id": "g1", "name": "ops"}], "next": None})
    assert run_module(info_module.main, {"name": "nope"}, fake_api)["resources"] == []
