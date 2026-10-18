# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import credential_type_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

LIST = "/api/v1/credential_types"
SCHEMA = {"fields": [{"id": "password", "label": "Password", "secret": True}]}


def _type(name, **kw):
    obj = {"id": "t-" + name, "name": name, "inputs": SCHEMA, "injectors": {"env": {"X": "{{ password }}"}}, "managed": True}
    obj.update(kw)
    return obj


def test_type_info_name_exact_match_returns_schema_inputs(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_type("ssh"), _type("ssh-key"), _type("git")], "next": None})
    result = run_module(module_under_test.main, {"name": "ssh"}, fake_api)
    assert result["changed"] is False
    assert [r["name"] for r in result["resources"]] == ["ssh"]
    assert result["resources"][0]["inputs"] == SCHEMA
    assert result["resources"][0]["injectors"] == {"env": {"X": "{{ password }}"}}


def test_type_info_lists_all(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_type("ssh"), _type("git")], "next": None})
    result = run_module(module_under_test.main, {}, fake_api)
    assert len(result["resources"]) == 2
