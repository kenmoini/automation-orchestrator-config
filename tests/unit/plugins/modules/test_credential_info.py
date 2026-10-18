# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import credential_info as module_under_test
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import run_module

PID = "11111111-1111-4111-8111-111111111111"
TID = "22222222-2222-4222-8222-222222222222"
LIST = "/api/v1/projects/" + PID + "/credentials"


def _cred(name, **kw):
    obj = {"id": "c-" + name, "name": name, "credential_type_id": TID, "inputs": {"password": "$encrypted$"}, "enabled": True, "project_id": PID}
    obj.update(kw)
    return obj


def test_info_name_exact_and_inputs_stripped(fake_api):
    fake_api.add("GET", LIST, 200, {"resources": [_cred("a"), _cred("ab")], "next": None})
    result = run_module(module_under_test.main, {"project": PID, "name": "a"}, fake_api)
    assert [r["name"] for r in result["resources"]] == ["a"]
    assert result["resources"][0]["inputs"] == "$encrypted$"


def test_info_filters_passed_as_query(fake_api):
    fake_api.add("GET", "/api/v1/credential_types", 200, {"resources": [{"id": TID, "name": "ssh"}], "next": None})
    fake_api.add("GET", LIST, 200, {"resources": [_cred("a")], "next": None})
    result = run_module(module_under_test.main, {"project": PID, "credential_type": "ssh", "enabled": True}, fake_api)
    assert len(result["resources"]) == 1
    call = [c for c in fake_api.calls if c["path"] == LIST][0]
    assert call["query"]["credential_type_id"] == TID
    assert call["query"]["enabled"] == "true"
