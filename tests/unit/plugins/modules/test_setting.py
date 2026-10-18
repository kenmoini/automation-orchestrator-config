# -*- coding: utf-8 -*-
# Copyright (c) 2026 Ken Moini
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import setting as setting_module
from ansible_collections.kenmoini.automation_orchestrator_config.plugins.modules import setting_info as info_module
from ansible_collections.kenmoini.automation_orchestrator_config.tests.unit.plugins.utils import AnsibleFailJson, run_module

BASE = "/api/v1/settings"


def _s(key, value=None, default=10, effective=None, **kw):
    obj = {
        "id": "id-" + key,
        "key": key,
        "category": "general",
        "group": "core",
        "value": value,
        "default_value": default,
        "effective_value": (value if value is not None else default) if effective is None else effective,
        "value_type": "integer",
        "version": 3,
    }
    obj.update(kw)
    return obj


def _calls(api, method):
    return [c for c in api.calls if c["method"] == method]


def test_single_key_patch_when_differs(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    fake_api.add("PATCH", BASE + "/a.b", 200, _s("a.b", value=20))
    result = run_module(setting_module.main, {"name": "a.b", "value": 20, "expected_version": 3}, fake_api)
    assert result["changed"] is True
    assert result["settings"] == {"a.b": 20}
    assert result["changed_keys"] == ["a.b"]
    assert _calls(fake_api, "PATCH")[0]["body"] == {"value": 20, "expected_version": 3}


def test_single_key_patch_without_expected_version(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    fake_api.add("PATCH", BASE + "/a.b", 200, _s("a.b", value=20))
    run_module(setting_module.main, {"name": "a.b", "value": 20}, fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"value": 20}


def test_single_key_noop(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    result = run_module(setting_module.main, {"name": "a.b", "value": 5}, fake_api)
    assert result["changed"] is False
    assert result["settings"] == {"a.b": 5}
    assert result["changed_keys"] == []
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_bulk_patch_only_changed_keys(fake_api):
    fake_api.add("GET", BASE, 200, {"resources": [_s("z", value=1), _s("a", value=2), _s("m", value=3), _s("other", value=9)], "next": None})
    fake_api.add("PATCH", BASE, 200, {"resources": [_s("z", value=100), _s("m", value=300)], "next": None})
    result = run_module(setting_module.main, {"settings": {"z": 100, "a": 2, "m": 300}}, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"updates": [{"key": "z", "value": 100}, {"key": "m", "value": 300}]}
    assert result["changed_keys"] == ["m", "z"]
    assert result["settings"] == {"z": 100, "a": 2, "m": 300}


def test_null_value_equal_to_default_is_noop(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=None, default=10))
    result = run_module(setting_module.main, {"name": "a.b", "value": 10}, fake_api)
    assert result["changed"] is False
    assert result["settings"] == {"a.b": 10}
    assert [c["method"] for c in fake_api.calls] == ["GET"]


def test_reset_to_default_sends_null(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    fake_api.add("PATCH", BASE + "/a.b", 200, _s("a.b", value=None, default=10))
    result = run_module(setting_module.main, {"name": "a.b"}, fake_api)
    assert result["changed"] is True
    assert result["settings"] == {"a.b": 10}
    assert _calls(fake_api, "PATCH")[0]["body"] == {"value": None}


def test_reset_to_default_noop_when_unset(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=None))
    result = run_module(setting_module.main, {"name": "a.b"}, fake_api)
    assert result["changed"] is False


def test_unknown_key_fails(fake_api):
    fake_api.add("GET", BASE + "/nope", 404, {"detail": "not found"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(setting_module.main, {"name": "nope", "value": 1}, fake_api)
    assert exc.value.kwargs["msg"] == "setting 'nope' not found"


def test_unknown_key_in_bulk_fails(fake_api):
    fake_api.add("GET", BASE, 200, {"resources": [_s("a")], "next": None})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(setting_module.main, {"settings": {"a": 1, "nope": 2}}, fake_api)
    assert exc.value.kwargs["msg"] == "setting 'nope' not found"
    assert not _calls(fake_api, "PATCH")


def test_check_mode_no_write_but_changed(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    result = run_module(setting_module.main, {"name": "a.b", "value": 20, "_ansible_check_mode": True}, fake_api)
    assert result["changed"] is True
    assert result["changed_keys"] == ["a.b"]
    assert result["settings"] == {"a.b": 20}
    assert not _calls(fake_api, "PATCH")


def test_diff_mode_restricted_to_changed_keys(fake_api):
    fake_api.add("GET", BASE, 200, {"resources": [_s("a", value=1), _s("b", value=2)], "next": None})
    fake_api.add("PATCH", BASE, 200, {"resources": [_s("b", value=3)], "next": None})
    result = run_module(setting_module.main, {"settings": {"a": 1, "b": 3}, "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {"b": 2}, "after": {"b": 3}}


def test_api_error_reports_fail_api(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    fake_api.add("PATCH", BASE + "/a.b", 409, {"detail": "version mismatch"})
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(setting_module.main, {"name": "a.b", "value": 6, "expected_version": 1}, fake_api)
    assert exc.value.kwargs["msg"].startswith("Failed to update setting(s) a.b")
    assert exc.value.kwargs["status"] == 409


def test_expected_version_requires_name(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(setting_module.main, {"settings": {"a": 1}, "expected_version": 1}, fake_api)
    assert "expected_version" in exc.value.kwargs["msg"]


def test_info_single_key(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    result = run_module(info_module.main, {"name": "a.b"}, fake_api)
    assert [r["key"] for r in result["resources"]] == ["a.b"]


def test_info_single_key_missing_is_empty(fake_api):
    fake_api.add("GET", BASE + "/nope", 404, {"detail": "nope"})
    assert run_module(info_module.main, {"name": "nope"}, fake_api)["resources"] == []


def test_info_filters_passed_as_query(fake_api):
    fake_api.add("GET", BASE, 200, {"resources": [_s("a")], "next": None})
    result = run_module(info_module.main, {"category": "general", "group": "core"}, fake_api)
    assert len(result["resources"]) == 1
    query = fake_api.calls[0]["query"]
    assert query["category"] == "general" and query["group"] == "core"


def test_info_categories(fake_api):
    cats = [{"slug": "general", "name": "General", "description": "", "display_order": 1, "group_names": ["core"]}]
    fake_api.add("GET", BASE + "/categories", 200, {"resources": cats})
    result = run_module(info_module.main, {"categories": True}, fake_api)
    assert result["resources"] == cats


def test_bool_vs_int_is_a_change(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=1, value_type="json"))
    fake_api.add("PATCH", BASE + "/a.b", 200, _s("a.b", value=True, value_type="json"))
    result = run_module(setting_module.main, {"name": "a.b", "value": True}, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"value": True}


def test_string_number_coerced_for_integer_setting(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=10))
    assert run_module(setting_module.main, {"name": "a.b", "value": "10"}, fake_api)["changed"] is False
    assert not _calls(fake_api, "PATCH")
    fake_api.add("PATCH", BASE + "/a.b", 200, _s("a.b", value=11))
    result = run_module(setting_module.main, {"name": "a.b", "value": "11"}, fake_api)
    assert result["changed"] is True
    assert _calls(fake_api, "PATCH")[0]["body"] == {"value": 11}


def test_string_bool_coerced_for_boolean_setting(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=True, default=False, value_type="boolean"))
    assert run_module(setting_module.main, {"name": "a.b", "value": "TRUE"}, fake_api)["changed"] is False
    fake_api.add("PATCH", BASE + "/a.b", 200, _s("a.b", value=False, default=False, value_type="boolean"))
    run_module(setting_module.main, {"name": "a.b", "value": "false"}, fake_api)
    assert _calls(fake_api, "PATCH")[0]["body"] == {"value": False}


def test_noop_diff_is_empty(fake_api):
    fake_api.add("GET", BASE + "/a.b", 200, _s("a.b", value=5))
    result = run_module(setting_module.main, {"name": "a.b", "value": 5, "_ansible_diff": True}, fake_api)
    assert result["diff"] == {"before": {}, "after": {}}


def test_empty_name_fails(fake_api):
    with pytest.raises(AnsibleFailJson) as exc:
        run_module(setting_module.main, {"name": "", "value": 1}, fake_api)
    assert exc.value.kwargs["msg"] == "name must not be empty"
